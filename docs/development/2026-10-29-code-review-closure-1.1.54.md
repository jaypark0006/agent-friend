# 2026-10-29 Codex 代码审查全量收口与开源发布准备交付 (1.1.54)

## 交付概述

本轮严格对照 Codex 在 [`docs/development/2026-10-29-code-review.md`](docs/development/2026-10-29-code-review.md)（commit `62f146b`）提出的 11 项代码缺陷及次级交付问题，完成了全量修复、工程收口与开源准备，并在官方构建工具下完成编译和真机升级验证（app-update 成功，normal/healthy）。

---

## 修复项对照表与验证证据

| 审查编号 | 级别 | 涉及文件 | 问题与解决方案 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| **R1** | P1 | `projects/lan_screen/main/screen_interact_http.c` | **LED 崩溃入口防护**：`effect` 存在时增加严格的 `cJSON_IsString(effect) && effect->valuestring` 检查，彻底消除空指针解引用崩溃；同时 REST 入口新增支持 `slot: "auto"` 及缺省自动寻址。 | **已解决** |
| **R2** | P1 | `README.md`, `CONTRIBUTING.md` | **烧录地址与芯片参数纠正**：删除错误的 `0x140000`（factory 保留区），纠正为 `0x210000`（`ota_0` 真实起始地址）；芯片参数明确为 ESP32-S3 / S31。 | **已解决** |
| **R3** | P2 | `main/skill.md`, `skills/mosaico-notify/SKILL.md` | **协议与事件字段对齐**：对齐设备 `/skills` 与固件实际发出的反向事件字段：`"action": "approve" \| "cancel"`，`"trigger": "physical_button_left" \| "physical_button_right" \| "touch"`；补充“先连接 WebSocket 监听再发送确认卡片”的最佳实践。 | **已解决** |
| **R4** | P2 | `projects/lan_screen/main/console-api.js` | **网页图片上传分流**：在 WebSocket 回调中过滤异步广播事件（`page.changed`, `task.action`, `device.orientation`, `sensors`），仅匹配 `image` 命令的 ACK，彻底避免广播事件误判为图片发送失败。 | **已解决** |
| **R5** | P2 | `projects/lan_screen/main/screen_ui_messages.c` | **16–64 字号行距渲染修正**：行间距按实际映射的字模档位（20/24/32）计算：`actual_size * 29 / 20 - lv_font_get_line_height(font)`，消除大字号请求时由于行距过大撑破卡片的问题。 | **已解决** |
| **R6** | P2 | `projects/lan_screen/tools/gen_flash_font.js` | **字库生成脚本 Magic 与路径兼容**：将头文件宏修正为小端正确的 `0x544E464D`（`"MFNT"`）；支持环境变量 `LV_FONT_CONV_PATH`、`FONT_REGULAR_TTF`、`FONT_BOLD_TTF`，消除本机硬编码路径锁定。 | **已解决** |
| **R7** | P2 | `main/screen_font_flash.c`, `main/screen_theme.c` | **字库初始化失败与 UI 兜底**：`screen_font_flash_init` 在 Magic 错误时明确返回 `ESP_ERR_INVALID_VERSION` 并记录错误；`screen_theme.c` 在字库加载失败或空指针时安全回退至 `lv_font_get_default()`，杜绝崩溃。 | **已解决** |
| **R8** | P2 | `main/screen_widget.h`, `main/screen_widget.c` | **报错任务退出待确认态**：`screen_agent_pending` 增加 `!it->error` 判定；上报 `error: true` 时自动清空未决 `action_type[0] = '\0'`，让失败任务退出裁决态，此刻页正确呈现红色错误脸与原因。 | **已解决** |
| **R9** | P2 | `progress.py`, `README.md` | **客户端唯一 ID 动态生成**：省略 `--id` 时动态使用 `<avatar/agent>-<timestamp>` 生成独立 ID，杜绝多 Agent 任务相互覆盖；`README.md` 示例显式展示 `--id` 保持流水线连续性。 | **已解决** |
| **R10** | P2 | `skills/mosaico-notify/scripts/progress.py` | **确认等待超时单调递减**：使用 `time.monotonic()` 严格计算单调递减的剩余超时时间；捕获 socket 超时后输出标准的 `{"error":"timeout"}` 并以退出码 3 退出，与 HTTP 轮询路径行为严格一致。 | **已解决** |
| **R11** | P2 | `projects/lan_screen/main/screen_ws.c` | **传感器 WS 跨线程竞争消除**：移除 `ws_broadcast_worker` 中跨线程直写 81 端口传感器 socket 的非线程安全调用；Port 81 由 `telemetry_task` 独占调度，Port 80 主 Hub 由 `a->http` 调度，帧边界安全隔离。 | **已解决** |

---

## 次级交付问题收尾

1. **发布导出脚本参数实现**：
   - 重构 [`scripts/export-release.py`](scripts/export-release.py)，使用 `argparse` 支持 `--version` 与 `--output-dir`，元数据缺失时自动回退提取 CMakeLists.txt，生成 SHA256SUMS 校验清单。
2. **客户端设备探测去私有化**：
   - 移除了 [`skills/mosaico-notify/scripts/notify.py`](skills/mosaico-notify/scripts/notify.py) 中的硬编码私人 MAC；优先从本地缓存、SSDP 组播探测，未指定 MAC 环境变量时自动接入局域网发现的 Agent Friend 伴侣屏。
3. **未完成模块原型标识**：
   - 在 [`apps/agent-visualizer/README.md`](apps/agent-visualizer/README.md) 中明确标注为实验性原型（Experimental Prototype），避免与固件主线构建混淆。
4. **架构与内存文档同步**：
   - 更新 [`docs/architecture.md`](vendor/esp-mosaico-vibe/projects/lan_screen/docs/architecture.md) 与 [`docs/memory-budget.md`](vendor/esp-mosaico-vibe/projects/lan_screen/docs/memory-budget.md) 至 1.1.54，准确记录 Flash 紧凑字库持久化与 PSRAM LRU 动态按需缓存（128 槽位 ~144 KB）系统，可用 PSRAM 达到 9.89 MB。
5. **设备服务描述与命名彻底统一**：
   - 固件重新烧录后，设备局域网 UPnP 描述 `http://192.168.5.92/description.xml` 与自描述技能 `http://192.168.5.92/skills` 全量统一为 `agent-friend` 与 `Agent Friend Companion Screen`。

---

## 构建与部署闭环

- **固件构建**：低噪音编译 10.7s，产物大小 8,930,853 字节（包含 6.17 MB Flash 字库）；
- **官方真机安装**：`mosaico.py iris app-update --skip-build` OTA 烧录 100% 成功；
- **设备运行状态**：设备恢复连接并上报 `mode=normal`，`app=lan_screen`，`version=1.1.54`，`crash_count=0`；
- **便携式归档**：子仓库提交为 `e5bf847`，运行 `save-firmware-history.py` 刷新 `dependencies/esp-mosaico-vibe.bundle`（4,109 objects, 25.49 MB）并验证通过。
