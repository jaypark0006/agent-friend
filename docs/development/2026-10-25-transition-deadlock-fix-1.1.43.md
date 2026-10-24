# 2026-10-25 LAN Screen 1.1.43 交付记录：根除切页状态机死锁与触控手势冲突

## 背景与问题复现

用户反馈随身屏出现死机假死现象（"怎么回事 怎么司机了"）。
通过分析排查 `/api/status` 与设备堆栈：
- 设备未崩溃重启（`crash_count=0`，HTTP Server 存活）。
- 但 GUI Display 任务永久卡在 `"page": "settings"`, `"transitioning": true`，`gui.touch_polls` 计数停止在 69094。
- `/api/screenshot` 接口返回 503 超时，原因是其依赖的 `screen_display_task` 未能消费 `capture_request`。

## 根本原因剖析

1. **切页状态机竞争与无看门狗兜底**：
   `screen_pages_navigate` 与 `screen_pages_resolve` 在先前的实现中缺少进入保护（`if (a->transitioning || a->transition_preparing) return;`）。在快速连续触控、滑动切换或顶栏点按时，切页指令在上一次转场尚未完成（LCD DMA 传输中）时再次修改 `next_page`，导致状态机状态错乱，`transitioning` 标志位未能被正确清零，从而永久假死。
2. **底栏滑动手势区与设置按钮重叠冲突**：
   在 1.1.41 及以前，Status 与 Home 页面底部放置了宽度达 444px 的大按钮（"打开设置中心"）。用户在屏幕底部进行自然的拇指横向切页滑动时，极易误触点中该按钮并强行跳转 `PAGE_SETTINGS`。而在设置页面底部的返回按钮（y=372..426）与原位置重叠，用户连击触发页面快速进出抖动（Flapping），加剧并发竞争。
3. **顶栏手势判定与 Page Dots 触控重叠**：
   随身屏顶部 `y <= 32` 为全局下滑调出设置界面的手势区。当在 `y=18` 附近点按 Page Dots 跳页时，松手事件与手势识别逻辑同时触发，造成切页与呼出设置中心的双重并发调用。
4. **副板输入轮询锁竞争**：
   `screen_display_task`（优先级 5）在每个循环中（1~5ms 间隔，高达 200~1000Hz）频繁获取 `interact_lock` 轮询副板按键，导致低优先级的副板驱动任务与其他锁陷入争抢。
5. **背光 SPI 传输与 LCD DMA 未串行化**：
   屏幕闲置睡眠与唤醒时调用的 `bsp_display_brightness_set` 直接在 SPI 总线上发送控制指令，未先调用 `screen_display_wait(a)` 等待前一次屏幕 DMA 完成。

## 优化与修复实现

1. **状态机防重入与 450ms 强制看门狗（Watchdog）**：
   - 在 `struct screen_app` 中引入 `int64_t transition_start_us;`。
   - 在 `screen_display_task` 中，每轮心跳检查当前转场是否超时：若转场持续时间超过 450ms（正常转场仅需 150~200ms），看门狗强制重置 `a->transitioning = false; a->transition_preparing = false;`，彻底根除任何潜在的转场假死。
   - `screen_pages_navigate` 和 `screen_pages_resolve` 增加安全屏障：在 `transitioning` 或 `transition_preparing` 期间直接拦截任何外来切页请求。
2. **彻底消解底部重叠，采用无死区圆角 Home Bar**：
   - Status、Home、Widget 各页面底部统一替换为优雅的 80x4px 圆角药丸指示条（`draw_home_bar`），剥除 `LV_OBJ_FLAG_CLICKABLE`，底部全宽度 480x60px 彻底让渡给用户的水平切页手势。
   - Pipeline 任务列表高度合理留白（410px），防止与底部指示条重合。
3. **顶栏 Page Dots 触控互斥与防抖**：
   - `page_dot_click_cb` 增加触控按下状态判定（`a->touch_state.down` 时不触发跳页，防止与下滑手势冲突），仅在安全释放且非转场中响应。
4. **副板输入轮询平滑降频**：
   - `screen_interact_get_inputs` 轮询频率限制为 30ms（~33Hz），并且在转场期间自动静默，大幅减轻总线与互斥锁压力。
5. **显示背光操作安全串行化**：
   - 所有调用 `bsp_display_brightness_set` 前均严格执行 `screen_display_wait(a)`。

## 验证结论

- 固件全量低噪编译通过，ELF SHA256 签名更新，固件尺寸 5,044,688 字节。
- 通过官方 `mosaico.py iris app-update` 成功刷入设备 `4553502d4952495301001c2904d0ad2a`。
- 设备自动软重启，版本确认为 `1.1.43`，`connected=true`，`transitioning=false`，`crash_count=0`。
- `/api/screenshot` 恢复毫秒级响应，BMP 输出正常（450KB）。
