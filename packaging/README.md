# 打包

入口与 PyInstaller 配置均在本目录。

## 开发启动

```bash
# 在项目根
python packaging/entry_main.py
```

## 打包

```bash
# 在项目根
python packaging/build_app.py
# 或 scripts/build_release.bat
```

产出：`../dist/DesktopPet.exe` 与 zip（内仅一个 exe）。

`DesktopPet.spec` 路径相对 `SPECPATH`，无绝对路径。
