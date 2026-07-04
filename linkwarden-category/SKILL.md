---
name: linkwarden-category
description: 使用 Linkwarden API 和本地脚本管理书签自动整理、分类与标签化。LLM 驱动，脚本只提供数据接口。
---

# Linkwarden 书签分类（LLM 驱动）

## 概述

脚本只负责数据查询和写入，**所有分类决策由 LLM 完成**。脚本不包含任何关键词匹配或兜底逻辑。

## 适用场景

- 自动整理未分类书签
- 根据书签内容决定归属收藏夹和标签
- 修改或复用 Linkwarden 自动化脚本
- 读取 Linkwarden API 配置位置

## 凭证

支持以下环境变量配置 Linkwarden 接口：
- `LINKWARDEN_URL` - Linkwarden 服务地址（例如：`https://link.example.com:6443`）
- `LINKWARDEN_API_TOKEN` - API 访问令牌

### 配置方式

1. **`.env` 文件**：在当前 skill 目录下创建 `.env` 文件。
2. **环境变量**：通过 `export` 设置。

### 优先级

环境变量优先级：**已有环境变量 > `.env` 文件 > 默认值**

脚本启动时会自动读取当前 skill 目录下的 `.env`（如果存在），仅在对应环境变量**尚未设置**时作为默认值注入。

### 配置落盘

当用户在会话中首次提供配置时，一次性询问所有必填字段（URL、API Token、是否保存到 .env），用户确认后统一写入，写入时避免覆盖已有配置项。

## 工作流程

### 初始化（首次运行）

```bash
python3 scripts/auto_organize.py init
```

创建默认收藏夹（AI、编程、自托管、折腾、工具、网络、阅读、其他）和默认标签。

### 日常分类流程

1. 运行 `python3 scripts/auto_organize.py list` 获取未分类书签（JSON 输出）
2. 运行 `python3 scripts/auto_organize.py list-collections` 获取所有收藏夹
3. 运行 `python3 scripts/auto_organize.py list-tags` 获取所有标签
4. **LLM 根据书签内容，决定每个书签应归属的收藏夹和标签**
5. 运行 `python3 scripts/auto_organize.py update <link_id> --collection-id <id> --tags "tag1,tag2"` 更新每个书签

### 状态查询

```bash
python3 scripts/auto_organize.py summary
```

## 命令行工具

脚本路径：`scripts/auto_organize.py`

| 命令 | 说明 |
|------|------|
| `init` | 初始化默认收藏夹和标签 |
| `list [--limit N]` | 列出未分类书签（JSON） |
| `list-collections` | 列出所有收藏夹 |
| `list-tags` | 列出所有标签 |
| `update <id> --collection-id <id> [--tags "t1,t2"]` | 更新书签分类 |
| `summary` | 分类状态摘要 |

## 注意事项

- 脚本不包含关键词匹配逻辑，所有分类由 LLM 决定
- 收藏夹和标签由 LLM 按需创建，脚本不预设分类规则
- 凭证默认不明文记录
- 不要通过浏览器操作 Linkwarden Web 界面，使用此脚本的 API 接口

## 参考文件

- `scripts/auto_organize.py` - 分类工具脚本
- `.env` - 环境变量配置（需用户自行创建）
