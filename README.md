
# 可换角色桌面宠物（Desktop Pet）

Windows 桌面互动宠物：无边框透明置顶、番茄钟、时光机历史、喂食/快递投递、喝水与用餐提醒、备忘录等。

**核心设计：引擎与角色完全分离。** 内置 **琪琪（Kiki）** 与 **哆啦A梦** 两套角色包；换成猫、机器人、自绘 OC 只需丢一个文件夹，**不用改 Python 代码**。

技术栈：Python 3.10+ / Tkinter / Pillow（可选 `keyboard` 全局热键）

---

## 给朋友：最快安装（推荐）

朋友**不需要**装 Python，也**不用**打开仓库里那些 `.py` 源码。

1. 打开 [Releases 发布页](https://github.com/witguang/desktop-pet/releases)
2. 下载 **`DesktopPet-v*-windows.zip`**
3. 解压后双击 **`DesktopPetSetup.exe`**（选安装目录 + 备忘录目录）  
   或直接双击 **`DesktopPet.exe`** 便携运行

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

输出：

| 路径 | 用途 |
|------|------|
| `dist/DesktopPet/` | 整文件夹拷给别人也能用 |
| `dist/DesktopPet-v*-windows.zip` | **推荐发给朋友 / 上传 Release** |

发布示例：

```bash
gh release create v1.1.6 dist/DesktopPet-v1.1.6-windows.zip --title "v1.1.6" --notes "Windows 安装包：解压后运行 DesktopPetSetup.exe"
```

---

## 目录结构（已收纳）

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
│   ├── ui/              窗口与面板
│   └── utils/           更新、安装、素材加载
│
├── packaging/           ★ 打包工具（PyInstaller）
│   ├── build_app.py / build_app.bat
│   └── *.spec
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

当前选择会写入 `data_store/settings.json`。

### 方式 B：新增自定义角色（推荐）

```text
1. 复制  characters/_template
2. 改名为  characters/my_cat
3. 编辑   character.json（id / name / food / dialogues）
4. 替换   assets/ 下的像素图
5. 在「切换角色」面板点刷新 → 使用
```

**不需要改任何 `.py` 文件。**

### 角色包目录结构

```text
characters/<id>/
  character.json     # 元数据（必需）
  assets/
    idle.png         # 待机（必需）
    focus.png
    eat.gif
    timemachine.gif
    drink.png
    hungry.png
    food.png         # 食物道具 ~48×48
    preview.png      # 切换面板缩略图（可选）
```

### `character.json` 要点

```json
{
  "id": "my_cat",
  "name": "小橘",
  "food": { "id": "fish", "name": "小鱼干", "emoji": "🐟", "file": "food.png" },
  "states": {
    "idle": { "file": "idle.png" },
    "focus": { "file": "focus.png" },
    "eat": { "file": "eat.gif" }
  },
  "dialogues": {
    "greeting": ["你好，我是{name}！"],
    "hungry": ["想吃{food} {food_emoji}"],
    "eat": ["{food}真香！"],
    "focus_start": ["开始专注：{task}"]
  },
  "ui": {
    "panel_title": "{name} · 控制面板",
    "spawn_food_button": "生成{food} {food_emoji}"
  }
}
```

可用占位符：`{name}` `{food}` `{food_emoji}` `{task}` `{time}` `{period}` `{id}`

完整字段说明见 `characters/_template/README.md`。

### 素材注意

- 建议 **128×128** 像素风，透明底 PNG / 多帧 GIF
- Windows 透明色键默认 `#010101`，素材里避免大面积使用
- 缺少某状态图时，引擎会回退到 `idle` 或程序占位图，不会崩溃

---

## 内置角色

| id | 名称 | 互动道具 | 计量 | 风格 |
|----|------|----------|------|------|
| `kiki` | 琪琪 | 快递包裹 📦 | 愉悦值（mood） | 魔女宅急便风，**默认角色** |
| `doraemon` | 哆啦A梦 | 铜锣烧 🍩 | 饥饿值（hunger） | 经典蓝胖子 |

在控制面板点「切换角色」，或使用 `Ctrl+Shift+C` / `python main.py --character <id>`。

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

## 功能说明

### 番茄钟

自定义专注 \(x\) 分钟、休息 \(y\) 分钟；开始 / 暂停 / 重置。专注中角色进入 `focus` 形态，记录写入本地 JSON。

### 时光机

播放 `timemachine` 动画，按日期回顾任务与番茄钟（`data_store/task_logs.json`）。

### 饥饿 / 愉悦与投递

- **哆啦A梦**：饥饿值；拖铜锣烧喂食后重置。
- **琪琪**：愉悦值；拖快递包裹投递后恢复心情。

间隔与阈值见 `config.py`，也可在「吃喝设置」里改喝水/用餐时刻表。

### 喝水提醒

每日多时段（`config.py` → `WATER_REMINDERS`，主设置/吃喝设置可改）。

---

## 数据文件

| 文件 | 内容 |
|------|------|
| `data_store/task_logs.json` | 任务与番茄钟会话 |
| `data_store/settings.json` | 当前角色 id、备忘录路径、更新源等（不进 Git） |
| `data_store/memos/` 或自定义目录 | 每日备忘录 `YYYY-MM-DD.md` |

---

## 系统要求

- Windows 10/11（色键透明效果最佳）
- Python 3.10+、Tkinter、Pillow
- 可选：`keyboard`（全局热键；部分环境需管理员）

---

## 版权

本项目为学习 / 演示用引擎框架。内置「琪琪」「哆啦A梦」等形象仅为示意/同人向占位；请使用**自绘或已授权**素材，勿将未授权官方美术用于商用。
