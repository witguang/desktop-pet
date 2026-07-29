"""
清理琪琪 GIF 边缘绿边，并从 box.gif 导出静态包裹 PNG。

用法（在 doraemon_pet 目录）:
    python -m utils.clean_kiki_assets
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image


ASSETS = Path(__file__).resolve().parent.parent / "characters" / "kiki" / "assets"
# 与 character.json transparent_color 一致
KEY_RGB = (1, 1, 1)


def _is_key_or_transparent(r: int, g: int, b: int, a: int, thr: int = 18) -> bool:
    if a < thr:
        return True
    # near pure key / near-black key
    if r <= 8 and g <= 8 and b <= 8:
        return True
    return False


def _is_fringe_green(r: int, g: int, b: int, a: int) -> bool:
    """高饱和绿 / 抠图绿边（避免误伤裙子上的低饱和橄榄绿需结合邻域）。"""
    if a < 20:
        return False
    # classic chroma / screen green
    if g >= 140 and r <= 120 and b <= 120 and g >= r + 35 and g >= b + 35:
        return True
    if g >= 100 and r <= 90 and b <= 90 and g >= r + 40 and g >= b + 40:
        return True
    # olive fringe often left by bad keys: moderate g dominance near edges
    if g >= 85 and g > r + 28 and g > b + 28 and (r + b) < g + 40:
        return True
    return False


def _neighbors_background(px, w: int, h: int, x: int, y: int) -> bool:
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if nx < 0 or ny < 0 or nx >= w or ny >= h:
                return True
            r, g, b, a = px[nx, ny]
            if _is_key_or_transparent(r, g, b, a):
                return True
    return False


def clean_rgba_frame(im: Image.Image, edge_band: int = 10) -> Image.Image:
    """Edge flood-fill from borders to remove ONLY background green canvas.
    Preserves any internal green pixels (eyes, hair, etc.) because they are not connected to border green.
    """
    fr = im.convert("RGBA")
    w, h = fr.size
    px = fr.load()

    from collections import deque
    visited = set()
    background = set()

    # Flood fill from all border pixels (top, bottom, left, right)
    queue = deque()
    # Top and bottom borders
    for x in range(w):
        queue.append((x, 0))
        queue.append((x, h - 1))
    # Left and right borders
    for y in range(h):
        queue.append((0, y))
        queue.append((w - 1, y))

    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        visited.add((x, y))
        r, g, b, a = px[x, y]
        # Background green is connected green or key
        if _is_fringe_green(r, g, b, a) or _is_key_or_transparent(r, g, b, a):
            background.add((x, y))
            # Add 8-connected neighbors
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                        queue.append((nx, ny))

    # Set all connected background pixels to key color (transparent)
    for x, y in background:
        px[x, y] = (*KEY_RGB, 0)

    # Despill for any remaining near-background green cast (keeps internal greens untouched)
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if _neighbors_background(px, w, h, x, y) and g > r + 15 and g > b + 15 and a > 40:
                ng = min(g, max(r, b) + 12)
                if ng < g:
                    px[x, y] = (r, ng, b, a)

    # Final transparent pass
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 16:
                px[x, y] = (*KEY_RGB, 0)
    return fr


def frame_to_gif_rgb(fr: Image.Image) -> Image.Image:
    """RGBA → 铺 key 底的 RGB，再转 P（保留透明索引 0）。"""
    rgba = fr.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, (*KEY_RGB, 255))
    composed = Image.alpha_composite(bg, rgba)
    # force near-key low-alpha to exact key
    px = composed.load()
    w, h = composed.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 16 or (r <= 8 and g <= 8 and b <= 8):
                px[x, y] = (*KEY_RGB, 255)
    rgb = composed.convert("RGB")
    # adaptive palette; index 0 reserved roughly for dark key via remapping
    pal = rgb.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    # ensure key maps close to transparency — rebuild with explicit key at 0
    return _force_key_palette(rgb)


def _force_key_palette(rgb: Image.Image) -> Image.Image:
    """把 KEY_RGB 映射为 palette 索引 0，便于 transparency=0。"""
    # Use adaptive but replace pure-key pixels after
    img = rgb.convert("RGB")
    # paint key pixels as unique marker first? simpler path:
    w, h = img.size
    px = img.load()
    key_set = []
    for y in range(h):
        for x in range(w):
            if px[x, y] == KEY_RGB:
                key_set.append((x, y))
                # temporary bright magenta marker unlikely in art
                px[x, y] = (255, 0, 255)
    pal = img.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    # find magenta index and key
    pal_rgb = pal.convert("RGB")
    pr = pal_rgb.load()
    # rebuild palette list
    p = pal.getpalette() or []
    # set index 0 to key; remap magenta → 0
    # Actually quantize may put magenta at some index — convert those pixels to 0
    data = list(pal.getdata())
    # find most common color among former key positions
    magenta_idx = None
    if key_set:
        counts: dict[int, int] = {}
        for x, y in key_set:
            idx = pal.getpixel((x, y))
            if isinstance(idx, tuple):
                idx = idx[0]
            counts[idx] = counts.get(idx, 0) + 1
        magenta_idx = max(counts, key=counts.get) if counts else None
    if magenta_idx is not None:
        data = [0 if v == magenta_idx else (v if v != 0 else 1) for v in data]
        # shift old 0 away already handled; set palette[0]=key
    # Build new P image
    out = Image.new("P", (w, h))
    palette = [0] * (256 * 3)
    src_pal = pal.getpalette() or [0] * (256 * 3)
    for i in range(256):
        palette[i * 3 : i * 3 + 3] = src_pal[i * 3 : i * 3 + 3]
    palette[0:3] = list(KEY_RGB)
    if magenta_idx is not None and magenta_idx != 0:
        # keep others
        pass
    out.putpalette(palette)
    out.putdata(data)
    return out


def clean_and_save_gif(path: Path) -> dict:
    im = Image.open(path)
    n = getattr(im, "n_frames", 1)
    durations: list[int] = []
    cleaned: list[Image.Image] = []
    removed = 0
    for i in range(n):
        im.seek(i)
        dur = int(im.info.get("duration", 120) or 120)
        if dur < 20:
            dur = 120
        durations.append(dur)
        raw = im.convert("RGBA")
        before = _count_fringe(raw)
        fr = clean_rgba_frame(raw)
        after = _count_fringe(fr)
        removed += max(0, before - after)
        cleaned.append(frame_to_gif_rgb(fr))

    cleaned[0].save(
        path,
        save_all=True,
        append_images=cleaned[1:],
        duration=durations if len(set(durations)) > 1 else durations[0],
        loop=0,
        transparency=0,
        disposal=2,
        optimize=False,
    )
    return {"file": path.name, "frames": n, "fringe_removed_est": removed}


def _count_fringe(im: Image.Image) -> int:
    px = im.convert("RGBA").load()
    w, h = im.size
    n = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if _is_fringe_green(r, g, b, a) and (
                x < 10 or y < 10 or x >= w - 10 or y >= h - 10 or _neighbors_background(px, w, h, x, y)
            ):
                n += 1
    return n


def clean_png(path: Path) -> dict:
    raw = Image.open(path).convert("RGBA")
    before = _count_fringe(raw)
    fr = clean_rgba_frame(raw)
    after = _count_fringe(fr)
    # save with real alpha (PNG)
    fr.save(path)
    return {"file": path.name, "fringe_removed_est": max(0, before - after)}


def extract_box_png() -> dict:
    box_gif = ASSETS / "box.gif"
    if not box_gif.exists():
        return {"file": "box.gif", "error": "missing"}
    im = Image.open(box_gif)
    im.seek(0)
    fr = clean_rgba_frame(im.convert("RGBA"), edge_band=4)
    # food.png + box.png aliases
    food_path = ASSETS / "food.png"
    box_path = ASSETS / "box.png"
    fr.save(food_path)
    fr.save(box_path)
    return {"file": "food.png/box.png", "size": fr.size}


def ensure_hungry_png() -> dict:
    src = ASSETS / "hungry_0.png"
    dst = ASSETS / "hungry.png"
    if dst.exists():
        return clean_png(dst)
    if src.exists():
        fr = clean_rgba_frame(Image.open(src).convert("RGBA"))
        fr.save(dst)
        return {"file": "hungry.png", "from": "hungry_0.png"}
    return {"file": "hungry.png", "error": "missing source"}


def main() -> None:
    if not ASSETS.is_dir():
        raise SystemExit(f"assets missing: {ASSETS}")

    results = []
    results.append(extract_box_png())
    results.append(ensure_hungry_png())

    for gif in sorted(ASSETS.glob("*.gif")):
        print(f"cleaning {gif.name} …")
        results.append(clean_and_save_gif(gif))

    for png_name in ("idle.png", "focus.png", "drink.png", "fly.png", "preview.png", "timemachine.png", "food.png", "box.png", "hungry.png"):
        p = ASSETS / png_name
        if p.exists():
            results.append(clean_png(p))

    for r in results:
        print(r)


if __name__ == "__main__":
    main()
