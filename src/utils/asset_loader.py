"""
像素素材加载器 — 绑定当前 CharacterPack。


支持静态 PNG 与多帧 GIF；缺失文件时用配色占位图，保证任意角色包都能跑起来。
"""
from __future__ import annotations


from pathlib import Path


from PIL import Image, ImageDraw, ImageTk


from config import DEFAULT_FRAME_MS, DEFAULT_PET_SIZE, DEFAULT_TRANSPARENT_COLOR
from core.character_pack import CharacterPack



def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)



class AnimationFrames:
    def __init__(
        self,
        frames: list[ImageTk.PhotoImage],
        delays_ms: list[int] | None = None,
        *,
        is_motion: bool = False,
        source: str = "",
    ):
        self.frames = frames
        self.delays_ms = delays_ms or [DEFAULT_FRAME_MS] * len(frames)
        self.is_motion = is_motion
        self.source = source
        if not self.frames:
            raise ValueError("AnimationFrames 需要至少一帧")
        if len(self.delays_ms) != len(self.frames):
            self.delays_ms = [DEFAULT_FRAME_MS] * len(self.frames)


    def __len__(self) -> int:
        return len(self.frames)



# 角色无关的简易几何占位（仅当素材缺失时）
_STATE_PALETTE = {
    "idle": ((40, 120, 220), (255, 255, 255), (255, 200, 50)),
    "focus": ((30, 90, 180), (255, 255, 255), (80, 80, 80)),
    "eat": ((40, 120, 220), (255, 255, 255), (210, 140, 40)),
    "timemachine": ((60, 40, 160), (200, 230, 255), (255, 100, 200)),
    "drink": ((40, 140, 200), (255, 255, 255), (80, 180, 255)),
    "hungry": ((40, 100, 180), (255, 240, 200), (220, 60, 60)),
    "preview": ((100, 60, 180), (255, 230, 250), (120, 220, 120)),
    "food": ((210, 140, 40), (240, 200, 120), (160, 90, 30)),
}



def _make_placeholder(
    state: str,
    size: tuple[int, int],
    transparent_color: str,
    accent_rgb: tuple[int, int, int] | None = None,
) -> Image.Image:
    w, h = size
    key = _hex_to_rgb(transparent_color)
    img = Image.new("RGBA", (w, h), (*key, 255))
    draw = ImageDraw.Draw(img)


    body, face, accent = _STATE_PALETTE.get(state, _STATE_PALETTE["idle"])
    if accent_rgb:
        body = accent_rgb


    if state in ("food", "dorayaki"):
        draw.ellipse([4, 10, w - 4, h - 10], fill=body + (255,))
        draw.ellipse([8, 14, w - 8, h - 14], fill=face + (255,))
        draw.rectangle([10, h // 2 - 3, w - 10, h // 2 + 3], fill=accent + (255,))
        return img


    margin = w // 10
    draw.ellipse([margin, margin // 2, w - margin, h - margin // 3], fill=body + (255,))
    face_m = w // 5
    draw.ellipse([face_m, h // 4, w - face_m, h - margin], fill=face + (255,))
    eye_y = h // 3
    draw.ellipse([w // 2 - 18, eye_y, w // 2 - 6, eye_y + 14], fill=(20, 20, 20, 255))
    draw.ellipse([w // 2 + 6, eye_y, w // 2 + 18, eye_y + 14], fill=(20, 20, 20, 255))
    if state == "focus":
        draw.rectangle([w // 2 - 22, eye_y + 2, w // 2 - 2, eye_y + 12], outline=(40, 40, 40, 255))
        draw.rectangle([w // 2 + 2, eye_y + 2, w // 2 + 22, eye_y + 12], outline=(40, 40, 40, 255))
    if state == "hungry":
        draw.ellipse([w // 2 - 16, eye_y + 14, w // 2 - 10, eye_y + 22], fill=(100, 180, 255, 255))
    draw.ellipse([w // 2 - 4, eye_y + 14, w // 2 + 4, eye_y + 22], fill=(220, 40, 40, 255))
    if state == "eat":
        draw.ellipse([w // 2 - 12, eye_y + 24, w // 2 + 12, eye_y + 36], fill=(40, 40, 40, 255))
    elif state == "hungry":
        draw.arc([w // 2 - 14, eye_y + 28, w // 2 + 14, eye_y + 42], 20, 160, fill=(40, 40, 40, 255))
    else:
        draw.arc([w // 2 - 14, eye_y + 24, w // 2 + 14, eye_y + 40], 200, 340, fill=(40, 40, 40, 255))
    draw.ellipse([w // 2 - 8, h - 28, w // 2 + 8, h - 14], fill=accent + (255,))
    if state == "timemachine":
        draw.rectangle([w // 8, h // 2, w - w // 8, h - 4], outline=(255, 100, 200, 255), width=2)
    if state == "drink":
        draw.rectangle([w - 28, h // 2, w - 8, h - 16], fill=(80, 180, 255, 200), outline=(30, 30, 30, 255))
    return img



class AssetLoader:
    """绑定某个 CharacterPack；切换角色时调用 bind() 清空缓存。"""


    def __init__(self, pack: CharacterPack | None = None) -> None:
        self.pack: CharacterPack | None = pack
        self._cache: dict[str, AnimationFrames] = {}


    def bind(self, pack: CharacterPack) -> None:
        self.pack = pack
        self.clear_cache()


    def clear_cache(self) -> None:
        self._cache.clear()


    @property
    def transparent_color(self) -> str:
        if self.pack:
            return self.pack.transparent_color
        return DEFAULT_TRANSPARENT_COLOR


    @property
    def pet_size(self) -> tuple[int, int]:
        if self.pack:
            return self.pack.pet_size
        return DEFAULT_PET_SIZE


    @property
    def food_size(self) -> tuple[int, int]:
        if self.pack:
            return self.pack.food_size
        return (48, 48)


    @property
    def frame_ms(self) -> int:
        if self.pack:
            return self.pack.default_frame_ms
        return DEFAULT_FRAME_MS


    def _pil_to_tk(self, img: Image.Image, size: tuple[int, int]) -> ImageTk.PhotoImage:
        key = _hex_to_rgb(self.transparent_color)
        src = img.convert("RGBA")
        # NEAREST 适合像素风上采样；高清贴纸缩小/放大用 LANCZOS 更清晰不糊
        if src.size == size:
            resized = src
        else:
            sw, sh = src.size
            tw, th = size
            scale_up = tw > sw or th > sh
            # 像素角色（源图≈目标）用 NEAREST；明显缩放用 LANCZOS
            if abs(tw - sw) <= 2 and abs(th - sh) <= 2:
                resample = Image.Resampling.NEAREST
            elif scale_up and sw <= 160 and sh <= 160 and tw <= 192 and th <= 192:
                resample = Image.Resampling.NEAREST
            else:
                resample = Image.Resampling.LANCZOS
            resized = src.resize(size, resample)
        background = Image.new("RGBA", size, (*key, 255))
        composed = Image.alpha_composite(background, resized)
        return ImageTk.PhotoImage(composed.convert("RGB"))


    def _load_gif(self, path: Path, size: tuple[int, int]) -> AnimationFrames:
        frames: list[ImageTk.PhotoImage] = []
        delays: list[int] = []
        default_delay = self.frame_ms
        with Image.open(path) as im:
            index = 0
            while True:
                try:
                    im.seek(index)
                except EOFError:
                    break
                frame = im.convert("RGBA")
                delay = im.info.get("duration", default_delay)
                if not delay or delay < 20:
                    delay = default_delay
                frames.append(self._pil_to_tk(frame, size))
                delays.append(int(delay))
                index += 1
        if not frames:
            raise ValueError(f"GIF 无帧: {path}")
        return AnimationFrames(frames, delays, is_motion=len(frames) > 1, source=str(path))


    def _load_static(self, path: Path, size: tuple[int, int]) -> AnimationFrames:
        with Image.open(path) as im:
            tk_img = self._pil_to_tk(im, size)
            return AnimationFrames([tk_img, tk_img], [400, 400], is_motion=False, source=str(path))


    def _placeholder(self, state: str, size: tuple[int, int]) -> AnimationFrames:
        base = _make_placeholder(state, size, self.transparent_color)
        frame2 = base.copy()
        draw = ImageDraw.Draw(frame2)
        draw.point((size[0] // 2, 8), fill=(255, 255, 100, 255))
        return AnimationFrames(
            [self._pil_to_tk(base, size), self._pil_to_tk(frame2, size)],
            [300, 300],
            is_motion=False,
            source="placeholder",
        )


    def _food_candidates(self) -> list[Path]:
        if not self.pack:
            return []
        names = [
            self.pack.food.file,
            "food.png",
            "box.png",
            "box.gif",
            "package.png",
            "package.gif",
        ]
        seen: set[str] = set()
        out: list[Path] = []
        for name in names:
            if not name or name in seen:
                continue
            seen.add(name)
            p = self.pack.assets_dir / name
            if p.exists():
                out.append(p)
        return out


    def _resolve_path(self, state: str) -> Path | None:
        if not self.pack:
            return None
        # 食物 / 包裹别名
        if state in ("food", "dorayaki", "package", getattr(self.pack.food, "id", "")):
            cands = self._food_candidates()
            return cands[0] if cands else None
        return self.pack.state_path(state)


    def _find_variant(self, state: str, prefer_exts: tuple[str, ...]) -> Path | None:
        """在角色包中按扩展名偏好查找 state 素材（不改 character.json 也能用 gif+png 对）。"""
        if not self.pack:
            return None
        if state in ("food", "dorayaki", "package", getattr(self.pack.food, "id", "")):
            for p in self._food_candidates():
                if p.suffix.lower() in prefer_exts:
                    return p
            cands = self._food_candidates()
            return cands[0] if cands else None

        declared = self.pack.state_path(state)
        # 先按偏好扩展名在 assets 下找 state.*
        for ext in prefer_exts:
            p = self.pack.assets_dir / f"{state}{ext}"
            if p.exists():
                return p
        # hungry_0.png 等后备
        if state == "hungry":
            for ext in prefer_exts:
                for alt in self.pack.assets_dir.glob(f"hungry_*{ext}"):
                    return alt
        # 再回退 character.json 声明
        if declared and declared.exists() and declared.suffix.lower() in prefer_exts:
            return declared
        if declared and declared.exists() and not prefer_exts:
            return declared
        return declared if declared and declared.exists() else None


    def get_motion(self, state: str, size: tuple[int, int] | None = None) -> AnimationFrames | None:
        """动作 GIF（多帧）。没有则 None。"""
        size = size or self.pet_size
        pack_id = self.pack.id if self.pack else "none"
        key = f"{pack_id}:motion:{state}:{size[0]}x{size[1]}"
        if key in self._cache:
            return self._cache[key]
        path = self._find_variant(state, (".gif", ".webp"))
        if path is None:
            return None
        try:
            if path.suffix.lower() == ".gif":
                anim = self._load_gif(path, size)
            else:
                anim = self._load_static(path, size)
            # 单帧 gif 不算 motion
            if not anim.is_motion and len(anim.frames) <= 1:
                return None
            if len(anim.frames) == 1:
                anim.is_motion = False
                return None
            anim.is_motion = True
            self._cache[key] = anim
            return anim
        except Exception:
            return None


    def get_still(self, state: str, size: tuple[int, int] | None = None) -> AnimationFrames | None:
        """定格 PNG。没有则尝试 GIF 末帧语义上的静态回退 / idle。"""
        size = size or self.pet_size
        pack_id = self.pack.id if self.pack else "none"
        key = f"{pack_id}:still:{state}:{size[0]}x{size[1]}"
        if key in self._cache:
            return self._cache[key]
        path = self._find_variant(state, (".png", ".webp", ".jpg", ".jpeg"))
        try:
            if path and path.exists():
                anim = self._load_static(path, size)
                self._cache[key] = anim
                return anim
            # 无 png：用 motion 第一帧做假 still
            motion = self.get_motion(state, size=size)
            if motion and motion.frames:
                still = AnimationFrames(
                    [motion.frames[0], motion.frames[0]],
                    [400, 400],
                    is_motion=False,
                    source=motion.source + "#frame0",
                )
                self._cache[key] = still
                return still
            if state != "idle":
                return self.get_still("idle", size=size)
            anim = self._placeholder(state, size)
            self._cache[key] = anim
            return anim
        except Exception:
            return self._placeholder(state, size)


    def get(self, state: str, size: tuple[int, int] | None = None) -> AnimationFrames:
        """兼容旧接口：优先 motion，否则 still。"""
        size = size or self.pet_size
        motion = self.get_motion(state, size=size)
        if motion is not None:
            return motion
        still = self.get_still(state, size=size)
        if still is not None:
            return still
        return self._placeholder(state, size)


    def get_food(self) -> AnimationFrames:
        food_state = self.pack.food.id if self.pack else "food"
        # 包裹：优先静态 png，便于拖拽清晰
        still = self.get_still(food_state, size=self.food_size)
        if still is not None:
            return still
        return self.get(food_state, size=self.food_size)


    def get_preview_photo(self, size: tuple[int, int] = (64, 64)) -> ImageTk.PhotoImage | None:
        """角色切换面板用缩略图。"""
        if not self.pack:
            return None
        path = self.pack.preview_path()
        try:
            if path and path.exists():
                with Image.open(path) as im:
                    return self._pil_to_tk(im, size)
            anim = self.get("idle", size=size)
            return anim.frames[0]
        except Exception:
            return None
