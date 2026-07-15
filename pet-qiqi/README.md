# qiqi Codex 宠物安装说明

`qiqi` 是一个 Codex v2 动画宠物，包含 8×11 精灵图、9 组标准动作和 16 个注视方向。

素材仓库：[GodD6366/skills — pet-qiqi](https://github.com/GodD6366/skills/tree/main/pet-qiqi)

## 安装

### 从 GitHub 获取并安装

```bash
git clone --depth 1 https://github.com/GodD6366/skills.git
cd skills/pet-qiqi
PACKAGE_DIR="$(pwd)"
mkdir -p "$HOME/.codex/pets/qiqi"
cp "$PACKAGE_DIR/spritesheet.webp" "$HOME/.codex/pets/qiqi/spritesheet.webp"
cp "$PACKAGE_DIR/pet.json" "$HOME/.codex/pets/qiqi/pet.json"
```

### 从已下载的包安装

进入已下载或解压后的 `pet-qiqi` 目录，再执行：

```bash
PACKAGE_DIR="$(pwd)"
mkdir -p "$HOME/.codex/pets/qiqi"
cp "$PACKAGE_DIR/spritesheet.webp" "$HOME/.codex/pets/qiqi/spritesheet.webp"
cp "$PACKAGE_DIR/pet.json" "$HOME/.codex/pets/qiqi/pet.json"
```

然后完全退出并重新打开 Codex，在宠物选择器中启用 `qiqi`。

## 更新已有安装

重新执行上面的两条 `cp` 命令即可覆盖旧版精灵图和配置。无需删除宠物目录。

## 包内容

- `spritesheet.webp`：v2 精灵图，1536×2288，透明背景。
- `pet.json`：宠物元数据，包含 `spriteVersionNumber: 2`。
- `qa/`：动作、注视方向和校验记录，供排查或验收使用。

## 验证

安装后检查：

```bash
cat "$HOME/.codex/pets/qiqi/pet.json"
```

输出中应包含：

```json
"id": "qiqi",
"spriteVersionNumber": 2
```
