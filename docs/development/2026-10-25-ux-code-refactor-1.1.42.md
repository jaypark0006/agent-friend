# 交付记录：全面 UX 体验优化与代码健壮性重构 (1.1.42)

- 日期：2026-10-25
- 版本：LAN Screen 1.1.42
- 目标架构：ESP-Mosaico (`esp32s31`)
- 固件状态：官方 app-update 刷入成功（`lan_screen.bin` 5,040,480 字节，healthy=true，normal 运行，crash_count=0）。

---

## 1. 背景与交付目标

用户在代码与 UX 设计审查后提出全量优化需求（"很好。都做一下"）。针对审查中发现的痛点与体验断层，本次交付完成了从嵌入式底层稳定性到手持随身屏触控、副板实体联动以及 Web 工作台夜间模式的全链路重构：

1. **代码健壮性与版本收归**：
   - 彻底解决中文多字节截断导致 LVGL 乱码黑块的潜在隐患；
   - 扩容 `status`、`title`、`badge` 缓冲区；
   - 收拢版本号配置，修复历史遗留的 `CONFIG_APP_PROJECT_VER` 配置覆盖问题，全局统一升级为 1.1.42。
2. **随身硬件屏 (480×480) 交互体验重塑**：
   - **顶部 Page Dots 直接触控 (Direct Touch)**：顶部指示圆点外扩点击热区（8px），支持手指直接点击跳页，同时保留大行程左右滑动；
   - **底部栏极简瘦身 (Home Indicator)**：去除 Status / Media 页面底部 44px 笨重占高假按钮，改为优雅的 80x4px 圆角药丸 Home Bar，释放出垂直可视面积；
   - **Pipeline 垂直列表扩容**：任务列表高度从 386px 提升至 414px（+28px 纯展示区），底部改为沉浸式微胶囊指示条。
3. **软硬件协同实体裁决与免触唤醒**：
   - **副板机械键直接裁决 Pipeline 步骤**：在流水线待确认状态下，屏幕审批按钮明确标注 `[L]` 与 `[R]`，副板物理左键直接触发 Approve，物理右键直接触发 Cancel，联动绿/橙 LED 庆祝反馈；
   - **PIR 桌面人走感应免触唤醒**：在设备因超时息屏或变暗（dim）后，副板 PIR 传感器感应到人体运动或手靠近，自动唤醒屏幕恢复正常背光。
4. **Web 控制台极客深色模式与看板重构**：
   - 引入极客深海暗色模式（跟随系统或顶栏 🌓 一键切换），配色与随身屏 `#101720` 完全同调；
   - 流水线大看板主导：注入表单收纳为折叠卡片，突出大号任务卡片流光扫射动效。

---

## 2. 核心代码变更清单

### 1) 嵌入式 C 固件 (`projects/lan_screen`)
- **`screen_widget.h` & `screen_widget.c`**：
  - 引入 `utf8_safe_copy()` 工具函数，截断时自动对齐 UTF-8 字符多字节边界，退格补 `\0`，从源头根除 `\xFF` 乱码；
  - `SCREEN_WIDGET_STATUS_MAX` 扩容至 128 字节，`SCREEN_WIDGET_BADGE_MAX` 扩容至 32 字节；
  - 导出 `screen_widget_trigger_action(a, which)`，实现实体按键与屏幕触控共用决策引擎；
  - 卡片操作按钮增加 `[L] Approve` 与 `[R] Cancel` 物理按键提示；
  - 列表容器高度扩至 414px，底部替换为 80x4px 胶囊指示条。
- **`screen_ui.c`**：
  - 顶部 `screen_ui_draw_page_dots` 为每个圆点增加 `LV_OBJ_FLAG_CLICKABLE` 与 `lv_obj_set_ext_click_area(dot, 8)`，绑定 `page_dot_click_cb`；
  - 动态调用 `esp_app_get_description()->version`，根除硬编码版本；
  - Status 页与 Media 页底部更换为胶囊按钮与 Home Indicator。
- **`screen_interact.h` & `screen_interact.c`**：
  - 导出 `screen_interact_get_inputs(h, slot, out_inputs, out_seq)`，供主显示任务低开销无锁轮询按键与 PIR 边缘事件。
- **`screen_display.c`**：
  - 在渲染主循环中捕获副板左键按下（触发 `screen_widget_trigger_action(a, 1)`）、右键按下（触发 `screen_widget_trigger_action(a, 2)`）；
  - 捕获 PIR 运动上升沿，自动调用 `screen_activity_kick(a)` 唤醒休眠/变暗屏幕。
- **`CMakeLists.txt` & `build/sdkconfig` & `version.txt`**：
  - 统一更新为 `1.1.42`，修正 Kconfig 静态缓存。

### 2) Web 控制台前端 (`projects/lan_screen/main/`)
- **`api.html`**：
  - 顶栏导航右侧增加 🌓 主题切换快捷键；
  - 流水线任务注入表单收拢为 `<details class="card fold">` 折叠区域。
- **`console.css`**：
  - 新增完整的暗色模式变量与卡片、导航、输入框、代码块适配体系；
  - 新增 `.pipeline-bar-fill::after` 的 50Hz 纯 CSS 流光扫射动画（`shimmer-sweep`），与实体屏幕扫光同步。
- **`console.js`**：
  - 增加主题状态管理与持久化到 `localStorage`（支持跟随系统、强制浅色、强制深色）。

---

## 3. 固件构建与设备安装验证

- **编译构建**：`idf_low_noise_build.py` 增量构建，产物 `lan_screen.bin` (5,040,480 bytes)，0 错误，2 条目录警告。
- **官方安装**：`mosaico.py iris app-update --skip-build` 完整刷入设备 `4553502d4952495301001c2904d0ad2a`。
- **接口核验**：
  - `GET http://192.168.5.69/api/info` 返回版本：`"1.1.42"`；
  - 设备状态正常（`healthy=true`, `crash_count=0`）。
