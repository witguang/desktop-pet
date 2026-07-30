# 打包说明

业务代码在 `../src/`，资源在项目根 `../characters/`。

## 一键打包

在项目根目录：

```bash
python packaging/build_app.py
```

或双击：

- 项目根：`打包给朋友.bat`
- 本目录：`build_app.bat`

首次打包可能要 **1–3 分钟**（会收集 Pillow 等依赖），停在  
`Module search paths (PYTHONPATH):` 后面属于正常，请等它跑完。

## 可移植 .spec（禁止硬编码绝对路径）

| 文件 | 说明 |
|------|------|
| `DesktopPet.spec` | 主程序（`main.py`） |
| `DesktopPetSetup.spec` | 安装向导（`install_app.py`） |
| `build_app.spec` | 与 `DesktopPet.spec` 等价的兼容入口 |

路径一律相对 `SPECPATH`（本目录）解析：`root = Path(SPECPATH).parent`。  
**不要**把 PyInstaller 自动生成、含本机盘符（如 `D:\...`）的 `.spec` 提交进仓库。

手动只打主程序：

```bash
pyinstaller --noconfirm --clean --distpath dist --workpath build packaging/DesktopPet.spec
```

## 输出

| 路径 | 说明 |
|------|------|
| `../dist/DesktopPet/` | 完整分发目录 |
| `../dist/DesktopPet-v*-windows.zip` | 发给朋友的压缩包 |

exe 旁会**平铺** `app.py` / `core/` 等（不是 `src/` 结构），以便在线更新热加载。
