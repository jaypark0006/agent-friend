# LAN Screen 1.1.32 交付记录：Pipeline 任务历史留存与滚动浏览

日期：2026-10-17
固件版本：1.1.32
目标设备：ESP-Mosaico (`esp32s31`)
Device ID: `4553502d4952495301001c2904d0ad2a`
局域网地址：`http://192.168.5.192`

---

## 1. 核心需求背景

用户反馈：“pipeline做完就丢了？我不是说上滑还能看到历史吗？”
在 1.1.31 及之前版本中：
1. **任务槽位覆盖**：`update_one_agent` 仅根据 `id` 查找并覆写卡片，一旦任务完成并进入下一轮，新进度直接覆写已完成的卡片，无法留存执行足迹。
2. **强制跳出界面**：`receipt.py` 默认在交付收尾时强制执行 `POST /api/view {"page": "image"}`，导致设备立即切出 Pipeline 界面，无法停留在任务看板。
3. **滚动与翻页手势冲突**：用户在上下滑动查看 Pipeline 历史记录时，手势容易与全局切页手势（如上滑回主屏/切换页面）产生误触冲突。
4. **滚动焦点抢夺**：当用户正在向上滚动浏览历史任务时，若新任务进度推送到达，列表会强制自动滚到底部打断阅读。

---

## 2. 核心架构重构与优化

### 2.1 任务双阶段匹配（Two-Pass Slot Matching）与历史留存
在 `screen_widget.c` 中重写 `update_one_agent`：
- **阶段一（活跃任务优先）**：逆向遍历当前队列，寻找匹配 `id` 且 `!it->done` 的活跃任务。若找到，执行就地更新（In-place update）。
- **阶段二（追加新任务）**：若未找到活跃任务（即该 Agent 的前序任务已完成 `done: true`），且当前不是专门修改历史卡片结果的操作，则在队列尾部**追加分配新卡片**（`w->count++`）。
- **历史卡片固化**：已完成卡片保留在队列上方，标题、状态、进度条（固化为100%绿色暗底）均完整留存，直至超出队列最大容量（16条）时自动从顶部按 FIFO 淘汰最老记录。

### 2.2 滚动保护与手势解耦
- **手势冲突规避**：在 `screen_display.c` 的 `allow_push` 判定中加入 `!(a->page==PAGE_WIDGET && a->widget_list_box && lv_obj_is_scrolling(a->widget_list_box))`。当列表处于拖动或惯性滚动状态时，彻底屏蔽页面切换手势。
- **自动跟焦保护**：在 `screen_ui_widget_refresh` 中加入 `bool follow = (lv_obj_get_scroll_bottom(a->widget_list_box) < 40);`。仅当用户本来就在队列最底部时才自动滚动到新卡片；若用户正在向上查阅历史，绝不抢夺滚动位置。

### 2.3 零栈拷贝锁针优化（Stack Overflow Prevention）
- 将 `screen_widget_json`、`screen_ui_widget_build`、`screen_ui_widget_refresh` 中的 `struct screen_widget_state w = a->widget;` 栈拷贝全面消除，统一改用 `const struct screen_widget_state *w = &a->widget;` 配合 `screen_lock(a)` 保护。
- 将 `httpd` 栈大小调至 `10240` 字节，彻底杜绝 FreeRTOS 栈溢出风险。

### 2.4 Pipeline 头部动态计数
- 头部标题根据活跃与已完成数量自适应展示：
  - 存在历史完成任务时：`Pipeline (%lu Active • %lu Done)`
  - 无历史任务时：`Pipeline (%lu Active)`

### 2.5 技能脚本收尾逻辑调整
- 将 `receipt.py` 的 `--switch-page` 默认值调整为 `False`。交付证明图片正常写入设备存储历史并供网页或历史查阅，而随身屏保持在 Pipeline 任务看板，直观展现全部执行流与完成态。

---

## 3. 刷机与实机运行验证

- **固件编译与刷入**：
  - 通过 `idf_low_noise_build.py` 成功编译 `lan_screen.bin` (5027680 bytes)。
  - 通过官方 `mosaico.py iris app-update` 刷入目标设备 `4553502d4952495301001c2904d0ad2a`。
- **设备运行状态**：
  - `firmware_mode: normal`, `app_version: 1.1.32`, `crash_count: 0`。
  - GUI 刷新帧率：`fps: 29.999580`。
- **队列多任务实测验证**：
  - 发送任务1并标记完成（`count: 1, done_count: 1`）。
  - 发送任务2并标记进行中（`count: 2, active_count: 1, done_count: 1`），任务1正常留存。
  - 任务2标记完成（`count: 2, done_count: 2`）。
  - 同一 Agent 开启新轮次任务，成功追加为第3张卡片（`count: 3, active_count: 1, done_count: 2`），历史两张卡片均完好保留。
  - 滚动列表生效，`scroll_max: -118`。
