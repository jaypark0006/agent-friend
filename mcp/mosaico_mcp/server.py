"""Standard MCP Server (JSON-RPC 2.0 over `stdio`) for ESP-Mosaico 2.0."""

from __future__ import annotations

import io
import json
import sys
import threading
from typing import Any, BinaryIO, TextIO
import urllib.parse

from .client import VALID_AVATARS, VALID_LED_EFFECTS, MosaicoClient
from .prompts import get_prompt, list_prompts

SUPPORTED_PROTOCOL_VERSIONS = (
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
)
DEFAULT_PROTOCOL_VERSION = "2024-11-05"

TOOLS_SPEC: list[dict[str, Any]] = [
    {
        "name": "send_message",
        "description": (
            "向 Mosaico 随身屏《消息页》投递出版级精排中日文卡片（搭载 7,318 字 Noto Sans SC 多字号字库，"
            "视口静止可见满 1 秒自动标记 `read: true`），可选绑定副板左/右物理按键快捷回信胶囊。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sender": {
                    "type": "string",
                    "description": "发送者署名（如 '早报主编'、'Claude'、'潮汐哨兵'，最大 31 字节）",
                },
                "text": {
                    "type": "string",
                    "description": "消息正文（UTF-8 <= 1024 字节，支持 GB2312 一二级汉字、日文假名与全套标点）",
                },
                "title": {
                    "type": "string",
                    "description": "可选加粗短标题（最大 63 字节）",
                    "default": "",
                },
                "font_size": {
                    "type": "integer",
                    "description": "字号像素（16..64，阅读长文推荐 20 或 24，短句醒目签推荐 32）",
                    "minimum": 16,
                    "maximum": 64,
                    "default": 24,
                },
                "align": {
                    "type": "string",
                    "enum": ["left", "center", "right"],
                    "default": "left",
                },
                "reply_left": {
                    "type": "string",
                    "description": "可选副板左物理键 [L] 快捷回信文案（如 '收到'、'继续深挖'，最大 23 字节）",
                    "default": "",
                },
                "reply_right": {
                    "type": "string",
                    "description": "可选副板右物理键 [R] 快捷回信文案（如 '稍后'、'跳过'，最大 23 字节）",
                    "default": "",
                },
                "avatar": {
                    "type": "string",
                    "description": "可选 9x7 专属点阵头像 key",
                    "enum": list(VALID_AVATARS),
                    "default": "generic",
                },
            },
            "required": ["sender", "text"],
        },
    },
    {
        "name": "ask_human_decision",
        "description": (
            "触发随身屏琥珀橙整屏接管 + 副板 alert 警示双闪，通过复用的 `/ws/hub` 长连接毫秒级阻塞等待人类按压"
            "左/右物理按键或触屏拍板裁决。超时明确返回 `timed_out: true, approved: null`，绝不假冒人类同意。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "发起询问的 Agent 展示名称（如 'Claude'、'Codex'、'Antigravity'）",
                },
                "question": {
                    "type": "string",
                    "description": "需要人类拍板的核心问题（精炼直白，一屏可读）",
                },
                "session": {
                    "type": "string",
                    "description": "所属会话或项目名",
                    "default": "",
                },
                "avatar": {
                    "type": "string",
                    "enum": list(VALID_AVATARS),
                    "default": "generic",
                },
                "left_choice": {
                    "type": "string",
                    "description": "左物理键 [L] 代表的批准/方案A文案",
                    "default": "批准",
                },
                "right_choice": {
                    "type": "string",
                    "description": "右物理键 [R] 代表的拒绝/方案B文案",
                    "default": "拒绝",
                },
                "timeout_sec": {
                    "type": "number",
                    "description": "最长阻塞等待秒数（默认 120 秒）",
                    "minimum": 0.1,
                    "maximum": 600,
                    "default": 120,
                },
            },
            "required": ["agent_name", "question"],
        },
    },
    {
        "name": "update_agent_seat",
        "description": (
            "面向 Multi-Agent Team 桌面圆桌剧场，更新某个智能体在《此刻页》与《任务页》的专属席位状态、"
            "13 种 9x7 动效脸与 50Hz 交互板灯效。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "智能体或任务席位唯一 ID（如 'seat-claude'、'researcher-1'）",
                },
                "agent_name": {
                    "type": "string",
                    "description": "席位展示名（如 'Claude'、'论文精读员'）",
                },
                "title": {
                    "type": "string",
                    "description": "当前负责议题或短标题（<=14 字最佳）",
                },
                "session": {
                    "type": "string",
                    "description": "所属团队或会话名",
                    "default": "",
                },
                "avatar": {
                    "type": "string",
                    "enum": list(VALID_AVATARS),
                    "default": "generic",
                },
                "status": {
                    "type": "string",
                    "description": "当前发言摘要或进展一句话说明",
                    "default": "",
                },
                "state": {
                    "type": "string",
                    "enum": ["working", "review", "done", "error"],
                    "description": "席位状态：working=工作中 / review=等你回看 / done=已完成 / error=异常",
                    "default": "working",
                },
                "led": {
                    "type": "string",
                    "description": "可选联动 50Hz 副板灯效（留空则遵循设备 led_hints 自动状态灯）",
                    "enum": ["", *VALID_LED_EFFECTS],
                    "default": "",
                },
            },
            "required": ["agent_id", "agent_name", "title"],
        },
    },
    {
        "name": "push_canvas",
        "description": (
            "推送 480x480 画面至随身屏 AMOLED《画面页》（支持本地图片路径、Base64、`data:image/...`、URL、"
            "SVG 或零依赖纯色幕布 `solid:#101720`），并可选联动 50Hz 六灯氛围灯效。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path_or_base64": {
                    "type": "string",
                    "description": "图片文件路径、Base64 字符串、`data:image/...` URI、HTTP URL 或 `solid:#RRGGBB`",
                },
                "led_effect": {
                    "type": "string",
                    "description": "可选联动 50Hz RGB 灯效（如 breathe / chase / rainbow / success / off）",
                    "enum": ["", *VALID_LED_EFFECTS],
                    "default": "",
                },
                "caption": {
                    "type": "string",
                    "description": "可选画面配文（同步留存至消息历史）",
                    "default": "",
                },
                "led_color": {
                    "type": "string",
                    "description": "可选灯效主色调十六进制（如 '#39e69d'）",
                    "default": "#39e69d",
                },
                "switch_to_canvas": {
                    "type": "boolean",
                    "description": "推送后是否立即切到《画面页》展示",
                    "default": True,
                },
            },
            "required": ["image_path_or_base64"],
        },
    },
    {
        "name": "read_inbox_and_receipts",
        "description": (
            "一键读取人类从网页 `#send` 投递给 Agent Team 的双向收件箱留言、屏幕物理键快捷回信、顶部橙键 `⭐ 星标`，"
            "以及每张精排卡片的 `read: true`（视口静止可见满 1 秒真·已读）状态。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "unread_only": {
                    "type": "boolean",
                    "description": "若为 true，仅返回未读或含人类回执/星标/收件箱标记的条目",
                    "default": False,
                }
            },
        },
    },
    {
        "name": "board_post",
        "description": (
            "【物理共享黑板】往 Mosaico 共享黑板上贴一条发言（支持写 `@codex`、`@claude`、`@human`、`@all`）："
            "屏幕上立即用 7,318 字字库排印呈现，同时通过 `/ws/hub` 毫秒级广播唤醒所有挂载在屏幕上的异构 Agent。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sender": {
                    "type": "string",
                    "description": "发言 Agent 或人类身份（如 'claude'、'codex'、'antigravity'）",
                },
                "text": {
                    "type": "string",
                    "description": "黑板发言内容（可含 `@peer` 或 `@all` 唤醒对应智能体）",
                },
                "to": {
                    "type": "string",
                    "description": "可选显式目标对象（如 'codex'、'all'、'human'）",
                    "default": "",
                },
                "avatar": {
                    "type": "string",
                    "enum": list(VALID_AVATARS),
                    "default": "generic",
                },
                "title": {
                    "type": "string",
                    "description": "可选议题短抬头",
                    "default": "",
                },
                "reply_left": {
                    "type": "string",
                    "description": "可选屏幕物理左键 [L] 快捷表态胶囊",
                    "default": "",
                },
                "reply_right": {
                    "type": "string",
                    "description": "可选屏幕物理右键 [R] 快捷表态胶囊",
                    "default": "",
                },
            },
            "required": ["sender", "text"],
        },
    },
    {
        "name": "board_read",
        "description": (
            "【物理共享黑板】按单调递增游标 `since_seq` 增量读取黑板上的跨 Agent 对话、人类插话、"
            "`1秒已读 (read)` 与物理按键回执，返回最新 `head_seq`。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "since_seq": {
                    "type": "integer",
                    "description": "上次已读的最大序号（传 0 拉取最近全部黑板记录）",
                    "minimum": 0,
                    "default": 0,
                },
                "limit": {
                    "type": "integer",
                    "description": "最多返回条数（1..100，默认 20）",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20,
                },
            },
        },
    },
    {
        "name": "board_wait",
        "description": (
            "【物理共享黑板 · 零轮询休眠等待】基于本地单条 `/ws/hub` 长连接事件驱动等待（等待期间零 Token 消耗、"
            "零 HTTP 轮询）。当黑板出现 `@<agent_name>`、`@all`、人类 `#send` 投信或物理键回复时 10ms 内唤醒，"
            "并返回 `since_seq` 之后的全部增量消息！"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "当前等待被召唤的智能体名（如 'codex'、'claude'）",
                },
                "since_seq": {
                    "type": "integer",
                    "description": "上次已处理的黑板序号（确保等待前刚到达的消息绝不漏读）",
                    "minimum": 0,
                    "default": 0,
                },
                "mentions_only": {
                    "type": "boolean",
                    "description": "true=仅在 @自己/@all/人类收件箱/按键回执时唤醒；false=黑板有任何他人新帖即唤醒",
                    "default": True,
                },
                "timeout_sec": {
                    "type": "number",
                    "description": "最长休眠秒数（默认 120 秒）",
                    "minimum": 0.05,
                    "maximum": 600,
                    "default": 120,
                },
            },
            "required": ["agent_name", "since_seq"],
        },
    },
]

RESOURCES_SPEC: list[dict[str, Any]] = [
    {
        "uri": "mosaico://board",
        "name": "Mosaico Physical Blackboard",
        "description": "跨 Agent 物理共享黑板实时对话流、最新 head_seq、人类插话与按键表态",
        "mimeType": "application/json",
    },
    {
        "uri": "mosaico://inbox",
        "name": "Mosaico Human-to-Agent Inbox",
        "description": "人类从网页 #send 投递给 Agent Team 的消息、物理 L/R 快捷回复与橙键星标条目",
        "mimeType": "application/json",
    },
    {
        "uri": "mosaico://receipts",
        "name": "Mosaico 1-Second Read & Button Receipts",
        "description": "每张精排中文卡片的视口 1 秒真·已读 (read: true)、星标与物理键回执总览",
        "mimeType": "application/json",
    },
    {
        "uri": "mosaico://status",
        "name": "Mosaico Companion Screen & Roundtable Status",
        "description": "随身屏设备在线状态、固件版本、当前舞台页与 Multi-Agent 圆桌席位快照",
        "mimeType": "application/json",
    },
]

RESOURCE_TEMPLATES_SPEC: list[dict[str, Any]] = [
    {
        "uriTemplate": "mosaico://board?since={since}&limit={limit}",
        "name": "Incremental Physical Blackboard Slice",
        "description": "按游标 since 增量读取 Mosaico 物理共享黑板记录",
        "mimeType": "application/json",
    }
]


class MosaicoMCPServer:
    """JSON-RPC 2.0 MCP Server over `stdio` with async `notifications/resources/updated` push."""

    def __init__(
        self,
        client: MosaicoClient | None = None,
        *,
        explicit_ip: str | None = None,
        explicit_port: int | None = None,
        stdin: BinaryIO | None = None,
        stdout: BinaryIO | None = None,
        stderr: TextIO | None = None,
        background_warmup: bool = True,
    ) -> None:
        self._stdin: BinaryIO = stdin if stdin is not None else sys.stdin.buffer
        self._stdout: BinaryIO = stdout if stdout is not None else sys.stdout.buffer
        self._stderr: TextIO = stderr if stderr is not None else sys.stderr
        self._write_lock = threading.Lock()
        self._framing_mode: str = "line"  # "line" (MCP standard) or "content-length"
        self._initialized = False
        self._subscribed_uris: set[str] = set()
        self._workers_lock = threading.Lock()
        self._active_workers: set[threading.Thread] = set()

        self.client = client or MosaicoClient(
            explicit_ip=explicit_ip,
            explicit_port=explicit_port,
            on_resource_updated=self.notify_resource_updated,
        )
        if client is not None and client.hub._on_resource_updated is None:
            client.hub._on_resource_updated = self.notify_resource_updated

        if background_warmup:
            self.client.start_background_warmup()

    def _log(self, message: str) -> None:
        try:
            self._stderr.write(f"[mosaico-mcp] {message}\n")
            self._stderr.flush()
        except Exception:
            pass

    def _send_jsonrpc(self, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        with self._write_lock:
            try:
                if self._framing_mode == "content-length":
                    header = f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii")
                    self._stdout.write(header + encoded)
                else:
                    self._stdout.write(encoded + b"\n")
                self._stdout.flush()
            except BrokenPipeError:
                pass

    def notify_resource_updated(self, uri: str) -> None:
        """Emit MCP `notifications/resources/updated` asynchronously when `/ws/hub` events arrive."""
        if not self._initialized:
            return
        # If client explicitly subscribed to specific URIs, honor filter; otherwise broadcast core inbox/board updates.
        if self._subscribed_uris and uri not in self._subscribed_uris:
            return
        self._send_jsonrpc(
            {
                "jsonrpc": "2.0",
                "method": "notifications/resources/updated",
                "params": {"uri": uri},
            }
        )

    def handle_payload(self, raw_obj: Any) -> dict[str, Any] | list[dict[str, Any]] | None:
        """Process a parsed JSON-RPC 2.0 request, notification, or batch."""
        if isinstance(raw_obj, list):
            if not raw_obj:
                return self._error_response(None, -32600, "Invalid Request: empty batch")
            responses: list[dict[str, Any]] = []
            for item in raw_obj:
                resp = self._handle_single(item)
                if resp is not None:
                    responses.append(resp)
            return responses if responses else None
        return self._handle_single(raw_obj)

    def _error_response(self, req_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
        err: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        return {"jsonrpc": "2.0", "id": req_id, "error": err}

    def _result_response(self, req_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _handle_single(self, msg: Any) -> dict[str, Any] | None:
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
            req_id = msg.get("id") if isinstance(msg, dict) else None
            return self._error_response(req_id, -32600, "Invalid Request: expected JSON-RPC 2.0 object")

        method = msg.get("method")
        has_id = "id" in msg
        req_id = msg.get("id")
        params = msg.get("params")

        if not isinstance(method, str) or not method:
            return self._error_response(req_id, -32600, "Invalid Request: missing method")
        if params is not None and not isinstance(params, (dict, list)):
            return self._error_response(req_id, -32602, "Invalid params: expected object or array")

        param_dict = params if isinstance(params, dict) else {}

        # Notifications (no `id` member) never receive a JSON-RPC response
        if not has_id:
            if method == "notifications/initialized":
                self._initialized = True
            return None

        try:
            if method == "initialize":
                client_proto = str(param_dict.get("protocolVersion") or DEFAULT_PROTOCOL_VERSION)
                negotiated = (
                    client_proto
                    if client_proto in SUPPORTED_PROTOCOL_VERSIONS
                    else DEFAULT_PROTOCOL_VERSION
                )
                self._initialized = True
                return self._result_response(
                    req_id,
                    {
                        "protocolVersion": negotiated,
                        "capabilities": {
                            "tools": {"listChanged": False},
                            "resources": {"subscribe": True, "listChanged": False},
                            "prompts": {"listChanged": False},
                        },
                        "serverInfo": {
                            "name": "mosaico-mcp",
                            "version": "2.0.0",
                        },
                        "instructions": (
                            "ESP-Mosaico (Agent Friend) 2.0 Physical Companion & Multi-Agent Blackboard MCP Server. "
                            "Use `send_message` for 7,318-glyph CJK/Kana typesetting with 1s read receipts, "
                            "`board_post`/`board_read`/`board_wait` for cross-agent zero-polling Blackboard collaboration, "
                            "`update_agent_seat` for Roundtable presence, `ask_human_decision` for physical L/R button decisions, "
                            "and `push_canvas` for 480x480 AMOLED visuals."
                        ),
                    },
                )

            if method == "ping":
                return self._result_response(req_id, {})

            if method == "logging/setLevel":
                return self._result_response(req_id, {})

            if method == "tools/list":
                return self._result_response(req_id, {"tools": TOOLS_SPEC})

            if method == "tools/call":
                return self._handle_tool_call(req_id, param_dict)

            if method == "resources/list":
                return self._result_response(req_id, {"resources": RESOURCES_SPEC})

            if method == "resources/templates/list":
                return self._result_response(req_id, {"resourceTemplates": RESOURCE_TEMPLATES_SPEC})

            if method == "resources/read":
                return self._handle_resource_read(req_id, param_dict)

            if method == "resources/subscribe":
                uri = str(param_dict.get("uri") or "")
                if not uri:
                    return self._error_response(req_id, -32602, "Missing `uri` parameter")
                self._subscribed_uris.add(uri)
                return self._result_response(req_id, {})

            if method == "resources/unsubscribe":
                uri = str(param_dict.get("uri") or "")
                self._subscribed_uris.discard(uri)
                return self._result_response(req_id, {})

            if method == "prompts/list":
                return self._result_response(req_id, {"prompts": list_prompts()})

            if method == "prompts/get":
                pname = str(param_dict.get("name") or "")
                if not pname:
                    return self._error_response(req_id, -32602, "Missing `name` parameter")
                pargs = param_dict.get("arguments")
                if pargs is not None and not isinstance(pargs, dict):
                    return self._error_response(req_id, -32602, "`arguments` must be an object")
                try:
                    prompt_res = get_prompt(pname, pargs)
                except KeyError as exc:
                    return self._error_response(req_id, -32602, str(exc))
                return self._result_response(req_id, prompt_res)

            return self._error_response(req_id, -32601, f"Method not found: {method}")

        except Exception as exc:
            return self._error_response(req_id, -32603, f"Internal error: {exc}")

    def _handle_tool_call(self, req_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        tool_name = str(params.get("name") or "")
        if not tool_name:
            return self._error_response(req_id, -32602, "Missing tool `name`")
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            return self._error_response(req_id, -32602, "Tool `arguments` must be an object")

        known_tools = {
            "send_message",
            "ask_human_decision",
            "update_agent_seat",
            "push_canvas",
            "push_canvas_svg_or_jpeg",
            "read_inbox_and_receipts",
            "board_post",
            "board_read",
            "board_wait",
        }
        if tool_name not in known_tools:
            return self._error_response(req_id, -32602, f"Unknown tool: {tool_name}")

        def _int_arg(key: str, default: int) -> int:
            val = args.get(key)
            return default if val is None else int(val)

        def _float_arg(key: str, default: float) -> float:
            val = args.get(key)
            return default if val is None else float(val)

        def _bool_arg(key: str, default: bool) -> bool:
            val = args.get(key)
            return default if val is None else bool(val)

        try:
            if tool_name == "send_message":
                text_val = args.get("text") if args.get("text") is not None else args.get("body", "")
                res = self.client.send_message(
                    sender=str(args.get("sender") or "Agent"),
                    text=str(text_val or ""),
                    title=str(args.get("title") or ""),
                    font_size=_int_arg("font_size", 24),
                    align=str(args.get("align") or "left"),
                    reply_left=str(args.get("reply_left") or ""),
                    reply_right=str(args.get("reply_right") or ""),
                    avatar=str(args.get("avatar") or ""),
                    to=str(args.get("to") or ""),
                    to_inbox=_bool_arg("to_inbox", False),
                )
            elif tool_name == "ask_human_decision":
                res = self.client.ask_human_decision(
                    agent_name=str(args.get("agent_name") or "Agent"),
                    question=str(args.get("question") or ""),
                    session=str(args.get("session") or ""),
                    avatar=str(args.get("avatar") or "generic"),
                    left_choice=str(args.get("left_choice") or "批准"),
                    right_choice=str(args.get("right_choice") or "拒绝"),
                    timeout_sec=_float_arg("timeout_sec", 120.0),
                    agent_id=str(args.get("agent_id") or ""),
                    title=str(args.get("title") or ""),
                )
            elif tool_name == "update_agent_seat":
                res = self.client.update_agent_seat(
                    agent_id=str(args.get("agent_id") or ""),
                    agent_name=str(args.get("agent_name") or ""),
                    title=str(args.get("title") or ""),
                    session=str(args.get("session") or ""),
                    avatar=str(args.get("avatar") or "generic"),
                    status=str(args.get("status") or ""),
                    state=str(args.get("state") or "working"),
                    led=str(args.get("led") or ""),
                    progress=_int_arg("progress", -1),
                )
            elif tool_name in ("push_canvas", "push_canvas_svg_or_jpeg"):
                img_src = (
                    args.get("image_path_or_base64")
                    or args.get("image_source")
                    or args.get("image_jpeg_or_url")
                    or ""
                )
                res = self.client.push_canvas(
                    image_path_or_base64=str(img_src),
                    led_effect=str(args.get("led_effect") or ""),
                    caption=str(args.get("caption") or ""),
                    led_color=str(args.get("led_color") or "#39e69d"),
                    switch_to_canvas=_bool_arg("switch_to_canvas", True),
                )
            elif tool_name == "read_inbox_and_receipts":
                res = self.client.read_inbox_and_receipts(
                    unread_only=_bool_arg("unread_only", False),
                )
            elif tool_name == "board_post":
                res = self.client.board_post(
                    sender=str(args.get("sender") or "Agent"),
                    text=str(args.get("text") or ""),
                    to=str(args.get("to") or ""),
                    avatar=str(args.get("avatar") or "generic"),
                    title=str(args.get("title") or ""),
                    font_size=_int_arg("font_size", 24),
                    reply_left=str(args.get("reply_left") or ""),
                    reply_right=str(args.get("reply_right") or ""),
                    to_inbox=_bool_arg("to_inbox", False),
                )
            elif tool_name == "board_read":
                res = self.client.board_read(
                    since_seq=_int_arg("since_seq", 0),
                    limit=_int_arg("limit", 20),
                )
            elif tool_name == "board_wait":
                res = self.client.board_wait(
                    agent_name=str(args.get("agent_name") or ""),
                    since_seq=_int_arg("since_seq", 0),
                    mentions_only=_bool_arg("mentions_only", True),
                    timeout_sec=_float_arg("timeout_sec", 120.0),
                )
            else:
                return self._error_response(req_id, -32602, f"Unknown tool: {tool_name}")

            return self._result_response(
                req_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(res, ensure_ascii=False, indent=2),
                        }
                    ],
                    "isError": False,
                },
            )
        except Exception as exc:
            err_body = {"ok": False, "error": str(exc), "tool": tool_name}
            return self._result_response(
                req_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(err_body, ensure_ascii=False, indent=2),
                        }
                    ],
                    "isError": True,
                },
            )

    def _handle_resource_read(self, req_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        uri = str(params.get("uri") or "").strip()
        if not uri:
            return self._error_response(req_id, -32602, "Missing resource `uri`")

        parsed = urllib.parse.urlsplit(uri)
        if parsed.scheme != "mosaico":
            return self._error_response(req_id, -32602, f"Unsupported resource URI scheme: {uri}")

        resource_key = (parsed.netloc or parsed.path.lstrip("/")).lower()
        query_params = dict(urllib.parse.parse_qsl(parsed.query))

        if resource_key not in ("board", "inbox", "receipts", "status"):
            return self._error_response(req_id, -32602, f"Unknown resource URI: {uri}")

        try:
            if resource_key == "board":
                since = int(query_params.get("since", "0"))
                limit = int(query_params.get("limit", "32"))
                payload = self.client.board_read(since_seq=since, limit=limit)
            elif resource_key == "inbox":
                unread_only = query_params.get("unread_only") in ("1", "true", "yes")
                full = self.client.read_inbox_and_receipts(unread_only=unread_only)
                payload = {
                    "device_ip": full["device_ip"],
                    "head_seq": full["head_seq"],
                    "inbox_count": full["inbox_count"],
                    "unread_count": full["unread_count"],
                    "inbox": full["inbox"],
                }
            elif resource_key == "receipts":
                full = self.client.read_inbox_and_receipts(unread_only=False)
                payload = {
                    "device_ip": full["device_ip"],
                    "head_seq": full["head_seq"],
                    "read_count": full["read_count"],
                    "unread_count": full["unread_count"],
                    "starred_count": full["starred_count"],
                    "replied_count": full["replied_count"],
                    "receipts": full["receipts"],
                }
            else:  # status
                payload = self.client.get_device_status()
        except Exception as exc:
            # Return structured offline/error snapshot rather than crashing resource read when unplugged
            payload = {
                "online": False,
                "uri": uri,
                "error": str(exc),
                "cached_head_seq": self.client.hub.head_seq,
                "cached_entries": [
                    self.client.hub.board_entries[s]
                    for s in sorted(self.client.hub.board_entries.keys())
                ],
            }

        return self._result_response(
            req_id,
            {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(payload, ensure_ascii=False, indent=2),
                    }
                ]
            },
        )

    def _read_next_message(self) -> bytes | None:
        """Read one JSON-RPC message from `self._stdin` (supports newline JSON and Content-Length)."""
        while True:
            line = self._stdin.readline()
            if not line:
                return None
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower().startswith(b"content-length:"):
                self._framing_mode = "content-length"
                length = int(stripped.split(b":", 1)[1].strip())
                # Consume remaining headers up to blank line
                while True:
                    hdr_line = self._stdin.readline()
                    if not hdr_line or hdr_line in (b"\r\n", b"\n"):
                        break
                body = self._stdin.read(length)
                return body if body else None
            self._framing_mode = "line"
            return stripped

    def serve_forever(self) -> int:
        """Run the blocking `stdio` JSON-RPC 2.0 event loop until EOF."""
        try:
            while True:
                raw_bytes = self._read_next_message()
                if raw_bytes is None:
                    break
                try:
                    parsed = json.loads(raw_bytes.decode("utf-8"))
                except Exception as exc:
                    self._send_jsonrpc(self._error_response(None, -32700, f"Parse error: {exc}"))
                    continue

                # Run blocking tools (`ask_human_decision`, `board_wait`) on worker threads so `ping`
                # and concurrent tool calls never stall the stdio read loop!
                if (
                    isinstance(parsed, dict)
                    and parsed.get("method") == "tools/call"
                    and isinstance(parsed.get("params"), dict)
                    and parsed["params"].get("name") in ("ask_human_decision", "board_wait")
                ):
                    worker = threading.Thread(
                        target=self._run_worker,
                        args=(parsed,),
                        name="mosaico-mcp-blocking-tool",
                        daemon=True,
                    )
                    with self._workers_lock:
                        self._active_workers.add(worker)
                    worker.start()
                else:
                    self._run_and_reply(parsed)
        except KeyboardInterrupt:
            pass
        finally:
            with self._workers_lock:
                pending = list(self._active_workers)
            for worker in pending:
                worker.join(timeout=10.0)
            self.client.close()
        return 0

    def _run_worker(self, parsed: Any) -> None:
        try:
            self._run_and_reply(parsed)
        finally:
            with self._workers_lock:
                self._active_workers.discard(threading.current_thread())

    def _run_and_reply(self, parsed: Any) -> None:
        response = self.handle_payload(parsed)
        if response is not None:
            self._send_jsonrpc(response)
