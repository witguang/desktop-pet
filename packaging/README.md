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

## 输出

| 路径 | 说明 |
|------|------|
| `../dist/DesktopPet/` | 完整分发目录 |
| `../dist/DesktopPet-v*-windows.zip` | 发给朋友的压缩包 |

exe 旁会**平铺** `app.py` / `core/` 等（不是 `src/` 结构），以便在线更新热加载。
