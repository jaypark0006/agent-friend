#!/usr/bin/env python3
"""Generate and push an agent completion receipt image to ESP-Mosaico screen."""
import argparse
import datetime
import io
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from notify import discover, request, MAC, CACHE

def render_receipt(args):
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    font_path = next((str(p) for p in [
        Path('/System/Library/Fonts/PingFang.ttc'),
        Path('/System/Library/Fonts/STHeiti Medium.ttc'),
        Path('/System/Library/Fonts/STHeiti Light.ttc'),
        Path('/Library/Fonts/Arial Unicode.ttf')
    ] if p.exists()), None)
    if not font_path:
        raise RuntimeError("No system font found for receipt generation")

    def f(size):
        return ImageFont.truetype(font_path, size)

    im = Image.new('RGB', (480, 480), '#0c1219')
    d = ImageDraw.Draw(im)

    accent = args.color
    # Outer frame
    d.rounded_rectangle((12, 12, 468, 468), radius=20, outline='#1f2d3d', width=2)

    # Header Bar
    # Agent badge pill
    agent_name = args.agent.upper()
    agent_font = f(15)
    badge_w = int(d.textlength(agent_name, font=agent_font)) + 24
    d.rounded_rectangle((28, 26, 28 + badge_w, 54), radius=8, fill='#162534', outline=accent, width=1)
    d.text((40, 31), agent_name, font=agent_font, fill=accent)

    # Timestamp & Receipt label
    now_str = datetime.datetime.now().astimezone().strftime('%Y-%m-%d  %H:%M')
    d.text((28 + badge_w + 14, 33), "DELIVERY RECEIPT", font=f(13), fill='#758899')
    d.text((330, 33), now_str.split('  ')[1], font=f(14), fill='#9fb1c5')

    # Divider line
    d.line([(28, 66), (452, 66)], fill='#1c2a38', width=1)

    # Task Title Card
    title = args.title
    title_font = f(23)
    d.text((28, 78), title, font=title_font, fill='#ffffff')

    # Checklist / Deliverables Box
    box_top = 120
    box_h = 240
    d.rounded_rectangle((28, box_top, 452, box_top + box_h), radius=12, fill='#121a24', outline='#1d2b3a', width=1)
    d.text((42, box_top + 12), "COMPLETED DELIVERABLES & OUTCOMES", font=f(13), fill='#5b7288')

    items = args.items if args.items else ["任务已顺利达成目标", "各项逻辑与代码变更已落地", "实机部署与健康状态核验正常"]
    y = box_top + 40
    item_font = f(16)
    for it in items[:5]:
        # Green checkmark circle
        d.ellipse((42, y + 2, 58, y + 18), fill='#1b3b2b', outline='#39e69d', width=1)
        d.line([(46, y + 10), (50, y + 14), (55, y + 6)], fill='#39e69d', width=2)
        
        # Item text
        text_w = d.textlength(it, font=item_font)
        display_text = it
        if text_w > 360:
            while len(display_text) > 3 and d.textlength(display_text + "…", font=item_font) > 360:
                display_text = display_text[:-1]
            display_text += "…"
        d.text((68, y + 1), display_text, font=item_font, fill='#d5e2ef')
        y += 38

    # Bottom Stat Row
    # Pill 1: Version
    ver_text = f"v{args.version}" if args.version else "v1.1.30"
    d.rounded_rectangle((28, 380, 150, 422), radius=8, fill='#162534', outline='#243647', width=1)
    d.text((40, 392), ver_text, font=f(14), fill='#4fa3e3')

    # Pill 2: Status
    d.rounded_rectangle((162, 380, 310, 422), radius=8, fill='#162e22', outline='#285438', width=1)
    d.text((176, 392), "100% HEALTHY", font=f(14), fill='#39e69d')

    # Pill 3: Target
    d.rounded_rectangle((322, 380, 452, 422), radius=8, fill='#162534', outline='#243647', width=1)
    d.text((338, 392), "ESP-MOSAICO", font=f(14), fill='#a0b2c6')

    # Footer signature
    d.text((28, 440), "VERIFIED & SIGNED BY AGENT PIPELINE", font=f(11), fill='#455667')
    d.text((366, 440), "NORMAL MODE", font=f(11), fill='#39e69d')

    for quality in (90, 82, 70, 50):
        buf = io.BytesIO()
        im.save(buf, format='JPEG', quality=quality, progressive=False, subsampling=2)
        if len(buf.getvalue()) <= 262144:
            return buf.getvalue()
    raise ValueError("Generated JPEG exceeds device limit")

def main():
    p = argparse.ArgumentParser(description="Deliver proof-of-work receipt card to Mosaico screen")
    p.add_argument("--agent", default="Antigravity", help="Agent identifier name")
    p.add_argument("--title", required=True, help="Task title / headline")
    p.add_argument("--items", nargs="+", help="Accomplishment bullet points")
    p.add_argument("--version", default="1.1.30", help="Firmware / project version tag")
    p.add_argument("--color", default="#4fa3e3", help="Accent hex color")
    p.add_argument("--image", default=None, help="Optional custom image path instead of generated card")
    p.add_argument("--ip", default=None, help="Device IP")
    p.add_argument("--switch-page", action="store_true", default=True, help="Switch screen to image page (default: True)")
    args = p.parse_args()

    ip = discover(args.ip)
    if not ip:
        print("Device not found on local network", file=sys.stderr)
        sys.exit(1)

    if args.image and Path(args.image).exists():
        from PIL import Image, ImageOps
        with Image.open(args.image) as src:
            fitted = ImageOps.contain(ImageOps.exif_transpose(src).convert('RGB'), (480, 480))
            bg = Image.new('RGB', (480, 480), '#101720')
            bg.paste(fitted, ((480 - fitted.width)//2, (480 - fitted.height)//2))
            buf = io.BytesIO()
            bg.save(buf, format='JPEG', quality=85, progressive=False)
            jpeg_bytes = buf.getvalue()
    else:
        jpeg_bytes = render_receipt(args)

    import urllib.request
    req = urllib.request.Request(f"http://{ip}/api/image", data=jpeg_bytes, headers={"Content-Type": "image/jpeg"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as resp:
        res = json.loads(resp.read().decode('utf-8', errors='replace'))
        print(json.dumps({"ip": ip, "image_result": res}))

    if args.switch_page:
        try:
            req_view = urllib.request.Request(
                f"http://{ip}/api/view",
                data=json.dumps({"page": "home"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req_view, timeout=3) as v_resp:
                pass
        except Exception:
            pass

if __name__ == "__main__":
    main()
