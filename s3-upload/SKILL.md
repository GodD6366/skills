---
name: s3-upload
description: 当任务需要把一个或多个本地文件上传到 AWS S3 或任意兼容 S3 的对象存储时使用，包括私有部署的 MinIO。支持自定义 endpoint、path-style 访问、metadata、公有或私有对象，以及通过内置脚本进行可重复、确定性的上传。
---

# S3 上传

## 概述

在 Codex 环境中把本地文件上传到兼容 S3 的对象存储时，使用这个 Skill。
适用于 AWS S3、私有 MinIO 部署，以及其他提供 endpoint、bucket、凭证和对象 key 的 S3 兼容服务。

## 适用场景

当用户提出以下需求时使用这个 Skill：

- 将构建产物、日志、截图、导出文件或备份上传到对象存储
- 将文件发送到自托管 MinIO 服务
- 把文件上传到指定 bucket，并指定对象 key 或前缀
- 使用 S3 兼容凭证和自定义 endpoint 上传文件
- 在上传时设置 metadata、content type 或对象可见性

不要把这个 Skill 用于网页应用里的浏览器文件上传；这类任务应改用浏览器或 computer-use 工作流。

## 工作流程

1. 确认本地文件路径存在。
2. 收集上传参数：
   - bucket
   - key 或 key 前缀
   - MinIO 或其他私有 S3 兼容服务的 endpoint URL
   - region（如果需要）
   - access key 和 secret key
   - 可选的 session token
3. 如果用户在本次会话中提供了可复用的 S3 配置（如 endpoint、bucket、region、access key、secret key、session token、path-style 偏好），主动询问是否要持久化到当前 skill 目录下的 `.env`，避免后续类似场景重复询问。
4. 尽量通过环境变量或 skill 目录下的 `.env` 提供密钥，不要直接把密钥写进 prompt。
5. 运行 `scripts/upload_s3.py`。
6. 返回生成的 `s3://bucket/key`，以及可用时的 HTTPS URL。

## 快速开始

### 上传单个文件到 AWS S3

```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
python3 "$CLAUDE_SKILL_DIR/scripts/upload_s3.py" \
  --file /path/to/report.csv \
  --bucket my-bucket \
  --key exports/report.csv \
  --region us-east-1
```

### 上传单个文件到私有 MinIO

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

### 将多个文件上传到同一个前缀下

```bash
python3 "$CLAUDE_SKILL_DIR/scripts/upload_s3.py" \
  --file /tmp/a.txt \
  --file /tmp/b.txt \
  --bucket my-bucket \
  --prefix batch/2026-05-21/
```

## 脚本能力

内置上传脚本具有以下特点：

- 仅使用 Python 标准库
- 使用 AWS Signature Version 4 进行签名
- 支持 AWS S3 和兼容 S3 的 endpoint
- 同时支持 virtual-hosted 和 path-style 两种寻址方式
- 可设置 content type、cache control、ACL 和自定义 metadata
- 支持 `--dry-run`，可在不上传的情况下校验配置

## 寻址规则

- 默认行为：
  - AWS S3：可以优先使用 virtual-hosted style
  - MinIO / 私有部署：优先使用 `--path-style`
- 如果 endpoint 使用内网主机名、非通配 TLS、IP 地址或自定义端口，优先使用 `--path-style`。
- 如果用户提供的是单个对象 key，使用 `--key`。
- 如果用户希望把多个文件上传到同一个“目录式”位置，使用 `--prefix`。

## 凭证

支持以下输入方式：

- 环境变量：
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_SESSION_TOKEN`
  - `AWS_DEFAULT_REGION`
  - `AWS_REGION`
- 命令行参数：
  - `--access-key`
  - `--secret-key`
  - `--session-token`
  - `--region`

### 配置方式

1. **交互式弹窗（优先）**：如果工具支持交互式弹窗（如 `AskUserQuestion`），优先通过弹窗引导用户输入配置，一次性询问所有必填字段。
2. **`.env` 文件**：在当前 skill 目录下创建 `.env` 文件。
3. **环境变量**：通过 `export` 设置。

### 优先级

环境变量优先级：**已有环境变量 > `.env` 文件 > 默认值**

脚本启动时会自动读取当前 skill 目录下的 `.env`（如果存在），仅在对应环境变量**尚未设置**时作为默认值注入。

如无必要，优先使用环境变量，避免密钥进入 shell 历史记录。

### 配置落盘

当用户在会话中首次提供配置时，一次性询问所有必填字段（Endpoint、Bucket、Access Key、Secret Key、Region、是否保存到 .env 等），用户确认后统一写入，写入时避免覆盖已有配置项。

## 常用命令

### 上传并设置 content type

```bash
python3 "$CLAUDE_SKILL_DIR/scripts/upload_s3.py" \
  --file ./dist/app.js \
  --bucket static-assets \
  --key web/app.js \
  --content-type application/javascript
```

### 以 public-read 上传

```bash
python3 "$CLAUDE_SKILL_DIR/scripts/upload_s3.py" \
  --file ./public/logo.png \
  --bucket site-assets \
  --key images/logo.png \
  --acl public-read
```

### 添加 metadata

```bash
python3 "$CLAUDE_SKILL_DIR/scripts/upload_s3.py" \
  --file ./build.zip \
  --bucket releases \
  --key app/build.zip \
  --metadata commit=abc123 \
  --metadata env=prod
```

## 故障排查

- `SignatureDoesNotMatch`
  - 检查 endpoint、region、系统时间、access key 和 secret key
  - 如果是 MinIO，尝试 `--path-style`
- `AccessDenied`
  - 检查 bucket policy、凭证权限，以及请求的 ACL 是否被允许
- TLS 或主机名不匹配
  - 使用正确的 endpoint，并优先尝试 `--path-style`
- 对象上传到了错误位置
  - 检查使用的是 `--key` 还是 `--prefix`

如需查看更详细的配置说明和示例，读取 `references/configuration.md`。

## 资源

### scripts/upload_s3.py
适用于 AWS S3 和兼容 S3 endpoint（包括私有 MinIO）的确定性上传脚本。

### references/
使用 `references/configuration.md` 查看环境变量、命令示例和 MinIO 专项说明。
