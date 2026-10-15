#!/usr/bin/env python3
"""Report task progress or status to ESP-Mosaico companion screen widget pipeline."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from notify import discover, request

def main():
    p = argparse.ArgumentParser(description="Report agent progress to Mosaico screen")
    p.add_argument("--id", default="codex", help="Unique agent identifier")
    p.add_argument("--title", default="Codex Assistant", help="Agent title")
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
    p.add_argument("--ip", default=None, help="Device IP candidate")
    args = p.parse_args()

    ip = discover(args.ip)
    if not ip:
        print("Device not found on local network", file=sys.stderr)
        sys.exit(1)

    payload = {
        "id": args.id,
        "title": args.title,
        "status": args.status,
        "progress": args.progress,
        "color": args.color,
        "show": True
    }
    if args.badge:
        payload["badge"] = args.badge
    if args.confirm:
        payload["action"] = {"type": "confirm", "options": [args.btn1, args.btn2]}
    if args.done or args.progress >= 100:
        payload["done"] = True
    if args.delete:
        payload["delete"] = True

    try:
        res = request(ip, "/api/widget", json.dumps(payload).encode("utf-8"), timeout=3)
        if args.wait_confirm:
            import time
            while True:
                time.sleep(0.5)
                st = request(ip, "/api/widget", timeout=3)
                for it in st.get("agents", []):
                    if it.get("id") == args.id:
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
