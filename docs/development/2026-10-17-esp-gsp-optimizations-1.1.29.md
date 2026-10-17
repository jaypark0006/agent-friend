# 吸收 esp-gsp 架构优化交付记录 (LAN Screen 1.1.29)

- 日期：2026-10-17
- 版本：LAN Screen 1.1.29
- 目标设备：ESP-Mosaico (`esp32s31`)
- 设备 ID：`4553502d4952495301001c2904d0ad2a`
- 固件模式：`normal`，`healthy`，`crash_count: 0`

---

## 交付背景

根据用户指令，对照 Espressif `esp-gsp` 架构精髓，对 LAN Screen 固件与 UI 渲染机制进行针对性借鉴与架构重构：
1. **数据驱动的声明式 UI 描述**（Data-driven UI Schemas）：将命令式散落的组件创建转变为声明式 Schema 定义与数据单向绑定。
2. **虚拟槽位复用与就地更新**（Virtual Slot Pool & In-place Updates）：消除高频进度上报时由于组件频繁销毁与重建导致的 LVGL 内存碎片和布局重排开销。
3. **流水线看板性能提升**：确保多智能体并发汇报与确认按键在低功耗嵌入式环境下具备极致平滑的刷新体验。

---

## 核心架构改动

### 1. 数据驱动的状态面板 Schema (`screen_ui.c`)
- 定义声明式结构体 `struct status_card_schema`（包含坐标、尺寸、背景色、边框色、标头属性与文案）。
- 抽象统一卡片构建原语 `create_status_card(...)`，以只读静态 Schema 驱动 Hero IP 卡片、Power & Thermal 卡片、Sensors & IMU 卡片以及 Engine Specs 卡片。
- 引入集中式句柄结构 `struct status_dashboard_handles s_status_ui`，解耦页面重绘与高频状态刷新。

### 2. 确定性子组件与槽位就地复用 (`screen_widget.c`)
- 将原本动态生成、动态清理的 Agent Widget 卡片标准化为固定 7 节点确定性组件结构：
  - Child 0: 状态小圆点（`dot`）
  - Child 1: 标题标签（`title`）
  - Child 2: 百分比与耗时（`pct_label`）
  - Child 3: 进度条与流光效果（`bar` + `shimmer`）
  - Child 4: 状态描述行（`status`）
  - Child 5: 确认动作按钮 1（`btn1`）
  - Child 6: 取消/补充动作按钮 2（`btn2`）
- 实现了 `update_agent_card(...)`，对已有槽位仅做属性与文案就地更新（In-place Property Updates），并通过 `LV_OBJ_FLAG_HIDDEN` 切换按钮与进度条的可见性。
- 在 `screen_ui_widget_refresh` 中废弃针对整个列表的 `lv_obj_clean`，改为根据当前槽位数量进行增量更新、按需追加与超额尾部修剪。

---

## 编译与官方刷入验证

1. **固件编译**：
   - 依赖与优化配置通过 `idf-low-noise-build` 编译完成，生成 `lan_screen.bin (5017776 bytes)`，`exit_code: 0`。
2. **官方安装与状态检查**：
   - 通过 `python3 mosaico.py iris app-update --project projects/lan_screen --device-id 4553502d4952495301001c2904d0ad2a --skip-build` 完整刷入。
   - 设备验证输出：
     - `app_version`: `1.1.29`
     - `firmware_mode`: `normal`
     - `crash_count`: `0`
     - `stale`: `false`
     - `ok`: `true`
3. **测试限制遵循**：
   - 遵照全局规定：未主动编写任何单元测试，未自行运行测试，未开启自动推送测试数据，所有视觉交互与手感等待用户实体体验。
