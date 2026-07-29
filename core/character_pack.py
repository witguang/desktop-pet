"""
角色包（Character Pack）系统 — 类似 Codex 的可替换角色。


目录约定
--------
characters/
  <character_id>/
    character.json      # 元数据、状态素材映射、台词、UI 文案
    assets/             # 像素图 / GIF
      idle.png
      focus.png
      eat.gif
      ...
      food.png
      preview.png       # 可选，切换面板缩略图


只需复制一份角色文件夹并改 character.json + 换图，即可新增角色，无需改引擎代码。
"""
from __future__ import annotations


import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


from config import (
    ALL_STATES,
    CHARACTERS_DIR,
    DEFAULT_CHARACTER_ID,
    DEFAULT_FOOD_SIZE,
    DEFAULT_FRAME_MS,
    DEFAULT_PET_SIZE,
    DEFAULT_TRANSPARENT_COLOR,
    EAT_ANIMATION_MS,
    TIMEMACHINE_ANIMATION_MS,
)



# 引擎内置的默认台词（角色包未写时回退）
_DEFAULT_DIALOGUES: dict[str, list[str]] = {
    "greeting": ["你好！我是{name}~\n右键打开控制面板"],
    "hungry": ["肚子饿了…想吃{food} {food_emoji}\n双击我或按 Ctrl+Shift+D"],
    "spawn_food": ["把{food}拖到我嘴边~"],
    "eat": ["{food}真好吃！"],
    "water": ["💧 {period}喝水时间到！\n（{time}）记得多喝水哦~\n点「已喝完」才算数"],
    "meal": ["🍽 {period}时间到\n（{time}）先吃饭再继续~\n点「已用餐」打卡"],
    "focus_start": ["开始专注：{task}\n加油！"],
    "break_start": ["休息一下吧"],
    "paused": ["已暂停"],
    "reset": ["已重置番茄钟"],
    "focus_done": ["专注完成！\n进入休息时间吧"],
    "break_done": ["休息结束，继续加油！"],
    "task_done": ["任务完成！真棒"],
    "timemachine": ["启动时光机！\n去看看过去的记录~"],
    "no_task": ["当前没有进行中的任务。"],
    "character_switched": ["变身完成！现在是{name}"],
    "switch_hint": ["可以在面板里切换角色哦"],
}


_DEFAULT_UI: dict[str, str] = {
    "panel_title": "{name} · 控制面板",
    "spawn_food_button": "生成{food} {food_emoji}",
    "timemachine_button": "时光机 · 历史回顾",
    "timemachine_title": "时光机 · 历史回顾",
    "character_button": "切换角色",
    "app_title": "{name}",
    # 控制面板状态行 / 计量条（{value}/{max} 由引擎注入）
    "status_line": "角色：{name}  ·  食物：{food} {food_emoji}",
    "meter_label": "饥饿值: {value} / {max}",
    "tip_line": (
        "拖动桌宠移动 · 右键打开本面板 · 双击生成{food}\n"
        "快捷键：{food} Ctrl+Shift+D · 面板 Ctrl+Shift+P · 角色 Ctrl+Shift+C\n"
        "退出：本面板底部「退出桌宠」"
    ),
    "memo_button": "备忘录 📝",
    "settings_button": "主设置 ⚙",
}



@dataclass
class StateAsset:
    """某一形态对应的资源文件。"""


    file: str
    label: str = ""



@dataclass
class FoodInfo:
    id: str = "food"
    name: str = "零食"
    emoji: str = "🍪"
    file: str = "food.png"



@dataclass
class CharacterPack:
    """一个完整角色包的运行时表示。"""


    id: str
    name: str
    root: Path
    assets_dir: Path
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    name_en: str = ""
    preview_file: str | None = None
    pet_size: tuple[int, int] = DEFAULT_PET_SIZE
    food_size: tuple[int, int] = DEFAULT_FOOD_SIZE
    transparent_color: str = DEFAULT_TRANSPARENT_COLOR
    food: FoodInfo = field(default_factory=FoodInfo)
    states: dict[str, StateAsset] = field(default_factory=dict)
    dialogues: dict[str, list[str]] = field(default_factory=dict)
    ui: dict[str, str] = field(default_factory=dict)
    eat_animation_ms: int = EAT_ANIMATION_MS
    timemachine_animation_ms: int = TIMEMACHINE_ANIMATION_MS
    default_frame_ms: int = DEFAULT_FRAME_MS
    # "hunger" = 饥饿喂食；"mood" = 愉悦值 + 投递包裹
    meter_mode: str = "hunger"
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def uses_mood(self) -> bool:
        return self.meter_mode == "mood"

    # ------------------------------------------------------------------
    # 文案
    # ------------------------------------------------------------------
    def _vars(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        base = {
            "name": self.name,
            "name_en": self.name_en or self.name,
            "food": self.food.name,
            "food_emoji": self.food.emoji,
            "id": self.id,
        }
        if extra:
            base.update(extra)
        return base


    def line(self, key: str, **kwargs: Any) -> str:
        """取一条台词（列表则随机），支持 {name}/{food}/... 占位符。"""
        pool = self.dialogues.get(key) or _DEFAULT_DIALOGUES.get(key) or [key]
        if isinstance(pool, str):
            pool = [pool]
        text = random.choice(pool) if pool else key
        try:
            return text.format(**self._vars(kwargs))
        except (KeyError, ValueError):
            return text


    def ui_text(self, key: str, **kwargs: Any) -> str:
        template = self.ui.get(key) or _DEFAULT_UI.get(key) or key
        try:
            return template.format(**self._vars(kwargs))
        except (KeyError, ValueError):
            return template


    # ------------------------------------------------------------------
    # 资源路径
    # ------------------------------------------------------------------
    def state_path(self, state: str) -> Path | None:
        asset = self.states.get(state)
        if asset is None:
            # 常见别名：food 状态用 food.file
            if state in ("food", "dorayaki", self.food.id):
                p = self.assets_dir / self.food.file
                return p if p.exists() else None
            return None
        path = self.assets_dir / asset.file
        return path if path.exists() else None


    def resolve_state_file(self, state: str) -> str:
        """返回相对 assets 的文件名（供 loader 使用）。"""
        if state in self.states:
            return self.states[state].file
        if state in ("food", "dorayaki", self.food.id):
            return self.food.file
        return f"{state}.png"


    def preview_path(self) -> Path | None:
        if self.preview_file:
            p = self.assets_dir / self.preview_file
            if p.exists():
                return p
        # 回退 idle
        return self.state_path("idle")


    def missing_assets(self) -> list[str]:
        missing: list[str] = []
        for state in ALL_STATES:
            if state not in self.states:
                if state == "idle":
                    missing.append("idle (required)")
                continue
            path = self.assets_dir / self.states[state].file
            if not path.exists():
                missing.append(self.states[state].file)
        food_path = self.assets_dir / self.food.file
        if not food_path.exists():
            missing.append(self.food.file)
        return missing



def _as_size(value: Any, default: tuple[int, int]) -> tuple[int, int]:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return int(value[0]), int(value[1])
        except (TypeError, ValueError):
            return default
    return default



def _normalize_dialogues(raw: Any) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    if not isinstance(raw, dict):
        return result
    for key, val in raw.items():
        if isinstance(val, str):
            result[key] = [val]
        elif isinstance(val, list):
            result[key] = [str(x) for x in val if str(x).strip()]
        else:
            result[key] = [str(val)]
    return result



def load_character_pack(pack_dir: Path) -> CharacterPack:
    """从 characters/<id>/ 加载角色包。"""
    meta_path = pack_dir / "character.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"角色包缺少 character.json: {pack_dir}")


    with open(meta_path, "r", encoding="utf-8") as f:
        data = json.load(f)


    char_id = str(data.get("id") or pack_dir.name).strip()
    name = str(data.get("name") or char_id)
    assets_subdir = data.get("assets_dir", "assets")
    assets_dir = pack_dir / str(assets_subdir)
    if not assets_dir.is_dir():
        # 允许素材直接放在包根目录
        assets_dir = pack_dir


    display = data.get("display") or {}
    food_raw = data.get("food") or {}
    food = FoodInfo(
        id=str(food_raw.get("id", "food")),
        name=str(food_raw.get("name", "零食")),
        emoji=str(food_raw.get("emoji", "🍪")),
        file=str(food_raw.get("file", "food.png")),
    )


    states: dict[str, StateAsset] = {}
    raw_states = data.get("states") or {}
    for state_key, spec in raw_states.items():
        if isinstance(spec, str):
            states[state_key] = StateAsset(file=spec)
        elif isinstance(spec, dict):
            states[state_key] = StateAsset(
                file=str(spec.get("file", f"{state_key}.png")),
                label=str(spec.get("label", "")),
            )


    # 若未声明 states，按约定文件名自动探测
    if not states:
        for state in ALL_STATES:
            for ext in (".png", ".gif", ".webp"):
                candidate = assets_dir / f"{state}{ext}"
                if candidate.exists():
                    states[state] = StateAsset(file=candidate.name)
                    break


    anim = data.get("animation") or {}
    gameplay = data.get("gameplay") or {}
    meter_raw = str(gameplay.get("meter") or data.get("meter") or "hunger").strip().lower()
    meter_mode = "mood" if meter_raw in ("mood", "pleasure", "joy", "愉悦", "愉悦值") else "hunger"

    pack = CharacterPack(
        id=char_id,
        name=name,
        root=pack_dir,
        assets_dir=assets_dir,
        version=str(data.get("version", "1.0.0")),
        author=str(data.get("author", "")),
        description=str(data.get("description", "")),
        name_en=str(data.get("name_en", "")),
        preview_file=data.get("preview") or data.get("preview_file"),
        pet_size=_as_size(display.get("pet_size"), DEFAULT_PET_SIZE),
        food_size=_as_size(display.get("food_size"), DEFAULT_FOOD_SIZE),
        transparent_color=str(display.get("transparent_color", DEFAULT_TRANSPARENT_COLOR)),
        food=food,
        states=states,
        dialogues=_normalize_dialogues(data.get("dialogues")),
        ui={str(k): str(v) for k, v in (data.get("ui") or {}).items()},
        eat_animation_ms=int(anim.get("eat_ms", EAT_ANIMATION_MS)),
        timemachine_animation_ms=int(anim.get("timemachine_ms", TIMEMACHINE_ANIMATION_MS)),
        default_frame_ms=int(anim.get("frame_ms", DEFAULT_FRAME_MS)),
        meter_mode=meter_mode,
        raw=data,
    )
    return pack



def discover_characters(characters_dir: Path | None = None) -> list[CharacterPack]:
    """扫描 characters/ 下所有合法角色包。"""
    root = characters_dir or CHARACTERS_DIR
    if not root.exists():
        return []
    packs: list[CharacterPack] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("_") or child.name.startswith("."):
            continue  # _template 等
        meta = child / "character.json"
        if not meta.exists():
            continue
        try:
            packs.append(load_character_pack(child))
        except Exception as exc:
            print(f"[character] 跳过无效角色包 {child.name}: {exc}")
    return packs



def get_character(character_id: str, characters_dir: Path | None = None) -> CharacterPack:
    root = characters_dir or CHARACTERS_DIR
    pack_dir = root / character_id
    if pack_dir.is_dir() and (pack_dir / "character.json").exists():
        return load_character_pack(pack_dir)
    # id 与文件夹名不一致时，全量扫描
    for pack in discover_characters(root):
        if pack.id == character_id:
            return pack
    raise FileNotFoundError(f"未找到角色包: {character_id}")



def get_default_character() -> CharacterPack:
    try:
        return get_character(DEFAULT_CHARACTER_ID)
    except FileNotFoundError:
        packs = discover_characters()
        if packs:
            return packs[0]
        raise FileNotFoundError(
            f"未找到任何角色包。请在 {CHARACTERS_DIR} 下放置角色文件夹。"
        )
