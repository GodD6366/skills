---
name: linkwarden
description: 使用 Linkwarden API 和本地脚本管理书签自动整理、分类与标签化。
---

# Linkwarden

用于操作 GodD 的 Linkwarden 实例，尤其是书签自动分类脚本和相关配置。

## 适用场景

- 自动整理未分类书签
- 根据关键词映射收藏夹与标签
- 修改或复用 Linkwarden 自动化脚本
- 读取 Linkwarden API 配置位置

## 已知环境

- Linkwarden 服务地址：`https://link.godd.site:6443`
- 配置文件：`/Users/godd/.openclaw/extensions/linkwarden/config.json`
- 自动分类脚本：`/Users/godd/.openclaw/extensions/linkwarden/scripts/auto_organize.py`

## 工作流程

1. 先读取脚本与配置，确认当前映射和 API 参数。
2. 如需调整分类逻辑，优先改脚本中的关键词映射，再验证脚本行为。
3. 不要明文泄露凭证；如果需要展示敏感配置，只说明位置，不直接回显 token。
4. 修改后应验证脚本语法或运行结果。

## 注意事项

- Linkwarden 自动整理会同时更新收藏夹和标签。
- “其他”收藏夹用于无法自动匹配的书签。
- 凭证默认不明文记录。

## 参考文件

- `/Users/godd/.openclaw/extensions/linkwarden/scripts/auto_organize.py`
- `/Users/godd/.openclaw/extensions/linkwarden/config.json`
