"""
从 ref/kiki 参考图生成琪琪角色包素材：
- 去白底
- 裁多格分镜
- 映射到 idle / focus / drink / hungry / eat.gif(送快递) / timemachine.gif(飞行)
"""
from __future__ import annotations


import json
import math
import sys
from pathlib import Path


from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


REF = ROOT.parent / "ref" / "kiki"
OUT = ROOT / "characters" / "kiki" / "assets"
META = ROOT / "characters" / "kiki" / "character.json"



def remove_bg(im: Image.Image, thr: int = 245) -> Image.Image:
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r >= thr and g >= thr and b >= thr:
                px[x, y] = (r, g, b, 0)
            elif abs(r - g) < 8 and abs(g - b) < 8 and r > 230:
                px[x, y] = (r, g, b, 0)
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            if r > 220 and g > 220 and b > 220:
                alpha = max(0, min(255, int((255 - r) * 4)))
                if alpha < 40:
                    px[x, y] = (r, g, b, 0)
    return im



def trim(im: Image.Image, pad: int = 4) -> Image.Image:
    bbox = im.getbbox()
    if not bbox:
        return im
    l, t, r, b = bbox
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(im.width, r + pad)
    b = min(im.height, b + pad)
    return im.crop((l, t, r, b))



def fit_square(im: Image.Image, size: int = 128) -> Image.Image:
    im = im.convert("RGBA")
    margin = 4
    target = size - margin * 2
    w, h = im.size
    scale = min(target / max(w, 1), target / max(h, 1))
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ox = (size - nw) // 2
    oy = (size - nh) // 2
    canvas.paste(im, (ox, oy), im)
    return canvas



def load_clean(path: Path, thr: int = 245) -> Image.Image:
    im = Image.open(path)
    im = remove_bg(im, thr)
    return trim(im)



def crop_vpanels(im: Image.Image, n: int = 4, thr: int = 245) -> list[Image.Image]:
    im = im.convert("RGBA")
    im = remove_bg(im, thr)
    w, h = im.size
    panels: list[Image.Image] = []
    ph = h // n
    for i in range(n):
        part = im.crop((0, i * ph, w, (i + 1) * ph if i < n - 1 else h))
        part = trim(part)
        if part.getbbox():
            panels.append(part)
    return panels



def save_gif(frames: list[Image.Image], path: Path, duration: int = 140) -> None:
    key = (1, 1, 1)
    out: list[Image.Image] = []
    for fr in frames:
        bg = Image.new("RGBA", fr.size, (*key, 255))
        composed = Image.alpha_composite(bg, fr.convert("RGBA"))
        px = composed.load()
        w, h = composed.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a < 16:
                    px[x, y] = (*key, 255)
        out.append(composed.convert("P", palette=Image.Palette.ADAPTIVE, colors=255))
    out[0].save(
        path,
        save_all=True,
        append_images=out[1:],
        duration=duration,
        loop=0,
        transparency=0,
        disposal=2,
    )



def draw_package(size: int = 48) -> Image.Image:
    food = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(food)
    d.rectangle([6, 16, 42, 42], fill=(210, 160, 90, 255), outline=(120, 80, 40, 255), width=2)
    d.polygon([(6, 16), (24, 6), (42, 16), (24, 24)], fill=(230, 185, 110, 255), outline=(120, 80, 40, 255))
    d.line([(24, 6), (24, 24)], fill=(120, 80, 40, 255), width=2)
    d.rectangle([20, 16, 28, 42], fill=(230, 200, 80, 255))
    d.rectangle([30, 22, 38, 30], fill=(200, 50, 50, 255))
    return food



def main() -> None:
    if not REF.exists():
        raise SystemExit(f"找不到参考目录: {REF}")


    OUT.mkdir(parents=True, exist_ok=True)


    kiki_main = load_clean(REF / "Kiki.jpg", thr=240)
    drink_src = load_clean(REF / "kiki _3.jpg", thr=235)
    flying = load_clean(REF / "IMGBIN_com - Download Transparent PNG Images, For Free.jpg", thr=248)
    with_jiji = load_clean(REF / "Kiki And Jiji Sticker.jpg", thr=248)
    sitting = load_clean(REF / "4123.jpg", thr=248)
    running = load_clean(REF / "3232.jpg", thr=248)


    delivery_panels = crop_vpanels(Image.open(REF / "kiki's delivery service.jpg"), n=4, thr=240)
    grid_panels = crop_vpanels(Image.open(REF / "958844576932089491.jpg"), n=4, thr=240)


    print("delivery panels", len(delivery_panels), [p.size for p in delivery_panels])
    print("grid panels", len(grid_panels), [p.size for p in grid_panels])


    # 状态映射（按你提供的素材语义）
    idle = fit_square(kiki_main, 128)
    if len(grid_panels) >= 3:
        focus = fit_square(grid_panels[2], 128)  # 读信 / 看地图
    else:
        focus = fit_square(load_clean(REF / "839639924325270244.jpg", thr=248), 128)
    drink = fit_square(drink_src, 128)
    hungry = fit_square(sitting, 128)  # 等单
    preview = fit_square(with_jiji, 128)


    idle.save(OUT / "idle.png")
    focus.save(OUT / "focus.png")
    drink.save(OUT / "drink.png")
    hungry.save(OUT / "hungry.png")
    preview.save(OUT / "preview.png")
    print("saved static pngs")


    # eat.gif = 送快递
    eat_frames: list[Image.Image] = []
    for p in delivery_panels:
        eat_frames.append(fit_square(p, 128))
    eat_frames.append(fit_square(running, 128))
    if grid_panels:
        eat_frames.append(fit_square(grid_panels[0], 128))
    if len(eat_frames) < 4:
        eat_frames = [
            fit_square(running, 128),
            fit_square(kiki_main, 128),
            fit_square(with_jiji, 128),
            fit_square(running, 128),
        ]
    save_gif(eat_frames, OUT / "eat.gif", duration=160)
    print("eat.gif frames", len(eat_frames))


    # timemachine.gif = 飞行日记
    tm_frames: list[Image.Image] = []
    if len(grid_panels) >= 2:
        tm_frames.append(fit_square(grid_panels[1], 128))
    base_fly = fit_square(flying, 128)
    for i, dy in enumerate([0, -3, -5, -3, 0, 2, 0, -2]):
        fr = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        dx = int(2 * math.sin(i * 0.9))
        fr.paste(base_fly, (dx, dy), base_fly)
        d = ImageDraw.Draw(fr)
        for j, (sx, sy) in enumerate([(10, 20), (110, 30), (20, 100), (100, 90), (64, 8)]):
            if (i + j) % 2 == 0:
                r = 2
                d.ellipse([sx - r + dx, sy - r + dy, sx + r + dx, sy + r + dy], fill=(255, 230, 100, 220))
        tm_frames.append(fr)
    if len(grid_panels) >= 4:
        tm_frames.append(fit_square(grid_panels[3], 128))
    save_gif(tm_frames, OUT / "timemachine.gif", duration=120)
    print("timemachine.gif frames", len(tm_frames))


    draw_package(48).save(OUT / "food.png")


    # 确保 character.json 是送快递设定
    if META.exists():
        meta = json.loads(META.read_text(encoding="utf-8"))
    else:
        meta = {}
    meta.update(
        {
            "id": "kiki",
            "name": "琪琪",
            "name_en": "Kiki",
            "version": "1.2.0",
            "author": "builtin",
            "description": "魔女宅急便风桌宠（基于你提供的参考图）。双击生成快递包裹，拖到身边完成投递。",
            "preview": "preview.png",
            "display": {
                "pet_size": [128, 128],
                "food_size": [48, 48],
                "transparent_color": "#010101",
            },
            "food": {"id": "package", "name": "快递包裹", "emoji": "📦", "file": "food.png"},
            "states": {
                "idle": {"file": "idle.png", "label": "待机"},
                "focus": {"file": "focus.png", "label": "看地图"},
                "eat": {"file": "eat.gif", "label": "投递包裹"},
                "timemachine": {"file": "timemachine.gif", "label": "飞行日记"},
                "drink": {"file": "drink.png", "label": "喝水"},
                "hungry": {"file": "hungry.png", "label": "等单"},
            },
            "animation": {"eat_ms": 2600, "timemachine_ms": 3200, "frame_ms": 120},
        }
    )
    meta.setdefault(
        "dialogues",
        {
            "greeting": ["嗨！我是琪琪~\n今天也要加油送快递！", "扫帚就绪，右键打开控制面板 🧹"],
            "hungry": [
                "有新订单了吗？📦\n双击我或 Ctrl+Shift+D 生成包裹",
                "包裹堆空了…再接一单吧！",
            ],
            "spawn_food": ["新包裹来了！拖到我身边~", "好嘞，这单我送 📦"],
            "eat": ["送达！✓ 谢谢惠顾~", "投递完成 ✨ 下单再见！"],
            "water": ["💧 {period}喝水时间\n（{time}）魔女也要好好补水"],
            "focus_start": ["开始专注：{task}\n先看清送货地图 📖"],
            "break_start": ["休息一下吧，看看海 ☕"],
            "paused": ["已暂停 ⏸ 扫帚先靠墙"],
            "reset": ["番茄钟重置，路线重新规划"],
            "focus_done": ["专注完成！🎉\n要不要再送一单？"],
            "break_done": ["休息结束，继续出发！"],
            "task_done": ["任务送达！✓ 琪琪点赞"],
            "timemachine": ["打开飞行日记 ⏳\n看看以前的记录~"],
            "character_switched": ["琪琪报到！魔女快递为你服务~"],
        },
    )
    meta.setdefault(
        "ui",

===== gen kiki headings =====


LineNumber Line                                                                                                       
---------- ----                                                                                                       
         2 生成琪琪（魔女宅急便风）与皮卡丘角色包素材。                                                                                     
         5     python -m utils.gen_kiki_pikachu                                                                       
        23 def _new(size: int = 128) -> Image.Image:                                                                  
        27 def _save_png(img: Image.Image, path: Path) -> None:                                                       
        32 def _save_gif(frames: list[Image.Image], path: Path, duration: int = 140) -> None:                         
        58 # 琪琪（魔女宅急便风，原创 chibi）                                                                                      
        60 def draw_witch(state: str, size: int = 128, frame: int = 0) -> Image.Image:                                
        65     if state == "eat":                                                                                     
        83     if state != "eat":                                                                                     
       119     if state == "drink":                                                                                   
       129     elif state == "eat":                                                                                   
       141     elif state == "focus":                                                                                 
       185     if state == "hungry":                                                                                  
       190     elif state == "eat":                                                                                   
       204     if state != "hungry":                                                                                  
       222 def draw_herring_bread(size: int = 48) -> Image.Image:                                                     
       242 def draw_pika(state: str, size: int = 128, frame: int = 0) -> Image.Image:                                 
       247     if state == "eat":                                                                                     
       261     spark = state in ("timemachine",) or (state == "focus")                                                
       295     if state == "drink":                                                                                   
       305     elif state == "eat":                                                                                   
       311     elif state == "focus":                                                                                 
       350     if state == "hungry":                                                                                  
       355     elif state == "eat":                                                                                   
       376     if state in ("timemachine", "focus"):                                                                  
       388 def draw_berry(size: int = 48) -> Image.Image:                                                             
       398 def _write_json(path: Path, data: dict) -> None:                                                           
       404 def _write_pack(pack_id: str, meta: dict, draw_fn, food_fn) -> Path:                                       
       410         ("idle", "idle.png"),                                                                              
       411         ("focus", "focus.png"),                                                                            
       412         ("hungry", "hungry.png"),                                                                          
       413         ("drink", "drink.png"),                                                                            
       417     _save_png(draw_fn("idle", 128, 0), assets / "preview.png")                                             
       419     _save_gif([draw_fn("eat", 128, i) for i in range(5)], assets / "eat.gif", duration=130)                
       420     _save_gif([draw_fn("timemachine", 128, i) for i in range(8)], assets / "timemachine.gif", duration=110)
       426 KIKI_META = {                                                                                              
       427     "id": "kiki",                                                                                          
       428     "name": "琪琪",                                                                                          
       429     "name_en": "Kiki",                                                                                     
       441         "idle": {"file": "idle.png", "label": "待机"},                                                       
       442         "focus": {"file": "focus.png", "label": "专注"},                                                     
       443         "eat": {"file": "eat.gif", "label": "吃东西"},                                                        
       444         "timemachine": {"file": "timemachine.gif", "label": "飞行日记"},                                       
       445         "drink": {"file": "drink.png", "label": "喝水"},                                                     
       446         "hungry": {"file": "hungry.png", "label": "饥饿"},                                                   
       448     "animation": {"eat_ms": 2400, "timemachine_ms": 3000, "frame_ms": 120},                                
       451             "嗨！我是琪琪~\n今天也要加油送快递！",                                                                         
       454         "hungry": [                                                                                        
       458         "spawn_food": ["把青鱼面包拖给我~", "好香！是给琪琪的吗？"],                                                         
       459         "eat": ["嗯嗯，好好吃！", "补充魔力完毕 ✨"],                                                                    
       461         "focus_start": ["开始专注：{task}\n静静飞行中… 📖"],                                                         
       465         "focus_done": ["专注完成！🎉\n来块青鱼面包庆祝？"],                                                              
       467         "task_done": ["任务送达！✓ 琪琪点赞"],                                                                      
       469         "character_switched": ["琪琪报到！魔女快递为你服务~"],                                                          
       496         "idle": {"file": "idle.png", "label": "待机"},                                                       
       497         "focus": {"file": "focus.png", "label": "专注"},                                                     
       498         "eat": {"file": "eat.gif", "label": "吃东西"},                                                        
       499         "timemachine": {"file": "timemachine.gif", "label": "电击回忆"},                                       
       500         "drink": {"file": "drink.png", "label": "喝水"},                                                     
       501         "hungry": {"file": "hungry.png", "label": "饥饿"},                                                   
       503     "animation": {"eat_ms": 2200, "timemachine_ms": 2800, "frame_ms": 100},                                
       509         "hungry": [                                                                                        
       514         "eat": ["好好吃！皮卡~", "电力回满 ⚡"],                                                                      
       516         "focus_start": ["开始专注：{task}\n脸颊蓄电中… ⚡"],                                                          
       520         "focus_done": ["专注完成！🎉\n来颗树果庆祝？"],                                                                
       536 def generate_kiki() -> Path:                                                                               
       537     return _write_pack("kiki", KIKI_META, draw_witch, draw_herring_bread)                                  
       540 def generate_pikachu() -> Path:                                                                            
       544 def generate_all() -> None:                                                                                
       546     print("生成 琪琪 / 皮卡丘 角色包…")                                                                              
       547     generate_kiki()                                                                                        




===== root assets/ref =====


FullName                                                                            Length
--------                                                                            ------
D:\Appstore\cat\assets\characters\kiki\ai_gen\drink.png                              39528
D:\Appstore\cat\assets\characters\kiki\ai_gen\focus.png                              45776
D:\Appstore\cat\assets\characters\kiki\ai_gen\happy.png                              44235
D:\Appstore\cat\assets\characters\kiki\ai_gen\idle.png                               34183
D:\Appstore\cat\assets\characters\kiki\ai_gen\ref_url.txt                               36
D:\Appstore\cat\assets\characters\kiki\ai_gen\sleep.png                              38043
D:\Appstore\cat\assets\characters\kiki\ai_gen\summary.json                             642
D:\Appstore\cat\assets\characters\kiki\ai_gen\wait_order.png                         27872
D:\Appstore\cat\assets\characters\kiki\ai_gen\_probe.png                             34183
D:\Appstore\cat\assets\characters\kiki\ai_gen\processed_128\drink.png                12582
D:\Appstore\cat\assets\characters\kiki\ai_gen\processed_128\focus.png                14107
D:\Appstore\cat\assets\characters\kiki\ai_gen\processed_128\happy.png                13940
D:\Appstore\cat\assets\characters\kiki\ai_gen\processed_128\idle.png                  9172
D:\Appstore\cat\assets\characters\kiki\ai_gen\processed_128\idle_sticker.png         13189
D:\Appstore\cat\assets\characters\kiki\ai_gen\processed_128\sleep.png                12953
D:\Appstore\cat\assets\characters\kiki\ai_gen\processed_128\wait_order.png            9504
D:\Appstore\cat\ref\kiki_gen_test.png                                                34174
D:\Appstore\cat\ref\README.md                                                         1199
D:\Appstore\cat\ref\kiki\IMGBIN_com - Download Transparent PNG Images, For Free.jpg  83417
D:\Appstore\cat\ref\kiki\kiki _3.jpg                                                 25448
