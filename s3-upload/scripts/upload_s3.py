#!/usr/bin/env python3
"""
Upload local files to AWS S3 or any S3-compatible endpoint.

This script intentionally uses only the Python standard library so the skill
works without boto3 or awscli.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_ENV_FILE = SKILL_DIR / ".env"


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def load_dotenv(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_signature_key(secret_key: str, date_stamp: str, region: str, service: str) -> bytes:
    k_date = sign(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    k_region = sign(k_date, region)
    k_service = sign(k_region, service)
    k_signing = sign(k_service, "aws4_request")
    return k_signing


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def normalize_endpoint(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = "https://" + raw
    return raw.rstrip("/")


def _join_url_path(base_path: str, extra_path: str) -> str:
    base = base_path.rstrip("/")
    extra = extra_path.lstrip("/")
    if not base:
        return "/" + extra if extra else "/"
    if not extra:
        return base or "/"
    return f"{base}/{extra}"


def parse_metadata(items: Iterable[str]) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid metadata entry '{item}', expected key=value")
        key, value = item.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if not key:
            raise ValueError(f"Invalid metadata entry '{item}', empty key")
        metadata[key] = value
    return metadata


def guess_content_type(path: Path, override: str | None) -> str:
    if override:
        return override
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


def ensure_args_valid(args: argparse.Namespace) -> None:
    if not args.files:
        raise SystemExit("At least one --file is required")
    if args.key and args.prefix:
        raise SystemExit("Use either --key or --prefix, not both")
    if not args.key and not args.prefix:
        raise SystemExit("One of --key or --prefix is required")
    if args.key and len(args.files) != 1:
        raise SystemExit("--key can only be used with exactly one --file")
    if args.virtual_hosted_style and args.path_style:
        raise SystemExit("Use either --path-style or --virtual-hosted-style, not both")


def collect_credentials(args: argparse.Namespace) -> Tuple[str, str, str | None]:
    access_key = args.access_key or os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = args.secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")
    session_token = args.session_token or os.getenv("AWS_SESSION_TOKEN")
    if not access_key or not secret_key:
        raise SystemExit(
            "Missing credentials. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY "
            "or pass --access-key and --secret-key."
        )
    return access_key, secret_key, session_token


def detect_region(endpoint: str | None, bucket: str, path_style: bool) -> str | None:
    candidates: List[str] = []

    if endpoint:
        parsed = urllib.parse.urlparse(endpoint)
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc or parsed.path
        base_path = parsed.path.rstrip("/")
        candidates.append(f"{scheme}://{netloc}{base_path or '/'}")
        if path_style:
            candidates.append(f"{scheme}://{netloc}{_join_url_path(base_path, bucket)}")
        else:
            candidates.append(f"{scheme}://{bucket}.{netloc}{base_path or '/'}")
    else:
        candidates.append(f"https://{bucket}.s3.amazonaws.com/")
        candidates.append("https://s3.amazonaws.com/")

    opener = urllib.request.build_opener()
    for url in candidates:
        req = urllib.request.Request(url=url, method="HEAD")
        try:
            with opener.open(req, timeout=10) as resp:
                region = resp.headers.get("x-amz-bucket-region")
                if region:
                    return region
        except urllib.error.HTTPError as exc:
            region = exc.headers.get("x-amz-bucket-region")
            if region:
                return region
        except Exception:
            continue
    return None


def collect_region(args: argparse.Namespace, endpoint: str | None, bucket: str, path_style: bool) -> str:
    region_arg = args.region
    env_region = os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION")

    if region_arg and region_arg.strip().lower() != "auto":
        return region_arg.strip()
    if env_region and (not region_arg or region_arg.strip().lower() != "auto"):
        return env_region

    detected = detect_region(endpoint, bucket, path_style)
    if detected:
        return detected
    return "us-east-1"


def determine_path_style(args: argparse.Namespace, endpoint: str | None) -> bool:
    if args.path_style:
        return True
    if args.virtual_hosted_style:
        return False
    env_force = parse_bool(os.getenv("S3_FORCE_PATH_STYLE"), default=False)
    if env_force:
        return True
    if endpoint:
        # Custom endpoints often work more reliably with path-style, especially MinIO.
        return True
    return False


def build_target_url(
    bucket: str,
    key: str,
    endpoint: str | None,
    path_style: bool,
    region: str,
) -> Tuple[str, str, str]:
    encoded_key = urllib.parse.quote(key.lstrip("/"), safe="/~")
    if endpoint:
        parsed = urllib.parse.urlparse(endpoint)
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc or parsed.path
        base_path = parsed.path.rstrip("/")
        if path_style:
            url = f"{scheme}://{netloc}{base_path}/{bucket}/{encoded_key}"
            host = netloc
            canonical_uri = f"{base_path}/{bucket}/{encoded_key}" or f"/{bucket}/{encoded_key}"
        else:
            url = f"{scheme}://{bucket}.{netloc}{base_path}/{encoded_key}"
            host = f"{bucket}.{netloc}"
            canonical_uri = f"{base_path}/{encoded_key}" or f"/{encoded_key}"
        return url, host, canonical_uri

    aws_host = "s3.amazonaws.com" if region == "us-east-1" else f"s3.{region}.amazonaws.com"
    host = f"{bucket}.{aws_host}"
    if path_style:
        url = f"https://{aws_host}/{bucket}/{encoded_key}"
        host = aws_host
        canonical_uri = f"/{bucket}/{encoded_key}"
    else:
        url = f"https://{host}/{encoded_key}"
        canonical_uri = f"/{encoded_key}"
    return url, host, canonical_uri


def build_headers(
    *,
    host: str,
    content_sha256: str,
    content_type: str,
    cache_control: str | None,
    acl: str | None,
    metadata: Dict[str, str],
    session_token: str | None,
    timestamp: str,
) -> Dict[str, str]:
    headers = {
        "host": host,
        "x-amz-content-sha256": content_sha256,
        "x-amz-date": timestamp,
        "content-type": content_type,
    }
    if cache_control:
        headers["cache-control"] = cache_control
    if acl:
        headers["x-amz-acl"] = acl
    if session_token:
        headers["x-amz-security-token"] = session_token
    for key, value in metadata.items():
        headers[f"x-amz-meta-{key}"] = value
    return headers


def canonicalize_headers(headers: Dict[str, str]) -> Tuple[str, str]:
    items = sorted((k.lower().strip(), " ".join(v.strip().split())) for k, v in headers.items())
    canonical_headers = "".join(f"{k}:{v}\n" for k, v in items)
    signed_headers = ";".join(k for k, _ in items)
    return canonical_headers, signed_headers


def build_authorization(
    *,
    method: str,
    canonical_uri: str,
    canonical_querystring: str,
    headers: Dict[str, str],
    payload_hash: str,
    access_key: str,
    secret_key: str,
    region: str,
    service: str,
    amz_date: str,
    date_stamp: str,
) -> str:
    canonical_headers, signed_headers = canonicalize_headers(headers)
    canonical_request = "\n".join(
        [
            method,
            canonical_uri,
            canonical_querystring,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )

    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            sha256_hex(canonical_request.encode("utf-8")),
        ]
    )
    signing_key = get_signature_key(secret_key, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    return (
        "AWS4-HMAC-SHA256 "
        f"Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )


def upload_one(
    *,
    file_path: Path,
    bucket: str,
    key: str,
    endpoint: str | None,
    region: str,
    path_style: bool,
    access_key: str,
    secret_key: str,
    session_token: str | None,
    acl: str | None,
    cache_control: str | None,
    content_type_override: str | None,
    metadata: Dict[str, str],
    dry_run: bool,
) -> Dict[str, object]:
    body = file_path.read_bytes()
    payload_hash = sha256_hex(body)
    url, host, canonical_uri = build_target_url(bucket, key, endpoint, path_style, region)
    content_type = guess_content_type(file_path, content_type_override)

    now = dt.datetime.now(dt.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    headers = build_headers(
        host=host,
        content_sha256=payload_hash,
        content_type=content_type,
        cache_control=cache_control,
        acl=acl,
        metadata=metadata,
        session_token=session_token,
        timestamp=amz_date,
    )
    authorization = build_authorization(
        method="PUT",
        canonical_uri=canonical_uri,
        canonical_querystring="",
        headers=headers,
        payload_hash=payload_hash,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        service="s3",
        amz_date=amz_date,
        date_stamp=date_stamp,
    )

    final_headers = {k.title(): v for k, v in headers.items()}
    final_headers["Authorization"] = authorization
    final_headers["Content-Length"] = str(len(body))

    result = {
        "file": str(file_path),
        "bucket": bucket,
        "key": key,
        "size_bytes": len(body),
        "content_type": content_type,
        "endpoint": endpoint or "https://s3.amazonaws.com",
        "path_style": path_style,
        "s3_uri": f"s3://{bucket}/{key}",
        "url": url,
    }

    if dry_run:
        result["dry_run"] = True
        return result

    req = urllib.request.Request(url=url, data=body, method="PUT")
    for k, v in final_headers.items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req) as resp:
            response_body = resp.read().decode("utf-8", errors="replace")
            result["status"] = resp.status
            result["etag"] = resp.headers.get("ETag")
            result["response"] = response_body
            return result
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Upload failed for {file_path} -> s3://{bucket}/{key}: "
            f"HTTP {exc.code}\n{response_body}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Upload failed for {file_path} -> s3://{bucket}/{key}: {exc.reason}"
        ) from exc


def main() -> int:
    load_dotenv(SKILL_ENV_FILE)
    parser = argparse.ArgumentParser(
        description="Upload local files to AWS S3 or S3-compatible object storage.",
    )
    parser.add_argument("--file", dest="files", action="append", help="Local file path. Repeatable.")
    parser.add_argument("--bucket", required=True, help="Bucket name.")
    parser.add_argument("--key", help="Object key. Only valid when uploading exactly one file.")
    parser.add_argument(
        "--prefix",
        help="Object key prefix for one or more files. Each uploaded file uses prefix + basename(file).",
    )
    parser.add_argument("--endpoint", default=os.getenv("S3_ENDPOINT_URL"), help="Custom S3 endpoint URL.")
    parser.add_argument(
        "--region",
        help="AWS region. Use 'auto' to probe x-amz-bucket-region when possible.",
    )
    parser.add_argument("--path-style", action="store_true", help="Force path-style addressing.")
    parser.add_argument(
        "--virtual-hosted-style",
        action="store_true",
        help="Force virtual-hosted style addressing.",
    )
    parser.add_argument("--access-key", help="Access key. Defaults to AWS_ACCESS_KEY_ID.")
    parser.add_argument("--secret-key", help="Secret key. Defaults to AWS_SECRET_ACCESS_KEY.")
    parser.add_argument("--session-token", help="Session token. Defaults to AWS_SESSION_TOKEN.")
    parser.add_argument("--content-type", help="Override MIME type.")
    parser.add_argument("--cache-control", help="Set Cache-Control header.")
    parser.add_argument("--acl", help="Optional canned ACL, for example private or public-read.")
    parser.add_argument("--metadata", action="append", default=[], help="Custom metadata key=value. Repeatable.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print planned upload JSON without uploading.")
    args = parser.parse_args()

    ensure_args_valid(args)

    files = [Path(p).expanduser().resolve() for p in args.files]
    missing = [str(p) for p in files if not p.exists() or not p.is_file()]
    if missing:
        raise SystemExit("Missing or non-file paths:\n" + "\n".join(missing))

    metadata = parse_metadata(args.metadata)
    access_key, secret_key, session_token = collect_credentials(args)
    endpoint = normalize_endpoint(args.endpoint)
    path_style = determine_path_style(args, endpoint)
    region = collect_region(args, endpoint, args.bucket, path_style)

    uploads: List[Dict[str, object]] = []
    prefix = args.prefix or ""
    if prefix and not prefix.endswith("/"):
        prefix = prefix + "/"

    for file_path in files:
        key = args.key if args.key else prefix + file_path.name
        result = upload_one(
            file_path=file_path,
            bucket=args.bucket,
            key=key,
            endpoint=endpoint,
            region=region,
            path_style=path_style,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            acl=args.acl,
            cache_control=args.cache_control,
            content_type_override=args.content_type,
            metadata=metadata,
            dry_run=args.dry_run,
        )
        uploads.append(result)

    print(json.dumps(uploads, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        eprint(f"Error: {exc}")
        raise SystemExit(2)
    except RuntimeError as exc:
        eprint(str(exc))
        raise SystemExit(1)
