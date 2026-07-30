"""
全局引擎配置（与具体角色无关）。

角色外观、台词、食物名等全部放在 characters/<id>/character.json。
"""
from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 路径（支持 PyInstaller 打包；开发时源码在 src/，资源与数据在项目根）
# ---------------------------------------------------------------------------
def project_root() -> Path:
    """项目根目录：含 main.py / characters / data_store。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    here = Path(__file__).resolve().parent
    # 标准布局：src/config.py → 上一级为项目根
    if here.name == "src":
        return here.parent
    # 兼容：平铺布局（打包后 exe 旁热加载的 app 树）
    return here


def _resolve_base_dir() -> Path:
    # 用户数据始终在 exe / 项目根旁，便于更新不丢
    return project_root()


def resource_dir() -> Path:
    """只读资源目录（角色包等）。"""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return project_root()


BASE_DIR = _resolve_base_dir()
RESOURCE_DIR = resource_dir()
CHARACTERS_DIR = RESOURCE_DIR / "characters"
# 用户数据始终在 exe / 项目旁，便于更新不丢
DATA_DIR = BASE_DIR / "data_store"
LOG_FILE = DATA_DIR / "task_logs.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

# 默认角色（首次启动 / 角色包缺失时回退）
DEFAULT_CHARACTER_ID = "kiki"

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
    ("12:00", "午餐"),
    ("18:00", "晚餐"),
    ("22:00", "宵夜"),
]
MEAL_PERIOD_OPTIONS = ("早餐", "午餐", "晚餐", "宵夜")
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

# ---------------------------------------------------------------------------
# 空闲随机动作（增强生动感）
# ---------------------------------------------------------------------------
# 两次随机动作之间的间隔（秒）
IDLE_RANDOM_MIN_SEC = 25
IDLE_RANDOM_MAX_SEC = 70
# 随机动作定格 PNG 后再停留多久回 idle
IDLE_RANDOM_STILL_HOLD_MS = 2200
# 可参与随机的状态（角色包无该状态则自动跳过）
IDLE_RANDOM_STATES = ("fly", "eat", "timemachine", "drink")

# ---------------------------------------------------------------------------
# 状态轮播（自动定期切换 preview / drink / fly / eat / focus / idle）
# ---------------------------------------------------------------------------
# 外循环：两次轮播之间随机多少小时
STATE_CAROUSEL_MIN_HOURS = 1
STATE_CAROUSEL_MAX_HOURS = 3
# 内循环：在上述小时基础上再随机多少分钟（0-59）
STATE_CAROUSEL_MIN_MINUTES = 0
STATE_CAROUSEL_MAX_MINUTES = 59
# 轮播进入某个状态后保持多久再回 idle（毫秒）
STATE_CAROUSEL_HOLD_MIN_MS = 25_000
STATE_CAROUSEL_HOLD_MAX_MS = 55_000
# 可参与轮播的状态（角色包无该状态则自动跳过）
STATE_CAROUSEL_STATES = ("preview", "drink", "fly", "eat", "focus", "idle")

# 标准状态键（角色包必须至少提供 idle；其余缺失时回退 idle 或程序占位）
REQUIRED_STATES = ("idle",)
OPTIONAL_STATES = ("focus", "eat", "fly", "timemachine", "drink", "hungry", "preview")
ALL_STATES = REQUIRED_STATES + OPTIONAL_STATES


class PetState:
    IDLE = "idle"
    FOCUS = "focus"
    EAT = "eat"
    FLY = "fly"
    TIME_MACHINE = "timemachine"
    DRINK = "drink"
    HUNGRY = "hungry"
    PREVIEW = "preview"
