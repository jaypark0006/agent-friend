# 交付记录：随身屏顶栏常驻电池指示、电量计容错重试与 Dashboard 遥测增强 (1.1.39)

- 日期：2026-10-19
- 版本：LAN Screen 1.1.39
- 设备目标：ESP-Mosaico (`esp32s31`), IP: `192.168.5.209`
- 固件状态：已编译并官方 app-update 刷入，`firmware_mode: normal`, `crash_count: 0`, `stale: false`

---

## 1. 用户反馈与问题定位

用户报告：
> "mosaico刚才启动了一会儿，然后突然关机了 然后不断的震动重启 我再关机重启也不好使，点了开机键后 不断的震动 就像是短路了一样"
> "那你应该还要加个电池电量了把"

### 根因深入剖析
1. **欠压震动死循环（Brownout Bootloop）**：
   - ESP-Mosaico 标称电池容量仅为 3.7V / 65mAh。在屏幕、Wi-Fi、IMU 全速运行时工作电流约 150~300mA，未插 USB 供电时仅能支撑 10~20 分钟即彻底耗尽电量；
   - 底层 Bootloader（`mosaico_boot_splash.c`）在启动最初会调用 `boot_feedback_start()` 驱动板载马达震动；
   - 当电池极度亏电（仅有微弱虚电）时，开机瞬间马达的感性大电流把供电直接拉崩，触发 ESP32 芯片的硬件 Brownout 复位；
   - 复位后马达断电，虚电轻微回弹，Bootloader 再次启动并开启马达，再次欠压复位……形成持续不断的震动死循环，体感如“短路”；
2. **UI 缺乏电量常驻感知**：
   - 随身屏此前在各主要页面（Pipeline、Messages、Media、Camera）顶栏均未常驻显示电池百分比与充电状态；
   - 即使在 Dashboard 设置页，也仅输出了原始毫伏数（`mV`），缺乏直观的百分比；
3. **电量计一次性初始化失步**：
   - `screen_sensors.c` 原先仅在启动时执行单次 `bsp_battery_init()`，一旦开机 I2C 偶发忙碌失败，后续永远不再重试，导致 `battery: null`。

---

## 2. 核心优化方案与实现

### 1) 顶栏常驻电池状态胶囊（Header Battery Indicator）
- 在 `struct screen_app` 中统一引入 `lv_obj_t *header_battery;`；
- 重构 `screen_ui_draw_page_dots(a, parent, active_idx, total)`，在顶栏 5 点指示器左侧（`x = 302, y = 20, w = 72, h = 20`）自动挂载电池指示标签；
- 状态自适应着色与图标：
  - **充电中**（`current_ma > 15`）：显示 `⚡ <百分比>%`，主题采用高亮青绿（`#39e69d`）；
  - **放电中**：根据 SOC 自动匹配 `LV_SYMBOL_BATTERY_FULL / 3 / 2 / 1 / EMPTY`；
    - 严重亏电（`<= 10%`）：危险警示红（`#ff5555`）；
    - 低电量（`11% ~ 20%`）：警告橙黄（`#e5c07b`）；
    - 正常电量（`> 20%`）：自然白灰（`#c5d1de`）；
  - **纯 USB / 未就绪**：显示 `⚡ USB`（浅蓝 `#4fa3e3`）；
- 全局主屏无缝覆盖：Dashboard、Pipeline、Media Stream、Messages、Camera 五大顶层页面全部常驻显示。

### 2) 电量计后台自愈重试机制（Robust Fuel Gauge Recovery）
- 在 `screen_sensors.c` 中增加与 IMU 类似的周期自愈状态机：
  ```c
  if(!battery && (tick % 40 == 0)) {
      battery = (bsp_battery_init() == ESP_OK);
  }
  if(tick++%20==0) {
      if(battery) {
          esp_err_t err = bsp_battery_read(&s->battery);
          s->battery_ok = (err == ESP_OK);
          if(err != ESP_OK) battery = false;
      } else {
          s->battery_ok = false;
      }
  }
  ```
  即使启动瞬间 I2C 偶发离线，2 秒内即可全自动重试恢复，杜绝失步。

### 3) Dashboard 首屏电源信息增强
- 规范 `s_status_ui.power_label` 为结构化实时看板：
  `Battery: 45% (3814 mV)`
  `Rate: +63 mA (Charging)`
  `Temp: 35.1 °C`

---

## 3. 固件交付与验证

- 固件版本：`1.1.39`
- 刷机验证：`mosaico.py iris app-update --skip-build` 成功（100.0%），耗时 47.5 秒；
- 设备状态回执：`firmware_mode: normal`, `crash_count: 0`, `stale: false`；
- 实测遥测数据（`GET /api/sensors`）：
  ```json
  "battery": {
    "voltage_mv": 3814,
    "current_ma": 63,
    "temperature_c": 35.15,
    "soc_percent": 45
  }
  ```
  电量计通信完全恢复，随身屏顶栏绿色 `⚡ 45%` 稳定常驻刷新。
