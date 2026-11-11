#!/usr/bin/env python3
"""示例配方 02：《跨智能体圆桌辩论台（Physical Blackboard Multi-Agent Roundtable）》

展示场景：
- 异构多智能体（`@claude` 架构师 vs `@codex` 性能极客）通过 Mosaico 随身屏作为「物理共享黑板（Physical Blackboard）」直接对话！
- 全程使用 `board_post`、`board_read` 与事件驱动的 `board_wait`（基于 `/ws/hub` 长连接，等待期间零 HTTP 轮询、零 Token 消耗，10ms 唤醒）；
- 两轮交锋收敛出方案 A vs 方案 B 后，主持人 `@antigravity` 调用 `ask_human_decision` 触发琥珀橙整屏接管，请桌前人类按副板 `[L / R]` 物理键一锤定音！

运行方式：
  PYTHONPATH=mcp python3 mcp/examples/02_agent_roundtable_blackboard.py [--ip 192.168.5.92] [--decision-timeout 30]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mosaico_mcp import MosaicoClient  # noqa: E402


def run_codex_peer(ip: str | None, port: int | None, start_seq: int, out_log: list[dict]) -> None:
    """模拟独立进程中的 `@codex` 智能体：在物理黑板上 `board_wait` 守候 `@codex` 召唤并自动回帖。"""
    codex = MosaicoClient(explicit_ip=ip, explicit_port=port)
    try:
        codex.update_agent_seat(
            agent_id="seat-codex",
            agent_name="Codex",
            title="圆桌候命",
            session="Blackboard-Debate",
            avatar="codex",
            status="正在物理黑板守候 @codex 召唤...",
            state="working",
        )
        # 零轮询休眠：直到黑板上出现 `@codex` 或 `@all`
        wake = codex.board_wait(
            agent_name="codex",
            since_seq=start_seq,
            mentions_only=True,
            timeout_sec=15.0,
        )
        out_log.append(wake)
        if not wake["woke"]:
            return

        # 收到 Claude 的 @codex 提问后，在物理黑板回帖并 @antigravity 汇总裁决
        reply = codex.board_post(
            sender="codex",
            to="antigravity",
            avatar="codex",
            title="圆桌发言 · Codex",
            text=(
                "@claude 同意避免 7-socket 阻塞！但我建议保留板载无状态 POST /mcp 供云端直连，"
                "长等待走本地单条 /ws/hub。@antigravity 请提交人类拍板！"
            ),
            reply_left="支持双模",
            reply_right="仅留本地",
        )
        codex.update_agent_seat(
            agent_id="seat-codex",
            agent_name="Codex",
            title="已发表双模方案",
            session="Blackboard-Debate",
            avatar="codex",
            status=f"已在黑板 #{reply['seq']} 回应 Claude 并移交主持人",
            state="done",
        )
    finally:
        codex.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Mosaico 2.0 跨智能体物理黑板圆桌辩论示例")
    parser.add_argument("--ip", default=None, help="随身屏 IP（省略则自动发现）")
    parser.add_argument("--port", type=int, default=None, help="端口（默认 80）")
    parser.add_argument("--decision-timeout", type=float, default=20.0, help="等待人类物理按键拍板秒数")
    args = parser.parse_args()

    claude = MosaicoClient(explicit_ip=args.ip, explicit_port=args.port)
    moderator = MosaicoClient(explicit_ip=args.ip, explicit_port=args.port)
    codex_events: list[dict] = []

    try:
        initial_board = moderator.board_read(since_seq=0, limit=5)
        base_seq = initial_board["head_seq"]
        print(f"[圆桌开场] 已连接 Mosaico 物理黑板 ({initial_board['device_ip']})，当前 head_seq={base_seq}")

        # 启动独立线程模拟另一智能体 Codex 挂载在同一块物理黑板上
        codex_thread = threading.Thread(
            target=run_codex_peer,
            args=(initial_board["device_ip"], moderator.endpoint.port if moderator.endpoint else 80, base_seq, codex_events),
            daemon=True,
        )
        codex_thread.start()
        time.sleep(0.2)

        # 1. Claude 入席并发出第一帖，点名 @codex
        claude.update_agent_seat(
            agent_id="seat-claude",
            agent_name="Claude",
            title="发起架构辩论",
            session="Blackboard-Debate",
            avatar="claude",
            status="正在黑板阐述连接池边界...",
            state="working",
            led="breathe",
        )
        p1 = claude.board_post(
            sender="claude",
            to="codex",
            avatar="claude",
            title="圆桌发言 · Claude",
            text="@codex ESP32 HTTP 仅有 7 个并发槽位，长阻塞审批若走 HTTP 必死锁，应当全部收敛至 /ws/hub，你怎么看？",
            reply_left="赞同",
            reply_right="补充意见",
        )
        print(f"[Claude -> 黑板 #{p1['seq']}] 已发帖并 @codex")

        # 2. 主持人 Antigravity 在黑板上等待 @antigravity 汇总信号
        mod_wake = moderator.board_wait(
            agent_name="antigravity",
            since_seq=p1["seq"],
            mentions_only=True,
            timeout_sec=15.0,
        )
        codex_thread.join(timeout=5.0)
        print(f"[Antigravity 唤醒] 原因={mod_wake['reason']}，收到增量发言 {mod_wake['count']} 条")

        # 3. 琥珀橙整屏接管：请桌前人类按物理 [L / R] 键做最终架构裁决
        print(f"[琥珀橙拍板] 正在请求桌前人类物理按键裁决（限时 {args.decision_timeout}s）...")
        decision = moderator.ask_human_decision(
            agent_name="Antigravity",
            session="Blackboard-Debate",
            avatar="antigravity",
            title="圆桌架构裁决",
            question="Claude 与 Codex 已达成共识：采用「板载无状态 /mcp + 本地单 WS 复用」双模架构，是否批准实施？",
            left_choice="批准双模",
            right_choice="退回重议",
            timeout_sec=args.decision_timeout,
        )
        print(json.dumps(decision, ensure_ascii=False, indent=2))
        return 0
    finally:
        claude.close()
        moderator.close()


if __name__ == "__main__":
    raise SystemExit(main())
