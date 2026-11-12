# 版本交付与历史演进归档

本文档归档自根仓库 `AGENTS.md` 的历次版本交付摘要与早期硬件排查记录，供回溯查阅。各版本的完整技术细节见同目录下的专项交付记录（`YYYY-MM-DD-*.md`）。

## 1.1.26 – 1.1.60 交付摘要

- **1.1.60（2026-11-12）**：全面定位并根治用户反馈的「消息界面上下滑动很困难」紧急交互缺陷。剖析 LVGL 9 `lv_indev_search_obj` 穿透根因：为三大列表容器（`screen_ui_messages.c` 的 `a->text_list`、`screen_ui_tasks.c` 的 `s_tasks.list`、`screen_ui_settings.c` 的 `list`）重新挂载 `LV_OBJ_FLAG_CLICKABLE` 并移除 `LV_OBJ_FLAG_SCROLL_ELASTIC`；在快捷回复胶囊、待办任务跳转、Wi-Fi 点击中增加 `lv_obj_is_scrolling` 防御判定；移除 `read_tick` 每帧布局更新开销。子仓库提交 `1c169a0`，已刷入物理设备（IP `192.168.5.42`）。见 [2026-11-12-touch-scroll-fix-1.1.60.md](2026-11-12-touch-scroll-fix-1.1.60.md)。
- **1.1.59（2026-11-12）**：交付零外部依赖标准 Python MCP Server 包 `mcp/`（`mosaico-mcp`：8 Tools 含跨智能体物理共享黑板 `board_post`/`board_read`/`board_wait` 零轮询唤醒、4 Resources、3 Prompts 与 3 套多 Agent 示例，单条 `/ws/hub` 多路复用）、板载原生无状态 `POST /mcp` JSON-RPC 端点（`<50ms` 非阻塞，`GET /mcp` 返回 405 守住 7-socket 红线）与 `mosaico.local` mDNS、双向消息收件箱与快捷回信/1秒已读/橙键星标，收口 `review` 待回看提醒与 `/skills/agent_friend.py`，完成网页 `#send` 双向信箱投送台与 `#device` 首屏伴侣化折叠抽屉升级。子仓库提交 `0052e9e`。见 [2026-11-12-mcp-blackboard-1.1.59.md](2026-11-12-mcp-blackboard-1.1.59.md)。
- **1.1.58（2026-10-29）**：收口此前未上机的 1.1.57 与首屏连接/缓存、手机开发者页、favicon 修复。功能提交 `28dfdbc`。见 [2026-10-29-delivery-1.1.58.md](2026-10-29-delivery-1.1.58.md)。
- **1.1.56（2026-10-29）**：随身屏网页控制台全量重设计与裁决闭环。全量落地「Agent伴侣UI」规范，划分此刻（`#now`）、推送（`#send`）、设备（`#device`）、开发者（`#dev`）4 主页与 14 个旧 Hash 兼容重定向；新增 `POST /api/widget/decide` 原生裁决接口并以 `trigger:"web"` 向 `/ws/hub` 广播 `task.action`。见 [2026-10-29-web-console-redesign-1.1.56.md](2026-10-29-web-console-redesign-1.1.56.md)。
- **1.1.55（2026-10-29）**：界面调整第一批。常规体 20/24/32 补 GB2312 二级 3008 字与假名（共 7318 字），粗体保持 4118 字；`/api/widget` 新增 `agent`、`session`，`title` 只放任务名；进行中任务 10 分钟无上报标为「可能中断」，除待确认外 24 小时无上报自动清除。见 [2026-10-29-ui-batch1-1.1.55.md](2026-10-29-ui-batch1-1.1.55.md)。
- **1.1.54（2026-10-29）**：全量收口 Codex 代码审查 11 项发现并完成开源发布准备；实现 SPI Flash 持久化字库与 PSRAM LRU 动态按需缓存系统（6.17 MB 点阵包追加于固件尾部 `0x210000` OTA 分区）。见 [2026-10-29-code-review-closure-1.1.54.md](2026-10-29-code-review-closure-1.1.54.md) 与 [2026-10-29-persistent-flash-font-1.1.54.md](2026-10-29-persistent-flash-font-1.1.54.md)。
- **1.1.48（2026-10-28）**：按 Claude 设计画布「Mosaico 随身屏 · Agent 伴侣 UI」全量重做设备界面；主页面改为此刻/任务/消息/画面 4 页不循环；此刻页按「等你确认 › 1分钟内完成/出错 › 工作中 › 空闲」只显示一件事，确认整屏橙色接管；新增「灯光提示」（`led_hints`）。见 [2026-10-28-agent-companion-ui-1.1.48.md](2026-10-28-agent-companion-ui-1.1.48.md)。
- **1.1.47（2026-10-25）**：重构 `trigger_action_internal`，显式目标未决状态失败关闭；客户端 `progress.py` 先连接 WebSocket 再发布卡片，补齐 RFC 6455 合规性与 `--timeout` 超时机制。见 [2026-10-25-fix-card-index-and-ws-rfc-1.1.47.md](2026-10-25-fix-card-index-and-ws-rfc-1.1.47.md)。
- **1.1.46（2026-10-25）**：重构 `screen_widget_trigger_action_by_index` 与 `screen_widget_trigger_action_by_id`；`screen_interact` 实现 LED 槽位自动寻址；`progress.py` 接入原生 WebSocket `/ws/hub` 监听反向 `task.action` 事件。见 [2026-10-25-confirm-card-index-led-slot-1.1.46.md](2026-10-25-confirm-card-index-led-slot-1.1.46.md)。
- **1.1.45（2026-10-25）**：全量落地全双工 WebSocket 事件总线（`ws://IP/ws/hub`），支持下行 RPC 与上行反向事件流（`task.action`、`page.changed`、`device.orientation`）。见 [2026-10-25-websocket-hub-event-bus-1.1.45.md](2026-10-25-websocket-hub-event-bus-1.1.45.md)。
- **1.1.44（2026-10-25）**：根治转方向死机、切页滑动重启与长时间静置假死三大稳定性痛点。见 [2026-10-25-fix-freeze-reboot-1.1.44.md](2026-10-25-fix-freeze-reboot-1.1.44.md)。
- **1.1.43（2026-10-25）**：落地随身屏深海蓝黑 UI、控制中心 480×480 悬浮抽屉与待确认大尺寸胶囊按钮。见 [2026-10-25-claude-ui-design-v1.1.43.md](2026-10-25-claude-ui-design-v1.1.43.md)。
- **1.1.42（2026-10-25）**：引入 `utf8_safe_copy`、Page Dots 触控跳页、左右物理按键裁决与副板 PIR 免触感应唤醒。见 [2026-10-25-ux-code-refactor-1.1.42.md](2026-10-25-ux-code-refactor-1.1.42.md)。
- **1.1.41（2026-10-19）**：引入 SSDP 局域网组播服务发现（`239.255.255.250:1900`）与 UPnP `/description.xml` 支持。见 [2026-10-19-ssdp-upnp-discovery-1.1.41.md](2026-10-19-ssdp-upnp-discovery-1.1.41.md)。
- **1.1.40（2026-10-19）**：剥除 `screen_ui_refresh_battery` 内部递归锁，根除 GUI 任务死锁。见 [2026-10-19-gui-deadlock-fix-1.1.40.md](2026-10-19-gui-deadlock-fix-1.1.40.md)。
- **1.1.39（2026-10-19）**：顶栏常驻电池指示胶囊，修复 BQ27220 电量计初始化失步并引入后台自愈重试。见 [2026-10-19-battery-ui-gauge-recovery-1.1.39.md](2026-10-19-battery-ui-gauge-recovery-1.1.39.md)。
- **1.1.27 – 1.1.38（2026-10-09 至 2026-10-17）**：交互板初始化重试（1.1.27）、`/skills` 自描述服务（1.1.28）、声明式卡片就地更新（1.1.29）、50Hz 原生 LED 预制灯效与单轮生命周期（1.1.30）、Web 控制台重构（1.1.31/1.1.34）、双阶段槽位匹配保留历史（1.1.32）、对称渐变进度条扫光（1.1.33）、列表滑动性能优化（1.1.35/1.1.37/1.1.38）、Task ID 与 Title 解耦（1.1.36）。
- **1.1.26（2026-10-05）**：完成 P1–P5 模块化重构迁移（类型化命令/值快照、集中页面控制与相机意图服务、显示管线拆分、1MiB 图片历史预算）。见 [2026-10-05-refactor-1.1.26.md](2026-10-05-refactor-1.1.26.md)。

## 1.0.1 – 1.1.24 早期交付摘要

- **1.1.16 – 1.1.24（2026-10-04）**：交互子板（Slot 1 右槽 ID `0x16`）与翻转摄像头（Slot 0 左槽 ID `7`）接入、256×256 2×2 色块相机页、镜像安装校准 `Mx*R270` 与重力补偿、传感器 `:81/ws/sensors` 订阅工作台。见各对应日期文档及 [interaction-subboard-api.md](interaction-subboard-api.md)。
- **1.0.1 – 1.1.13（2026-10-03 至 2026-10-04）**：LAN Screen 原生工程起步、IMU 6 轴姿态自动旋转、图文独立主页面与 1 秒可见已读判定、230ms 页面滑动过渡、浏览器端 480×480 JPEG 粘贴压缩、麦克风/按键/摄像头扩展传感器 API。
