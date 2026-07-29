
# 角色包目录（Character Packs）
本目录下**每一个子文件夹**（以下划线 `_` 开头的除外）若包含 `character.json`，就会被引擎自动发现。
## 内置
| 文件夹 | 角色 |
|--------|------|
| `doraemon/` | 哆啦A梦 · 铜锣烧 |
| `kiki/` | 琪琪（魔女宅急便风） · 青鱼面包 |
| `pikachu/` | 皮卡丘 · 树果 |
| `codex_spark/` | Spark 编程猫 · 小鱼干 |
| `_template/` | 自定义模板（不会出现在列表里） |
## 新增角色（30 秒）
```bash
# 1. 复制模板
cp -r _template my_hero     # Windows 可用资源管理器复制
# 2. 改 character.json 里的 id / name / food / dialogues
# 3. 替换 assets/*.png *.gif
# 4. 运行应用 → 切换角色 → 刷新
```
详细字段说明见 `_template/README.md`。
重新生成内置占位图：
```bash
python -m utils.pack_generator
```
