#!/usr/bin/env python3
"""Report task progress or status to ESP-Mosaico companion screen widget pipeline."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from notify import discover, request

def wait_confirm_ws(ip, task_id, timeout=120):
    import socket, base64, os, json, time
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3.0)
    sock.connect((ip, 80))
    key = base64.b64encode(os.urandom(16)).decode('ascii')
    req = (
        f"GET /ws/hub HTTP/1.1\r\n"
        f"Host: {ip}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(req.encode('ascii'))

    header_data = b""
    while b"\r\n\r\n" not in header_data:
        chunk = sock.recv(1024)
        if not chunk:
            raise ConnectionError("Connection closed during WS handshake")
        header_data += chunk

    status_line = header_data.split(b"\r\n")[0]
    if b"101" not in status_line:
        raise ConnectionError(f"WS handshake failed: {status_line.decode('utf-8', errors='ignore')}")

    buf = header_data.split(b"\r\n\r\n", 1)[1]
    sock.settimeout(timeout)

    def read_exact(n):
        nonlocal buf
        while len(buf) < n:
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("Socket EOF")
            buf += chunk
        res = buf[:n]
        buf = buf[n:]
        return res

    deadline = time.time() + timeout
    while time.time() < deadline:
        hdr = read_exact(2)
        b1, b2 = hdr[0], hdr[1]
        opcode = b1 & 0x0F
        masked = (b2 & 0x80) != 0
        payload_len = b2 & 0x7F
        if payload_len == 126:
            ext = read_exact(2)
            payload_len = int.from_bytes(ext, 'big')
        elif payload_len == 127:
            ext = read_exact(8)
            payload_len = int.from_bytes(ext, 'big')
        mask_key = read_exact(4) if masked else None
        payload = read_exact(payload_len)
        if masked:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

        if opcode == 0x8:
            break
        elif opcode == 0x9:
            pong_hdr = bytes([0x8A, 0x00])
            sock.sendall(pong_hdr)
        elif opcode == 0x1:
            try:
                msg = json.loads(payload.decode('utf-8', errors='replace'))
                if msg.get('type') == 'event' and msg.get('event') == 'task.action':
                    if not task_id or msg.get('id') == task_id:
                        sock.close()
                        return msg
            except Exception:
                pass
    sock.close()
    return None

def main():
    p = argparse.ArgumentParser(description="Report task progress to Mosaico screen")
    p.add_argument("--id", default=None, help="Unique task/conversation identifier (decided by agent)")
    p.add_argument("--title", default=None, help="Task title on screen (recommended: <Agent>:<Session>-<Task>, concise <=22 CJK chars)")
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
            try:
                # 1. Instantaneous WebSocket reverse event reception (ws://<ip>/ws/hub)
                ws_event = wait_confirm_ws(ip, task_id, timeout=120)
                if ws_event:
                    print(json.dumps({
                        "ip": ip,
                        "decision": ws_event.get("choice", ws_event.get("action")),
                        "trigger": ws_event.get("trigger", "ws"),
                        "task_id": ws_event.get("id"),
                        "event": ws_event
                    }))
                    return
            except Exception:
                pass
            # 2. Fallback to HTTP polling if WebSocket is unavailable
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
