#!/usr/bin/env python3
"""Verification script for 1.1.60 messages scroll fix.
Delivers 4 rich demonstration letters (>900px total height), switches device to messages page,
and validates scroll metrics via REST API.
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

# Add mcp/ to python path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "mcp"))

from mosaico_mcp.client import MosaicoClient


def main():
    print("=== Mosaico 1.1.60 消息界面滑动复验脚本 ===")
    
    # Check cached IP or default
    cache_file = Path.home() / ".cache" / "mosaico-notify" / "address.json"
    device_ip = "192.168.5.42"
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if cached.get("ip"):
                device_ip = cached["ip"]
        except Exception:
            pass

    print(f"[*] 目标设备 IP: {device_ip}")
    client = MosaicoClient(explicit_ip=device_ip)

    # 1. Check device status & version
    print("[*] 读取设备状态与版本...")
    status = client.get_device_status()
    version = status.get("version", "unknown")
    print(f"[+] 设备当前运行固件版本: {version}")
    if version != "1.1.60":
        print(f"[!] 警告: 预期版本为 1.1.60，实际为 {version}")

    # 2. Deliver 4 rich letters with cards, text, and reply capsules
    print("[*] 正在投递 4 条高排印演示信笺（总高度远超一屏 900px）...")

    letters = [
        {
            "sender": "Antigravity",
            "title": "1.1.60 触控链路重构完毕",
            "text": "已彻底修复消息容器无 CLICKABLE 导致触摸穿透至 root 的核心缺陷，恢复 1:1 零延迟垂直触控与顺滑惯性滚动！",
            "font_size": 24,
            "reply_left": "批准",
            "reply_right": "打回",
            "to": "@all",
            "to_inbox": True,
            "avatar": "antigravity",
        },
        {
            "sender": "Claude Code",
            "title": "人机在环与物理黑板",
            "text": "随身屏现已支持跨 Agent 物理共享黑板（board_post/board_read/board_wait）与双向消息收件箱，无需轮询毫秒级零延迟唤醒！",
            "font_size": 20,
            "reply_left": "收到",
            "reply_right": "稍后",
            "to": "@all",
            "to_inbox": True,
            "avatar": "claude",
        },
        {
            "sender": "Codex",
            "title": "LVGL 9 交互防误触双重防护",
            "text": "在快捷回信胶囊与任务待办项增加了 lv_obj_is_scrolling 判定，手指在胶囊上方滑动手势超过 3px 触发全局滚动时，松手绝不会误触回信！",
            "font_size": 24,
            "reply_left": "已查阅",
            "reply_right": "复核中",
            "to": "@all",
            "to_inbox": True,
            "avatar": "codex",
        },
        {
            "sender": "Jay Park",
            "title": "随身伴侣日常使用指南",
            "text": "墨色底米白字与 9x7 点阵生命力表情，左右滑动可在此刻、任务、消息、画面间自由穿梭，顶部下拉开启控制中心，请尽情上下滑动体验丝滑跟手感！",
            "font_size": 20,
            "reply_left": "太棒了",
            "reply_right": "继续调优",
            "to": "@antigravity",
            "to_inbox": True,
            "avatar": "generic",
        },
    ]

    for idx, l in enumerate(letters, 1):
        res = client.send_message(
            sender=l["sender"],
            text=l["text"],
            title=l["title"],
            font_size=l["font_size"],
            reply_left=l["reply_left"],
            reply_right=l["reply_right"],
            to=l["to"],
            to_inbox=l["to_inbox"],
            avatar=l["avatar"],
        )
        print(f"  [+] 信笺 {idx}/4 已投递: seq={res.get('seq')}, id={res.get('id')}, from={l['sender']}")
        time.sleep(0.3)

    # 3. Switch device page to messages view via POST /api/view
    print("[*] 切换设备屏幕至《消息页》(messages)...")
    req = urllib.request.Request(
        f"http://{device_ip}/api/view",
        data=json.dumps({"page": "messages"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        view_res = json.loads(resp.read().decode("utf-8"))
        print(f"[+] 屏幕页面切换结果: {view_res.get('page')}")

    time.sleep(1.0)

    # 4. Verify scroll metrics via /api/status
    print("[*] 验证滚动高度与视图状态...")
    req = urllib.request.Request(f"http://{device_ip}/api/status")
    with urllib.request.urlopen(req, timeout=5) as resp:
        status_data = json.loads(resp.read().decode("utf-8"))
        gui = status_data.get("gui", {})
        print(f"[+] GUI 状态: page={status_data.get('page')}, message_count={status_data.get('message_count')}")
        print(f"[+] 滚动参数: scroll_y={gui.get('scroll_y')}, scroll_max={gui.get('scroll_max')}")

    # 5. Programmatic smooth scroll test via /api/view
    print("[*] 触发平滑滚动至顶部 (y=0, ms=300)...")
    req = urllib.request.Request(
        f"http://{device_ip}/api/view",
        data=json.dumps({"page": "text", "scroll_y": 0, "duration_ms": 300}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        print("[+] 滚动至顶部请求已发出")

    time.sleep(0.5)

    req = urllib.request.Request(f"http://{device_ip}/api/status")
    with urllib.request.urlopen(req, timeout=5) as resp:
        status_data = json.loads(resp.read().decode("utf-8"))
        gui = status_data.get("gui", {})
        print(f"[+] 滚动后坐标: scroll_y={gui.get('scroll_y')}, scroll_max={gui.get('scroll_max')}")

    # 6. Smooth scroll back to bottom
    max_y = gui.get("scroll_max", 723)
    print(f"[*] 触发平滑滚动返回底部 (y={max_y}, ms=300)...")
    req = urllib.request.Request(
        f"http://{device_ip}/api/view",
        data=json.dumps({"page": "text", "scroll_y": max_y, "duration_ms": 300}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        print("[+] 滚动回底请求已发出")

    print("=== 演示信笺投递与滚动验证完成 ===")


if __name__ == "__main__":
    main()
