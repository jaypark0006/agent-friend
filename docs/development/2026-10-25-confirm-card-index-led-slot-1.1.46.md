# 1.1.46 交付记录：确认卡片索引精准裁决、LED Slot 自动寻址与通知缓存自愈

- 交付日期：2026-10-25
- 固件版本：1.1.46
- 硬件目标：ESP-Mosaico (`esp32s31`)

## 一、 背景与审查发现

在 Codex 进行项目代码与通知链路审查时，指出了两个固件实际问题和三个客户端通知链路痛点：
1. **固件缺陷 A：触控裁决误伤第一张卡片**：
   - 在 `screen_widget.c` 中，点击卡片按钮的事件回调 `action_btn_cb` 仅传入按钮类型（`which=1` 为批准，`2` 为取消），但 `screen_widget_trigger_action_ex` 内部循环 `for(i=0; i<w->count; i++)` 只要遇到第一张待确认卡片就执行裁决并 `break`。
   - 当任务列表中存在多张待确认卡片时，点击第二张或更后面的卡片，会误裁决队列第一张卡片。
2. **固件缺陷 B：WebSocket `led.set` 与状态通知硬编码 Slot 0**：
   - 随身屏左槽为摄像头（Slot 0），右槽为交互副板（Slot 1）。
   - 在 `screen_ws.c` 中，`led.set` 命令硬编码调用 `screen_interact_set_leds_effect(..., 0, ...)`，且 `screen_widget.c` 裁决反馈也硬编码操作 Slot 0。当 Slot 0 没有交互板驱动时，驱动拒绝执行指令，导致外部 Agent 通过 WebSocket 设置 LED 动画失败。
3. **客户端痛点 C：发现机制未刷新本地缓存导致 Codex 误判设备离线**：
   - `~/.cache/mosaico-notify/address.json` 遗留了旧 IP（`192.168.5.192`）；
   - 平时 `progress.py` 与 `receipt.py` 即使通过 SSDP/ARP 自动发现了设备真实 IP（`192.168.5.69`），也未将新 IP 写回 `address.json`；
   - Codex 读取该文件后以单点验证失败，严格遵守不可重试与离线停止保护规则，误判设备离线。
4. **客户端痛点 D：`progress.py` `--wait-confirm` 仍走 HTTP 轮询**：
   - 固件 1.1.45 已实现全双工 WebSocket 反向事件广播（`task.action`），但客户端脚本仍每 500ms 轮询 HTTP。
5. **客户端痛点 E：`receipt.py` 包含过期的 1.1.30 默认版本与假验收字样**。

---

## 二、 核心重构与改动

### 1. 固件层（C / ESP-IDF）
- **`screen_widget.h` / `screen_widget.c`**：
  - 新增 `screen_widget_trigger_action_by_index(struct screen_app *a, int target_idx, int which, const char *trigger)` 与 `screen_widget_trigger_action_by_id(...)`；
  - 触控卡片时，`action_btn_cb` 从父级 `card` 对象的 `user_data` 读取 `target_idx`，精准锁定被点击卡片槽位；
  - 实体物理机械按键调用时传入 `target_idx = -1`，保持对当前最顶层待确认卡片的快捷裁决。
- **`screen_interact.h` / `screen_interact.c`**：
  - 定义 `SCREEN_INTERACT_SLOT_AUTO = 0xFF`；
  - 在 `screen_interact_set_leds_pattern` 与 `screen_interact_set_leds_effect` 中引入插槽自适应探测逻辑：若指定 Slot 不可用或为 AUTO，自动探测并使用当前可用的副板插槽（Slot 1 右槽优先，Slot 0 左槽备用），彻底解决槽位硬编码问题。
- **`screen_ws.c`**：
  - `led.set` 支持可选参数 `"slot": "auto"|"right"|"left"`，默认采用自动寻址，彻底打通 WebSocket 全双工灯效控制。
- **版本号升级**：
  - `CMakeLists.txt`、`sdkconfig.defaults`、`version.txt`、`/skills` 与自描述 API 全面升级收拢为 **1.1.46**。

### 2. 客户端脚本与技能规范（Python / Skills）
- **`notify.py`**：
  - 提取 `save_cache(ip)`，在 `discover()` 成功验证设备后无条件将真实活跃 IP 和 MAC 覆盖写入 `~/.cache/mosaico-notify/address.json`，实现缓存自愈。
- **`progress.py`**：
  - 实现基于 Python 标准库（零外部依赖、RFC 6455 纯套接字）的轻量 WebSocket 客户端 `wait_confirm_ws`，长连接接入 `ws://<DEVICE_IP>/ws/hub`；
  - 优先监听 `task.action` 反向事件推送，实现毫秒级即刻响应退出；若网络异常则自动回退至 HTTP 轮询。
- **`receipt.py`**：
  - 统一更新默认版本至 `1.1.46`；
  - 剔除“100% HEALTHY”、“实机部署与健康状态核验正常”等文字，将视觉重心放回真实成果。
- **全平台同步**：
  - 统一同步至 `.agents/skills/mosaico-notify/`、`skills/mosaico-notify/`、`~/.gemini/config/skills/mosaico-notify/` 及 `~/.codex/skills/mosaico-notify/`；
  - 更新 `AGENTS.md` 与全局规则 `mosaico_notify.md`。

---

## 三、 固件构建与实机刷入确认

- **固件构建**：官方增量低噪音编译，产物 `lan_screen.bin`（5,051,056 字节），0 错误；
- **官方安装**：`mosaico.py iris app-update --skip-build` 完整刷入目标设备 `4553502d4952495301001c2904d0ad2a`；
- **设备运行状态**：
  - `app=lan_screen`
  - `version=1.1.46`
  - `ip=192.168.5.69`
  - `connected=true`
  - `crash_count=0`
