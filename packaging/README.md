# 打包说明

## 一键打包

```bash
python packaging/build_app.py
# 或双击 打包给朋友.bat
```

## 产物（只有一个 exe）

| 路径 | 说明 |
|------|------|
| `../dist/DesktopPet.exe` | **唯一**发给朋友的程序 |
| `../dist/DesktopPet-v*-windows.zip` | zip 里也只有 `DesktopPet.exe` |

不再生成 `DesktopPetSetup.exe`。首次运行 `DesktopPet.exe` 会弹出设置向导（位置 / 备忘录 / 快捷方式 / 打开桌宠）。

安装目录默认 **只有** `DesktopPet.exe`；运行后才会出现 `data_store/`（用户数据）。

## 窗口图标

`app.ico` 打进 exe，并在运行时用 `iconbitmap` / `iconphoto` 设置，替换标题栏左上角的 Python 羽毛。

## Spec

`DesktopPet.spec`：onefile，路径相对 `SPECPATH`，无绝对路径。
