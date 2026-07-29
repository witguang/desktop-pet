
# 可换角色桌面宠物（Desktop Pet）

类似 **Codex** 的 Windows 桌面互动宠物：无边框透明置顶、番茄钟、时光机历史、饥饿喂食、喝水提醒。

**核心设计：引擎与角色完全分离。** 哆啦A梦只是内置角色包之一；换成猫、机器人、自绘 OC 只需丢一个文件夹，**不用改 Python 代码**。

技术栈：Python 3.10+ / Tkinter / Pillow（可选 `keyboard` 全局热键）

---

## 快速开始

```bash
cd doraemon_pet
pip install -r requirements.txt
python main.py
```

指定角色启动 / 列出角色：

```bash
python main.py --character codex_spark
python main.py --list-characters
```

重新生成内置角色占位图：

```bash
python -m utils.pack_generator
```

---

## 架构

```
doraemon_pet/
├── main.py / app.py          # 入口与编排（角色无关）
├── config.py                 # 引擎级配置（番茄钟、饥饿、热键…）
├── characters/               # ★ 角色包目录（热插拔）
│   ├── doraemon/             # 内置：哆啦A梦
│   ├── codex_spark/          # 内置：Codex 风格编程猫
│   └── _template/            # 自定义模板（复制即用）
├── core/
│   ├── character_pack.py     # 角色包加载 / 发现 / 台词
│   ├── pomodoro.py / hunger.py / water_reminder.py / pet_state.py
├── data/                     # JSON 任务日志 + 用户设置（当前角色）
├── ui/                       # 宠物窗、面板、食物、角色切换器
└── utils/asset_loader.py     # 按当前角色包加载 PNG/GIF
```

| 层 | 职责 |
|----|------|
| **角色包** `characters/*` | 外观、食物名、台词、UI 文案 |
| **引擎** `core/` + `app.py` | 番茄钟、饥饿、喝水、状态机 |
| **存储** `data/` | 任务日志、当前角色 id |
| **UI** `ui/` | 渲染与交互，文案全部问角色包要 |

状态优先级：`时光机 > 吃东西 > 喝水 > 专注 > 饥饿 > 待机`

---

## 像 Codex 一样替换角色

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

| id | 名称 | 食物 | 风格 |
|----|------|------|------|
| `doraemon` | 哆啦A梦 | 铜锣烧 🍩 | 经典蓝胖子 |
| `codex_spark` | Spark | 小鱼干 🐟 | Codex 风编程猫 |

占位图由 `utils/pack_generator.py` 程序绘制，正式使用请换成你的像素原稿。

---

## 操作一览

| 操作 | 方式 |
|------|------|
| 移动 | 左键拖动 |
| 控制面板 | 右键 / `Ctrl+Shift+P` |
| 生成食物 | 双击 / 面板 / `Ctrl+Shift+D` |
| 喂食 | 把食物拖到角色身上 |
| 切换角色 | 面板 / `Ctrl+Shift+C` |
| 时光机 | 面板按钮 |

---

## 功能说明

### 番茄钟

自定义专注 \(x\) 分钟、休息 \(y\) 分钟；开始 / 暂停 / 重置。专注中角色进入 `focus` 形态，记录写入本地 JSON。

### 时光机

播放 `timemachine` 动画，按日期回顾任务与番茄钟（`data_store/task_logs.json`）。

### 饥饿与喂食

默认每 30 秒饥饿 +1，达到 60 气泡提示；拖食物喂食后播 `eat` 并重置。

### 喝水提醒

每日 6 次（`config.py` → `WATER_REMINDERS` 可改）：08:00 / 10:00 / 12:30 / 15:00 / 18:00 / 20:30。

---

## 数据文件

| 文件 | 内容 |
|------|------|
| `data_store/task_logs.json` | 任务与番茄钟会话 |
| `data_store/settings.json` | 当前角色 id 等 |

---

## 系统要求

- Windows 10/11（色键透明效果最佳）
- Python 3.10+、Tkinter、Pillow
- 可选：`keyboard`（全局热键；部分环境需管理员）

---

## 版权

本项目为学习 / 演示用引擎框架。内置「哆啦A梦」仅为占位示意；请使用**自绘或已授权**素材，勿将未授权官方美术用于商用。
