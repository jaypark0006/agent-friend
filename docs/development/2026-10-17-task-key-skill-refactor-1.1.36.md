# 交付记录：解耦 Agent 身份与任务唯一键 (1.1.36)

- 日期：2026-10-17
- 版本：LAN Screen 1.1.36
- 设备目标：ESP-Mosaico (`esp32s31`), IP: `192.168.5.192`
- 安装状态：已构建并官方刷入，`firmware_mode: normal`, `crash_count: 0`, `stale: false`

---

## 1. 概念与架构重构

此前设计中，将 `id` 误用作 Agent 名称（如 `id="Antigravity"`），导致：
- 无法自然支持同一 Agent 的多轮对话历史推进；
- 固件端需要采用双阶段匹配等复杂启发式代码来猜测是否应覆盖还是新建卡片。

经与用户深入探讨，彻底厘清并规范职责模型：
1. **`id` 为任务唯一键（Task Key）**：
   - 由 Agent 自主决定（如 `task-1`、`turn-xxx`、时间戳或会话哈希）；
   - 纯作为内部卡片寻址与更新的主键，**无需且不会在屏幕上展示**；
   - 同一轮对话在初始化、推进与交付时，复用同一个 Task Key 进行原地更新；
   - 下一轮新对话到来时，Agent 派发新的 Task Key，在随身屏自然追加新的进度条，已完成历史完整留存。
2. **`title` 为屏幕展示标题**：
   - 由 Agent 自主决定（例如 `[Antigravity] 任务名称`），展示给用户。
3. **`agent` 为主体身份**：
   - 负责 Badge、主题色等视觉标识。

---

## 2. 代码改动清单

1. **固件端槽位匹配简化（`screen_widget.c`）**：
   - 彻底废除按 `done` 状态搜索倒序卡片的多阶段猜测算法；
   - 统一为严格的 Task Key 确定性直配：只要 `strcmp(items[i].id, id) == 0`，即进行就地更新；未匹配则在队尾追加新卡片；
   - 保护标题展示：若 `title` 为空，默认展示 `"Task"`，杜绝原始 Task ID 泄露到用户屏幕。
2. **容量扩展（`screen_widget.h`）**：
   - 将 `SCREEN_WIDGET_ID_MAX` 与 `SCREEN_WIDGET_TITLE_MAX` 从 32/36 扩展至 64 字节，充分容纳复合键与完整富文本标题。
3. **Skill 规范与脚本同步（`progress.py` & `SKILL.md`）**：
   - 更新 `progress.py` 参数语义：`--id` 明确标注为任务唯一键（由 Agent 自主决定），`--title` 为屏幕展示标题；新增可选 `--agent` 标识；
   - 同步更新项目 `.agents/skills/mosaico-notify/` 与用户全局 `~/.gemini/config/skills/mosaico-notify/` 以及 `mosaico_notify.md` 规则。
4. **编译部署**：
   - 版本递增为 `1.1.36`；低噪编译并通过官方 `iris app-update` 成功刷入，运行健康。
