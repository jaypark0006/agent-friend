# 1.1.59 标准 MCP Server、物理共享黑板与双向收件箱交付

日期：2026-11-12（Asia/Shanghai）。本轮围绕「从被动工具端点（MCP Sink）跃迁为多智能体物理协作伴侣」完成架构升级，交付零外部依赖标准 Python MCP Server（`mosaico-mcp`）、板载无状态 `POST /mcp` 与 `mosaico.local` mDNS、跨智能体物理共享黑板、双向消息收件箱与快捷回信/星标，并同步收口此前未提交的 `review`（待回看）提醒与网页 `#send` / `#device` 净化升级。

## 交付内容

1. **标准 Python MCP Server 包（`mcp/`，`mosaico-mcp` v2.0.0）**
   - 纯 Python 3.10+ 标准库零第三方运行时依赖，支持 `uvx --from ./mcp mosaico-mcp` 或 `PYTHONPATH=./mcp python3 -m mosaico_mcp` 标准 `stdio` 接入。
   - **零配置局域网寻址（`discovery.py`）**：按 `MOSAICO_IP` / `MOSAICO_HOST` → `mosaico.local` mDNS（OS 解析 + UDP 5353 原生报文兜底） → SSDP 组播（`239.255.255.250:1900`） → 本地缓存 → ARP 身份核验顺序自动发现设备。
   - **单连接多路复用总线（`ws_hub.py`）**：手写合规 RFC 6455 客户端复用单条 `/ws/hub` 连接承载下行 RPC 与上行反向事件流，严守 ESP32 HTTP Server 7-socket 安全预算，断连自动平滑降级 REST。
   - **8 Tools · 4 Resources · 3 Prompts**：
     - 交互与画布工具：`send_message`（7,318 字中文/假名精排短笺 + 左右物理键快捷回信选项）、`ask_human_decision`（琥珀橙整屏接管 + 副板双闪警示，阻塞等待真实按键/触屏/网页裁决，超时明确失败关闭绝不假冒同意）、`update_agent_seat`（13 种 9×7 专属动效脸与状态席位）、`push_canvas`（480×480 baseline JPEG 转换与纯标准库纯色幕布合成）、`read_inbox_and_receipts`（人类来信、1 秒真·已读、星标与按键回执）。
     - 跨智能体物理共享黑板三原语：`board_post`、`board_read`、`board_wait`（基于 `Condition` 与 `/ws/hub` 实时广播实现零轮询休眠与 `<10ms` `@mention` / `@all` 唤醒）。
     - 资源与主动推送：`mosaico://board`、`mosaico://inbox`、`mosaico://receipts`、`mosaico://status`，收到设备事件自动向宿主推送 `notifications/resources/updated`。
     - 内置工作流模板与示例：`morning_zine`、`agent_roundtable`、`market_tide_note` 及 `mcp/examples/` 下 3 套多 Agent 协作脚本。

2. **固件 C 层升级（子仓库提交 `eb46323`）**
   - **回看提醒（`review`）与自举脚本**：收口 `action.type="review"` 待回看提醒状态（屏幕/物理键/网页支持「知道了」或「稍后」确认）及 `/skills/agent_friend.py` 自举助手脚本。
   - **板载原生无状态 `POST /mcp`（`screen_mcp.c`）与 `mosaico.local` mDNS（`screen_network.c`）**：新增非阻塞 JSON-RPC 2.0 Streamable HTTP 端点 `POST /mcp`（`<50ms` 立即返回，`GET /mcp` 返回 `405 Method Not Allowed` 拒绝 SSE 长挂起保护 7-socket 上限；人机确认拆分为非阻塞 `post_decision` + `check_decision`）；随 Wi-Fi 启动 `mosaico.local` mDNS 服务广播。
   - **双向消息收件箱与物理共享黑板（`screen_text.c`、`screen_content_http.c`、`screen_ui_messages.c`、`screen_buttons.c`、`screen_ws.c`）**：
     - 扩展 `POST /api/text` 支持 `from`、`to`、`to_inbox`、`reply_left`、`reply_right` 并维护单调递增 `seq`；新增 `POST /api/text/reply`、`GET /api/board`、`GET /api/inbox`；
     - 随身屏《消息页》卡片静止浏览满 1 秒自动置位 `read: true` 并广播 `message.read`；副板 L/R 物理键一键触发快捷回复胶囊并广播 `message.reply`；短按机身橙色 AI 键切换 `★` 星标；
     - `/ws/hub` 新增 `board.post`、`inbox.message`、`message.reply`、`message.read` 四类异步广播事件（均在释放 UI 锁后经 `httpd_queue_work` 投递，零锁竞争），并修复代码审查发现的 `screen_http_text_reply` 悬垂指针读取与 `action` 对象 Schema 兼容。

3. **网页控制台升级（`api.html`、`console-send.js`、`console-device.js` 等）**
   - `#send` 升级为「双向信箱与物理黑板精排投送台」：支持发送方署名、`to_inbox` 开关、`@all`/`@claude`/`@codex`/`@antigravity` 快捷点名胶囊、左右快捷回复词预设、480×480 实时等比预览、分段过滤历史流及按需单条 `/ws/hub` 实时回执同步（切页或隐藏标签页立即断开释放）。
   - `#device` 首屏伴侣化净化：突出控制开关、6 颗 RGB 灯光工作台与「电量与网络（含 `mosaico.local` 与 `/mcp` 入口）」核心卡，将陀螺仪/磁力计/加速度、原始音频/镜头帧、红外等治具遥测完整收纳至底部默认折叠的诊断抽屉。
   - 15 个内嵌静态文件总计 `198,953` 字节（`194.29 KiB < 200 KB` 预算），`innerHTML` 计数为 `0`，HTML 行内 `style=` 计数为 `0`，13 个 JS 模块 `node --check` 全部通过。

## 构建、测试与归档证据

| 项目 | 结果 |
| --- | --- |
| 固件子仓库提交 | `eb463237d382cc85b8fdf29242247ff497124c10`（`eb46323`），未向官方上游推送 |
| Git Bundle 校验 | `dependencies/esp-mosaico-vibe.bundle` 覆盖 `refs/heads/main -> eb46323`，`git bundle verify` 通过 |
| 工具链与目标 | ESP-IDF `7b9cc1ac79f865983f59bb8ff3ff43eb74ff1dbe`，target `esp32s31` |
| 官方低噪音编译 | `exit_code=0`，C 编译器警告 `0` 条（仅保留 ESP-IDF 对未使用 `factory` 分区的既有固定尺寸提示） |
| 构建工程版本 | `1.1.59` |
| `build/lan_screen.elf` | `25,757,876` 字节，SHA-256 `e113dc393becef33b7be74432028b295b7efb429011db21efbcdefa004880617` |
| `build/lan_screen.bin` | `12,097,737` 字节（11.54 MiB，含前端静态资源与追加字库包），SHA-256 `8a5a18a1b42a3fd2fa72f4070f047220a7d038fe413a5928474bd73417e76a08` |
| 导出发行包 | `dist/release-v1.1.59/lan_screen_v1.1.59.bin` 与 `SHA256SUMS`（`.gitignore` 忽略本地 `dist/`） |
| MCP 协议单测 | `python3 -m unittest discover -s mcp/tests -p "test_*.py" -v`：**`8/8` 全绿通过（`OK`）**，含真实 `stdio` 子进程握手与 3 套多 Agent 示例脚本端到端验证 |

## 实机状态与诚实边界

- 执行只读 `mosaico.py iris list --details --json` 核查，当前物理设备未连接本机 USB（`endpoints: []`，缓存设备 `offline`）。
- 因此 **1.1.59 本轮仅完成本地固件编译、自动化协议单测、Git Bundle 归档与 GitHub 开源仓库发布，尚未通过 USB 刷入物理设备，也未执行 1.1.59 实机触屏/按键/mDNS 效果验收**；未开启摄像头或麦克风，未向局域网已运行设备乱推测试卡片。
- 物理设备当前上机运行版本仍为 **1.1.58**（见[1.1.58 交付记录](2026-10-29-delivery-1.1.58.md)）；后续连接 USB 后可执行 `python3 mosaico.py iris app-update --project projects/lan_screen --skip-build` 刷入 1.1.59。
