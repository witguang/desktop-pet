# packaging/

本目录集中：**程序入口、VERSION、依赖列表、PyInstaller 配置**。

| 文件 | 作用 |
|------|------|
| `entry_main.py` | 开发 / 打包入口 |
| `VERSION` | 版本号（仓库根不再放 VERSION） |
| `requirements.txt` | 运行时依赖 |
| `requirements-dev.txt` | 开发 + 打包 + 测试 |
| `build_app.py` / `*.spec` | 一键打 onefile |

```bash
# 在项目根
pip install -r packaging/requirements.txt
python packaging/entry_main.py
python packaging/build_app.py
```

产出：`../dist/DesktopPet.exe` 与 zip。spec 路径相对 `SPECPATH`，无绝对路径。
