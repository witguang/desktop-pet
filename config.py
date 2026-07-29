"""
全局引擎配置（与具体角色无关）。

角色外观、台词、食物名等全部放在 characters/<id>/character.json。
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CHARACTERS_DIR = BASE_DIR / "characters"
DATA_DIR = BASE_DIR / "data_store"
LOG_FILE = DATA_DIR / "task_logs.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

# 默认角色（首次启动 / 角色包缺失时回退）
DEFAULT_CHARACTER_ID = "doraemon"

# 兼容旧路径：若仍有根目录 assets/，可作为最后回退
LEGACY_ASSETS_DIR = BASE_DIR / "assets"

# ---------------------------------------------------------------------------
# 番茄钟默认值（分钟）— 引擎级，角色包可覆盖
# ---------------------------------------------------------------------------
DEFAULT_FOCUS_MINUTES = 25
DEFAULT_BREAK_MINUTES = 5

# ---------------------------------------------------------------------------
# 饥饿系统（兼容旧逻辑；包裹投递改为恢复心情）
# ---------------------------------------------------------------------------
HUNGER_TICK_SECONDS = 30
HUNGER_INCREASE_PER_TICK = 1
HUNGER_MAX = 100
HUNGER_THRESHOLD = 60
HUNGER_RESET_ON_FEED = 0

# ---------------------------------------------------------------------------
# 心情 / 愉悦值（包裹投递恢复）
# ---------------------------------------------------------------------------
MOOD_TICK_SECONDS = 30
MOOD_DECREASE_PER_TICK = 1
MOOD_MAX = 100
MOOD_LOW_THRESHOLD = 40
MOOD_RESTORE_ON_DELIVER = 100
MOOD_RESTORE_AMOUNT = 25

# ---------------------------------------------------------------------------
# 喝水 / 用餐提醒（预设 + 用户自定义 HH:MM）
# ---------------------------------------------------------------------------
WATER_REMINDERS = [
    ("08:00", "早晨"),
    ("10:00", "早晨"),
    ("12:30", "中午"),
    ("15:00", "下午"),
    ("18:00", "晚上"),
    ("20:30", "晚上"),
]
MEAL_REMINDERS = [
    ("09:00", "早餐"),
    ("11:00", "午餐"),
    ("18:00", "晚餐"),
]
WATER_REMINDER_DURATION_MS = 12_000
WATER_CHECK_INTERVAL_MS = 15_000
DEFAULT_MEMO_DIR_NAME = "memos"

# ---------------------------------------------------------------------------
# 全局快捷键
# ---------------------------------------------------------------------------
HOTKEY_SPAWN_FOOD = "ctrl+shift+d"
HOTKEY_TOGGLE_PANEL = "ctrl+shift+p"
HOTKEY_SWITCH_CHARACTER = "ctrl+shift+c"

# ---------------------------------------------------------------------------
# 动画 / 显示默认值（角色包可覆盖）
# ---------------------------------------------------------------------------
DEFAULT_FRAME_MS = 120
EAT_ANIMATION_MS = 2500
DRINK_ANIMATION_MS = 2800
FLY_ANIMATION_MS = 3000
# 动作 GIF 定格到 PNG 后，再停留多久回到 idle（毫秒）
ACTION_STILL_HOLD_MS = 5000
TIMEMACHINE_ANIMATION_MS = 3000
DEFAULT_PET_SIZE = (128, 128)
DEFAULT_FOOD_SIZE = (48, 48)
DEFAULT_TRANSPARENT_COLOR = "#010101"

# 标准状态键（角色包必须至少提供 idle；其余缺失时回退 idle 或程序占位）
REQUIRED_STATES = ("idle",)
OPTIONAL_STATES = ("focus", "eat", "fly", "timemachine", "drink", "hungry")
ALL_STATES = REQUIRED_STATES + OPTIONAL_STATES


class PetState:
    IDLE = "idle"
    FOCUS = "focus"
    EAT = "eat"
    FLY = "fly"
    TIME_MACHINE = "timemachine"
    DRINK = "drink"
    HUNGRY = "hungry"
