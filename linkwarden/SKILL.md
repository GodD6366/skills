---
name: use-linkwarden
description: 通过 Linkwarden API 管理自托管的书签服务，支持链接、集合、标签的增删改查操作
---

# Linkwarden API Skill

通过 HTTP API 与 Linkwarden 自托管书签服务交互，实现链接管理自动化。

## 前置条件

1. **Linkwarden 实例**：需要一个运行中的 Linkwarden 实例（自托管或 linkwarden.app）
2. **API Token**：在 Linkwarden 设置中创建 API Token

## 环境变量配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `LINKWARDEN_BASE_URL` | Linkwarden 实例地址 | `https://your-linkwarden-instance.com` |
| `LINKWARDEN_API_TOKEN` | API Token | `your_api_token_here` |

### 配置方式

**方式一：`.env` 文件（推荐）**

在当前 skill 目录下创建 `.env` 文件：

```bash
LINKWARDEN_BASE_URL=https://your-linkwarden-instance.com
LINKWARDEN_API_TOKEN=your_api_token_here
```

**方式二：环境变量**

```bash
export LINKWARDEN_BASE_URL=https://your-linkwarden-instance.com
export LINKWARDEN_API_TOKEN=your_api_token_here
```

### 优先级

环境变量优先级：**已有环境变量 > `.env` 文件 > 默认值**

脚本启动时会自动读取当前 skill 目录下的 `.env`（如果存在），仅在对应环境变量**尚未设置**时作为默认值注入。

### 配置落盘

当用户在会话中首次提供配置时：
1. 明确询问用户是否写入当前 skill 目录下的 `.env`
2. 只有在用户同意后，才可以落盘保存
3. 写入时避免覆盖已有配置项

## 认证方式

所有 API 请求需要在 Header 中携带 Bearer Token：

```
Authorization: Bearer <your_api_token>
```

## API 基础信息

| 项目 | 值 |
|------|-----|
| Base URL | `{LINKWARDEN_BASE_URL}/api/v1` |
| 认证方式 | HTTP Bearer Auth (JWT) |
| 响应格式 | JSON |

---

## 核心资源端点

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
  "collection": {
    "id": 1
  },
  "tags": [
    { "name": "技术" },
    { "name": "教程" }
  ]
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

---

## 其他功能端点

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| Dashboard | GET | `/dashboard` | 获取仪表板数据 |
| Archives | GET | `/archives/{id}` | 获取归档文件 |
| Preserved | POST | `/preserved` | 创建短时保留格式 URL |
| Highlights | POST | `/highlights` | 创建/更新高亮标注 |
| Search | GET | `/search` | 搜索链接 |
| Favicon | GET | `/favicon` | 获取网站 Favicon |
| RSS | GET | `/rss` | 列出 RSS 订阅 |
| Config | GET | `/config` | 获取运行时配置 |
| Users | GET | `/users` | 获取用户列表 |
| Tokens | GET | `/tokens` | 获取 API Token 列表 |
| Tokens | POST | `/tokens` | 创建新 Token |
| Tokens | DELETE | `/tokens/{id}` | 撤销 Token |

---

## 响应格式

### 成功响应
```json
{
  "response": {
    "data": { ... },
    "status": 200
  }
}
```

### 错误响应
```json
{
  "response": {
    "message": "错误描述",
    "status": 401
  }
}
```

---

## 使用示例

### 创建链接
```bash
curl -X POST "${LINKWARDEN_BASE_URL}/api/v1/links" \
  -H "Authorization: Bearer ${LINKWARDEN_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "name": "示例链接",
    "collection": { "id": 1 },
    "tags": [{ "name": "技术" }]
  }'
```

### 获取所有集合
```bash
curl -X GET "${LINKWARDEN_BASE_URL}/api/v1/collections" \
  -H "Authorization: Bearer ${LINKWARDEN_API_TOKEN}"
```

### 搜索链接
```bash
curl -X GET "${LINKWARDEN_BASE_URL}/api/v1/search?q=关键词" \
  -H "Authorization: Bearer ${LINKWARDEN_API_TOKEN}"
```

---

## 注意事项

1. **认证**：所有端点（除 Public 和 Config 外）都需要 Bearer Token 认证
2. **分页**：部分端点（如 Tags）支持分页，注意处理分页参数
3. **错误处理**：遇到 401 错误时检查 Token 是否有效或过期
4. **Base URL**：确保 `LINKWARDEN_BASE_URL` 不包含尾部斜杠

## 参考文档

- 官方文档：https://docs.linkwarden.app/api/api-introduction
- GitHub：https://github.com/linkwarden/linkwarden
