# 交付记录：Pipeline 左右切页历史卡片叠盖与滚动还原修复 (1.1.38)

- 日期：2026-10-17
- 版本：LAN Screen 1.1.38
- 设备目标：ESP-Mosaico (`esp32s31`), IP: `192.168.5.192`
- 安装状态：已构建并官方刷入，`firmware_mode: normal`, `crash_count: 0`, `stale: false`

---

## 1. 用户反馈与问题定位

用户在多任务队列下左右翻页测试中反馈：
> "我怎么左右切换 再到pipeline页面就只有一条了 历史的 即使是active也丢了"

经比对设备 RAM 状态接口与 LVGL 布局渲染逻辑，发现：
- 设备内存中所有任务数据完好无损（接口实时返回 `count: 7, active_count: 6, done_count: 1`）；
- 但在屏幕渲染层，切页返回 Pipeline 页面时确实只看到 1 张卡片，且无法向上滚动查看历史卡片。

深入剖析根因：
1. **未就绪坐标导致的卡片绝对坐标重叠（Card Coords Collapse）**：
   - 1.1.37 中为优化滚动性能移除了 `LV_FLEX_FLOW_COLUMN`，改用轻量线性函数 `widget_list_layout(a)`（`y += lv_obj_get_height(card) + 8`）。
   - 切页时，`screen_ui_build` 销毁旧页面并调用 `screen_ui_widget_build` 重新构建所有卡片。在卡片刚创建完且尚未执行过全局 `lv_obj_update_layout` 时，`lv_obj_get_height(card)` 读取的是未经布局计算的 `card->coords`（高度为 0 或 1）。
   - 导致所有卡片的垂直坐标被赋予了 `y = 0, 8, 16, 24, 32...`（每个仅相差 8px）。
   - 后续布局引擎根据样式将所有卡片拉伸为实际高度（84px），导致后建的卡片（如第 6 张卡片）像“千层饼”一样完全压在前面所有卡片之上。整块内容总高度仅约 132px，远小于容器可见高度 386px，**因此 LVGL 认为无需滚动，滑动无法响应**，直观呈现为“只剩一条卡片，前面的历史与活动卡片全丢了”。
2. **切页滚动位置丢失（Scroll Anchor Reset）**：
   - `screen_ui_widget_build` 在构建完成后硬编码调用 `lv_obj_scroll_to_view(last_card, LV_ANIM_OFF)`，重置了用户此前上下滑动的阅读进度。

---

## 2. 优化方案与代码改动

### 1) 严密卡片高度判定与精确线性排版
- 新增 `get_card_height(card)` 辅助函数：
  ```c
  static int32_t get_card_height(lv_obj_t *card)
  {
      if(!card) return 84;
      int32_t h = lv_obj_get_style_height(card, LV_PART_MAIN);
      if(h > 0) return h;
      lv_obj_update_layout(card);
      h = lv_obj_get_height(card);
      return (h > 0) ? h : 84;
  }
  ```
- 优先读取 `lv_obj_get_style_height`（创建时设置的 84 或 116），彻底不受 `card->coords` 未就绪的影响。
- `widget_list_layout` 采用居中绝对坐标 `lv_obj_set_pos(card, 2, y)` 与 `y += h + 8`，确保每张卡片垂直间距严格正确，容器尺寸准确撑开。

### 2) 页面切换滚动位置记忆与平滑还原（Scroll State Preservation）
- 在 `screen_app` 中引入 `bool widget_scroll_saved;` 状态标识；
- 在用户切出 `PAGE_WIDGET` 时以及周期刷新循环中记录最新滚动位置：
  ```c
  if(a->page==PAGE_WIDGET && a->widget_list_box) {
      int y=lv_obj_get_scroll_y(a->widget_list_box),maximum=y+lv_obj_get_scroll_bottom(a->widget_list_box);
      screen_lock(a); a->widget_scroll_y=y; a->widget_scroll_max=maximum; a->widget_scroll_saved=true; screen_unlock(a);
  }
  ```
- 切回 `PAGE_WIDGET` 时，优先精准还原此前的滚动纵坐标 `a->widget_scroll_y`，保持浏览上下文一致；无历史滚动记录时才默认聚焦最新卡片。

### 3) 空列表保护（Empty State Fallback）
- 在 `screen_ui_widget_build` 中同步加入空队列保护，当 `w->count == 0` 时展示居中提示占位符。

---

## 3. 固件交付与验证

- 固件版本：`1.1.38`
- 刷机验证：`mosaico.py iris app-update --skip-build` 成功（100.0%）。
- 设备状态回执：`firmware_mode: normal`, `crash_count: 0`, `stale: false`。
