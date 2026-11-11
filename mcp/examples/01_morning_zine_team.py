#!/usr/bin/env python3
"""示例配方 01：《晨间精排中文私刊团（Morning Zine & 1s Read Receipt Loop）》

展示场景：
- 3 人研究小队（RSS 捕手 + 论文精读员 + 私刊主编）每天清晨用 Mosaico 的 7,318 字出版级平滑字库
  （GB2312 一二级汉字 + 日文平片假名，#0C0B0A 墨黑底 + #F5F1EA 米白字）往《消息页》投递 3 张精排短笺；
- 每张短笺绑定副板物理左/右键快捷回信胶囊（`[L] 继续深挖` / `[R] 下一篇`）；
- 读取人类的 `1秒真·已读 (read: true)` 与顶部橙色实体键 `⭐ 星标 (starred: true)` 回执，动态调整选题。

运行方式：
  PYTHONPATH=mcp python3 mcp/examples/01_morning_zine_team.py [--ip 192.168.5.92]
  PYTHONPATH=mcp python3 mcp/examples/01_morning_zine_team.py --wait-reply 30
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mosaico_mcp import MosaicoClient  # noqa: E402

MORNING_CARDS = [
    {
        "sender": "论文精读员",
        "avatar": "claude",
        "title": "晨刊 01 · 端侧小模型推理新范式",
        "font_size": 24,
        "text": (
            "今日 arXiv 焦点：通过 4-bit 混合激活量化与投机解码协同，3B 级模型在边缘芯片上的首字延迟再降 42%。\n"
            "核心启示：本地智能体无需事事上云，端云分层路由已成定局。"
        ),
        "reply_left": "继续深挖",
        "reply_right": "下一篇",
    },
    {
        "sender": "私刊主编",
        "avatar": "antigravity",
        "title": "晨刊 02 · 硬件伴侣的「安静美学」",
        "font_size": 24,
        "text": (
            "真正耐看的桌面器物从不靠弹窗刷存在感。\n"
            "平时是一页温润不刺眼的墨底短笺，当你目光停留一秒，后台团队便默契知晓「你已阅过」。"
        ),
        "reply_left": "深以为然",
        "reply_right": "下一篇",
    },
    {
        "sender": "日语闪卡君",
        "avatar": "gemini",
        "title": "晨刊 03 · 今日日语词汇（假名原生渲染）",
        "font_size": 24,
        "text": (
            "【木漏れ日】（こもれび · Komorebi）\n"
            "释义：林间树叶缝隙洒落的斑驳阳光。\n"
            "例句：朝の散歩で、美しい木漏れ日を見つけた。"
        ),
        "reply_left": "加入生词本",
        "reply_right": "已掌握",
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Mosaico 2.0 晨间精排中文私刊团示例")
    parser.add_argument("--ip", default=None, help="随身屏 IP（省略则自动经 mosaico.local / SSDP / ARP 发现）")
    parser.add_argument("--port", type=int, default=None, help="端口（默认 80）")
    parser.add_argument("--wait-reply", type=float, default=0.0, help="投递后静默监听按键回执秒数（默认 0 不等待）")
    args = parser.parse_args()

    client = MosaicoClient(explicit_ip=args.ip, explicit_port=args.port)
    try:
        # 1. 先查看昨日收件箱与 1 秒已读/星标回执
        before = client.read_inbox_and_receipts(unread_only=False)
        print(
            f"[1/4] 已连接随身屏 {before['device_ip']} · 历史已读 {before['read_count']} 篇 / "
            f"星标 {before['starred_count']} 篇 / 人类来信 {before['inbox_count']} 条"
        )

        # 2. 主编入席，点亮柔和蓝紫呼吸灯
        client.update_agent_seat(
            agent_id="zine-chief",
            agent_name="私刊主编",
            title="编撰晨间私刊",
            session="Morning-Zine",
            avatar="antigravity",
            status="正在排版 3 张今日中文短笺与假名闪卡...",
            state="working",
            led="breathe",
        )

        # 3. 依次投递 3 张 7,318 字精排卡片
        last_seq = 0
        for idx, card in enumerate(MORNING_CARDS, start=1):
            res = client.send_message(**card)
            last_seq = res["seq"]
            print(f"[2/4] 已投递第 {idx} 张卡片 (seq={last_seq})：《{card['title']}》")
            time.sleep(0.15)

        # 4. 切换圆桌席位为 `review`（等你清晨归座翻阅）
        client.update_agent_seat(
            agent_id="zine-chief",
            agent_name="私刊主编",
            title="今日晨刊已送达",
            session="Morning-Zine",
            avatar="antigravity",
            status="3 篇短笺已在消息页就绪，按 L 键可要求继续深挖",
            state="review",
            led="success",
        )
        print("[3/4] 晨刊投递完毕！席位已置为「等你回来 (review)」。")

        if args.wait_reply > 0:
            print(f"[4/4] 正在通过 /ws/hub 零轮询守候您的按键回执（最长 {args.wait_reply}s）...")
            wake = client.board_wait(
                agent_name="私刊主编",
                since_seq=last_seq,
                mentions_only=False,
                timeout_sec=args.wait_reply,
            )
            print(json.dumps(wake, ensure_ascii=False, indent=2))
        else:
            after = client.read_inbox_and_receipts(unread_only=False)
            print(f"[4/4] 当前最新黑板序号 head_seq={after['head_seq']}，未读卡片 {after['unread_count']} 张。")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
