---
name: linkwarden-category
description: 使用 Linkwarden API 和本地脚本管理书签自动整理、分类与标签化。
---

# Linkwarden

用于操作 Linkwarden 实例，尤其是书签自动分类脚本和相关配置。

## 适用场景

- 自动整理未分类书签
- 根据关键词映射收藏夹与标签
- 修改或复用 Linkwarden 自动化脚本
- 读取 Linkwarden API 配置位置

## 凭证

支持以下环境变量配置 Linkwarden 接口：
- `LINKWARDEN_URL` - Linkwarden 服务地址（例如：`https://link.example.com:6443`）
- `LINKWARDEN_API_TOKEN` - API 访问令牌

脚本启动时会自动读取当前 skill 目录下的 `.env`（如果存在），并仅在对应环境变量尚未设置时作为默认值注入。适合保存常用的接口配置，减少重复输入。

当用户在当前会话里首次提供一套可复用配置时，应明确询问是否写入当前 skill 目录下的 `.env`。只有在用户同意后，才可以落盘保存。

## 工作流程

1. 先读取脚本与配置，确认当前映射和 API 参数。
2. 如需调整分类逻辑，优先改脚本中的关键词映射，再验证脚本行为。
3. 不要明文泄露凭证；如果需要展示敏感配置，只说明位置，不直接回显 token。
4. 修改后应验证脚本语法或运行结果。

## 注意事项

- Linkwarden 自动整理会同时更新收藏夹和标签。
- "其他"收藏夹用于无法自动匹配的书签。
- 凭证默认不明文记录。

## 参考文件

- `scripts/auto_organize.py` - 自动分类脚本
- `.env` - 环境变量配置（需用户自行创建）
