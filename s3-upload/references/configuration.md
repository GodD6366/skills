# S3 上传配置参考

## 必填输入

上传脚本至少需要以下信息：

- 本地文件路径
- bucket 名称
- 以下二选一：
  - `--key`：上传为单个对象
  - `--prefix`：上传一个或多个文件
- 凭证

## 环境变量

当命令行参数未提供时，脚本会读取以下环境变量：

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN`
- `AWS_DEFAULT_REGION`
- `AWS_REGION`
- `S3_ENDPOINT_URL`
- `S3_FORCE_PATH_STYLE`

设置 `S3_FORCE_PATH_STYLE=1` 或 `true` 时，会默认启用 path-style 寻址。

## 命令参考

```bash
python3 scripts/upload_s3.py \
  --file /path/to/file \
  --bucket my-bucket \
  --key some/object/key
```

重要参数：

- `--file PATH`，可重复使用
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
- `--metadata key=value`，可重复使用
- `--dry-run`

## key 与 prefix 的区别

- 只有在上传恰好一个文件时，才使用 `--key`。
- 当需要上传多个文件，并保留各自原始文件名时，使用 `--prefix`。

示例：

```bash
# 单个文件，显式指定 key
--file ./report.pdf --key exports/2026/report.pdf

# 多个文件，自动追加各自 basename
--file ./a.txt --file ./b.txt --prefix exports/2026-05-21/
```

## MinIO 说明

对于私有 MinIO 部署：

- 设置 `--endpoint`，例如 `https://minio.example.internal`
- 通常优先使用 `--path-style`
- region 要与服务端配置保持一致；`us-east-1` 是常见默认值

示例：

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

## 输出

上传成功后，脚本会为每个文件输出一段 JSON，包含：

- 本地路径
- bucket
- key
- `s3_uri`
- HTTP 状态码
- 如果可推导，则包含对象 URL

## 常见失败模式

### 签名不匹配

可能原因：

- secret key 错误
- region 错误
- endpoint 主机错误
- path-style 设置不正确

### 权限被拒绝

可能原因：

- 缺少 put-object 权限
- bucket policy 禁止设置 ACL 或 metadata
- 当前凭证下 bucket 不存在

### TLS 失败

可能原因：

- endpoint 证书与主机名不匹配
- 运行环境不信任内部 CA

如果后续需要，也可以继续扩展脚本以支持自定义 CA、多段上传或预签名 URL。
