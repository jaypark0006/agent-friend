# ESP-Mosaico 项目参考笔记

> 本页保留2026-10-02起的官方资料调查与当时现场状态，不在本次文档整理中重新核验外部latest内容。当前工程为原生LAN Screen 1.1.24，已使用Git、固定ESP-IDF/BSP并完成官方安装；左侧摄像头、右侧交互子板。较早“未建仓库/未刷机/右槽空置/Lua优先”只描述历史。当前事实及验证边界见[应用文档](../vendor/esp-mosaico-vibe/projects/lan_screen/docs/current-state.md)，依赖固定点见[开发说明](../vendor/esp-mosaico-vibe/projects/lan_screen/docs/development.md)。


核对日期：2026-10-02（Asia/Shanghai）。用户指定的基础资料：[官方文档首页](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/index.html)。

本文件是项目长期参考，不是实物验收报告。调查开始时目录为空。已通过 Wi-Fi 读取设备控制台，USB 通信未建立；用户随后选择 LVGL 路线，已准备 Lua 触摸计数示例。尚无 Git 仓库，未配置 ESP-IDF 工具链、编译固件工程或烧录固件。实际硬件版本与正式应用需求仍待确定。

2026-10-02 补充：已检查六张实拍图并记录 Mac 接线前状态，见 [实物观察与接线准备](hardware/2026-10-02-device-observations.md)。已确认左侧安装翻转摄像头、右槽空置；PCB 与固件版本仍未知。

**2026-10-02 19:31 重要更正：** 官方 [FAQ](https://mosaico.espressif.com/zh/guide/faq/) 明确说明 v0.4.0 出厂固件尚未实现 USB 功能。这与硬件指南中的出厂 CDC 描述冲突；不要预期该版本正常开机后一定枚举 USB 或提供 ESP-Iris。实机固件版本仍未确认。

**网络入口已核实：** 用户提供 `192.168.5.61`，实机控制台显示 ESP-MOSAICO / ESP-Claw、`/nand` 存储、19 个能力组与 28 个 Lua 模块。可以优先探索 Lua + LVGL 应用路线；详细清单、参考包格式及后来连接超时的限制见 [网络控制台调查](hardware/2026-10-02-web-console.md)。没有执行脚本或改动设备。

用户随后重新开机，状态接口与 `/skills` 读取已恢复；实际技能包与参考规范一致。实机状态字段与固定上游源码有差异，具体固件版本仍未确认；恢复资源文件的原始标记与适用限制也记录在上述调查中。

用户补充技术交流群公告，已核对 Mosaico Ideas 的 Iris/BIN 固件入口及官方 Vibe 工程说明，见 [社区参考](development/community-reference.md)。默认 Vibe Hello World 使用 GSP，不能自动当作 LVGL 工程；当前 Lua 示例包与独立固件更新包应分别处理。

**2026-10-03 开发更新：** 用户已确认并授权独立 LAN Screen 固件，触屏配网、手势导航、LAN JPEG 推流及传感器 API。已有实际编译产物和本机测试；此前“未搭建工具链/正式需求待定”是历史状态。详见 [需求基准](development/lan-screen.md) 与 [工程说明](../vendor/esp-mosaico-vibe/projects/lan_screen/README.md)。设备尚未刷写，帧率未实测。

## 1. 资料入口与追溯

| 来源 | 用途 / 本次核对范围 |
| --- | --- |
| [CoreBoard V1.2](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide.html) | 硬件、管脚、电源、下载方式；页面末尾提供 CoreBoard / BaseBoard 原理图及屏幕规格书 |
| [CoreBoard V1.0](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide_v1.0.html) | 旧版本引脚与电源控制 |
| [摄像头模块](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide_camera.html) | 模块 V1.2 / V1.4、DVP、资源释放与示例入口 |
| [交互子板](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide_interact.html) | 双插槽映射、EEPROM 识别、传感与控制功能 |
| [ESP-IDF / ESP32-S31 入门](https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32s31/get-started/index.html) | 工具链入口；页面明确属于持续开发的 master 文档 |
| [官方 BSP 仓库](https://github.com/esp-mosaico/esp-mosaico-bsp) | 已阅读 README 与 BSP 组件清单；未审计完整实现 |
| [出厂应用指南](https://mosaico.espressif.com/zh/guide/) | 用户操作，与硬件开发指南分开理解 |
| [在线固件更新](https://mosaico.espressif.com/zh/firmware-update/) | 出厂固件恢复入口；本次只读 |

硬件文档页面的 GitHub 编辑链接指向提交 [`52772fba97197064a85456b472594355cfeff2b2`](https://github.com/espressif/esp-dev-kits/blob/52772fba97197064a85456b472594355cfeff2b2/docs/zh_CN/esp-mosaico/user_guide.rst)。

BSP 调查固定点：[`a4bfb426afcf2911c01fdd9b6d6f024019f00f8f`](https://github.com/esp-mosaico/esp-mosaico-bsp/commit/a4bfb426afcf2911c01fdd9b6d6f024019f00f8f)，提交日期 2026-09-28。下文 BSP 结论对应此提交，不能自动推广到未来版本。

## 2. 平台与版本差异

官方定义的设备由 CoreBoard 与 BaseBoard 组成，并通过左右模块插槽扩展。主板、底板、模块版本需要分别记录。[来源：文档首页](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/index.html)

| 硬件项 | 文档规格 |
| --- | --- |
| 主控 | ESP32-S31NRV16；双核 RISC-V，最高 320 MHz |
| 无线能力 | 2.4 GHz Wi-Fi 6、Bluetooth 5.4 LE / BR/EDR、IEEE 802.15.4 |
| 存储 | PSRAM 16 MB；SPI NOR 16 MB；SPI NAND 1 Gbit = 128 MB |
| 显示 | 2.16 英寸、480 × 480、CO5300 QSPI；触摸型号存在资料差异，见第 6 节 |
| 音频 / 传感器 | ES8311、NS4150B；BMI270、双 BMM150、BQ27220 |
| 电池 | 3.7 V / 65 mAh |

[来源：V1.2 硬件指南](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide.html)。无线能力是芯片规格，不代表已验证本项目所需的软件协议组合。

| 版本相关项 | CoreBoard V1.0 | CoreBoard V1.2 |
| --- | --- | --- |
| LCD RESET / QSPI CLK | GPIO42 / GPIO44 | GPIO44 / GPIO42 |
| 内部 I²C SDA / SCL | GPIO0 / GPIO1，与扩展共享 | GPIO56 / GPIO3，I2C0 |
| 扩展 I²C SDA / SCL | GPIO0 / GPIO1 | GPIO0 / GPIO1，I2C1 |
| GPIO3 | 橙色 LED，低有效 | 内部 I²C 时钟 |
| GPIO56 | Codec 电源，高有效 | 内部 I²C 数据 |
| 外部 3.3 V | 旧版供电结构 | 独立 DCDC |

[来源：V1.0 管脚表](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide_v1.0.html)、[V1.2 版本差异](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide.html)。**实物版本未确认前，不生成固定的板级 GPIO 配置。**

## 3. 板级资源约束

- GPIO60 低有效，控制屏幕供电和扩展电源输出；GPIO57 正常高阻，关机请求使用开漏拉低。
- 右槽 GPIO37 / 40 / 49 / 52 / 54 与音频 I²S 复用；使用板载音频时不能另行占用。
- 板内 7-bit I²C 地址：BMM150 `0x11/0x12`、ES8311 `0x19`、BQ27220 `0x55`、触摸 `0x5A`、BMI270 `0x69`。
- Type-C 对外输出标称上限为 5 V / 500 mA；不能将此数值套用于侧面扩展电源。

[来源：V1.2 硬件指南](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide.html)。完整管脚表和原理图继续以对应版本原文为准。

侧面扩展 `5V` 与 `3V` 在出厂应用指南中分别标注最大 100 mA；接入具体负载前需核对对应实物与原理图。[来源：出厂应用指南](https://mosaico.espressif.com/zh/guide/)

## 4. 扩展模块

### 摄像头

| 摄像头 PCB | Sensor | 模块晶振 | 默认采集格式 |
| --- | --- | --- | --- |
| V1.2 | OV3640 | 24 MHz | 1024 × 768 UYVY |
| V1.4 | SC101IOT | 20 MHz | 1280 × 720 UYVY |

仅接左槽 H2；EEPROM 为 `0x50`，板型 `0x07`。模块提供 XCLK，无需主机 GPIO 输出。安装时应关机或关闭扩展电源。

- GPIO14 被 DVP D4 占用后，左槽 EEPROM 访问暂停，释放摄像头资源后恢复。
- GPIO33 / GPIO34 占用后，左侧 USB Serial/JTAG 不可用；硬件指南说明 Type-C USB-OTG 通道不受此复用影响。
- 闪光灯 GPIO34 使用开漏，低有效。
- 采集帧必须归还；调用 `mosaico_camera_restart()` 前归还全部帧。上电访问 SCCB 前等待 XCLK 稳定，文档给出 BSP 默认约 20 ms。

[来源：摄像头指南](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide_camera.html)。模块版本号与主板版本号无对应关系；示例支持范围另见第 6 节。

### 多功能交互子板

左右槽均支持，右侧旋转 180° 安装。EEPROM 地址左 `0x50` / 右 `0x51`，板型 `0x16`；缺少识别信息会导致发现失败。具备 GL5506 环境光、AS312 PIR、NEC 38 kHz 红外发送、6 颗 WS2812、两路按键 / 触摸。

| 信号 | 左槽 GPIO | 右槽 GPIO |
| --- | --- | --- |
| 环境光 | 53 | 46 |
| 红外发射 | 48 | 47 |
| 左键 / 触摸 | 13 | 11 |
| 右键 / 触摸 | 12 | 10 |
| PIR | 4 | 5 |
| WS2812 | 15 | 38 |
| EEPROM 选址 | 14，低 | 39，高 |

[来源：交互子板指南](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide_interact.html)。模块 EEPROM 位于子板上，不应在未插模块时期待探测到它。

## 5. 软件基础与开发入口

[固定版本 BSP README](https://github.com/esp-mosaico/esp-mosaico-bsp/blob/a4bfb426afcf2911c01fdd9b6d6f024019f00f8f/README.md) 声明：ESP-IDF ≥ 6.2；主入口 `bsp/esp_mosaico.h`；从 eFuse USER_DATA 读取板型，未编程或不支持的版本返回 `ESP_ERR_NOT_SUPPORTED`。初始化应检查错误，扩展模块通过 `mosaico_module_mgr` 管理独占资源。不能把 eFuse 烧写当成普通初始化补救步骤。

[组件清单](https://github.com/esp-mosaico/esp-mosaico-bsp/blob/a4bfb426afcf2911c01fdd9b6d6f024019f00f8f/components/esp-mosaico-bsp/idf_component.yml) 提供的具体依赖证据：

| 项 | 声明值 |
| --- | --- |
| BSP 组件版本 | `0.2.0` |
| target / IDF | `esp32s31` / `>=6.2` |
| LVGL（启用对应功能时） | `^9.5.0,<9.6.0` |
| esp_lvgl_adapter（启用对应功能时） | `0.6.2` |
| LCD / Touch 组件 | `esp_lcd_co5300: ^2.2` / `esp_lcd_touch_cst9220: ^0.1` |

可从 BSP 的 `hmi_demo`、`audio_loopback`、`imu_gesture`、`camera_lcd_preview`、`camera_photo_app` 起步；多机功能可查 `espnow_chat`、`magnetic_interaction_demo`。磁交互标定依赖磁体、传感器方向和结构，改变装配后须重新验证。[来源：BSP README](https://github.com/esp-mosaico/esp-mosaico-bsp/blob/a4bfb426afcf2911c01fdd9b6d6f024019f00f8f/README.md)

建立真实 ESP-IDF 工程并激活匹配环境后，按所选版本使用普通或 preview 目标命令（二选一）：

```sh
idf.py set-target esp32s31
# 所选 ESP-IDF 将 S31 作为预览目标时：
idf.py --preview set-target esp32s31
```

USB 自动下载和日志依赖固件实现。硬件指南称出厂固件集成 CDC，但 [FAQ](https://mosaico.espressif.com/zh/guide/faq/) 对 v0.4.0 明确给出相反限制：尚未实现 USB 功能，直接连接电脑无反应。不能将前者泛化到本机；需先确认实际版本。自定义固件可实现 CDC，而 app 安装接口还需匹配开发框架。

芯片的 ROM 下载路径与普通应用的 USB 功能不同。硬件指南给出关机、按住 BOOT 再开机的进入方法；实际烧录应在开发范围确定后进行。BSP 文档列出的配置名为 `CONFIG_BSP_USB_CONSOLE`、`CONFIG_BSP_USB_CONSOLE_AUTO_INIT`、`CONFIG_BSP_USB_AUTO_DOWNLOAD`；`monitor --no-reset` 适用于已经可用的串口监视链路。端口应实际探测。[来源：V1.0 开发指南](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide_v1.0.html)

官方另提供两类应用入口，尚未作为本项目的技术选型：

- [VibeCoding 指南](https://mosaico.espressif.com/zh/guide/vibe-coding/) 指向 [esp-mosaico-vibe](https://github.com/esp-mosaico/esp-mosaico-vibe)，介绍 PC Agent、模拟器和实体设备协作；实拍调查阶段已核对该仓库 README 和设备模式说明，固定提交及开发准备见 [补充笔记](hardware/2026-10-02-device-observations.md)。
- [ESP-Claw](https://esp-claw.com/zh-cn/) 是官方指南关联的应用框架入口；本机 Web 控制台已确认提供其管理功能。针对当前 Mosaico 系统参考官方 FAQ 关联的 [legacy 文档](https://legacy.docs.esp-claw.com/zh-cn/tutorial/) 与分支；固件对应的确切源码版本仍未知。

在线更新页在调查日展示 Mosaico `0.4.0`（构建日期 2026-09-28），并注明整机刷写会清除现有数据。它是时点记录，不代表以后仍为最新版本。[来源：固件更新页](https://mosaico.espressif.com/zh/firmware-update/)

## 6. 不一致与待确认项

| 问题 | 已观察的资料差异 | 项目处理方式 |
| --- | --- | --- |
| 出厂固件 USB | 硬件指南写已集成 CDC；FAQ 写 v0.4.0 尚未实现 USB | 针对 v0.4.0 采用版本明确的 FAQ 限制；先确认实机版本，不能从正常模式无 USB 推断硬件故障或不可开发 |
| 触摸型号 | 硬件指南 CST9220；BSP README CST9217；组件清单依赖 CST9220 驱动 | 驱动依赖已核实，实际芯片及兼容关系尚未确认；后续核对实物、规格书和实现 |
| 充满指示灯 | 硬件指南写绿色；出厂应用指南写白色 | 按实物记录，不以颜色判断硬件版本 |
| CoreBoard V1.1 | BSP README 将其映射到 V1.2；硬件首页主要列出 V1.0 / V1.2 | 软件映射不等于新增一份已核验硬件规格 |
| 摄像头示例范围 | 模块指南支持 OV3640 / SC101IOT；BSP README 的摄像头示例段仍写 OV3640 | 对目标示例逐个核对依赖、配置和实机结果 |
| 摄像头调试通道 | 硬件指南区分左侧 USJ 与 Type-C OTG；BSP README 提醒部分示例走 UART | 以具体示例控制台配置为准，不承诺插摄像头后任意 USB 日志都可用 |

上述对照来源：[硬件指南](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide.html)、[摄像头指南](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide_camera.html)、[出厂应用指南](https://mosaico.espressif.com/zh/guide/)、[BSP README](https://github.com/esp-mosaico/esp-mosaico-bsp/blob/a4bfb426afcf2911c01fdd9b6d6f024019f00f8f/README.md)、[组件清单](https://github.com/esp-mosaico/esp-mosaico-bsp/blob/a4bfb426afcf2911c01fdd9b6d6f024019f00f8f/components/esp-mosaico-bsp/idf_component.yml)。

出厂固件 USB 差异来源：[官方 FAQ 的 USB 问题](https://mosaico.espressif.com/zh/guide/faq/)，2026-10-02 核对。

## 7. 本项目后续记录

- 实物：已确认左侧翻转摄像头、右侧空置及外壳接口位置；网络控制台已访问，当前系统提供 ESP-Claw 管理功能；CoreBoard / BaseBoard / 摄像头 PCB 版本、具体固件版本、实际 USB 通信能力——待确认。
- 工程：用户选择 Lua + LVGL 起步，已有 [触摸计数示例](../apps/mosaico_lvgl_counter/README.md) 与 ZIP，静态语法和元数据检查通过、实机运行未验证；正式应用目标、ESP-IDF 提交、BSP 提交、固件依赖锁文件及分区布局尚未选择。
- 验证：构建、显示触摸、音频、传感器、模块发现与恢复烧录——均未执行。
- 建议顺序（项目建议，并非官方强制要求）：恢复网络连通 → 确定首个应用功能 → 核对实机 Lua 接口及运行入口 → 验证最小显示触摸应用；若需求超出当前固件，再确认硬件、固定原生依赖、验证恢复路径并开发独立固件。


## 8. 2026-10-04交互子板与当前固件（更新后的事实）

用户新增[多功能交互子板](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide_interact.html)，并授权刷机/重启/验证。当前安装LAN Screen1.1.15，地址192.168.5.61。此前右槽空置的照片只代表10月2日，当前实机EEPROM确认右槽0x16交互子板，左槽0x07摄像头；两槽描述符hardware_version0x0102，不等同PCB丝印核对。

交互子板提供GL5506光敏、AS312 PIR、两路机械/电容共享输入、六颗WS2812、NEC38kHz红外发射和AT24C02 EEPROM。左/右LDR53/46、IR48/47、两键13/11与12/10、PIR4/5、LED15/38；EEPROM0x50/0x51，右槽旋转180°。按固定BSP模块管理器和mosaico_module_interact申请资源，禁止绕过识别直接驱动未知板。

统一REST/WS包含子板，默认key模式；AUTO优先touch，本机曾跳变，机械模式稳定观测。灯光/IR命令、统一WS、麦克风WAV及摄像头原始帧均取得真实接口证据；未确认真实按压/PIR移动触发、触摸可靠性、IR外部接收与30FPS。详见[交互子板与统一API](development/interaction-subboard-api.md)。本文前面的旧Lua阶段、未选依赖/未验证记录保留历史，以最新记录为准。
