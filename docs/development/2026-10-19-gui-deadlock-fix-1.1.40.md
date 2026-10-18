# 交付记录：修复顶栏电量刷新递归锁导致的 GUI 死锁与滑动冻结 (1.1.40)

- 日期：2026-10-19
- 版本：LAN Screen 1.1.40
- 设备目标：ESP-Mosaico (`esp32s31`), IP: `192.168.5.209`
- 固件状态：已编译并官方 app-update 刷入，`firmware_mode: normal`, `crash_count: 0`, `stale: false`

---

## 1. 用户反馈与问题定位

用户在升级 1.1.39 后反馈：
> "这回怎么还死机了 界面不响应滑动"

### 根因深入剖析
1. **FreeRTOS 非递归互斥锁在 Display 任务内自我死锁（Self-Deadlock）**：
   - `screen_lock(a)` 底层基于 FreeRTOS 的 `xSemaphoreCreateMutex()`，属于**非递归互斥锁（Non-recursive Mutex）**；
   - 在 Pipeline 任务流页面构建函数 `screen_ui_widget_build` 中：
     ```c
     void screen_ui_widget_build(struct screen_app *a, lv_obj_t *root)
     {
         screen_lock(a); // [1] 先行持有锁
         ...
         screen_ui_draw_page_dots(a, root, 1, 5); // 调用顶栏绘制
         ...
     ```
   - 1.1.39 新增的 `screen_ui_draw_page_dots` 会立即触发初始电量绘制 `screen_ui_refresh_battery(a)`；
   - 而 `screen_ui_refresh_battery(a)` 内部又执行了 `screen_lock(a);`；
   - **同一线程在未释放锁的前提下再次请求该非递归锁，直接永久陷入死锁（Deadlock）**；
   - 导致 Display 任务完全被挂起，屏幕渲染、LVGL 布局与触摸轮询彻底停摆，表现为“界面完全不响应滑动”；
   - 连带导致 HTTP 接口任务在执行 `GET /api/status` 时因等待 `screen_lock(a)` 而一同超时。

---

## 2. 修复方案

1. **彻底移除 `screen_ui_refresh_battery` 内部加锁**：
   - 渲染线程自身即单线程驱动 LVGL，读取的 `a->sensors.battery_ok`、`state_of_charge`、`current_ma` 均为原子基础类型；
   - 剥除内部的 `screen_lock(a)` 与 `screen_unlock(a)`，杜绝任何嵌套持有互斥锁的可能性；
2. **测试与遥测复核**：
   - 刷入 1.1.40 后，`GET /api/status` 瞬间 0 延迟秒回；
   - `touch_polls`、`refreshes`、`fps` 计数器平稳推进，GUI 与触控输入全面恢复，滑动即时响应。
