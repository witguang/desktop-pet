# Desktop Pet（可换角色桌面宠物）

Windows 桌面互动宠物：透明置顶、番茄钟、时光机、喂食/快递、喝水用餐提醒、备忘录。

**引擎与角色分离** — 内置 **琪琪（Kiki）** / **哆啦A梦**；换皮只需 `characters/<id>/`，不必改 Python。

技术栈：Python 3.10+ · Tkinter · Pillow（可选 `keyboard`）

版本：根目录 [`VERSION`](./VERSION) · `python packaging/entry_main.py --version`

---

## 给朋友（推荐）

1. [Releases](https://github.com/witguang/desktop-pet/releases) 下载 **`DesktopPet-v*-windows.zip`**（请勿直接下裸 `.exe`）
2. 解压后双击 **`DesktopPet.exe`**
3. 首次设置：安装位置 / 备忘录（**建议 D 盘，仅提示**）· 快捷方式 · 是否打开桌宠

说明与 SmartScreen 处理：**[docs/给朋友看.md](./docs/给朋友看.md)**

---

## 开发

```bash
pip install -r requirements.txt
python packaging/entry_main.py
# 或 scripts/run_dev.bat  /  scripts/启动桌宠.bat
```

```bash
python packaging/entry_main.py --character kiki
python packaging/entry_main.py --list-characters
python packaging/entry_main.py --version
```

### 打包

```bash
python packaging/build_app.py
# 或 scripts/build_release.bat  /  scripts/打包给朋友.bat
```

| 输出 | 说明 |
|------|------|
| `dist/DesktopPet.exe` | 单文件主程序 |
| `dist/DesktopPet-v*-windows.zip` | **发给朋友用这个** |

开发依赖：`pip install -r requirements-dev.txt` · 测试：`pytest tests/`

---

## 目录结构

```
desktop-pet/                 # 仓库根目录尽量干净
├── README.md
├── VERSION
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
│
├── characters/              # 角色包
├── src/                     # 业务源码
├── packaging/               # 入口 + PyInstaller
│   ├── entry_main.py
│   ├── build_app.py
│   └── DesktopPet.spec
├── scripts/                 # 本机快捷脚本
│   ├── run_dev.bat
│   └── build_release.bat
├── docs/                    # 文档
│   └── 给朋友看.md
└── tests/
```

| 层 | 职责 |
|----|------|
| `characters/*` | 外观、台词、UI 文案 |
| `src/core` + `app.py` | 番茄钟、状态机、提醒 |
| `src/ui` | 窗口与面板 |
| `packaging` | 启动入口与打包 |

---

## 新增角色

复制 `characters/_template` → 改 `character.json` + `assets/` → 控制面板「切换角色」。详见模板 README。

---

## 操作

| 操作 | 方式 |
|------|------|
| 移动 | 左键拖 |
| 控制面板 | 右键 / `Ctrl+Shift+P` |
| 生成道具 | 双击 / `Ctrl+Shift+D` |
| 切换角色 | `Ctrl+Shift+C` |
| 退出 | 控制面板 / 主设置 |

---

## 分发说明

未做代码签名时，浏览器可能拦截裸 `.exe`、SmartScreen 可能提示「未知发布者」——**请分发 zip**，并让用户「更多信息 → 仍要运行」。详见 [docs/给朋友看.md](./docs/给朋友看.md)。

---

## 版权

学习 / 演示框架。内置形象为示意占位；商用请使用自绘或已授权素材。
