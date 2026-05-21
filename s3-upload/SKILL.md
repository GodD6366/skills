---
name: s3-upload
description: Use when a task needs to upload one or more local files to AWS S3 or any S3-compatible object storage, including privately deployed MinIO. Supports custom endpoints, path-style access, metadata, public or private objects, and deterministic uploads through the bundled script.
---

# S3 Upload

## Overview

Use this skill to upload local files into S3-compatible object storage from the Codex environment.
It is appropriate for AWS S3, private MinIO deployments, and other S3-compatible services that expose an endpoint, bucket, credentials, and object key.

## When to Use

Use this skill when the user asks to:

- upload build artifacts, logs, screenshots, exports, or backups to object storage
- send files to a self-hosted MinIO server
- place files into a bucket with a specific key or prefix
- upload files with S3-compatible credentials and a custom endpoint
- set metadata, content type, or object visibility during upload

Do not use this skill for browser-based file uploads to web apps. Use a browser or computer-use workflow for those.

## Workflow

1. Confirm the local file path exists.
2. Gather upload settings:
   - bucket
   - key or key prefix
   - endpoint URL for MinIO or other private S3-compatible service
   - region if required
   - access key and secret key
   - optional session token
3. Prefer environment variables for secrets instead of placing secrets in the prompt when possible.
4. Run `scripts/upload_s3.py`.
5. Report the resulting `s3://bucket/key` plus the HTTPS URL when available.

## Quick Start

### Upload one file to AWS S3

```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
python3 "$CLAUDE_SKILL_DIR/scripts/upload_s3.py" \
  --file /path/to/report.csv \
  --bucket my-bucket \
  --key exports/report.csv \
  --region us-east-1
```

### Upload one file to private MinIO

```bash
export AWS_ACCESS_KEY_ID="minioadmin"
export AWS_SECRET_ACCESS_KEY="minioadmin"
python3 "$CLAUDE_SKILL_DIR/scripts/upload_s3.py" \
  --file /path/to/archive.tar.gz \
  --bucket backups \
  --key nightly/archive.tar.gz \
  --endpoint https://minio.example.internal \
  --region us-east-1 \
  --path-style
```

### Upload several files under one prefix

```bash
python3 "$CLAUDE_SKILL_DIR/scripts/upload_s3.py" \
  --file /tmp/a.txt \
  --file /tmp/b.txt \
  --bucket my-bucket \
  --prefix batch/2026-05-21/
```

## Script Behavior

The bundled uploader:

- uses only Python standard library
- signs requests with AWS Signature Version 4
- supports AWS S3 and S3-compatible endpoints
- supports both virtual-hosted and path-style addressing
- can set content type, cache control, ACL, and custom metadata
- can run in `--dry-run` mode to validate configuration without uploading

## Addressing Rules

- Default behavior:
  - AWS S3: virtual-hosted style is fine
  - MinIO/private deployments: prefer `--path-style`
- If the endpoint uses an internal hostname, non-wildcard TLS, IP address, or custom port, prefer `--path-style`.
- If the user provides a single object key, use `--key`.
- If the user wants to upload multiple files into the same folder-like location, use `--prefix`.

## Credentials

Supported inputs:

- environment variables:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_SESSION_TOKEN`
  - `AWS_DEFAULT_REGION`
  - `AWS_REGION`
- command-line flags:
  - `--access-key`
  - `--secret-key`
  - `--session-token`
  - `--region`

Prefer env vars when possible so secrets do not get baked into command history.

## Common Commands

### Upload and set content type

```bash
python3 "$CLAUDE_SKILL_DIR/scripts/upload_s3.py" \
  --file ./dist/app.js \
  --bucket static-assets \
  --key web/app.js \
  --content-type application/javascript
```

### Upload as public-read

```bash
python3 "$CLAUDE_SKILL_DIR/scripts/upload_s3.py" \
  --file ./public/logo.png \
  --bucket site-assets \
  --key images/logo.png \
  --acl public-read
```

### Add metadata

```bash
python3 "$CLAUDE_SKILL_DIR/scripts/upload_s3.py" \
  --file ./build.zip \
  --bucket releases \
  --key app/build.zip \
  --metadata commit=abc123 \
  --metadata env=prod
```

## Troubleshooting

- `SignatureDoesNotMatch`
  - verify endpoint, region, clock, access key, and secret key
  - for MinIO, try `--path-style`
- `AccessDenied`
  - verify bucket policy, credentials, and requested ACL
- TLS or hostname mismatch
  - use the correct endpoint and prefer `--path-style`
- Wrong object location
  - check whether `--key` or `--prefix` was used

For configuration details and examples, read `references/configuration.md`.

## Resources

### scripts/upload_s3.py
Deterministic uploader for AWS S3 and S3-compatible endpoints including private MinIO.

### references/
Use `references/configuration.md` for environment variables, examples, and MinIO-specific notes.
