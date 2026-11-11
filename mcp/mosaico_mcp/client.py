"""High-level ESP-Mosaico 2.0 client over multiplexed `/ws/hub` + REST fallback."""

from __future__ import annotations

import datetime
import re
import threading
import time
from typing import Any, Callable
import urllib.error

from .canvas import parse_hex_rgb, prepare_canvas_jpeg
from .discovery import DeviceEndpoint, discover_device, http_request, utf8_clip
from .ws_hub import MosaicoHub

VALID_AVATARS = (
    "generic",
    "claude",
    "codex",
    "antigravity",
    "hermes",
    "pi",
    "gemini",
    "cursor",
    "copilot",
    "opencode",
    "kiro",
    "cline",
    "goose",
    "windsurf",
)

VALID_LED_EFFECTS = (
    "breathe",
    "chase",
    "marquee",
    "rainbow",
    "alert",
    "warning",
    "success",
    "solid",
    "off",
)


class MosaicoClient:
    """Thread-safe client implementing Mosaico 2.0 MCP tools, Blackboard primitives, and resources."""

    def __init__(
        self,
        explicit_ip: str | None = None,
        explicit_port: int | None = None,
        *,
        on_resource_updated: Callable[[str], None] | None = None,
        allow_network_scan: bool = True,
        persist_cache: bool = True,
    ) -> None:
        self._explicit_ip = explicit_ip
        self._explicit_port = explicit_port
        self._allow_network_scan = allow_network_scan
        self._persist_cache = persist_cache
        self._endpoint: DeviceEndpoint | None = None
        self._ep_lock = threading.Lock()
        self._id_counter = 0
        self.hub = MosaicoHub(on_resource_updated=on_resource_updated)

    @property
    def endpoint(self) -> DeviceEndpoint | None:
        with self._ep_lock:
            return self._endpoint

    def start_background_warmup(self) -> None:
        """Warm up device discovery and single `/ws/hub` socket in a daemon thread."""

        def _warmup() -> None:
            try:
                ep = self.resolve_endpoint(required=False)
                if ep is not None:
                    self.hub.ensure_connected(ep.host, ep.port, timeout=2.5)
            except Exception:
                pass

        threading.Thread(target=_warmup, name="mosaico-mcp-warmup", daemon=True).start()

    def close(self) -> None:
        self.hub.close()

    def resolve_endpoint(self, *, required: bool = True, force_refresh: bool = False) -> DeviceEndpoint | None:
        with self._ep_lock:
            if self._endpoint is not None and not force_refresh:
                return self._endpoint

        ep = discover_device(
            explicit_ip=self._explicit_ip,
            explicit_port=self._explicit_port,
            allow_network_scan=self._allow_network_scan,
            persist_cache=self._persist_cache,
        )
        with self._ep_lock:
            self._endpoint = ep

        if ep is not None:
            self.hub.ensure_connected(ep.host, ep.port, timeout=2.5)
        elif required:
            raise RuntimeError(
                "未发现 ESP-Mosaico 随身屏（已尝试 MOSAICO_IP -> mosaico.local -> SSDP -> 本地缓存 -> ARP）。"
                "请确认设备与电脑在同一局域网，或设置环境变量 MOSAICO_IP=<设备IP>。"
            )
        return ep

    def _next_ticket_id(self, prefix: str) -> str:
        with self._ep_lock:
            self._id_counter += 1
            seq = self._id_counter
        slug = re.sub(r"[^A-Za-z0-9_-]", "", prefix or "agent")[:16] or "agent"
        ms = int(time.time() * 1000) % 100_000_000
        return utf8_clip(f"mcp-{slug}-{ms}-{seq}", 63)

    def _http(
        self,
        path: str,
        body: dict[str, Any] | bytes | None = None,
        *,
        mime: str = "application/json",
        timeout: float = 3.5,
        raw: bool = False,
    ) -> Any:
        ep = self.resolve_endpoint(required=True)
        assert ep is not None
        try:
            return http_request(
                ep.host,
                path,
                body,
                port=ep.port,
                mime=mime,
                timeout=timeout,
                raw=raw,
            )
        except urllib.error.HTTPError:
            raise
        except OSError:
            if self._explicit_ip:
                raise
            ep2 = self.resolve_endpoint(required=True, force_refresh=True)
            assert ep2 is not None
            return http_request(
                ep2.host,
                path,
                body,
                port=ep2.port,
                mime=mime,
                timeout=timeout,
                raw=raw,
            )

    def _ws_or_http_post_text(self, payload: dict[str, Any]) -> dict[str, Any]:
        ep = self.resolve_endpoint(required=True)
        assert ep is not None
        if self.hub.ensure_connected(ep.host, ep.port, timeout=2.0):
            try:
                return self.hub.send_rpc("text", payload, timeout=3.5)
            except Exception:
                pass
        return self._http("/api/text", payload, timeout=3.5)

    def _ws_or_http_widget(self, payload: dict[str, Any]) -> dict[str, Any]:
        ep = self.resolve_endpoint(required=True)
        assert ep is not None
        if self.hub.ensure_connected(ep.host, ep.port, timeout=2.0):
            try:
                ack = self.hub.send_rpc("widget.update", payload, timeout=3.5)
                return ack.get("widget") if isinstance(ack.get("widget"), dict) else ack
            except Exception:
                pass
        return self._http("/api/widget", payload, timeout=3.5)

    def set_led_effect(self, effect: str, color_hex: str = "#39e69d", brightness: int = 36) -> bool:
        """Trigger a 50Hz subboard RGB LED preset over `/ws/hub` (zero extra socket) or HTTP."""
        eff = (effect or "").strip().lower()
        if not eff:
            return False
        if eff not in VALID_LED_EFFECTS:
            raise ValueError(f"Unsupported `led` effect {effect!r}; choose from {VALID_LED_EFFECTS}")
        r, g, b = parse_hex_rgb(color_hex, default=(57, 230, 157))
        bri = max(0, min(64, int(brightness)))
        ep = self.resolve_endpoint(required=True)
        assert ep is not None
        if self.hub.ensure_connected(ep.host, ep.port, timeout=1.5):
            try:
                self.hub.send_rpc(
                    "led.set",
                    {"slot": "right", "effect": eff, "r": r, "g": g, "b": b, "brightness": bri},
                    timeout=2.0,
                )
                return True
            except Exception:
                pass
        led_body: dict[str, Any] = {"slot": "right", "effect": eff, "brightness": bri}
        if eff not in ("rainbow", "off"):
            led_body["color"] = [r, g, b]
        try:
            self._http("/api/interact/leds", led_body, timeout=2.5)
            return True
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Golden Primitive 1: send_message
    # -------------------------------------------------------------------------
    def send_message(
        self,
        sender: str,
        text: str,
        title: str = "",
        font_size: int = 24,
        align: str = "left",
        reply_left: str = "",
        reply_right: str = "",
        avatar: str = "",
        to: str = "",
        to_inbox: bool = False,
    ) -> dict[str, Any]:
        """Deliver a typeset CJK/Kana card (7,318-glyph Flash font) with optional L/R quick-reply pills."""
        if not str(text or "").strip():
            raise ValueError("`text` must be a non-empty string")
        clean_sender = utf8_clip(sender or "Agent", 31)
        clean_title = utf8_clip(title, 63)
        clean_text = utf8_clip(text, 1024)
        clean_size = max(16, min(64, int(font_size)))
        clean_align = align if align in ("left", "center", "right") else "left"
        clean_left = utf8_clip(reply_left, 23)
        clean_right = utf8_clip(reply_right, 23)
        clean_avatar = utf8_clip(avatar, 15)
        clean_to = utf8_clip(to, 31)
        wall_time = datetime.datetime.now().strftime("%H:%M")

        payload: dict[str, Any] = {
            "from": clean_sender,
            "title": clean_title,
            "text": clean_text,
            "font_size": clean_size,
            "align": clean_align,
            "time": wall_time,
            "to_inbox": bool(to_inbox),
            "reply_left": clean_left,
            "reply_right": clean_right,
        }
        if clean_avatar:
            payload["avatar"] = clean_avatar
        if clean_to:
            payload["to"] = clean_to

        res = self._ws_or_http_post_text(payload)
        seq = int(res.get("seq") or res.get("id") or res.get("accepted") or 0)
        head_seq = int(res.get("head_seq") or seq)
        if seq > 0:
            self.hub.merge_entries_from_snapshot(
                [
                    {
                        "id": seq,
                        "seq": seq,
                        "time": wall_time,
                        "from": clean_sender,
                        "to": clean_to,
                        "avatar": clean_avatar,
                        "title": clean_title,
                        "text": clean_text,
                        "font_size": clean_size,
                        "align": clean_align,
                        "to_inbox": bool(to_inbox),
                        "read": False,
                        "starred": False,
                        "reply_left": clean_left,
                        "reply_right": clean_right,
                        "replied_action": "",
                        "replied_text": "",
                    }
                ],
                head_seq=head_seq,
            )
        ep = self.endpoint
        return {
            "ok": True,
            "device_ip": ep.host if ep else "",
            "seq": seq,
            "id": seq,
            "head_seq": max(head_seq, self.hub.head_seq),
            "sender": clean_sender,
            "to": clean_to,
            "title": clean_title,
            "font_size": clean_size,
            "align": clean_align,
            "reply_options": [opt for opt in (clean_left, clean_right) if opt],
        }

    # -------------------------------------------------------------------------
    # Golden Primitive 2: ask_human_decision
    # -------------------------------------------------------------------------
    def ask_human_decision(
        self,
        agent_name: str,
        question: str,
        session: str = "",
        avatar: str = "generic",
        left_choice: str = "批准",
        right_choice: str = "拒绝",
        timeout_sec: float = 120.0,
        agent_id: str = "",
        title: str = "",
    ) -> dict[str, Any]:
        """Trigger full-screen amber takeover and block on `/ws/hub` for physical L/R decision.
        Never fabricates approval on timeout.
        """
        if not str(question or "").strip():
            raise ValueError("`question` must be a non-empty string")
        ep = self.resolve_endpoint(required=True)
        assert ep is not None

        # Connect WS BEFORE posting widget to eliminate any race window
        self.hub.ensure_connected(ep.host, ep.port, timeout=3.0)
        cursor_before = self.hub.current_event_cursor()

        task_id = utf8_clip(agent_id, 63) if agent_id else self._next_ticket_id(avatar if avatar != "generic" else agent_name)
        btn_left = utf8_clip(left_choice or "批准", 23)
        btn_right = utf8_clip(right_choice or "拒绝", 23)
        card_title = utf8_clip(title or question, 63, max_chars=16)

        widget_payload: dict[str, Any] = {
            "id": task_id,
            "agent": utf8_clip(agent_name or "Agent", 31),
            "session": utf8_clip(session, 47),
            "avatar": utf8_clip(avatar or "generic", 15),
            "title": card_title,
            "status": utf8_clip(question, 191),
            "progress": -1,
            "done": False,
            "error": False,
            "action": {
                "type": "confirm",
                "options": [btn_left, btn_right],
            },
            "show": True,
        }
        self._ws_or_http_widget(widget_payload)

        def _poll_if_ws_down() -> dict[str, Any] | None:
            try:
                st = self._http("/api/widget", timeout=2.0)
                for item in st.get("agents", []):
                    if item.get("id") == task_id:
                        result_str = (item.get("action") or {}).get("result") or ""
                        if result_str:
                            prog = item.get("progress")
                            if isinstance(prog, int) and item.get("done") and prog in (0, 100):
                                act = "approve" if prog >= 100 else "cancel"
                            else:
                                act = "approve" if result_str == btn_left else "cancel"
                            return {
                                "id": task_id,
                                "action": act,
                                "choice": result_str,
                                "trigger": "http_fallback",
                            }
            except Exception:
                pass
            return None

        event = self.hub.wait_for_task_action(
            task_id=task_id,
            timeout_sec=max(0.1, float(timeout_sec)),
            min_local_seq=cursor_before,
            poll_fallback=_poll_if_ws_down,
        )
        if event is None:
            return {
                "decided": False,
                "approved": None,
                "action": "timeout",
                "choice": None,
                "side": None,
                "trigger": None,
                "timed_out": True,
                "task_id": task_id,
                "device_ip": ep.host,
                "message": (
                    f"Human did not respond within {timeout_sec}s. "
                    "Timeout is NOT approval; remain paused or ask the user in chat."
                ),
            }

        act_code = str(event.get("action") or "")
        approved = act_code == "approve"
        choice_text = str(event.get("choice") or (btn_left if approved else btn_right))
        return {
            "decided": True,
            "approved": approved,
            "action": act_code,
            "choice": choice_text,
            "side": "left" if approved else "right",
            "trigger": str(event.get("trigger") or "ws"),
            "timed_out": False,
            "task_id": task_id,
            "device_ip": ep.host,
        }

    # -------------------------------------------------------------------------
    # Golden Primitive 3: update_agent_seat
    # -------------------------------------------------------------------------
    def update_agent_seat(
        self,
        agent_id: str,
        agent_name: str,
        title: str,
        session: str = "",
        avatar: str = "generic",
        status: str = "",
        state: str = "working",
        led: str = "",
        progress: int = -1,
    ) -> dict[str, Any]:
        """Update an Agent's seat on the Multi-Agent Roundtable (`working`/`review`/`done`/`error`)."""
        norm_state = (state or "working").strip().lower()
        if norm_state not in ("working", "review", "done", "error"):
            raise ValueError("`state` must be one of: 'working', 'review', 'done', 'error'")

        seat_id = utf8_clip(agent_id or agent_name or "agent-seat", 63)
        action_val: Any = "none"
        done_flag = False
        error_flag = False
        prog_val = max(-1, min(100, int(progress)))

        if norm_state == "review":
            action_val = {"type": "review", "options": ["知道了", "稍后"]}
            prog_val = -1
        elif norm_state == "done":
            done_flag = True
            prog_val = 100
        elif norm_state == "error":
            error_flag = True
            prog_val = -1

        payload: dict[str, Any] = {
            "id": seat_id,
            "agent": utf8_clip(agent_name or seat_id, 31),
            "session": utf8_clip(session, 47),
            "avatar": utf8_clip(avatar or "generic", 15),
            "title": utf8_clip(title or "圆桌协作中", 63),
            "status": utf8_clip(status, 191),
            "progress": prog_val,
            "done": done_flag,
            "error": error_flag,
            "action": action_val,
            "show": True,
        }
        widget_state = self._ws_or_http_widget(payload)
        led_applied = self.set_led_effect(led) if led else False
        ep = self.endpoint
        return {
            "ok": True,
            "device_ip": ep.host if ep else "",
            "agent_id": seat_id,
            "agent_name": payload["agent"],
            "state": norm_state,
            "avatar": payload["avatar"],
            "led_applied": led_applied,
            "active_count": widget_state.get("active_count") if isinstance(widget_state, dict) else None,
        }

    # -------------------------------------------------------------------------
    # Golden Primitive 4: push_canvas
    # -------------------------------------------------------------------------
    def push_canvas(
        self,
        image_path_or_base64: str | bytes,
        led_effect: str = "",
        caption: str = "",
        led_color: str = "#39e69d",
        switch_to_canvas: bool = True,
    ) -> dict[str, Any]:
        """Push a 480x480 baseline RGB JPEG to the AMOLED Canvas page and synchronize 50Hz LEDs."""
        jpeg_bytes = prepare_canvas_jpeg(image_path_or_base64)
        ep = self.resolve_endpoint(required=True)
        assert ep is not None

        frame_res: dict[str, Any] | None = None
        if self.hub.ensure_connected(ep.host, ep.port, timeout=2.0):
            try:
                frame_res = self.hub.send_jpeg_binary(jpeg_bytes, timeout=6.0)
            except Exception:
                frame_res = None
        if frame_res is None:
            frame_res = self._http("/api/frame", jpeg_bytes, mime="image/jpeg", timeout=8.0)

        caption_seq: int | None = None
        if caption and caption.strip():
            msg_res = self.send_message(sender="Canvas", text=caption.strip(), font_size=24)
            caption_seq = msg_res.get("seq")

        if switch_to_canvas:
            if self.hub.is_connected:
                try:
                    self.hub.send_rpc("view", {"page": "image"}, timeout=2.5)
                except Exception:
                    self._http("/api/view", {"page": "image"}, timeout=2.5)
            else:
                self._http("/api/view", {"page": "image"}, timeout=2.5)

        led_applied = self.set_led_effect(led_effect, color_hex=led_color) if led_effect else False
        return {
            "ok": True,
            "device_ip": ep.host,
            "accepted_frame": frame_res.get("accepted") if isinstance(frame_res, dict) else None,
            "jpeg_bytes": len(jpeg_bytes),
            "switched_to_canvas": bool(switch_to_canvas),
            "led_effect": led_effect or None,
            "led_applied": led_applied,
            "caption_seq": caption_seq,
        }

    # -------------------------------------------------------------------------
    # Golden Primitive 5: read_inbox_and_receipts
    # -------------------------------------------------------------------------
    def read_inbox_and_receipts(self, unread_only: bool = False) -> dict[str, Any]:
        """Fetch human `#send` messages, physical L/R button replies, stars, and 1-second `read` receipts."""
        ep = self.resolve_endpoint(required=True)
        assert ep is not None
        self.hub.ensure_connected(ep.host, ep.port, timeout=1.5)

        query = "?unread_only=1" if unread_only else ""
        data: dict[str, Any] | None = None

        # Try WS topic="inbox" or HTTP GET /api/inbox first, fallback to /api/history
        if not unread_only and self.hub.is_connected:
            try:
                ack = self.hub.send_rpc("get", {"topic": "inbox"}, timeout=2.5)
                if isinstance(ack.get("data"), dict):
                    data = ack["data"]
            except Exception:
                data = None

        if data is None:
            try:
                resp = self._http(f"/api/inbox{query}", timeout=3.0)
                if isinstance(resp, dict):
                    data = resp
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise
                data = None

        if data is not None and ("inbox" in data or "messages" in data):
            all_msgs = list(data.get("messages") or [])
            inbox_items = list(data.get("inbox") or [])
            self.hub.merge_entries_from_snapshot(all_msgs or inbox_items)
        else:
            hist = self._http("/api/history", timeout=3.0)
            raw_entries = list((hist.get("messages") or {}).get("entries") or [])
            self.hub.merge_entries_from_snapshot(raw_entries)
            merged_all = [self.hub.board_entries[s] for s in sorted(self.hub.board_entries.keys())]
            inbox_items = [
                e
                for e in merged_all
                if e.get("to_inbox") or e.get("starred") or e.get("replied_action") or e.get("replied_text")
            ]
            if unread_only:
                all_msgs = [
                    e
                    for e in merged_all
                    if (not e.get("read"))
                    or e.get("to_inbox")
                    or e.get("starred")
                    or bool(e.get("replied_action"))
                ]
            else:
                all_msgs = merged_all

        receipts = [
            {
                "seq": int(m.get("seq") or m.get("id") or 0),
                "from": m.get("from", ""),
                "to": m.get("to", ""),
                "title": m.get("title", ""),
                "text": m.get("text", ""),
                "time": m.get("time", ""),
                "read": bool(m.get("read", False)),
                "starred": bool(m.get("starred", False)),
                "to_inbox": bool(m.get("to_inbox", False)),
                "reply_left": m.get("reply_left", ""),
                "reply_right": m.get("reply_right", ""),
                "replied_action": m.get("replied_action", ""),
                "replied_text": m.get("replied_text", ""),
            }
            for m in all_msgs
        ]
        return {
            "device_ip": ep.host,
            "head_seq": self.hub.head_seq,
            "inbox_count": len(inbox_items),
            "unread_count": sum(1 for r in receipts if not r["read"]),
            "read_count": sum(1 for r in receipts if r["read"]),
            "starred_count": sum(1 for r in receipts if r["starred"]),
            "replied_count": sum(1 for r in receipts if r["replied_action"] or r["replied_text"]),
            "inbox": inbox_items,
            "receipts": receipts,
        }

    # -------------------------------------------------------------------------
    # Physical Blackboard Trio: board_post, board_read, board_wait
    # -------------------------------------------------------------------------
    def board_post(
        self,
        sender: str,
        text: str,
        to: str = "",
        avatar: str = "generic",
        title: str = "",
        font_size: int = 24,
        reply_left: str = "",
        reply_right: str = "",
        to_inbox: bool = False,
    ) -> dict[str, Any]:
        """Post a message onto the Mosaico Physical Blackboard (rendered on screen + broadcast to all Agents)."""
        res = self.send_message(
            sender=sender,
            text=text,
            title=title,
            font_size=font_size,
            align="left",
            reply_left=reply_left,
            reply_right=reply_right,
            avatar=avatar or "generic",
            to=to,
            to_inbox=to_inbox,
        )
        return {
            "ok": True,
            "seq": res["seq"],
            "id": res["id"],
            "head_seq": res["head_seq"],
            "from": res["sender"],
            "to": res["to"],
            "avatar": utf8_clip(avatar or "generic", 15),
            "text": utf8_clip(text, 1024),
            "device_ip": res["device_ip"],
        }

    def board_read(self, since_seq: int = 0, limit: int = 20) -> dict[str, Any]:
        """Incrementally read Physical Blackboard entries with `seq > since_seq`."""
        ep = self.resolve_endpoint(required=True)
        assert ep is not None
        self.hub.ensure_connected(ep.host, ep.port, timeout=1.5)

        clean_since = max(0, int(since_seq))
        clean_limit = max(1, min(100, int(limit)))

        board_data: dict[str, Any] | None = None
        if self.hub.is_connected:
            try:
                ack = self.hub.send_rpc(
                    "board.read",
                    {"since": clean_since, "limit": clean_limit},
                    timeout=2.5,
                )
                if "entries" in ack:
                    board_data = ack
                elif isinstance(ack.get("data"), dict):
                    board_data = ack["data"]
            except Exception:
                board_data = None

        if board_data is None:
            try:
                resp = self._http(f"/api/board?since={clean_since}&limit={clean_limit}", timeout=3.0)
                if isinstance(resp, dict) and "entries" in resp:
                    board_data = resp
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise
                board_data = None

        if board_data is not None:
            raw_entries = list(board_data.get("entries") or [])
            head_seq = int(board_data.get("head_seq") or 0)
            self.hub.merge_entries_from_snapshot(raw_entries, head_seq=head_seq)
            filtered = [
                dict(self.hub.board_entries.get(int(e.get("seq") or e.get("id") or 0), e))
                for e in raw_entries
                if int(e.get("seq") or e.get("id") or 0) > clean_since
            ]
            filtered.sort(key=lambda item: int(item.get("seq") or item.get("id") or 0))
            filtered = filtered[:clean_limit]
            unread_count = int(
                board_data.get("unread_count")
                if "unread_count" in board_data
                else sum(1 for item in filtered if not item.get("read"))
            )
            return {
                "device_ip": ep.host,
                "since_seq": clean_since,
                "head_seq": max(head_seq, self.hub.head_seq),
                "count": len(filtered),
                "unread_count": unread_count,
                "entries": filtered,
            }

        # Fallback to GET /api/history on pre-2.0 firmware
        hist = self._http(f"/api/history?since={clean_since}", timeout=3.0)
        hist_entries = list((hist.get("messages") or {}).get("entries") or [])
        self.hub.merge_entries_from_snapshot(hist_entries)
        entries = [
            dict(self.hub.board_entries[s])
            for s in sorted(self.hub.board_entries.keys())
            if s > clean_since
        ][:clean_limit]
        return {
            "device_ip": ep.host,
            "since_seq": clean_since,
            "head_seq": self.hub.head_seq,
            "count": len(entries),
            "unread_count": sum(1 for item in entries if not item.get("read")),
            "entries": entries,
        }

    def board_wait(
        self,
        agent_name: str,
        since_seq: int = 0,
        mentions_only: bool = True,
        timeout_sec: float = 120.0,
    ) -> dict[str, Any]:
        """Zero-polling `/ws/hub` event-driven sleep until `@<agent_name>`, `@all`, human inbox post,
        or physical L/R button reply arrives on the Mosaico Physical Blackboard.
        """
        if not str(agent_name or "").strip():
            raise ValueError("`agent_name` must be a non-empty string")
        ep = self.resolve_endpoint(required=True)
        assert ep is not None
        clean_since = max(0, int(since_seq))

        if not self.hub.ensure_connected(ep.host, ep.port, timeout=3.5):
            raise ConnectionError(f"Could not establish `/ws/hub` connection to {ep.ws_hub_url}")

        cursor_before = self.hub.current_event_cursor()
        # Initial sync so messages posted right before `board_wait` are never slept through
        self.board_read(since_seq=clean_since, limit=50)

        reason, entries, replies = self.hub.wait_for_board(
            agent_name=agent_name,
            since_seq=clean_since,
            mentions_only=bool(mentions_only),
            timeout_sec=max(0.05, float(timeout_sec)),
            min_local_seq=cursor_before,
        )
        if reason is None:
            return {
                "woke": False,
                "timed_out": True,
                "reason": "timeout",
                "agent_name": agent_name,
                "since_seq": clean_since,
                "head_seq": self.hub.head_seq,
                "count": len(entries),
                "entries": entries,
                "replies": [],
            }

        return {
            "woke": True,
            "timed_out": False,
            "reason": reason,
            "agent_name": agent_name,
            "since_seq": clean_since,
            "head_seq": self.hub.head_seq,
            "count": len(entries),
            "entries": entries,
            "replies": [
                {
                    "seq": r.get("seq") or r.get("id"),
                    "from": r.get("from", ""),
                    "action": r.get("action", ""),
                    "starred": r.get("starred", False),
                    "reply_text": r.get("reply_text", ""),
                    "trigger": r.get("trigger", ""),
                }
                for r in replies
            ],
        }

    def get_device_status(self) -> dict[str, Any]:
        """Return live device status + active Agent Roundtable seats."""
        ep = self.resolve_endpoint(required=True)
        assert ep is not None
        status = self._http("/api/status", timeout=2.5)
        try:
            widget = self._http("/api/widget", timeout=2.5)
        except Exception:
            widget = {}
        return {
            "device_ip": ep.host,
            "port": ep.port,
            "discovery_source": ep.source,
            "ws_hub_connected": self.hub.is_connected,
            "head_seq": self.hub.head_seq,
            "status": status,
            "roundtable": widget,
        }
