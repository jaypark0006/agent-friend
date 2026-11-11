"""Built-in MCP Prompt templates for Mosaico 2.0 community signature workflows."""

from __future__ import annotations

from typing import Any

PROMPTS_SPEC: list[dict[str, Any]] = [
    {
        "name": "morning_zine",
        "description": "【晨间精排中文私刊早报】用 7,318 字出版级平滑字库向《消息页》投递 3~5 张精排短笺/日语闪卡，绑定物理 L/R 快捷回复并感知 1 秒真·已读。",
        "arguments": [
            {
                "name": "topics",
                "description": "关注主题（如：AI 核心论文、独立硬件动态、每日一句日语假名闪卡）",
                "required": False,
            },
            {
                "name": "editor_persona",
                "description": "主编文风人设（默认：克制犀利、字字珠玑的桌面私刊主编）",
                "required": False,
            },
            {
                "name": "card_count",
                "description": "投递卡片张数（建议 3~5 张）",
                "required": False,
            },
        ],
    },
    {
        "name": "agent_roundtable",
        "description": "【多智能体圆桌会议室 · 物理黑板】跨厂商 Agent Team 围绕随身屏物理共享黑板（board_post / board_read / board_wait）辩论协作，分歧时触发琥珀橙整屏拍板。",
        "arguments": [
            {
                "name": "topic",
                "description": "本次圆桌讨论或方案评审的议题",
                "required": True,
            },
            {
                "name": "agent_name",
                "description": "当前智能体在黑板上的署名（如 claude / codex / antigravity）",
                "required": False,
            },
            {
                "name": "avatar",
                "description": "对应的 9x7 点阵专属动效脸（claude / codex / antigravity / gemini / cursor 等）",
                "required": False,
            },
            {
                "name": "peers",
                "description": "同桌协作的其他智能体列表（如 @codex, @antigravity）",
                "required": False,
            },
        ],
    },
    {
        "name": "market_tide_note",
        "description": "【会说人话的异动简报】拒绝冷冰冰滚数字：一句话讲透异动背后的核心逻辑投递《消息页》，同步推送 480x480 趋势画布并联动 50Hz 六灯氛围。",
        "arguments": [
            {
                "name": "asset_or_metric",
                "description": "关注的标的或创作者指标（如 NVDA、USD/CNY、GitHub Stars）",
                "required": True,
            },
            {
                "name": "change_summary",
                "description": "当前观测到的异动事实或原始数据摘要",
                "required": False,
            },
            {
                "name": "mood",
                "description": "异动情绪映射（surge=强势突破 / dip=回调警示 / calm=温和观察）",
                "required": False,
            },
        ],
    },
]


def list_prompts() -> list[dict[str, Any]]:
    return PROMPTS_SPEC


def get_prompt(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    if name == "morning_zine":
        topics = str(args.get("topics") or "AI 前沿突破、开源硬件灵感、每日日语假名词汇闪卡")
        persona = str(args.get("editor_persona") or "克制犀利、拒绝废话的独立私刊主编")
        count = str(args.get("card_count") or "3")
        text = (
            f"你现在担任 Mosaico 随身屏的「{persona}」。设备搭载 7,318 字 Noto Sans SC 多字号（20/24/32px）"
            "平滑字库（覆盖 GB2312 一二级汉字与日文平片假名，墨黑底 #0C0B0A + 米白字 #F5F1EA，注意屏幕自动滤除 Emoji，"
            "请善用中文标点、`·`、`←/→` 与精炼排版）。\n\n"
            f"请围绕主题【{topics}】编撰 {count} 张晨间私刊卡片，并依次执行：\n"
            "1. 先调用 `read_inbox_and_receipts(unread_only=False)` 查看用户昨天哪些卡片已停留满 1 秒标为 `read: true`、"
            "哪些打了 `starred: true` 星标或按了物理键回执，据此微调今日选题偏好；\n"
            "2. 对每张卡片调用 `send_message(sender='早报主编', title=..., text=..., font_size=24, "
            "reply_left='继续深挖', reply_right='下一篇')`，每张正文控制在 60~140 字，三句话讲透洞察；"
            "若含日语闪卡，直接使用平假名/片假名注音；\n"
            "3. 投递完成后，用 `update_agent_seat` 将席位设为 `state='review'`（提示用户清晨归座翻阅），"
            "或调用 `board_wait` 静默守候用户按下物理左键触发深挖。"
        )
        return {
            "description": "晨间精排中文私刊早报编撰与双向已读闭环工作流",
            "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
        }

    if name == "agent_roundtable":
        topic = str(args.get("topic") or "核心系统架构与体验取舍")
        agent_name = str(args.get("agent_name") or "claude").lstrip("@")
        avatar = str(args.get("avatar") or agent_name or "generic")
        peers = str(args.get("peers") or "@codex, @antigravity")
        text = (
            f"你正在参与基于 ESP-Mosaico 物理共享黑板（Physical Blackboard）的跨智能体圆桌会议。\n"
            f"- 你的身份：`@{agent_name}`（点阵动效脸 `avatar='{avatar}'`）\n"
            f"- 同桌伙伴：{peers}\n"
            f"- 当前议题：【{topic}】\n\n"
            "请严格遵循 Mosaico 圆桌黑板协议：\n"
            f"1. **入席亮灯**：先调用 `update_agent_seat(agent_id='{agent_name}', agent_name='{agent_name}', "
            f"title='圆桌辩论', avatar='{avatar}', status='正在研读黑板上下文', state='working', led='breathe')`；\n"
            "2. **先读后言**：调用 `board_read(since_seq=0, limit=20)` 读取黑板上的最新 `head_seq`、队友观点以及桌前人类的插话；\n"
            f"3. **精炼发帖**：调用 `board_post(sender='{agent_name}', avatar='{avatar}', text='...', "
            "reply_left='赞同此路', reply_right='换个方向')` 发表你的核心论点（控制在 120 字以内，在文末明确 `@下一位队友` 交棒）；\n"
            f"4. **零轮询休眠**：交棒后立即调用 `board_wait(agent_name='{agent_name}', since_seq=最新seq, mentions_only=True)` "
            "进入 `/ws/hub` 事件驱动休眠，绝不轮询刷屏；\n"
            "5. **人类一锤定音**：当你们收敛出方案 A vs 方案 B 时，调用 `ask_human_decision` 触发琥珀橙整屏接管，"
            "请桌前人类按副板物理左/右键拍板裁决！"
        )
        return {
            "description": f"多智能体物理黑板圆桌协议（议题：{topic}）",
            "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
        }

    if name == "market_tide_note":
        asset = str(args.get("asset_or_metric") or "核心关注标的")
        summary = str(args.get("change_summary") or "请结合最新异动数据总结")
        mood = str(args.get("mood") or "calm").lower()
        led_map = {"surge": "chase", "dip": "warning", "calm": "breathe"}
        led_effect = led_map.get(mood, "breathe")
        text = (
            f"你是 Mosaico 随身屏上的「潮汐数据哨兵」。传统副屏只滚冷冰冰的价格数字，而你的职责是用优美克制的中文"
            f"一句话讲清【{asset}】异动背后的真正逻辑。\n"
            f"- 观测摘要：{summary}\n"
            f"- 建议氛围灯效：`{led_effect}`\n\n"
            "请执行以下联动动作：\n"
            "1. 调用 `send_message(sender='潮汐哨兵', title=..., text=..., font_size=24, "
            "reply_left='展开拆解', reply_right='知悉静默')`，标题写清标的与幅度，正文不超过 3 句，直击驱动因素与后续观察点；\n"
            f"2. 若已准备好 480x480 深色趋势图（本地路径、base64 或先推纯色氛围幕布 `solid:#101720`），"
            f"调用 `push_canvas(..., led_effect='{led_effect}')` 同步点亮 50Hz 六灯氛围；\n"
            "3. 若异动触及预设风控阈值需要人类决策，调用 `ask_human_decision` 请求物理按键确认。"
        )
        return {
            "description": f"会说人话的异动简报与画布灯光联动（{asset}）",
            "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
        }

    raise KeyError(f"Unknown prompt: {name}")
