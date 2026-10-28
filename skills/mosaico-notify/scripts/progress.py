#!/usr/bin/env python3
"""Report task progress or status to ESP-Mosaico companion screen widget pipeline."""
import argparse
import base64
import hashlib
import json
import os
import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from notify import discover, request

class WebSocketHubClient:
    """Zero-dependency RFC 6455 compliant WebSocket client for ESP-Mosaico Hub."""
    def __init__(self, ip, port=80, path="/ws/hub"):
        self.ip = ip
        self.port = port
        self.path = path
        self.sock = None
        self.buf = b""
        self.connected = False

    def connect(self, timeout=4.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((self.ip, self.port))

        raw_key = os.urandom(16)
        key_str = base64.b64encode(raw_key).decode('ascii')
        expected_accept = base64.b64encode(
            hashlib.sha1((key_str + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode('ascii')).digest()
        ).decode('ascii')

        req = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.ip}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key_str}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode('ascii'))

        header_data = b""
        while b"\r\n\r\n" not in header_data:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("Connection closed during WS handshake")
            header_data += chunk

        parts = header_data.split(b"\r\n\r\n", 1)
        headers_raw = parts[0].decode('utf-8', errors='ignore')
        self.buf = parts[1] if len(parts) > 1 else b""

        lines = headers_raw.split("\r\n")
        status_line = lines[0]
        if "101" not in status_line:
            raise ConnectionError(f"WS upgrade rejected: {status_line}")

        accept_header = None
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                if k.strip().lower() == "sec-websocket-accept":
                    accept_header = v.strip()
                    break

        if accept_header and accept_header != expected_accept:
            raise ConnectionError(f"Sec-WebSocket-Accept mismatch (expected {expected_accept}, got {accept_header})")

        self.connected = True

    def _send_frame(self, opcode, payload=b""):
        # RFC 6455 5.1: Client MUST mask all frames sent to server
        mask = os.urandom(4)
        length = len(payload)
        hdr = bytearray()
        hdr.append(0x80 | (opcode & 0x0F)) # FIN=1

        if length <= 125:
            hdr.append(0x80 | length)
        elif length <= 65535:
            hdr.append(0x80 | 126)
            hdr.extend(length.to_bytes(2, 'big'))
        else:
            hdr.append(0x80 | 127)
            hdr.extend(length.to_bytes(8, 'big'))

        hdr.extend(mask)
        masked_payload = bytearray(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(hdr + masked_payload)

    def _read_exact(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("WS socket closed unexpectedly")
            self.buf += chunk
        res = self.buf[:n]
        self.buf = self.buf[n:]
        return res

    def wait_task_action(self, task_id, timeout=60):
        self.sock.settimeout(timeout)
        deadline = time.time() + timeout
        while time.time() < deadline:
            hdr = self._read_exact(2)
            b1, b2 = hdr[0], hdr[1]
            opcode = b1 & 0x0F
            masked = (b2 & 0x80) != 0
            payload_len = b2 & 0x7F
            if payload_len == 126:
                ext = self._read_exact(2)
                payload_len = int.from_bytes(ext, 'big')
            elif payload_len == 127:
                ext = self._read_exact(8)
                payload_len = int.from_bytes(ext, 'big')
            mask_key = self._read_exact(4) if masked else None
            payload = self._read_exact(payload_len)
            if masked:
                payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

            if opcode == 0x8: # Close
                break
            elif opcode == 0x9: # Ping -> Pong with identical payload, masked
                self._send_frame(0xA, payload)
            elif opcode == 0x1: # Text
                try:
                    msg = json.loads(payload.decode('utf-8', errors='replace'))
                    if msg.get('type') == 'event' and msg.get('event') == 'task.action':
                        if not task_id or msg.get('id') == task_id:
                            return msg
                except Exception:
                    pass
        return None

    def close(self):
        if self.sock:
            try:
                self._send_frame(0x8, b"")
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
            self.connected = False

def main():
    p = argparse.ArgumentParser(description="Report task progress to Mosaico screen")
    p.add_argument("--id", default=None, help="Unique task/conversation identifier (decided by agent)")
    p.add_argument("--title", default=None, help="Task title on screen (recommended: <Agent>:<Session>-<Task>, concise <=22 CJK chars)")
    p.add_argument("--agent", default=None, help="Optional agent identity (e.g. Antigravity, Codex)")
    p.add_argument("--avatar", default=None, help="Explicit working-face key; empty string resets to generic")
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
    p.add_argument("--timeout", type=int, default=60, help="Confirmation wait timeout in seconds (default: 60)")
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
    if args.avatar is not None:
        payload["avatar"] = args.avatar
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

    # Connect WebSocket FIRST to eliminate event omission window
    ws = None
    if args.wait_confirm:
        try:
            ws = WebSocketHubClient(ip)
            ws.connect(timeout=4.0)
        except Exception:
            ws = None

    try:
        res = request(ip, "/api/widget", json.dumps(payload).encode("utf-8"), timeout=3)
    except Exception as e:
        if ws:
            ws.close()
        print(f"Error reporting progress: {e}", file=sys.stderr)
        sys.exit(2)

    if args.wait_confirm:
        decision_event = None
        try:
            if ws and ws.connected:
                decision_event = ws.wait_task_action(task_id, timeout=args.timeout)
            else:
                # If WS was unavailable, fallback to bounded HTTP polling with strict deadline
                deadline = time.time() + args.timeout
                while time.time() < deadline:
                    time.sleep(0.5)
                    st = request(ip, "/api/widget", timeout=3)
                    for it in st.get("agents", []):
                        if it.get("id") == task_id:
                            res_val = it.get("action", {}).get("result")
                            if res_val:
                                decision_event = {"choice": res_val, "action": res_val, "trigger": "http", "id": task_id}
                                break
                    if decision_event:
                        break
        finally:
            if ws:
                ws.close()

        if decision_event:
            print(json.dumps({
                "ip": ip,
                "decision": decision_event.get("choice", decision_event.get("action")),
                "trigger": decision_event.get("trigger", "ws"),
                "task_id": decision_event.get("id", task_id),
                "event": decision_event
            }))
            return
        else:
            print(json.dumps({
                "ip": ip,
                "error": "timeout",
                "message": f"Confirmation timed out after {args.timeout}s without user input"
            }), file=sys.stderr)
            sys.exit(3)

    print(json.dumps({"ip": ip, "widget": res}))

if __name__ == "__main__":
    main()
