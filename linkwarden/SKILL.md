---
name: use-linkwarden
description: 通过 Linkwarden API 管理自托管的书签服务，支持链接、集合、标签的增删改查操作
---

# Linkwarden 书签管理

## 概述

通过命令行工具与 Linkwarden 自托管书签服务交互，实现链接管理自动化。
适用于批量收藏网页、整理书签分类、搜索历史收藏等场景。

## 适用场景

当用户提出以下需求时使用这个 Skill：

- 保存/收藏一个或多个网页链接到 Linkwarden
- 创建、编辑、删除链接
- 搜索已收藏的链接
- 管理链接集合（文件夹）和标签
- 批量整理书签分类
- 归档链接内容
- 查看仪表板统计数据

不要把这个 Skill 用于浏览器内直接操作 Linkwarden Web 界面；这类任务应改用 browser-use 工作流。

## 工作流程

1. 确认环境变量 `LINKWARDEN_BASE_URL` 和 `LINKWARDEN_API_TOKEN` 已配置。
2. 如果未配置，通过交互式弹窗引导用户输入，或提示用户在 skill 目录下创建 `.env` 文件。
3. 如果用户在本次会话中提供了可复用的配置，主动询问是否要持久化到 `.env`，避免后续重复询问。
4. 运行 `scripts/linkwarden.py` 执行操作。
5. 返回操作结果。

## 快速开始

### 前置条件

1. 运行中的 Linkwarden 实例（自托管或 linkwarden.app）
2. 在 Linkwarden 设置中创建 API Token

### 环境变量配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `LINKWARDEN_BASE_URL` | Linkwarden 实例地址 | `https://your-linkwarden-instance.com` |
| `LINKWARDEN_API_TOKEN` | API Token | `your_api_token_here` |

**配置方式**

1. **交互式弹窗（优先）**：如果工具支持交互式弹窗（如 `AskUserQuestion`），优先通过弹窗引导用户输入配置。

2. **`.env` 文件**：在当前 skill 目录下创建 `.env` 文件：

```bash
LINKWARDEN_BASE_URL=https://your-linkwarden-instance.com
LINKWARDEN_API_TOKEN=your_api_token_here
```

3. **环境变量**：

```bash
export LINKWARDEN_BASE_URL=https://your-linkwarden-instance.com
export LINKWARDEN_API_TOKEN=your_api_token_here
```

**优先级**：已有环境变量 > `.env` 文件 > 默认值

脚本启动时会自动读取当前 skill 目录下的 `.env`（如果存在），仅在对应环境变量**尚未设置**时作为默认值注入。

**配置落盘**：当用户在会话中首次提供配置时，一次性询问所有必填字段（Base URL、API Token、是否保存到 .env），用户确认后统一写入，写入时避免覆盖已有配置项。

---

## 命令行工具使用

脚本路径：`scripts/linkwarden.py`

### 链接管理

```bash
# 获取链接列表
python3 scripts/linkwarden.py links list

# 获取单个链接
python3 scripts/linkwarden.py links get <id>

# 创建链接
python3 scripts/linkwarden.py links create --url https://example.com --name "示例链接" --tags "技术,教程" --collection-id 1

# 更新链接
python3 scripts/linkwarden.py links update <id> --name "新名称" --tags "新标签"

# 删除链接
python3 scripts/linkwarden.py links delete <id>

# 搜索链接
python3 scripts/linkwarden.py links search --query "关键词"

# 归档链接
python3 scripts/linkwarden.py links archive <id>
```

### 集合管理

```bash
# 获取所有集合
python3 scripts/linkwarden.py collections list

# 获取单个集合
python3 scripts/linkwarden.py collections get <id>

# 创建集合
python3 scripts/linkwarden.py collections create --name "我的收藏" --description "描述"

# 更新集合
python3 scripts/linkwarden.py collections update <id> --name "新名称"

# 删除集合
python3 scripts/linkwarden.py collections delete <id>
```

### 标签管理

```bash
# 获取标签列表
python3 scripts/linkwarden.py tags list

# 获取单个标签
python3 scripts/linkwarden.py tags get <id>

# 批量创建标签
python3 scripts/linkwarden.py tags create --names "标签1,标签2,标签3"

# 更新标签
python3 scripts/linkwarden.py tags update <id> --name "新标签名"

# 删除标签
python3 scripts/linkwarden.py tags delete <id>
```

### 其他功能

```bash
# 获取仪表板数据
python3 scripts/linkwarden.py dashboard get

# 获取运行时配置
python3 scripts/linkwarden.py config get
```

---

## API 端点参考

### Links（链接）

| 操作 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 获取链接列表 | GET | `/links` | 获取所有链接 |
| 获取单个链接 | GET | `/links/{id}` | 根据 ID 获取链接 |
| 创建链接 | POST | `/links` | 创建新链接（支持 tags 和 collection） |
| 更新链接 | PUT | `/links/{id}` | 更新链接信息 |
| 批量更新 | PUT | `/links/bulk` | 批量更新多个链接 |
| 删除链接 | DELETE | `/links/{id}` | 删除单个链接 |
| 批量删除 | DELETE | `/links` | 批量删除链接 |
| 归档链接 | POST | `/links/{id}/archive` | 归档链接 |
| 搜索链接 | GET | `/search` | 根据查询参数搜索链接 |
| 获取链接高亮 | GET | `/links/{id}/highlights` | 获取链接的高亮标注 |

**创建链接请求体示例：**

```json
{
  "url": "https://example.com",
  "name": "示例链接",
  "description": "这是一个示例链接",
  "collection": { "id": 1 },
  "tags": [{ "name": "技术" }, { "name": "教程" }]
}
```

### Collections（集合）

| 操作 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 获取所有集合 | GET | `/collections` | 获取用户的所有集合 |
| 获取单个集合 | GET | `/collections/{id}` | 根据 ID 获取集合 |
| 创建集合 | POST | `/collections` | 创建新集合 |
| 更新集合 | PUT | `/collections/{id}` | 更新集合信息 |
| 删除集合 | DELETE | `/collections/{id}` | 删除集合 |

### Tags（标签）

| 操作 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 获取标签列表 | GET | `/tags` | 分页获取标签列表 |
| 获取单个标签 | GET | `/tags/{id}` | 根据 ID 获取标签 |
| 批量创建/更新 | POST | `/tags` | 批量创建或更新标签 |
| 更新标签 | PUT | `/tags/{id}` | 更新标签 |
| 删除标签 | DELETE | `/tags/{id}` | 删除单个标签 |
| 批量删除 | DELETE | `/tags` | 批量删除标签 |

### 其他端点

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| Dashboard | GET | `/dashboard` | 获取仪表板数据 |
| Archives | GET | `/archives/{id}` | 获取归档文件 |
| Preserved | POST | `/preserved` | 创建短时保留格式 URL |
| Highlights | POST | `/highlights` | 创建/更新高亮标注 |
| Favicon | GET | `/favicon` | 获取网站 Favicon |
| RSS | GET | `/rss` | 列出 RSS 订阅 |
| Config | GET | `/config` | 获取运行时配置 |
| Users | GET | `/users` | 获取用户列表 |
| Tokens | GET/POST/DELETE | `/tokens` | Token 管理 |

---

## 响应格式

```json
{
  "response": {
    "data": { ... },
    "status": 200
  }
}
```

错误响应：

```json
{
  "response": {
    "message": "错误描述",
    "status": 401
  }
}
```

## 注意事项

1. **认证**：所有端点（除 Public 和 Config 外）都需要 Bearer Token 认证
2. **分页**：部分端点（如 Tags）支持分页，注意处理分页参数
3. **错误处理**：遇到 401 错误时检查 Token 是否有效或过期
4. **Base URL**：确保 `LINKWARDEN_BASE_URL` 不包含尾部斜杠

## 参考文档

- 官方文档：https://docs.linkwarden.app/api/api-introduction
- GitHub：https://github.com/linkwarden/linkwarden
