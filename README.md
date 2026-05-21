# Skills 项目说明

这是一个用于存放 Codex Skills 的仓库。每个 Skill 都是一个独立目录，包含最少一个 `SKILL.md`，并可按需附带脚本、参考文档和界面元数据。

## 当前目录结构

```text
/Users/godd/workspace/skills
├── README.md
└── s3-upload/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    ├── references/
    │   └── configuration.md
    └── scripts/
        └── upload_s3.py
```

## 项目目标

- 统一管理本地可用的 Codex Skills
- 为特定任务提供稳定、可复用的流程说明
- 通过脚本、参考资料和资源文件减少重复劳动
- 让 Skill 文档、结构和触发描述保持清晰一致

## Skill 目录约定

每个 Skill 目录通常包含：

- `SKILL.md`：Skill 的核心说明文档，包含 frontmatter 与使用指引
- `agents/openai.yaml`：界面展示元数据，例如显示名、简短说明、默认提示词
- `scripts/`：可执行脚本，用于稳定完成重复性任务
- `references/`：按需读取的详细参考资料
- `assets/`：输出时需要使用但不必直接加载进上下文的资源文件

## 当前 Skill：`s3-upload`

`/Users/godd/workspace/skills/s3-upload` 用于把本地文件上传到 AWS S3 或兼容 S3 的对象存储，例如 MinIO。

支持能力包括：

- 上传单个或多个本地文件
- 指定对象 `key` 或批量上传前缀 `prefix`
- 使用自定义 endpoint
- 支持 path-style / virtual-hosted-style
- 设置 metadata、ACL、content type、cache control
- 通过 Python 标准库实现确定性上传

## 开发与维护建议

- 修改 Skill 后，优先保持 `SKILL.md` 与 `agents/openai.yaml` 一致
- 尽量把详细配置和长篇示例放入 `references/`
- 尽量把重复性操作沉淀为 `scripts/`
- 不要在单个 Skill 目录里添加与执行无关的额外说明文件，避免噪音

## 校验

可使用 Skill Creator 提供的校验脚本检查 Skill 基本格式是否正确：

```bash
python3 /Users/godd/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /Users/godd/workspace/skills/s3-upload
```
