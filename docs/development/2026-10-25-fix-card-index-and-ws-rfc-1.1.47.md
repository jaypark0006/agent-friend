# 1.1.47 交付记录：确认卡片目标隔离、WS 协议合规与防漏事件重构

- 交付日期：2026-10-25
- 固件版本：1.1.47
- 硬件目标：ESP-Mosaico (`esp32s31`)

## 一、 背景与复审问题

在 1.1.46 交付后，Codex 对固件 `fd62ed0` 与技能链路进行了深入复审，记录了以下待修复缺陷：
1. **P1：可能误裁决其他任务**：
   - `screen_widget_trigger_action_by_index` 在指定卡片失效、已裁决或变动时，仍然无脑回退查找首个待确认任务（`if (chosen_idx < 0) { for (...) }`）。
   - 触控事件与后台任务更新交错时，可能误将用户的点击当作另一个任务的批准/取消授权。
2. **P2：确认事件存在遗漏窗口**：
   - `progress.py --wait-confirm` 先通过 HTTP POST 发布确认卡片，后连接 WebSocket。
   - 用户在两步间隙若立即按下屏幕或实体按键，广播事件会在建连前发出，导致 WebSocket 监听错过该事件，白白等待 120 秒超时。
3. **P2：WS 超时后进入无限 HTTP 轮询**：
   - WebSocket 异常或超时后，原脚本进入 `while True: time.sleep(0.5); request(...)` 死循环，与“无需轮询”承诺不符，缺乏明确超时退出边界。
4. **P2：WS Pong 格式不完整**：
   - 手写客户端未加客户端掩码（RFC 6455 强制要求客户端向服务端发送的所有帧必须 Mask）；
   - 未回显 Ping 携带的 Payload，可能遭标准服务端断开；
   - 握手阶段未校验 `Sec-WebSocket-Accept`。
5. **P2：设备 `/skills` 中的 LED 接口示例错误**：
   - 示例给出 `{"preset":"breathe"}`，缺少 `slot`，且参数名与底层 HTTP 解析器要求的 `effect` 不符，照抄会被拒收。

---

## 二、 核心重构与改动

### 1. 固件层（C / ESP-IDF）
- **`screen_widget.c`**：
  - 重构为内部统一裁决核心 `trigger_action_internal(struct screen_app *a, const char *task_id, int target_idx, int which, const char *trigger)`；
  - **明确区分定向触发与无目标触发**：
    - 若传入显式目标（`task_id` 或 `target_idx >= 0`），仅在目标匹配且处于未决状态时裁决；若目标已处理、已失效或不存在，**直接置 `chosen_idx = -1` 并失败关闭，严禁回退到其他任务**！
    - **仅当物理按键触发（`target_idx < 0` 且 `task_id == NULL`）时**，允许从队列首部查找第一个待决任务进行兜底裁决；
    - 全程在单一 `screen_lock(a)` 锁内完成查找与修改，杜绝锁重入与时序交错。
- **`screen_network.c`**：
  - 更正 `/skills` 中的 LED 调用示例为：
    ```sh
    curl -X POST http://{{DEVICE_IP}}/api/interact/leds \
      -H "Content-Type: application/json" \
      -d '{"slot":"right","effect":"breathe"}' // slots: right, left, auto; effects: breathe, chase, rainbow, alert, success, off
    ```
- **版本号收拢**：
  - `CMakeLists.txt`、`sdkconfig.defaults`、`version.txt`、`/skills` 与自描述 API 全面升级收拢为 **1.1.47**。

### 2. 客户端脚本与协议层（Python / Skills）
- **`progress.py` 先建连后发卡**：
  - 在 `--wait-confirm` 模式下，**先建立并握手 WebSocket 连接**，再通过 HTTP 发布确认卡片；
  - 彻底根除发卡与建连间隙的事件遗漏窗口。
- **`progress.py` RFC 6455 全规范合规**：
  - **Sec-WebSocket-Accept 严格校验**：计算 `base64(sha1(key + MAGIC))` 并核验服务端回执；
  - **强制客户端帧掩码（Masking）**：发出的所有客户端帧（Pong、Close 等）均生成 4 字节安全随机掩码并异或编码；
  - **Ping 载荷镜像回传**：收到 Ping 帧时，原样读取 payload 并构筑 Pong 帧回传；
  - **资源释放安全保护**：使用 `finally` 块确保套接字无论成功、超时或异常均安全关闭。
- **`progress.py` 严格超时与终结无限轮询**：
  - 引入 `--timeout` 参数（默认 60s）；
  - 若在超时期限内未收到用户输入，明确输出 `{"error":"timeout","message":...}` 并以状态码 3 退出，杜绝死循环轮询。

---

## 三、 固件构建与实机刷入确认

- **固件构建**：官方增量低噪音编译，产物 `lan_screen.bin`（5,051,232 字节），0 错误；
- **官方安装**：`mosaico.py iris app-update --skip-build` 完整刷入目标设备 `4553502d4952495301001c2904d0ad2a`；
- **设备运行状态**：
  - `app=lan_screen`
  - `version=1.1.47`
  - `ip=192.168.5.69`
  - `connected=true`
  - `crash_count=0`
