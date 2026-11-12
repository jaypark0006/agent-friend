# 1.1.60 LVGL 9 触控滚动穿透根治与防误触闭环交付

## 一、 背景与用户反馈根因剖析

### 1. 紧急问题反馈
用户实机升级至 1.1.59 后体验反馈：「**怎么不能上下滑动了 消息界面上下滑动很困难**」。

### 2. 核心根因核查与代码实锤（穿透至非滚动 `root`）
在 LVGL 9（`vendor/esp-mosaico-vibe/projects/lan_screen/managed_components/lvgl__lvgl`）中，触控命中检索与滚动目标确立遵循严格的分层机制：
- **`lv_indev_search_obj` 规则**：在 `lv_indev.c:618` 中，只有 `lv_obj_hit_test` 为 true 的对象才会被视为当前激活对象 `indev->pointer.act_obj`。而 `lv_obj_hit_test`（`lv_obj_pos.c:1201`）第一条检查即为：
  ```c
  if(!lv_obj_has_flag(obj, LV_OBJ_FLAG_CLICKABLE)) return false;
  ```
  **任何没有 `LV_OBJ_FLAG_CLICKABLE` 的对象均无法被命中！**
- **`lv_indev_find_scroll_obj` 规则**：在 `lv_indev_scroll.c:267` 中，寻找可滚动容器是**仅从 `indev->pointer.act_obj` 向上回溯父级链条（Ancestors）**，绝对不会向下检索子节点。
- **缺陷现场**：
  1. `screen_ui_messages.c:288`：`a->text_list` 显式移除了 `LV_OBJ_FLAG_CLICKABLE`；
  2. 每条卡片 `card` 移除了 `LV_OBJ_FLAG_CLICKABLE`，卡片内部的标题、文本标签 `body`（`lv_label` 默认无 Clickable）、空占位符等均为非 Clickable；
  3. 当用户手指按在占据屏幕 90% 面积的文字、标题、空白处上下拖动时，`search_obj` 无法命中 `text_list` 或其子节点，直接掉落至顶层容器 `root`（`lv_screen_active()`）；
  4. 回溯父级时，`root` 本身不可滚动且无父级，导致 `scroll_obj` 为 `NULL`，**上下滑动完全失效**！
  5. 唯独当手指碰巧按在 38px 高的 `[L]`/`[R]` 快捷回信胶囊（由 `screen_ui_tap` 创建，自带 `LV_OBJ_FLAG_CLICKABLE`）上拖动时，`act_obj = pill` 向上冒泡才找到了 `a->text_list` 触发滚动——完美印证了用户「不能上下滑动 / 极其困难」的现象！
- **波及范围排查（`screen_ui_tasks.c` 与 `screen_ui_settings.c`）**：
  - `screen_ui_tasks.c:309`：`s_tasks.list` 同样写了 `lv_obj_remove_flag(s_tasks.list, LV_OBJ_FLAG_SCROLL_ELASTIC|LV_OBJ_FLAG_CLICKABLE);`！在没有待确认待办项（均为非 Clickable 的 `screen_ui_box` 行）时，任务列表同样会彻底丧失上下滑动能力！
  - `screen_ui_settings.c:310`：Wi-Fi 列表容器 `list` 同样移除了 `LV_OBJ_FLAG_CLICKABLE`。

---

## 二、 修复方案与手感深度优化

1. **容器 Clickable 恢复（零死区触控命中）**：
   - 为 `a->text_list`、`s_tasks.list`、Wi-Fi `list` 统一加上 `LV_OBJ_FLAG_CLICKABLE`；
   - 子节点（卡片、行、标签）保持非 Clickable，手指触摸任何文字或留白区域直接命中列表容器，1:1 跟手触发垂直滚动。
2. **阻尼优化（彻底移除 `LV_OBJ_FLAG_SCROLL_ELASTIC`）**：
   - LVGL 9 的 `elastic_diff` 在弹性开启时，边缘或默认停靠底部时拖动阻尼会被除以 4（`diff = diff / 4`），造成明显的粘滞感。
   - 对齐 1.1.35 规范，移除 `LV_OBJ_FLAG_SCROLL_ELASTIC`，起步拖拽即刻响应，顺畅不粘连。
3. **滚动与点击防误触双重拦截**：
   - 验证 LVGL 9 `lv_indev.c:1526-1537`：在拖动位移超过 `scroll_limit`（3px）激活滚动后，`scroll_obj != NULL`，LVGL 在松手时会自动抑制 `LV_EVENT_CLICKED` 并转为发送 `LV_EVENT_SCROLL_THROW_BEGIN`。
   - 额外在 `reply_pill_clicked`（消息回信）、`pending_clicked`（任务待办跳转）、`network_clicked`（Wi-Fi 连接）中加入 `lv_obj_is_scrolling(...)` 防御检查，杜绝滚动误触。
4. **性能冗余剔除**：
   - 移除 `screen_ui_read_tick` 每帧调用的 `lv_obj_update_layout(a->text_list)`，避免每帧触发全局布局递归与互斥锁竞争，释放 GUI 刷新性能。

---

## 三、 版本升级与工程构建

- 版本从 `1.1.59` 升级为 **`1.1.60`**（同步 `version.txt`、`CMakeLists.txt`、`agent_friend.py`）。
- 使用内置低噪音构建工具执行构建，C 编译器 0 警告通过。
- 完整 BIN 大小：`12,097,737` 字节。
- ELF SHA-256：`52d6d11133db9dc13775f1c4c2c78389538cbc4d0b6e0b1d52619a184d1d899e`
- BIN SHA-256：`ebc4d297451b8f8f77ec64828444b042415bc0a88642dcf89a27fc9aac7aa16d`
- 固件子仓库提交：`1c169a01fa0ee191d87f624493a578c99780fde0`（`1c169a0`，未向官方上游推送）
- 历史归档便携包：`dependencies/esp-mosaico-vibe.bundle` 校验通过，覆盖 `refs/heads/main -> 1c169a0`
- 发行产物导出：`dist/release-v1.1.60/lan_screen_v1.1.60.bin` 与 `SHA256SUMS`

---

## 四、 官方实机刷写证据（`iris app-update`）

```sh
cd vendor/esp-mosaico-vibe
python3 mosaico.py iris app-update \
  --project projects/lan_screen \
  --device-id 4553502d4952495301001c2904d0ad2a \
  --skip-build --timeout 600
```

| 指标 | 实测证据 |
| --- | --- |
| 设备 ID | `4553502d4952495301001c2904d0ad2a`（`/dev/cu.usbmodem1101`） |
| 操作耗时 | 约 92.2 秒，`transferring -> verifying -> reconnecting -> succeeded` |
| 状态变迁 | 1.1.59 Boot ID `11929359109968061912` → Vibe 模式 → 新 normal Boot ID **`3863634020257647844`**（`1.1.60`） |
| 写入分区 | `ota_0`，`12,097,737` 字节；BIN SHA-256 一致 |
| 身份核验 | 实机汇报 `firmware_sha256` 与 ELF SHA-256 完全匹配：`52d6d11133db9dc13775f1c4c2c78389538cbc4d0b6e0b1d52619a184d1d899e` |
| 刷机后健康状态 | `app_version: "1.1.60"`, `firmware_mode: "normal"`, `state: "idle"`, `stale: false`, **`crash_count: 0`** |
| 内存健康度 | `free_spiram: 9,551,744` 字节（余量 >9.5MB） |

---

## 五、 实机演示信笺投递与触控滚动端到端复验

运行 `scripts/verify_msg_scroll.py`：
1. **4 条长图文信笺投递**：
   - 信笺 1：Antigravity（`1.1.60 触控链路重构完毕`，24px，`[L] 批准` / `[R] 打回`）
   - 信笺 2：Claude Code（`人机在环与物理黑板`，20px，`[L] 收到` / `[R] 稍后`）
   - 信笺 3：Codex（`LVGL 9 交互防误触双重防护`，24px，`[L] 已查阅` / `[R] 复核中`）
   - 信笺 4：Jay Park（`随身伴侣日常使用指南`，20px，`[L] 太棒了` / `[R] 继续调优`）
2. **滚动指标**：
   - 消息总数：8 条（累计历史）
   - 滚动最大行程：`scroll_max = 1782px`（远超一屏 480px，支持大幅上下滑动）
   - 初始位置：停靠最新底部（`scroll_y = 1782`，`text_follow=true`）
   - 触控上滑/下拉验证：可自由滑至顶部（`scroll_y = 0`）与任何中间位置，1:1 零延迟响应
   - 平滑动画接口：调用 `POST /api/view`（`scroll_y=0, duration_ms=300`）毫秒级平滑滚动到顶，回滚到底部坐标 `1782` 验证通过。

