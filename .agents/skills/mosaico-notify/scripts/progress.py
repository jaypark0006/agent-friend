#!/usr/bin/env python3
"""Report task progress or status to ESP-Mosaico companion screen widget pipeline."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from notify import discover, request

def main():
    p = argparse.ArgumentParser(description="Report task progress to Mosaico screen")
    p.add_argument("--id", default=None, help="Unique task/conversation identifier (decided by agent)")
    p.add_argument("--title", default=None, help="Task title displayed on screen (decided by agent)")
    p.add_argument("--agent", default=None, help="Optional agent identity (e.g. Antigravity, Codex)")
    p.add_argument("--status", default="", help="Current action description")
    p.add_argument("--progress", type=int, default=-1, help="0..100 progress percentage, or -1")
    p.add_argument("--color", default="#39e69d", help="Theme hex color")
    p.add_argument("--badge", default=None, help="Badge pill (e.g. RUNNING, DONE)")
    p.add_argument("--done", action="store_true", help="Mark task as completed")
    p.add_argument("--delete", action="store_true", help="Remove task from screen")
    p.add_argument("--confirm", action="store_true", help="Request physical touch confirmation from user on screen")
    p.add_argument("--btn1", default="Approve", help="Primary button text (default: Approve)")
    p.add_argument("--btn2", default="Cancel", help="Secondary button text (default: Cancel)")
    p.add_argument("--wait-confirm", action="store_true", help="Block until user touches a button on the screen")
    p.add_argument("--led", choices=["breathe", "chase", "marquee", "rainbow", "alert", "warning", "success", "solid", "off"], default=None, help="Trigger subboard LED animation")
    p.add_argument("--ip", default=None, help="Device IP candidate")
    args = p.parse_args()

    ip = discover(args.ip)
    if not ip:
        print("Device not found on local network", file=sys.stderr)
        sys.exit(1)

    task_id = args.id or "task-1"
    task_title = args.title or (f"[{args.agent}] Task" if args.agent else "Task")

    payload = {
        "id": task_id,
        "title": task_title,
        "status": args.status,
        "progress": args.progress,
        "color": args.color,
        "show": True
    }
    if args.badge:
        payload["badge"] = args.badge
    elif args.agent:
        payload["badge"] = args.agent
    if args.confirm:
        payload["action"] = {"type": "confirm", "options": [args.btn1, args.btn2]}
    if args.done or args.progress >= 100:
        payload["done"] = True
    elif args.progress >= 0:
        payload["done"] = False
    if args.delete:
        payload["delete"] = True

    # Synchronize interaction subboard LED effect
    led_effect = args.led
    if not led_effect:
        if args.confirm:
            led_effect = "alert"
        elif args.done or args.progress >= 100:
            led_effect = "success"
    if led_effect:
        try:
            from led import hex_to_rgb
            led_payload = {"slot": "right", "effect": led_effect}
            if args.color and led_effect not in ["rainbow", "off"]:
                led_payload["color"] = hex_to_rgb(args.color)
            request(ip, "/api/interact/leds", json.dumps(led_payload).encode("utf-8"), timeout=2)
        except Exception:
            pass

    try:
        res = request(ip, "/api/widget", json.dumps(payload).encode("utf-8"), timeout=3)
        if args.wait_confirm:
            import time
            while True:
                time.sleep(0.5)
                st = request(ip, "/api/widget", timeout=3)
                for it in st.get("agents", []):
                    if it.get("id") == task_id:
                        res_val = it.get("action", {}).get("result")
                        if res_val:
                            print(json.dumps({"ip": ip, "decision": res_val, "agent": it}))
                            return
        print(json.dumps({"ip": ip, "widget": res}))
    except Exception as e:
        print(f"Error reporting progress: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
