# S3 Upload Configuration Reference

## Required Inputs

At minimum, the uploader needs:

- a local file path
- a bucket name
- either:
  - `--key` for one uploaded object, or
  - `--prefix` for one or more uploaded files
- credentials

## Environment Variables

The script reads these when flags are not provided:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN`
- `AWS_DEFAULT_REGION`
- `AWS_REGION`
- `S3_ENDPOINT_URL`
- `S3_FORCE_PATH_STYLE`

`S3_FORCE_PATH_STYLE=1` or `true` enables path-style addressing by default.

## Command Reference

```bash
python3 scripts/upload_s3.py \
  --file /path/to/file \
  --bucket my-bucket \
  --key some/object/key
```

Important flags:

- `--file PATH` repeatable
- `--bucket NAME`
- `--key KEY`
- `--prefix PREFIX`
- `--endpoint URL`
- `--region REGION`
- `--path-style`
- `--virtual-hosted-style`
- `--access-key VALUE`
- `--secret-key VALUE`
- `--session-token VALUE`
- `--content-type MIME`
- `--cache-control VALUE`
- `--acl VALUE`
- `--metadata key=value` repeatable
- `--dry-run`

## Key vs Prefix

- Use `--key` only when uploading exactly one file.
- Use `--prefix` when uploading many files and preserving each source filename.

Examples:

```bash
# One file, explicit key
--file ./report.pdf --key exports/2026/report.pdf

# Many files, auto-append basename
--file ./a.txt --file ./b.txt --prefix exports/2026-05-21/
```

## MinIO Notes

For private MinIO deployments:

- set `--endpoint`, for example `https://minio.example.internal`
- usually prefer `--path-style`
- keep region consistent with the server configuration; `us-east-1` is a common default

Example:

```bash
export AWS_ACCESS_KEY_ID="minioadmin"
export AWS_SECRET_ACCESS_KEY="minioadmin"
python3 scripts/upload_s3.py \
  --file ./backup.sql.gz \
  --bucket db-backups \
  --key nightly/backup.sql.gz \
  --endpoint https://minio.example.internal:9000 \
  --region us-east-1 \
  --path-style
```

## Output

On success the script prints JSON for each uploaded file, including:

- local path
- bucket
- key
- `s3_uri`
- HTTP status
- object URL when derivable

## Failure Patterns

### Signature mismatch

- wrong secret key
- wrong region
- wrong endpoint host
- wrong path-style setting

### Access denied

- missing put-object permission
- bucket policy denies ACL or metadata
- bucket does not exist for provided credentials

### TLS failure

- endpoint certificate does not match hostname
- internal CA is not trusted in the runtime

If needed, the script can be adapted later for custom CA handling, multipart uploads, or presigned URLs.
