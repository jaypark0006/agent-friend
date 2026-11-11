#!/usr/bin/env python3
"""示例配方 03：《会说人话的异动简报 & 二十四节气生成式画框（Market Tide & Solar Canvas）》

展示场景：
- 告别只会滚冰冷价格数字的单功能副屏！
- 模式 A（`--mode tide`）：当关注的开源仓库 Star 激增或核心资产异动时，用一句话讲清「为什么动 + 背后驱动力」投递《消息页》，
  同步生成 480x480 深色极客趋势海报推入《画面页》并点亮 50Hz `chase` 流光追逐灯效；
- 模式 B（`--mode solar`）：二十四节气「霜降 / 立冬」一诗一画数字画框，推送 480x480 意境画面与古典诗词签，联动柔和呼吸灯。
- 若本机装有 `Pillow` 自动绘制精美 480x480 矢量级卡片；若零第三方库环境则自动退化为纯标准库 ITU-T.81 480x480 纯色氛围幕布！

运行方式：
  PYTHONPATH=mcp python3 mcp/examples/03_market_tide_and_solar_canvas.py --mode tide [--ip 192.168.5.92]
  PYTHONPATH=mcp python3 mcp/examples/03_market_tide_and_solar_canvas.py --mode solar [--ip 192.168.5.92]
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mosaico_mcp import MosaicoClient  # noqa: E402
from mosaico_mcp.canvas import make_solid_jpeg_480  # noqa: E402


def render_480_poster(mode: str) -> bytes:
    """用 Pillow 绘制 480x480 深色数据趋势图/节气画框；无 Pillow 时使用纯标准库 480x480 JPEG。"""
    try:
        from PIL import Image, ImageDraw  # type: ignore[import-not-found]
    except ImportError:
        return make_solid_jpeg_480((14, 24, 34) if mode == "tide" else (20, 16, 14))

    if mode == "tide":
        img = Image.new("RGB", (480, 480), "#0C0B0A")
        draw = ImageDraw.Draw(img)
        # 绘制深色网格与平滑上扬潮汐折线
        for y in range(80, 420, 64):
            draw.line([(40, y), (440, y)], fill="#1E2630", width=1)
        points = [
            (44, 360),
            (108, 342),
            (172, 348),
            (236, 295),
            (300, 260),
            (364, 178),
            (436, 112),
        ]
        # 填充折线下方微光带与主趋势线
        poly = points + [(436, 400), (44, 400)]
        draw.polygon(poly, fill="#123026")
        draw.line(points, fill="#39E69D", width=5)
        for px, py in points:
            draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill="#F5F1EA", outline="#39E69D", width=2)
        draw.rounded_rectangle((28, 28, 452, 452), radius=24, outline="#2A3642", width=2)
    else:
        # 二十四节气 · 极简东方几何山水圆月意境画框
        img = Image.new("RGB", (480, 480), "#0C0B0A")
        draw = ImageDraw.Draw(img)
        draw.ellipse((270, 74, 386, 190), fill="#E8B059")
        draw.polygon([(0, 390), (140, 265), (295, 365), (480, 245), (480, 480), (0, 480)], fill="#1A2228")
        draw.polygon([(0, 430), (195, 325), (360, 405), (480, 340), (480, 480), (0, 480)], fill="#11171C")
        draw.rounded_rectangle((24, 24, 456, 456), radius=20, outline="#3A332A", width=2)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, progressive=False, subsampling=2)
    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description="Mosaico 2.0 会说人话的异动简报 & 节气画框示例")
    parser.add_argument("--mode", choices=("tide", "solar"), default="tide", help="tide=异动简报 / solar=一诗一画节气画框")
    parser.add_argument("--ip", default=None, help="随身屏 IP（省略则自动发现）")
    parser.add_argument("--port", type=int, default=None, help="端口（默认 80）")
    args = parser.parse_args()

    client = MosaicoClient(explicit_ip=args.ip, explicit_port=args.port)
    try:
        jpeg_data = render_480_poster(args.mode)
        if args.mode == "tide":
            msg = client.send_message(
                sender="潮汐哨兵",
                avatar="codex",
                title="异动解读 · 开源仓库单日 +620 Stars",
                font_size=24,
                text=(
                    "驱动原因：标准 MCP 接入指南刚登上 Hacker News 首页第 4 位，"
                    "来自 Claude Desktop 与 Cursor 社区的开发者实测讨论正在集中爆发。\n"
                    "建议动作：优先回复置顶 Issue 中的 USB 直连提问。"
                ),
                reply_left="展开详情",
                reply_right="知悉静默",
            )
            canvas_res = client.push_canvas(
                image_path_or_base64=jpeg_data,
                led_effect="chase",
                led_color="#39e69d",
                switch_to_canvas=True,
            )
        else:
            msg = client.send_message(
                sender="节气策展人",
                avatar="claude",
                title="立冬 · 一诗一画",
                font_size=28,
                align="center",
                text="冻笔新诗懒写，寒炉美酒时温。\n醉看墨花月白，恍疑雪满前村。\n—— 李白《立冬》",
                reply_left="收藏此画",
                reply_right="换一首诗",
            )
            canvas_res = client.push_canvas(
                image_path_or_base64=jpeg_data,
                led_effect="breathe",
                led_color="#e8b059",
                switch_to_canvas=True,
            )

        print(json.dumps({"message": msg, "canvas": canvas_res}, ensure_ascii=False, indent=2))
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
