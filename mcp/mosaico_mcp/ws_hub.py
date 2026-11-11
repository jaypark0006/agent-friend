"""Zero-dependency RFC 6455 multiplexed `/ws/hub` client & Blackboard event bus."""

from __future__ import annotations

import base64
from collections import deque
import hashlib
import json
import os
import re
import socket
import threading
import time
from typing import Any, Callable

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_MENTION_RE = re.compile(r"(?<![A-Za-z0-9_-])@([A-Za-z0-9_.-]+)")


def extract_mentions(text: str) -> set[str]:
    """Extract lowercased `@name` handles from message text."""
    return {m.group(1).lower() for m in _MENTION_RE.finditer(text or "")}


def entry_wakes_agent(entry: dict[str, Any], agent_name: str, mentions_only: bool = True) -> str | None:
    """Return wakeup reason if `entry` should wake `agent_name`, else `None`."""
    target = agent_name.lstrip("@").strip().lower()
    if not target:
        target = "agent"
    prefix_match = re.match(r"^(.+)-\d+$", target)
    prefix = prefix_match.group(1) if prefix_match else ""

    sender = str(entry.get("from") or "").lstrip("@").strip().lower()
    if sender and sender == target:
        # Never wake an agent on its own Blackboard post.
        return None

    if not mentions_only:
        return "message"

    to_field = str(entry.get("to") or "").lstrip("@").strip().lower()
    if to_field == "all":
        return "broadcast"
    if to_field and (to_field == target or (prefix and to_field == prefix)):
        return "mention"

    combined_text = f"{entry.get('title') or ''} {entry.get('text') or ''}"
    mentions = extract_mentions(combined_text)
    if "all" in mentions:
        return "broadcast"
    if target in mentions or (prefix and prefix in mentions):
        return "mention"

    if bool(entry.get("to_inbox")) and (
        not to_field or to_field in ("agent", "agents", "team", target) or (prefix and to_field == prefix)
    ):
        return "inbox"

    return None


class RawWebSocket:
    """Minimal RFC 6455 compliant client socket (verified handshake, masked client frames, Ping/Pong)."""

    def __init__(self, host: str, port: int = 80, path: str = "/ws/hub", timeout: float = 4.0) -> None:
        self.host = host
        self.port = port
        self.path = path
        self._sock: socket.socket | None = None
        self._buf = bytearray()
        self._send_lock = threading.Lock()
        self._closed = False
        self._connect(timeout)

    def _connect(self, timeout: float) -> None:
        sock = socket.create_connection((self.host, self.port), timeout=timeout)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        self._sock = sock
        try:
            key = base64.b64encode(os.urandom(16)).decode("ascii")
            expected_accept = base64.b64encode(
                hashlib.sha1((key + _WS_GUID).encode("ascii")).digest()
            ).decode("ascii")
            host_hdr = self.host if self.port == 80 else f"{self.host}:{self.port}"
            req = (
                f"GET {self.path} HTTP/1.1\r\n"
                f"Host: {host_hdr}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n\r\n"
            )
            sock.sendall(req.encode("ascii"))

            raw_hdr = bytearray()
            while b"\r\n\r\n" not in raw_hdr:
                chunk = sock.recv(4096)
                if not chunk:
                    raise ConnectionError("WebSocket handshake closed prematurely")
                raw_hdr.extend(chunk)
                if len(raw_hdr) > 65536:
                    raise ConnectionError("WebSocket handshake header exceeded 64 KiB")

            sep_idx = raw_hdr.index(b"\r\n\r\n")
            header_bytes = bytes(raw_hdr[:sep_idx])
            self._buf.extend(raw_hdr[sep_idx + 4 :])

            lines = header_bytes.decode("latin-1").split("\r\n")
            status_parts = lines[0].split()
            if len(status_parts) < 2 or status_parts[1] != "101":
                raise ConnectionError(f"WebSocket upgrade rejected: {lines[0]}")

            headers = {
                line.split(":", 1)[0].strip().lower(): line.split(":", 1)[1].strip()
                for line in lines[1:]
                if ":" in line
            }
            if (
                headers.get("sec-websocket-accept") != expected_accept
                or headers.get("upgrade", "").lower() != "websocket"
                or "upgrade" not in headers.get("connection", "").lower()
            ):
                raise ConnectionError("WebSocket handshake header verification failed")

            sock.settimeout(1.0)
        except Exception:
            self.close()
            raise

    @property
    def connected(self) -> bool:
        return self._sock is not None and not self._closed

    def send_frame(self, opcode: int, payload: bytes = b"") -> None:
        """Send a single FIN=1 RFC 6455 masked client frame."""
        with self._send_lock:
            sock = self._sock
            if sock is None or self._closed:
                raise ConnectionError("WebSocket is closed")
            mask = os.urandom(4)
            length = len(payload)
            hdr = bytearray([0x80 | (opcode & 0x0F)])
            if length < 126:
                hdr.append(0x80 | length)
            elif length <= 65535:
                hdr.append(0x80 | 126)
                hdr.extend(length.to_bytes(2, "big"))
            else:
                hdr.append(0x80 | 127)
                hdr.extend(length.to_bytes(8, "big"))
            hdr.extend(mask)
            masked = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
            sock.sendall(bytes(hdr) + masked)

    def send_text(self, text: str) -> None:
        self.send_frame(0x01, text.encode("utf-8"))

    def send_binary(self, data: bytes) -> None:
        self.send_frame(0x02, data)

    def _read_exact(self, n: int) -> bytes:
        while len(self._buf) < n:
            sock = self._sock
            if sock is None or self._closed:
                raise ConnectionError("WebSocket closed")
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("WebSocket EOF")
            self._buf.extend(chunk)
        out = bytes(self._buf[:n])
        del self._buf[:n]
        return out

    def recv_message(self) -> tuple[int, bytes] | None:
        """Read one complete WebSocket message (handling fragmentation and Ping/Pong).
        Returns `(opcode, payload)` or `None` on read timeout (allowing caller loop check).
        """
        fragments = bytearray()
        msg_opcode = 0
        fragmented = False
        while True:
            try:
                b1, b2 = self._read_exact(2)
            except (socket.timeout, TimeoutError):
                if not fragmented:
                    return None
                continue

            fin = bool(b1 & 0x80)
            rsv = b1 & 0x70
            opcode = b1 & 0x0F
            masked = bool(b2 & 0x80)
            length = b2 & 0x7F
            if rsv != 0:
                raise ConnectionError("Invalid WebSocket RSV bits")
            if length == 126:
                length = int.from_bytes(self._read_exact(2), "big")
            elif length == 127:
                length = int.from_bytes(self._read_exact(8), "big")
            if length > 2 * 1024 * 1024:
                raise ConnectionError("WebSocket frame too large")
            mask_key = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if masked:
                payload = bytes(b ^ mask_key[i & 3] for i, b in enumerate(payload))

            if opcode >= 0x08:
                if not fin or length > 125:
                    raise ConnectionError("Invalid WebSocket control frame")
                if opcode == 0x08:
                    self.close()
                    raise ConnectionError("WebSocket closed by peer")
                if opcode == 0x09:
                    # RFC 6455 5.5.2: Echo identical Ping payload in masked Pong frame
                    self.send_frame(0x0A, payload)
                continue

            if opcode in (0x01, 0x02):
                if fragmented:
                    raise ConnectionError("Unexpected new data frame during fragmentation")
                msg_opcode = opcode
                if fin:
                    return msg_opcode, payload
                fragments = bytearray(payload)
                fragmented = True
            elif opcode == 0x00 and fragmented:
                fragments.extend(payload)
                if len(fragments) > 2 * 1024 * 1024:
                    raise ConnectionError("Fragmented WebSocket message too large")
                if fin:
                    return msg_opcode, bytes(fragments)
            else:
                raise ConnectionError(f"Unexpected WebSocket opcode: {opcode}")

    def close(self) -> None:
        with self._send_lock:
            if self._closed:
                return
            self._closed = True
            sock = self._sock
            self._sock = None
            if sock is not None:
                try:
                    mask = os.urandom(4)
                    sock.sendall(b"\x88\x80" + mask)
                except OSError:
                    pass
                try:
                    sock.close()
                except OSError:
                    pass


class MosaicoHub:
    """Persistent single-socket `/ws/hub` multiplexer, Blackboard cache, and event notifier."""

    def __init__(
        self,
        on_resource_updated: Callable[[str], None] | None = None,
    ) -> None:
        self._on_resource_updated = on_resource_updated
        self._cond = threading.Condition()
        self._ws: RawWebSocket | None = None
        self._target: tuple[str, int] | None = None
        self._reader_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._connect_lock = threading.Lock()
        self._image_lock = threading.Lock()

        self._req_counter = 0
        self._event_seq = 0
        self._pending_rpcs: dict[str, tuple[threading.Event, dict[str, Any]]] = {}
        self._pending_image: tuple[threading.Event, dict[str, Any]] | None = None

        # Cached state synchronized from `/ws/hub` events + HTTP/WS snapshots
        self.head_seq: int = 0
        self.board_entries: dict[int, dict[str, Any]] = {}
        self.recent_events: deque[dict[str, Any]] = deque(maxlen=200)
        self.reply_events: deque[dict[str, Any]] = deque(maxlen=100)
        self.task_actions: deque[dict[str, Any]] = deque(maxlen=100)

    @property
    def is_connected(self) -> bool:
        ws = self._ws
        return ws is not None and ws.connected

    def ensure_connected(self, host: str, port: int = 80, timeout: float = 3.5) -> bool:
        """Ensure the single background `/ws/hub` connection is connected to `(host, port)`."""
        with self._connect_lock:
            if self._target == (host, port) and self.is_connected:
                return True
            self._close_ws_unlocked()
            self._target = (host, port)
            self._stop_event.clear()
            try:
                ws = RawWebSocket(host, port, path="/ws/hub", timeout=timeout)
            except Exception:
                return False
            self._ws = ws
            t = threading.Thread(
                target=self._reader_loop,
                args=(ws, host, port),
                name="mosaico-ws-hub",
                daemon=True,
            )
            self._reader_thread = t
            t.start()
            return True

    def start_background_connect(self, host: str, port: int = 80) -> None:
        """Connect asynchronously in a daemon thread without blocking startup."""
        threading.Thread(
            target=self.ensure_connected,
            args=(host, port, 2.5),
            name="mosaico-ws-bg-init",
            daemon=True,
        ).start()

    def close(self) -> None:
        self._stop_event.set()
        with self._connect_lock:
            self._close_ws_unlocked()
        with self._cond:
            self._cond.notify_all()

    def _close_ws_unlocked(self) -> None:
        ws = self._ws
        self._ws = None
        if ws is not None:
            ws.close()
        with self._cond:
            for ev, slot in self._pending_rpcs.values():
                slot["error"] = "WebSocket disconnected"
                ev.set()
            self._pending_rpcs.clear()
            if self._pending_image is not None:
                img_ev, img_slot = self._pending_image
                img_slot["error"] = "WebSocket disconnected"
                img_ev.set()
                self._pending_image = None
            self._cond.notify_all()

    def _reader_loop(self, ws: RawWebSocket, host: str, port: int) -> None:
        backoff = 0.3
        current_ws: RawWebSocket | None = ws
        while not self._stop_event.is_set():
            if self._target != (host, port):
                break
            if current_ws is None or not current_ws.connected:
                if self._stop_event.wait(backoff):
                    break
                backoff = min(5.0, backoff * 1.8)
                with self._connect_lock:
                    if self._stop_event.is_set() or self._target != (host, port):
                        break
                    try:
                        current_ws = RawWebSocket(host, port, path="/ws/hub", timeout=3.0)
                        self._ws = current_ws
                        backoff = 0.3
                    except Exception:
                        current_ws = None
                        continue

            try:
                frame = current_ws.recv_message()
            except Exception:
                with self._connect_lock:
                    if self._ws is current_ws:
                        self._close_ws_unlocked()
                current_ws = None
                continue

            if frame is None:
                continue
            opcode, payload = frame
            if opcode != 0x01:
                continue
            try:
                msg = json.loads(payload.decode("utf-8", errors="replace"))
            except ValueError:
                continue
            if isinstance(msg, dict):
                self._dispatch_incoming(msg)

    def _dispatch_incoming(self, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type")
        req_id = msg.get("request_id")
        updated_uris: list[str] = []

        with self._cond:
            # 1. Correlated RPC ACK / Response
            if msg_type in ("ack", "response"):
                if req_id is not None and str(req_id) in self._pending_rpcs:
                    ev, slot = self._pending_rpcs.pop(str(req_id))
                    slot["response"] = msg
                    ev.set()
                    return
                if msg.get("command") == "image" and self._pending_image is not None:
                    img_ev, img_slot = self._pending_image
                    self._pending_image = None
                    img_slot["response"] = msg
                    img_ev.set()
                    return

            # 2. Upstream Asynchronous Events (`board.post`, `inbox.message`, `message.reply`, `message.read`, `task.action`)
            event_name = msg.get("event")
            if not event_name:
                return

            self._event_seq += 1
            stamped = dict(msg, _local_seq=self._event_seq, _received_mono=time.monotonic())
            self.recent_events.append(stamped)

            if event_name == "board.post":
                seq = int(msg.get("seq") or msg.get("id") or 0)
                if seq > 0:
                    self.head_seq = max(self.head_seq, seq)
                    existing = self.board_entries.get(seq, {})
                    merged = {
                        "id": seq,
                        "seq": seq,
                        "from": msg.get("from", existing.get("from", "")),
                        "to": msg.get("to", existing.get("to", "")),
                        "avatar": msg.get("avatar", existing.get("avatar", "")),
                        "title": msg.get("title", existing.get("title", "")),
                        "text": msg.get("text", existing.get("text", "")),
                        "time": msg.get("time", existing.get("time", "")),
                        "to_inbox": bool(msg.get("to_inbox", existing.get("to_inbox", False))),
                        "read": bool(existing.get("read", False)),
                        "starred": bool(existing.get("starred", False)),
                        "reply_left": msg.get("reply_left", existing.get("reply_left", "")),
                        "reply_right": msg.get("reply_right", existing.get("reply_right", "")),
                        "replied_action": existing.get("replied_action", ""),
                        "replied_text": existing.get("replied_text", ""),
                        "timestamp_us": msg.get("timestamp_us", existing.get("timestamp_us", 0)),
                    }
                    self.board_entries[seq] = merged
                updated_uris.append("mosaico://board")
                if msg.get("to_inbox"):
                    updated_uris.append("mosaico://inbox")

            elif event_name == "inbox.message":
                seq = int(msg.get("seq") or msg.get("id") or 0)
                if seq > 0:
                    self.head_seq = max(self.head_seq, seq)
                    existing = self.board_entries.get(seq, {})
                    existing.update(
                        {
                            "id": seq,
                            "seq": seq,
                            "from": msg.get("from", existing.get("from", "Human")),
                            "title": msg.get("title", existing.get("title", "")),
                            "text": msg.get("text", existing.get("text", "")),
                            "time": msg.get("time", existing.get("time", "")),
                            "to_inbox": True,
                            "timestamp_us": msg.get("timestamp_us", existing.get("timestamp_us", 0)),
                        }
                    )
                    self.board_entries[seq] = existing
                updated_uris.extend(["mosaico://inbox", "mosaico://board"])

            elif event_name == "message.reply":
                seq = int(msg.get("seq") or msg.get("id") or 0)
                if seq > 0:
                    self.head_seq = max(self.head_seq, seq)
                    entry = self.board_entries.setdefault(seq, {"id": seq, "seq": seq})
                    if "starred" in msg:
                        entry["starred"] = bool(msg["starred"])
                    elif msg.get("action") == "star":
                        entry["starred"] = not bool(entry.get("starred", False))
                    if msg.get("action") in ("left", "right", "custom"):
                        entry["replied_action"] = msg.get("action", "")
                        entry["replied_text"] = msg.get("reply_text", "")
                    if msg.get("from") and not entry.get("from"):
                        entry["from"] = msg["from"]
                self.reply_events.append(stamped)
                updated_uris.extend(["mosaico://receipts", "mosaico://inbox", "mosaico://board"])

            elif event_name == "message.read":
                seq = int(msg.get("seq") or msg.get("id") or 0)
                if seq > 0:
                    self.head_seq = max(self.head_seq, seq)
                    entry = self.board_entries.setdefault(seq, {"id": seq, "seq": seq})
                    entry["read"] = bool(msg.get("read", True))
                    if msg.get("from") and not entry.get("from"):
                        entry["from"] = msg["from"]
                updated_uris.append("mosaico://receipts")

            elif event_name == "task.action":
                self.task_actions.append(stamped)

            self._cond.notify_all()

        if self._on_resource_updated and updated_uris:
            for uri in dict.fromkeys(updated_uris):
                try:
                    self._on_resource_updated(uri)
                except Exception:
                    pass

    def merge_entries_from_snapshot(self, entries: list[dict[str, Any]], head_seq: int = 0) -> None:
        """Synchronize HTTP/WS `board`/`history`/`inbox` entries into the local cache."""
        with self._cond:
            if head_seq > self.head_seq:
                self.head_seq = head_seq
            for raw in entries:
                if not isinstance(raw, dict):
                    continue
                seq = int(raw.get("seq") or raw.get("id") or 0)
                if seq <= 0:
                    continue
                self.head_seq = max(self.head_seq, seq)
                cur = self.board_entries.get(seq, {})
                merged = dict(cur)
                merged.update(raw)
                merged["id"] = seq
                merged["seq"] = seq
                self.board_entries[seq] = merged
            # Bound cache memory to most recent 256 messages
            if len(self.board_entries) > 256:
                for old_k in sorted(self.board_entries.keys())[:-256]:
                    self.board_entries.pop(old_k, None)

    def current_event_cursor(self) -> int:
        with self._cond:
            return self._event_seq

    def send_rpc(self, cmd_type: str, params: dict[str, Any] | None = None, timeout: float = 3.0) -> dict[str, Any]:
        """Send a JSON command on `/ws/hub` and await its correlated `ack`/`response`."""
        ws = self._ws
        if ws is None or not ws.connected:
            raise ConnectionError("WebSocket `/ws/hub` is not connected")
        ev = threading.Event()
        slot: dict[str, Any] = {}
        with self._cond:
            self._req_counter += 1
            req_id = f"mcp-{self._req_counter}"
            self._pending_rpcs[req_id] = (ev, slot)

        body = dict(params or {})
        body["type"] = cmd_type
        body["request_id"] = req_id
        try:
            ws.send_text(json.dumps(body, ensure_ascii=False))
        except Exception as exc:
            with self._cond:
                self._pending_rpcs.pop(req_id, None)
            raise ConnectionError(f"Failed sending WS RPC {cmd_type}: {exc}") from exc

        if not ev.wait(timeout=timeout):
            with self._cond:
                self._pending_rpcs.pop(req_id, None)
            raise TimeoutError(f"WS RPC `{cmd_type}` timed out after {timeout}s")

        if "error" in slot:
            raise ConnectionError(slot["error"])
        resp = slot.get("response") or {}
        if resp.get("ok") is False:
            raise RuntimeError(str(resp.get("error") or f"WS command `{cmd_type}` rejected"))
        return resp

    def send_jpeg_binary(self, jpeg_bytes: bytes, timeout: float = 6.0) -> dict[str, Any]:
        """Send a raw 480x480 baseline JPEG binary frame over `/ws/hub`."""
        with self._image_lock:
            ws = self._ws
            if ws is None or not ws.connected:
                raise ConnectionError("WebSocket `/ws/hub` is not connected")
            ev = threading.Event()
            slot: dict[str, Any] = {}
            with self._cond:
                self._pending_image = (ev, slot)
            try:
                ws.send_binary(jpeg_bytes)
            except Exception as exc:
                with self._cond:
                    if self._pending_image and self._pending_image[0] is ev:
                        self._pending_image = None
                raise ConnectionError(f"Failed sending WS binary JPEG: {exc}") from exc

            if not ev.wait(timeout=timeout):
                with self._cond:
                    if self._pending_image and self._pending_image[0] is ev:
                        self._pending_image = None
                raise TimeoutError("WS binary JPEG ACK timed out")
            if "error" in slot:
                raise ConnectionError(slot["error"])
            resp = slot.get("response") or {}
            if resp.get("ok") is False or "error" in resp:
                raise ValueError(str(resp.get("error") or "JPEG rejected by device"))
            return resp

    def wait_for_task_action(
        self,
        task_id: str,
        timeout_sec: float,
        min_local_seq: int = 0,
        poll_fallback: Callable[[], dict[str, Any] | None] | None = None,
    ) -> dict[str, Any] | None:
        """Block until a `task.action` for `task_id` arrives on `/ws/hub` or `timeout_sec` expires."""
        deadline = time.monotonic() + max(0.05, float(timeout_sec))
        next_poll_at = time.monotonic() + 1.5
        while True:
            with self._cond:
                for evt in self.task_actions:
                    if (
                        evt.get("_local_seq", 0) > min_local_seq
                        and evt.get("id") == task_id
                        and evt.get("action") in ("approve", "cancel")
                        and evt.get("type") in ("event", "confirm", "review")
                    ):
                        return evt
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                wait_slice = min(remaining, 0.5) if (poll_fallback and not self.is_connected) else remaining
                self._cond.wait(timeout=max(0.01, wait_slice))

            if poll_fallback and not self.is_connected and time.monotonic() >= next_poll_at:
                next_poll_at = time.monotonic() + 0.8
                polled = poll_fallback()
                if polled is not None:
                    return polled

    def wait_for_board(
        self,
        agent_name: str,
        since_seq: int,
        mentions_only: bool = True,
        timeout_sec: float = 120.0,
        min_local_seq: int = 0,
    ) -> tuple[str | None, list[dict[str, Any]], list[dict[str, Any]]]:
        """Event-driven zero-polling sleep on `/ws/hub` until a matching post or human reply arrives."""
        deadline = time.monotonic() + max(0.02, float(timeout_sec))
        target = agent_name.lstrip("@").strip().lower()
        while True:
            with self._cond:
                newer_entries = [
                    dict(self.board_entries[s])
                    for s in sorted(self.board_entries.keys())
                    if s > since_seq
                ]
                for entry in newer_entries:
                    reason = entry_wakes_agent(entry, agent_name, mentions_only=mentions_only)
                    if reason is not None:
                        replies = [
                            dict(r)
                            for r in self.reply_events
                            if r.get("_local_seq", 0) > min_local_seq
                        ]
                        return reason, newer_entries, replies

                matching_replies = [
                    dict(r)
                    for r in self.reply_events
                    if r.get("_local_seq", 0) > min_local_seq
                    and (
                        not mentions_only
                        or not r.get("from")
                        or str(r.get("from")).lstrip("@").strip().lower() in ("", target)
                        or int(r.get("seq") or r.get("id") or 0) > since_seq
                    )
                ]
                if matching_replies:
                    return "reply", newer_entries, matching_replies

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None, newer_entries, []
                self._cond.wait(timeout=remaining)
