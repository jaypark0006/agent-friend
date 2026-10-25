# 1.1.45 交付记录：全双工 WebSocket 事件总线与反向事件流

- 交付日期：2026-10-25
- 固件版本：1.1.45
- 硬件目标：ESP-Mosaico (`esp32s31`)

## 一、 交付目标

针对此前 WebSocket 通道割裂（80 端口 `/ws/frames` vs 81 端口 `/ws/sensors`）、网络线程跨线程穿透 UI 锁、以及最致命的“缺少反向事件推送导致 Agent 只能 500ms 轮询 HTTP”三大架构硬伤，构建**工业级全双工 WebSocket 事件总线**。

## 二、 核心改进

1. **统一端点与多路复用 (`/ws/hub` & `/ws/frames`)**：
   - 新增独立模块 `screen_ws.h` 与 `screen_ws.c`，注册统一长连接接入点 `/ws/hub`，兼容旧版 `/ws/frames`；
   - 支持结构化 RPC 命令（`widget.update`, `widget.get`, `view.switch`, `text.send`, `config.set`, `led.set`, `get`, `ping`），统一返回带 `request_id` 的确定性 `ack` 回执。
2. **反向事件流（Reverse Event Stream）实时主动推送**：
   - **`task.action`**：用户在屏幕上点击 `[L] 批准` / `[R] 取消`，或按压副板左右物理机械键时，毫秒级主动向所有已连接的 WebSocket 客户端广播事件：
     ```json
     {
       "type": "event",
       "event": "task.action",
       "id": "<task_id>",
       "action": "approve" | "cancel",
       "choice": "Approve" | "Cancel",
       "trigger": "touch" | "physical_button_left" | "physical_button_right",
       "timestamp_us": 12345678
     }
     ```
     **彻底终结 Agent 对 `/api/widget` 的高频 HTTP 轮询**！
   - **`page.changed`**：手势滑动切页、Page Dots 直达点按、或抽屉呼出时，实时广播当前主页名称。
   - **`device.orientation`**：6 轴 IMU 检测到物理旋转姿态变化时，实时广播 `rotation_deg`。
3. **异步工作队列解耦（Non-blocking Queue Work）**：
   - 广播通过 `httpd_queue_work` 异步调度，Display 渲染线程与物理按键中断绝不被网络 I/O 阻塞；
   - 自动向 Port 80 (`/ws/hub`, `/ws/frames`) 与 Port 81 (`/ws/sensors`) 上的所有存活 WebSocket 客户端并行广播，双向兼容。

## 三、 固件编译与刷入确认

- 固件编译：`lan_screen.bin`（5,050,528 字节，exit_code=0）；
- 官方 CLI：`mosaico.py iris app-update --skip-build` 刷入 100% 成功；
- 设备状态：`app=lan_screen`, `version=1.1.45`, `connected=true`, `crash_count=0`。
