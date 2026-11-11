"""Comprehensive unit & stdio integration tests for `mosaico-mcp` (zero external dependencies).

Covers:
- Standard MCP JSON-RPC 2.0 lifecycle (`initialize`, `notifications/initialized`, `ping`,
  `tools/list`, `tools/call`, `resources/list`, `resources/read`, `prompts/list`, `prompts/get`)
- Single multiplexed `/ws/hub` RFC 6455 connection (client masking, Ping/Pong, 7-socket safety)
- Bidirectional `#send` inbox, 1-second `read: true` receipts, L/R button replies, `⭐` stars,
  and proactive `notifications/resources/updated` pushes
- Physical Blackboard (`board_post`, `board_read`, `board_wait` zero-polling `<50ms` wakeup)
- `ask_human_decision` physical L/R arbitration + strict timeout non-approval guarantee
- `update_agent_seat` Roundtable states + `push_canvas` 480x480 baseline JPEG & 50Hz LED sync
- Real `python3 -m mosaico_mcp` subprocess `stdio` pipe E2E verification
"""

from __future__ import annotations

import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from typing import Any
import unittest
import urllib.parse

MCP_ROOT = Path(__file__).resolve().parents[1]
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

from mosaico_mcp import MosaicoClient, MosaicoMCPServer, discover_device, utf8_clip  # noqa: E402
from mosaico_mcp.canvas import make_solid_jpeg_480, validate_baseline_jpeg_480  # noqa: E402

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class _QuietThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class MockMosaicoDevice:
    """In-memory mock of ESP-Mosaico 2.0 HTTP + RFC 6455 `/ws/hub` firmware contract."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.seq_counter = 0
        self.frame_counter = 0
        self.active_page = "now"
        self.messages: list[dict[str, Any]] = []
        self.agents: dict[str, dict[str, Any]] = {}
        self.leds: list[dict[str, Any]] = []
        self.frames: list[bytes] = []
        self.ws_clients: set[socket.socket] = set()
        self.max_concurrent_ws = 0
        self.total_ws_upgrades = 0
        self.pong_payloads: list[bytes] = []
        self.http_board_reads = 0

        device = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt: str, *args: Any) -> None:
                return

            def _send_json(self, code: int, obj: dict[str, Any]) -> None:
                raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _read_body(self) -> bytes:
                length = int(self.headers.get("Content-Length") or "0")
                return self.rfile.read(length) if length > 0 else b""

            def do_GET(self) -> None:  # noqa: N802
                parsed = urllib.parse.urlsplit(self.path)
                route = parsed.path
                query = dict(urllib.parse.parse_qsl(parsed.query))

                if route == "/ws/hub" and self.headers.get("Upgrade", "").lower() == "websocket":
                    self._handle_ws_upgrade()
                    return

                if route == "/api/status":
                    with device.lock:
                        page = device.active_page
                    self._send_json(
                        200,
                        {
                            "app": "lan_screen",
                            "version": "1.1.60",
                            "ip": "127.0.0.1",
                            "page": page,
                        },
                    )
                    return

                if route == "/api/widget":
                    self._send_json(200, device._widget_snapshot())
                    return

                if route == "/api/board":
                    with device.lock:
                        device.http_board_reads += 1
                    since = int(query.get("since", "0"))
                    limit = int(query.get("limit", "32"))
                    self._send_json(200, device._board_snapshot(since=since, limit=limit))
                    return

                if route == "/api/inbox":
                    unread_only = query.get("unread_only") in ("1", "true")
                    self._send_json(200, device._inbox_snapshot(unread_only=unread_only))
                    return

                if route == "/api/history":
                    since = int(query.get("since", "0"))
                    snap = device._board_snapshot(since=since, limit=64)
                    self._send_json(
                        200,
                        {
                            "page": device.active_page,
                            "messages": {
                                "count": len(snap["entries"]),
                                "unread": snap["unread_count"],
                                "entries": snap["entries"],
                            },
                            "images": {"count": len(device.frames), "entries": []},
                        },
                    )
                    return

                self._send_json(404, {"error": "not_found"})

            def do_POST(self) -> None:  # noqa: N802
                body = self._read_body()
                if self.path == "/api/frame":
                    res = device._accept_jpeg(body)
                    self._send_json(200 if res.get("ok", True) else 400, res)
                    return

                data = json.loads(body.decode("utf-8")) if body else {}
                if self.path == "/api/text":
                    self._send_json(200, device._post_text(data))
                    return
                if self.path == "/api/text/reply":
                    res = device.simulate_reply(
                        seq=int(data.get("id") or data.get("seq") or 0),
                        action=str(data.get("action") or "left"),
                        reply_text=str(data.get("reply_text") or ""),
                        trigger="web",
                    )
                    self._send_json(200, res)
                    return
                if self.path == "/api/widget":
                    self._send_json(200, device._update_widget(data))
                    return
                if self.path == "/api/view":
                    with device.lock:
                        device.active_page = str(data.get("page") or "now")
                    self._send_json(200, {"accepted": True})
                    return
                if self.path == "/api/interact/leds":
                    with device.lock:
                        device.leds.append(data)
                    self._send_json(202, {"accepted": len(device.leds)})
                    return

                self._send_json(404, {"error": "not_found"})

            def _handle_ws_upgrade(self) -> None:
                key = self.headers.get("Sec-WebSocket-Key", "")
                accept = base64.b64encode(
                    hashlib.sha1((key + _WS_GUID).encode("ascii")).digest()
                ).decode("ascii")
                self.send_response(101, "Switching Protocols")
                self.send_header("Upgrade", "websocket")
                self.send_header("Connection", "Upgrade")
                self.send_header("Sec-WebSocket-Accept", accept)
                self.end_headers()
                self.wfile.flush()

                conn = self.connection
                conn.settimeout(1.0)
                with device.lock:
                    device.ws_clients.add(conn)
                    device.total_ws_upgrades += 1
                    device.max_concurrent_ws = max(device.max_concurrent_ws, len(device.ws_clients))

                try:
                    device._ws_loop(conn)
                finally:
                    with device.lock:
                        device.ws_clients.discard(conn)
                    self.close_connection = True

        self._httpd = _QuietThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port: int = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        with self.lock:
            clients = list(self.ws_clients)
            self.ws_clients.clear()
        for c in clients:
            try:
                c.close()
            except OSError:
                pass
        self._httpd.shutdown()
        self._httpd.server_close()

    # --- Internal state & WS frame helpers ---
    @staticmethod
    def _ws_send_frame(conn: socket.socket, opcode: int, payload: bytes) -> None:
        hdr = bytearray([0x80 | (opcode & 0x0F)])
        n = len(payload)
        if n < 126:
            hdr.append(n)
        elif n <= 65535:
            hdr.append(126)
            hdr.extend(n.to_bytes(2, "big"))
        else:
            hdr.append(127)
            hdr.extend(n.to_bytes(8, "big"))
        conn.sendall(bytes(hdr) + payload)

    def broadcast_ws(self, obj: dict[str, Any]) -> None:
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        with self.lock:
            clients = list(self.ws_clients)
        for c in clients:
            try:
                self._ws_send_frame(c, 0x01, raw)
            except OSError:
                pass

    def send_ping_to_all(self, payload: bytes = b"mosaico-hb") -> None:
        with self.lock:
            clients = list(self.ws_clients)
        for c in clients:
            try:
                self._ws_send_frame(c, 0x09, payload)
            except OSError:
                pass

    def _ws_read_exact(self, conn: socket.socket, buf: bytearray, n: int) -> bytes:
        while len(buf) < n:
            chunk = conn.recv(4096)
            if not chunk:
                raise ConnectionError("EOF")
            buf.extend(chunk)
        out = bytes(buf[:n])
        del buf[:n]
        return out

    def _ws_loop(self, conn: socket.socket) -> None:
        buf = bytearray()
        while True:
            try:
                b1, b2 = self._ws_read_exact(conn, buf, 2)
            except (socket.timeout, TimeoutError):
                continue
            except OSError:
                break

            opcode = b1 & 0x0F
            masked = bool(b2 & 0x80)
            if not masked:
                # RFC 6455 §5.1: Server MUST reject unmasked client frames
                break
            length = b2 & 0x7F
            try:
                if length == 126:
                    length = int.from_bytes(self._ws_read_exact(conn, buf, 2), "big")
                elif length == 127:
                    length = int.from_bytes(self._ws_read_exact(conn, buf, 8), "big")
                mask_key = self._ws_read_exact(conn, buf, 4)
                masked_payload = self._ws_read_exact(conn, buf, length)
            except OSError:
                break

            payload = bytes(b ^ mask_key[i & 3] for i, b in enumerate(masked_payload))
            if opcode == 0x08:
                break
            if opcode == 0x0A:  # Pong
                with self.lock:
                    self.pong_payloads.append(payload)
                continue
            if opcode == 0x09:  # Ping
                self._ws_send_frame(conn, 0x0A, payload)
                continue
            if opcode == 0x02:  # Binary JPEG
                res = self._accept_jpeg(payload)
                ack = {"type": "ack", "command": "image", **res}
                self._ws_send_frame(conn, 0x01, json.dumps(ack).encode("utf-8"))
                continue
            if opcode == 0x01:
                req = json.loads(payload.decode("utf-8"))
                reply = self._handle_ws_command(req)
                self._ws_send_frame(conn, 0x01, json.dumps(reply, ensure_ascii=False).encode("utf-8"))

    def _handle_ws_command(self, req: dict[str, Any]) -> dict[str, Any]:
        cmd = str(req.get("type") or "")
        req_id = req.get("request_id")
        base: dict[str, Any] = {"type": "ack", "command": cmd, "request_id": req_id, "ok": True}
        if cmd == "ping":
            base["message"] = "pong"
            return base
        if cmd in ("text", "text.send", "board.post"):
            res = self._post_text(req)
            base.update(res)
            return base
        if cmd in ("widget", "widget.update"):
            w = self._update_widget(req)
            base["widget"] = w
            return base
        if cmd == "board.read":
            snap = self._board_snapshot(since=int(req.get("since", 0)), limit=int(req.get("limit", 20)))
            base.update(snap)
            return base
        if cmd == "get":
            topic = req.get("topic")
            if topic == "inbox":
                base["data"] = self._inbox_snapshot(unread_only=False)
                return base
            if topic == "status":
                base["data"] = {"app": "lan_screen", "version": "1.1.60", "page": self.active_page}
                return base
        if cmd == "view":
            with self.lock:
                self.active_page = str(req.get("page") or "now")
            return base
        if cmd == "led.set":
            with self.lock:
                self.leds.append(dict(req))
            return base
        return {"type": "ack", "command": cmd, "request_id": req_id, "ok": False, "error": "unknown"}

    def _post_text(self, data: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.seq_counter += 1
            seq = self.seq_counter
            entry = {
                "id": seq,
                "seq": seq,
                "time": str(data.get("time") or "09:30"),
                "timestamp_us": int(time.monotonic() * 1_000_000),
                "from": str(data.get("from") or ""),
                "to": str(data.get("to") or ""),
                "avatar": str(data.get("avatar") or ""),
                "title": str(data.get("title") or ""),
                "text": str(data.get("text") or ""),
                "font_size": int(data.get("font_size") or 24),
                "align": str(data.get("align") or "left"),
                "to_inbox": bool(data.get("to_inbox", False)),
                "read": False,
                "starred": False,
                "reply_left": str(data.get("reply_left") or ""),
                "reply_right": str(data.get("reply_right") or ""),
                "replied_action": "",
                "replied_text": "",
            }
            self.messages.append(entry)
            head_seq = self.seq_counter

        # Broadcast `board.post` unconditionally (+ `inbox.message` if `to_inbox=True`) per Contract v2
        self.broadcast_ws({"type": "event", "event": "board.post", **entry})
        if entry["to_inbox"]:
            self.broadcast_ws(
                {
                    "type": "event",
                    "event": "inbox.message",
                    "id": seq,
                    "seq": seq,
                    "from": entry["from"],
                    "title": entry["title"],
                    "text": entry["text"],
                    "time": entry["time"],
                    "timestamp_us": entry["timestamp_us"],
                }
            )
        return {
            "accepted": seq,
            "id": seq,
            "seq": seq,
            "head_seq": head_seq,
            "content_type": "text",
            "to_inbox": entry["to_inbox"],
        }

    def simulate_read(self, seq: int) -> None:
        sender = ""
        with self.lock:
            for m in self.messages:
                if m["seq"] == seq:
                    m["read"] = True
                    sender = m["from"]
                    break
        self.broadcast_ws(
            {
                "type": "event",
                "event": "message.read",
                "id": seq,
                "seq": seq,
                "from": sender,
                "read": True,
                "timestamp_us": int(time.monotonic() * 1_000_000),
            }
        )

    def simulate_reply(
        self,
        seq: int,
        action: str = "left",
        reply_text: str = "",
        trigger: str = "physical_button_left",
    ) -> dict[str, Any]:
        with self.lock:
            target = next((m for m in self.messages if m["seq"] == seq), None)
            if target is None and self.messages:
                target = self.messages[-1]
            if target is None:
                return {"ok": False}
            if action == "star":
                target["starred"] = not target["starred"]
            else:
                if not reply_text:
                    reply_text = (
                        target["reply_left"] or "收到"
                        if action == "left"
                        else target["reply_right"] or "稍后"
                    )
                target["replied_action"] = action
                target["replied_text"] = reply_text
            snap = dict(target)

        self.broadcast_ws(
            {
                "type": "event",
                "event": "message.reply",
                "id": snap["seq"],
                "seq": snap["seq"],
                "from": snap["from"],
                "action": action,
                "starred": snap["starred"],
                "reply_text": snap["replied_text"],
                "trigger": trigger,
                "timestamp_us": int(time.monotonic() * 1_000_000),
            }
        )
        return {
            "ok": True,
            "id": snap["seq"],
            "seq": snap["seq"],
            "action": action,
            "starred": snap["starred"],
            "replied_action": snap["replied_action"],
            "replied_text": snap["replied_text"],
        }

    def simulate_task_decision(
        self,
        task_id: str,
        approve: bool = True,
        trigger: str = "physical_button_left",
    ) -> None:
        with self.lock:
            item = self.agents.get(task_id, {})
            act = item.get("action") or {}
            opts = act.get("options") or ["批准", "拒绝"]
            choice = opts[0] if approve else opts[1]
            if task_id in self.agents:
                self.agents[task_id]["done"] = True
                self.agents[task_id]["action"] = {
                    "type": "confirm",
                    "btn1": opts[0],
                    "btn2": opts[1],
                    "result": choice,
                }
        self.broadcast_ws(
            {
                "type": "confirm",
                "event": "task.action",
                "id": task_id,
                "action": "approve" if approve else "cancel",
                "choice": choice,
                "trigger": trigger,
                "timestamp_us": int(time.monotonic() * 1_000_000),
            }
        )

    def _update_widget(self, data: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            tid = str(data.get("id") or "assistant")
            cur = self.agents.get(tid, {"id": tid})
            cur.update(data)
            self.agents[tid] = cur
            return self._widget_snapshot_unlocked()

    def _widget_snapshot(self) -> dict[str, Any]:
        with self.lock:
            return self._widget_snapshot_unlocked()

    def _widget_snapshot_unlocked(self) -> dict[str, Any]:
        items = list(self.agents.values())
        active = sum(1 for a in items if not a.get("done"))
        done = sum(1 for a in items if a.get("done"))
        return {"count": len(items), "active_count": active, "done_count": done, "agents": items}

    def _board_snapshot(self, since: int = 0, limit: int = 32) -> dict[str, Any]:
        with self.lock:
            filtered = [dict(m) for m in self.messages if m["seq"] > since][:limit]
            unread = sum(1 for m in self.messages if not m["read"])
            return {
                "head_seq": self.seq_counter,
                "unread_count": unread,
                "count": len(filtered),
                "entries": filtered,
            }

    def _inbox_snapshot(self, unread_only: bool = False) -> dict[str, Any]:
        with self.lock:
            all_msgs = [dict(m) for m in self.messages]
            inbox = [
                m
                for m in all_msgs
                if m["to_inbox"] or m["starred"] or bool(m["replied_action"])
            ]
            if unread_only:
                msgs = [
                    m
                    for m in all_msgs
                    if (not m["read"]) or m["to_inbox"] or m["starred"] or bool(m["replied_action"])
                ]
            else:
                msgs = all_msgs
            unread = sum(1 for m in all_msgs if not m["read"])
            return {
                "inbox_count": len(inbox),
                "unread_count": unread,
                "inbox": inbox,
                "messages": msgs,
            }

    def _accept_jpeg(self, payload: bytes) -> dict[str, Any]:
        if not validate_baseline_jpeg_480(payload):
            return {"ok": False, "error": "expected 480x480 baseline RGB JPEG"}
        with self.lock:
            self.frame_counter += 1
            self.frames.append(payload)
            return {"accepted": self.frame_counter}


class MosaicoMCPProtocolTests(unittest.TestCase):
    """End-to-end verification of `mosaico-mcp` against the Mock ESP-Mosaico 2.0 device."""

    def setUp(self) -> None:
        self.device = MockMosaicoDevice()
        self.stdout_buf = io.BytesIO()
        self.client = MosaicoClient(
            explicit_ip="127.0.0.1",
            explicit_port=self.device.port,
            allow_network_scan=False,
            persist_cache=False,
        )
        self.server = MosaicoMCPServer(
            client=self.client,
            stdout=self.stdout_buf,
            background_warmup=False,
        )

    def tearDown(self) -> None:
        self.client.close()
        self.device.close()

    def test_01_jsonrpc_handshake_tools_resources_prompts_and_errors(self) -> None:
        # 1. initialize
        init_resp = self.server.handle_payload(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "unit-test", "version": "1.0"},
                },
            }
        )
        assert isinstance(init_resp, dict)
        self.assertEqual(init_resp["result"]["protocolVersion"], "2025-03-26")
        self.assertEqual(init_resp["result"]["serverInfo"]["name"], "mosaico-mcp")
        self.assertTrue(init_resp["result"]["capabilities"]["resources"]["subscribe"])

        # 2. notifications/initialized -> must return None (no response for notification)
        notif_resp = self.server.handle_payload({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertIsNone(notif_resp)

        # 3. ping
        ping_resp = self.server.handle_payload({"jsonrpc": "2.0", "id": 2, "method": "ping"})
        assert isinstance(ping_resp, dict)
        self.assertEqual(ping_resp["result"], {})

        # 4. tools/list
        tools_resp = self.server.handle_payload({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        assert isinstance(tools_resp, dict)
        tool_names = {t["name"] for t in tools_resp["result"]["tools"]}
        self.assertEqual(
            tool_names,
            {
                "send_message",
                "ask_human_decision",
                "update_agent_seat",
                "push_canvas",
                "read_inbox_and_receipts",
                "board_post",
                "board_read",
                "board_wait",
            },
        )

        # 5. resources/list & resources/templates/list
        res_resp = self.server.handle_payload({"jsonrpc": "2.0", "id": 4, "method": "resources/list"})
        assert isinstance(res_resp, dict)
        uris = {r["uri"] for r in res_resp["result"]["resources"]}
        self.assertEqual(
            uris,
            {"mosaico://board", "mosaico://inbox", "mosaico://receipts", "mosaico://status"},
        )
        tmpl_resp = self.server.handle_payload(
            {"jsonrpc": "2.0", "id": 5, "method": "resources/templates/list"}
        )
        assert isinstance(tmpl_resp, dict)
        self.assertEqual(len(tmpl_resp["result"]["resourceTemplates"]), 1)

        # 6. prompts/list & prompts/get (all 3 built-in community prompts)
        prompts_resp = self.server.handle_payload({"jsonrpc": "2.0", "id": 6, "method": "prompts/list"})
        assert isinstance(prompts_resp, dict)
        prompt_names = {p["name"] for p in prompts_resp["result"]["prompts"]}
        self.assertEqual(prompt_names, {"morning_zine", "agent_roundtable", "market_tide_note"})

        for pname in ("morning_zine", "agent_roundtable", "market_tide_note"):
            g = self.server.handle_payload(
                {
                    "jsonrpc": "2.0",
                    "id": f"p-{pname}",
                    "method": "prompts/get",
                    "params": {"name": pname, "arguments": {"topic": "测试议题", "asset_or_metric": "NVDA"}},
                }
            )
            assert isinstance(g, dict)
            self.assertIn("messages", g["result"])
            self.assertTrue(g["result"]["messages"][0]["content"]["text"])

        # 7. JSON-RPC error codes (-32601 unknown method, -32602 unknown tool, -32600 invalid request)
        unk_method = self.server.handle_payload({"jsonrpc": "2.0", "id": 7, "method": "unknown/foo"})
        assert isinstance(unk_method, dict)
        self.assertEqual(unk_method["error"]["code"], -32601)

        unk_tool = self.server.handle_payload(
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {"name": "nonexistent_tool", "arguments": {}},
            }
        )
        assert isinstance(unk_tool, dict)
        self.assertEqual(unk_tool["error"]["code"], -32602)

        bad_req = self.server.handle_payload({"id": 9})
        assert isinstance(bad_req, dict)
        self.assertEqual(bad_req["error"]["code"], -32600)

    def test_02_discovery_env_and_utf8_clip_safety(self) -> None:
        # Verify UTF-8 multibyte safe truncation never splits 3-byte CJK or 4-byte codepoints
        sample = "晨间私刊木漏れ日"
        for limit in range(1, 30):
            clipped = utf8_clip(sample, limit)
            self.assertLessEqual(len(clipped.encode("utf-8")), limit)

        # Verify `MOSAICO_IP=127.0.0.1:<port>` zero-config discovery
        prev = os.environ.get("MOSAICO_IP")
        try:
            os.environ["MOSAICO_IP"] = f"127.0.0.1:{self.device.port}"
            ep = discover_device(allow_network_scan=False, persist_cache=False)
            self.assertIsNotNone(ep)
            assert ep is not None
            self.assertEqual(ep.host, "127.0.0.1")
            self.assertEqual(ep.port, self.device.port)
            self.assertEqual(ep.version, "1.1.60")
        finally:
            if prev is None:
                os.environ.pop("MOSAICO_IP", None)
            else:
                os.environ["MOSAICO_IP"] = prev

    def test_03_bidirectional_inbox_read_receipts_and_resource_notifications(self) -> None:
        self.server.handle_payload({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})

        # 1. Agent delivers a morning zine card with Kana & L/R quick reply options
        call_resp = self.server.handle_payload(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "send_message",
                    "arguments": {
                        "sender": "早报主编",
                        "title": "今日日语 · 木漏れ日",
                        "text": "林间洒落的阳光（こもれび）。",
                        "font_size": 24,
                        "reply_left": "加入生词本",
                        "reply_right": "下一张",
                    },
                },
            }
        )
        assert isinstance(call_resp, dict)
        self.assertFalse(call_resp["result"]["isError"])
        sent_data = json.loads(call_resp["result"]["content"][0]["text"])
        self.assertEqual(sent_data["seq"], 1)

        # 2. Simulate human viewing card for 1 second (`message.read`), starring via AI orange button,
        # and pressing Left physical button (`message.reply`), plus sending a `#send` inbox note!
        self.device.simulate_read(1)
        self.device.simulate_reply(1, action="star", trigger="ai_button")
        self.device.simulate_reply(1, action="left", trigger="physical_button_left")
        self.device._post_text(
            {
                "from": "Human",
                "text": "下午 3 点提醒我复盘，顺便查杭州周末天气",
                "to_inbox": True,
            }
        )

        # Wait briefly for async `/ws/hub` reader thread to emit MCP notifications
        deadline = time.monotonic() + 1.5
        notifications: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            notifications.extend(self._drain_notifications())
            notified_uris = {n["params"]["uri"] for n in notifications if n.get("method") == "notifications/resources/updated"}
            if {"mosaico://inbox", "mosaico://receipts", "mosaico://board"}.issubset(notified_uris):
                break
            time.sleep(0.02)

        notified_uris = {
            n["params"]["uri"]
            for n in notifications
            if n.get("method") == "notifications/resources/updated"
        }
        self.assertIn("mosaico://inbox", notified_uris)
        self.assertIn("mosaico://receipts", notified_uris)
        self.assertIn("mosaico://board", notified_uris)

        # 3. Verify `read_inbox_and_receipts` tool returns human note + 1s read + star + button reply
        inbox_call = self.server.handle_payload(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "read_inbox_and_receipts", "arguments": {"unread_only": False}},
            }
        )
        assert isinstance(inbox_call, dict)
        inbox_res = json.loads(inbox_call["result"]["content"][0]["text"])
        self.assertEqual(inbox_res["read_count"], 1)
        self.assertEqual(inbox_res["starred_count"], 1)
        self.assertEqual(inbox_res["replied_count"], 1)
        self.assertEqual(inbox_res["inbox_count"], 2)  # card #1 (starred+replied) + human #2 (to_inbox)

        card1 = next(r for r in inbox_res["receipts"] if r["seq"] == 1)
        self.assertTrue(card1["read"])
        self.assertTrue(card1["starred"])
        self.assertEqual(card1["replied_text"], "加入生词本")

        # 4. Verify `resources/read` on `mosaico://inbox` and `mosaico://receipts`
        for uri in ("mosaico://inbox", "mosaico://receipts", "mosaico://board?since=0&limit=10", "mosaico://status"):
            r_resp = self.server.handle_payload(
                {"jsonrpc": "2.0", "id": f"r-{uri}", "method": "resources/read", "params": {"uri": uri}}
            )
            assert isinstance(r_resp, dict)
            self.assertEqual(r_resp["result"]["contents"][0]["uri"], uri)
            parsed_content = json.loads(r_resp["result"]["contents"][0]["text"])
            self.assertIsInstance(parsed_content, dict)

    def _drain_notifications(self) -> list[dict[str, Any]]:
        raw = self.stdout_buf.getvalue().decode("utf-8")
        self.stdout_buf.seek(0)
        self.stdout_buf.truncate(0)
        return [json.loads(line) for line in raw.splitlines() if line.strip()]

    def test_04_physical_blackboard_multi_agent_zero_polling_wait(self) -> None:
        # 1. `codex` posts #1 on the Blackboard (self-post must NOT wake `codex` later)
        p1 = self.client.board_post(
            sender="codex",
            avatar="codex",
            text="@claude 我建议用环形缓冲区承载历史。",
        )
        self.assertEqual(p1["seq"], 1)

        # 2. Start `codex` waiting on `board_wait(agent_name="codex", since_seq=0, mentions_only=True)`
        wait_result: dict[str, Any] = {}

        def _waiter() -> None:
            wait_result.update(
                self.client.board_wait(
                    agent_name="codex",
                    since_seq=0,
                    mentions_only=True,
                    timeout_sec=3.0,
                )
            )

        t = threading.Thread(target=_waiter, daemon=True)
        t.start()
        time.sleep(0.08)
        # Ensure `codex` did NOT wake up on its own #1 post!
        self.assertTrue(t.is_alive())

        # 3. `claude` posts #2 mentioning `@gemini` (NOT `@codex`) -> `codex` stays asleep!
        self.device._post_text({"from": "claude", "avatar": "claude", "text": "@gemini 请查一下传感器功耗"})
        time.sleep(0.08)
        self.assertTrue(t.is_alive())

        # 4. `claude` posts #3 mentioning `@codex` -> `codex` wakes in <100ms with BOTH #2 and #3!
        t0 = time.monotonic()
        self.device._post_text(
            {"from": "claude", "to": "codex", "avatar": "claude", "text": "@codex 赞同，已合入你的队列设计！"}
        )
        t.join(timeout=1.5)
        elapsed = time.monotonic() - t0

        self.assertFalse(t.is_alive())
        self.assertLess(elapsed, 0.5)
        self.assertTrue(wait_result["woke"])
        self.assertEqual(wait_result["reason"], "mention")
        self.assertEqual(wait_result["head_seq"], 3)
        returned_seqs = [e["seq"] for e in wait_result["entries"]]
        self.assertEqual(returned_seqs, [1, 2, 3])
        # Zero HTTP polling occurred on `/api/board` (initial sync + wakeup all went over single `/ws/hub`)
        self.assertEqual(self.device.http_board_reads, 0)

        # 5. Race-free check: message #4 (`@all`) arrives BEFORE `board_wait` is invoked -> instant wakeup!
        self.device._post_text({"from": "antigravity", "text": "@all 准备进入人类最终审批"})
        time.sleep(0.05)
        instant = self.client.board_wait(agent_name="codex", since_seq=3, mentions_only=True, timeout_sec=1.0)
        self.assertTrue(instant["woke"])
        self.assertEqual(instant["reason"], "broadcast")
        self.assertEqual([e["seq"] for e in instant["entries"]], [4])

    def test_05_ask_human_decision_approve_reject_and_timeout_safety(self) -> None:
        # 1. Simulate human pressing physical Left button (`approve`) after 80ms
        def _press_left() -> None:
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                snap = self.device._widget_snapshot()
                if snap["agents"]:
                    tid = snap["agents"][-1]["id"]
                    self.device.simulate_task_decision(tid, approve=True, trigger="physical_button_left")
                    return
                time.sleep(0.02)

        threading.Thread(target=_press_left, daemon=True).start()
        approved_res = self.client.ask_human_decision(
            agent_name="Claude",
            question="是否批准刷入 2.0 固件？",
            avatar="claude",
            left_choice="立即刷入",
            right_choice="暂缓",
            timeout_sec=3.0,
        )
        self.assertTrue(approved_res["decided"])
        self.assertIs(approved_res["approved"], True)
        self.assertEqual(approved_res["side"], "left")
        self.assertEqual(approved_res["choice"], "立即刷入")
        self.assertEqual(approved_res["trigger"], "physical_button_left")

        # 2. Simulate human pressing physical Right button (`cancel`)
        def _press_right() -> None:
            deadline = time.monotonic() + 2.0
            seen = {approved_res["task_id"]}
            while time.monotonic() < deadline:
                snap = self.device._widget_snapshot()
                for ag in snap["agents"]:
                    if ag["id"] not in seen:
                        self.device.simulate_task_decision(ag["id"], approve=False, trigger="physical_button_right")
                        return
                time.sleep(0.02)

        threading.Thread(target=_press_right, daemon=True).start()
        rejected_res = self.client.ask_human_decision(
            agent_name="Codex",
            question="是否删除旧缓存？",
            avatar="codex",
            left_choice="删除",
            right_choice="保留",
            timeout_sec=3.0,
        )
        self.assertTrue(rejected_res["decided"])
        self.assertIs(rejected_res["approved"], False)
        self.assertEqual(rejected_res["side"], "right")
        self.assertEqual(rejected_res["choice"], "保留")

        # 3. Timeout MUST return `timed_out=True, approved=None, decided=False` (NEVER fake approval!)
        timeout_res = self.client.ask_human_decision(
            agent_name="Antigravity",
            question="无人值守超时测试",
            timeout_sec=0.15,
        )
        self.assertFalse(timeout_res["decided"])
        self.assertIsNone(timeout_res["approved"])
        self.assertTrue(timeout_res["timed_out"])
        self.assertEqual(timeout_res["action"], "timeout")

    def test_06_roundtable_seats_canvas_ping_pong_and_single_ws_socket(self) -> None:
        # 1. Update Roundtable seats across all 4 states
        for state in ("working", "review", "done", "error"):
            seat_res = self.client.update_agent_seat(
                agent_id="seat-antigravity",
                agent_name="Antigravity",
                title="验证圆桌剧场",
                session="Mosaico-2.0",
                avatar="antigravity",
                status=f"当前状态：{state}",
                state=state,
                led="breathe" if state == "working" else "",
            )
            self.assertTrue(seat_res["ok"])
            self.assertEqual(seat_res["state"], state)

        # 2. Push 480x480 canvas via `solid:#101720` AND via base64 JPEG (`push_canvas_svg_or_jpeg` alias)
        c1 = self.client.push_canvas("solid:#101720", led_effect="chase", caption="深空极客趋势幕布")
        self.assertTrue(c1["ok"])
        self.assertEqual(c1["accepted_frame"], 1)

        b64_jpeg = base64.b64encode(make_solid_jpeg_480((32, 48, 64))).decode("ascii")
        alias_resp = self.server.handle_payload(
            {
                "jsonrpc": "2.0",
                "id": 99,
                "method": "tools/call",
                "params": {
                    "name": "push_canvas_svg_or_jpeg",
                    "arguments": {"image_path_or_base64": b64_jpeg, "led_effect": "success"},
                },
            }
        )
        assert isinstance(alias_resp, dict)
        self.assertFalse(alias_resp["result"]["isError"])
        self.assertEqual(len(self.device.frames), 2)

        # 3. Verify RFC 6455 Ping -> masked Pong echo
        self.device.send_ping_to_all(b"esp32-ping-42")
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and b"esp32-ping-42" not in self.device.pong_payloads:
            time.sleep(0.02)
        self.assertIn(b"esp32-ping-42", self.device.pong_payloads)

        # 4. Strictly 1 single WebSocket connection used throughout the entire session!
        self.assertEqual(self.device.max_concurrent_ws, 1)
        self.assertEqual(self.device.total_ws_upgrades, 1)

    def test_07_real_stdio_subprocess_pipe_e2e(self) -> None:
        """Spawn `python3 -m mosaico_mcp` over real OS stdio pipes and verify full MCP flow."""
        requests = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "stdio-e2e", "version": "2.0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "resources/list"},
            {"jsonrpc": "2.0", "id": 4, "method": "prompts/list"},
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "board_post",
                    "arguments": {
                        "sender": "claude",
                        "avatar": "claude",
                        "text": "@all 真实 stdio 管道联调成功！",
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "resources/read",
                "params": {"uri": "mosaico://board"},
            },
        ]
        stdin_bytes = ("\n".join(json.dumps(r, ensure_ascii=False) for r in requests) + "\n").encode("utf-8")

        env = dict(os.environ)
        env["PYTHONPATH"] = str(MCP_ROOT)
        env["MOSAICO_IP"] = f"127.0.0.1:{self.device.port}"

        proc = subprocess.run(
            [sys.executable, "-m", "mosaico_mcp", "--no-warmup"],
            input=stdin_bytes,
            capture_output=True,
            timeout=10.0,
            env=env,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr.decode("utf-8", errors="replace"))

        lines = [
            json.loads(line)
            for line in proc.stdout.decode("utf-8").splitlines()
            if line.strip()
        ]
        by_id = {msg["id"]: msg for msg in lines if "id" in msg}
        self.assertEqual(set(by_id.keys()), {1, 2, 3, 4, 5, 6})
        self.assertEqual(by_id[1]["result"]["serverInfo"]["name"], "mosaico-mcp")
        self.assertEqual(len(by_id[2]["result"]["tools"]), 8)
        self.assertEqual(len(by_id[3]["result"]["resources"]), 4)
        self.assertEqual(len(by_id[4]["result"]["prompts"]), 3)
        self.assertFalse(by_id[5]["result"]["isError"])

        board_payload = json.loads(by_id[6]["result"]["contents"][0]["text"])
        self.assertEqual(board_payload["head_seq"], 1)
        self.assertIn("真实 stdio 管道联调成功", board_payload["entries"][0]["text"])

    def test_08_example_recipes_run_end_to_end(self) -> None:
        """Verify all 3 Agent Team example recipes in `mcp/examples/` execute cleanly."""
        examples_dir = MCP_ROOT / "examples"
        env = dict(os.environ)
        env["PYTHONPATH"] = str(MCP_ROOT)

        # Recipe 01: Morning Zine Team
        r1 = subprocess.run(
            [
                sys.executable,
                str(examples_dir / "01_morning_zine_team.py"),
                "--ip",
                "127.0.0.1",
                "--port",
                str(self.device.port),
            ],
            capture_output=True,
            text=True,
            timeout=10.0,
            env=env,
            check=False,
        )
        self.assertEqual(r1.returncode, 0, msg=r1.stderr)
        self.assertIn("晨刊投递完毕", r1.stdout)

        # Recipe 02: Multi-Agent Roundtable Blackboard (with simulated human approval)
        def _auto_approve_roundtable() -> None:
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                snap = self.device._widget_snapshot()
                for ag in snap["agents"]:
                    act = ag.get("action")
                    if isinstance(act, dict) and act.get("type") == "confirm" and not act.get("result"):
                        self.device.simulate_task_decision(ag["id"], approve=True)
                        return
                time.sleep(0.03)

        threading.Thread(target=_auto_approve_roundtable, daemon=True).start()
        r2 = subprocess.run(
            [
                sys.executable,
                str(examples_dir / "02_agent_roundtable_blackboard.py"),
                "--ip",
                "127.0.0.1",
                "--port",
                str(self.device.port),
                "--decision-timeout",
                "4.0",
            ],
            capture_output=True,
            text=True,
            timeout=12.0,
            env=env,
            check=False,
        )
        self.assertEqual(r2.returncode, 0, msg=r2.stderr)
        self.assertIn("批准双模", r2.stdout)

        # Recipe 03: Market Tide & Solar Canvas
        for mode in ("tide", "solar"):
            r3 = subprocess.run(
                [
                    sys.executable,
                    str(examples_dir / "03_market_tide_and_solar_canvas.py"),
                    "--mode",
                    mode,
                    "--ip",
                    "127.0.0.1",
                    "--port",
                    str(self.device.port),
                ],
                capture_output=True,
                text=True,
                timeout=10.0,
                env=env,
                check=False,
            )
            self.assertEqual(r3.returncode, 0, msg=r3.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
