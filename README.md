# 可换角色桌面宠物（Desktop Pet）

Windows 桌面互动宠物：无边框透明置顶、番茄钟、时光机历史、喂食/快递投递、喝水与用餐提醒、备忘录等。

**核心设计：引擎与角色完全分离。** 内置 **琪琪（Kiki）** 与 **哆啦A梦** 两套角色包；换成猫、机器人、自绘 OC 只需丢一个文件夹，**不用改 Python 代码**。

技术栈：Python 3.10+ / Tkinter / Pillow（可选 `keyboard` 全局热键）

当前版本见根目录 [`VERSION`](./VERSION)（开发可用 `python main.py --version`）。

后续优化路线（建议 + 已落地项）见仓库外文档：`../.grok/optimization-roadmap-2026-07-31.md`（若从 monorepo 布局打开）。

---

## 给朋友：最快安装（推荐）

朋友**不需要**装 Python，也**不用**打开仓库里那些 `.py` 源码。

1. 打开 [Releases 发布页](https://github.com/witguang/desktop-pet/releases)
2. 下载 **`DesktopPet-v*-windows.zip`**（或直接拿 **`DesktopPet.exe`**）
3. 解压后**只双击 `DesktopPet.exe`**
4. 首次弹出设置向导：
   - **建议安装在 D 盘**（仅提示；路径需自己选，不会自动填 `D:\某文件夹`）
   - 软件安装位置、备忘录目录均可浏览
   - 默认勾选：桌面快捷方式、完成后打开桌宠（可取消）

安装完成后，安装目录里正常 **只有一个 `DesktopPet.exe`**（用一段时间后会出现 `data_store/` 存设置，可忽略）。

更短的一页说明见：**[给朋友看.md](./给朋友看.md)**

> Windows 若提示「未知发布者」：点「更多信息」→「仍要运行」。

---

## 开发者：从源码运行

```bash
# 或双击 启动桌宠.bat
pip install -r requirements.txt
python main.py
```

指定角色 / 列出角色：

```bash
python main.py --character kiki
python main.py --character doraemon
python main.py --list-characters
```

### 打包成 exe 发给朋友

```bash
# 或双击 打包给朋友.bat
python packaging/build_app.py
```

产出（**只有一个 exe**）：

| 路径 | 用途 |
|------|------|
| `dist/DesktopPet.exe` | 单文件主程序（角色资源 + 图标已打进包内） |
| `dist/DesktopPet-v*-windows.zip` | zip 内也只有上述 exe |

说明：

- **onefile**：不再生成 `DesktopPetSetup.exe`、不再把源码树铺在安装目录
- 窗口左上角图标为 Kiki `app.ico`（不是 Python 羽毛）
- 路径可移植：`.spec` 相对 `SPECPATH`，禁止硬编码绝对路径

发布示例：

```bash
gh release create v1.1.9 dist/DesktopPet-v1.1.9-windows.zip dist/DesktopPet.exe \
  --title "v1.1.9" \
  --notes "单文件 DesktopPet.exe：双击安装向导；建议 D 盘（仅提示）；安装目录只有一个 exe"
```

---

## 目录结构

朋友只下载 Releases；开发时根目录尽量只留入口与资源：

```
doraemon_pet/
├── 给朋友看.md / 启动桌宠.bat / 打包给朋友.bat   ← 实用入口
├── main.py / install_app.py                      ← 启动入口（薄）
├── VERSION / requirements.txt / README.md
│
├── characters/          ★ 角色包（换皮只改这里）
│   ├── kiki/  doraemon/  _template/
│
├── src/                 ★ 全部业务源码
│   ├── app.py / config.py
│   ├── core/            引擎（番茄钟、状态机…）
│   ├── data/            设置 / 任务日志
│   ├── ui/              窗口与面板 / 安装向导
│   └── utils/           更新、安装、素材加载
│
├── packaging/           ★ 打包（PyInstaller onefile）
│   ├── build_app.py / build_app.bat
│   └── DesktopPet.spec
│
└── data_store/          运行时用户数据（不进 Git）
```

| 层 | 职责 |
|----|------|
| **角色包** `characters/*` | 外观、食物名、台词、UI 文案 |
| **引擎** `src/core/` + `src/app.py` | 番茄钟、饥饿、喝水、状态机 |
| **存储** `src/data/` | 任务日志、当前角色 id |
| **UI** `src/ui/` | 渲染与交互，文案全部问角色包要 |

状态优先级：`时光机 > 吃东西 > 喝水 > 专注 > 饥饿 > 待机`

开发用占位图：`python -c "import sys; sys.path.insert(0,'src'); from utils.pack_generator import generate_all; generate_all()"`

---

## 替换 / 新增角色

### 方式 A：一键切换（已安装的包）

1. 右键桌宠 → 控制面板 → **切换角色**
2. 或快捷键 `Ctrl+Shift+C`
3. 点「使用」即可热切换，**无需重启**

### 方式 B：新增自定义角色

```text
1. 复制  characters/_template
2. 改名为  characters/my_cat
3. 编辑   character.json
4. 替换   assets/ 下的像素图
5. 在「切换角色」面板点刷新 → 使用
```

**不需要改任何 `.py` 文件。** 完整字段见 `characters/_template/README.md`。

---

## 内置角色

| id | 名称 | 互动道具 | 计量 | 风格 |
|----|------|----------|------|------|
| `kiki` | 琪琪 | 快递包裹 📦 | 愉悦值（mood） | 魔女宅急便风，**默认角色** |
| `doraemon` | 哆啦A梦 | 铜锣烧 🍩 | 饥饿值（hunger） | 经典蓝胖子 |

---

## 操作一览

| 操作 | 方式 |
|------|------|
| 移动 | 左键拖动 |
| 控制面板 | 右键 / `Ctrl+Shift+P` |
| 生成道具 | 双击 / 面板 / `Ctrl+Shift+D` |
| 投递 / 喂食 | 把道具拖到角色身上 |
| 切换角色 | 面板 / `Ctrl+Shift+C` |
| 时光机 | 面板按钮 |
| 退出 | 控制面板 / 主设置 →「退出桌宠」 |

---

## 数据文件

| 文件 | 内容 |
|------|------|
| `data_store/task_logs.json` | 任务与番茄钟会话 |
| `data_store/settings.json` | 角色 id、备忘录路径、更新源等（不进 Git） |
| 自定义备忘录目录 | 每日备忘录 `YYYY-MM-DD.md` |

---

## 系统要求

- Windows 10/11（色键透明效果最佳）
- 朋友：无需 Python，下载 Releases 单文件 exe 即可
- 开发：Python 3.10+、Tkinter、Pillow；可选 `keyboard`（全局热键）

---

## 版权

本项目为学习 / 演示用引擎框架。内置「琪琪」「哆啦A梦」等形象仅为示意/同人向占位；请使用**自绘或已授权**素材，勿将未授权官方美术用于商用。
