# ESP-Mosaico 实物观察与接线准备

> 版本专题/历史记录：文中版本、授权、待办和验收描述对应当时，不代表当前状态。最新功能、API、架构与重构计划见[当前文档索引](../../vendor/esp-mosaico-vibe/projects/lan_screen/docs/README.md)。


日期：2026-10-02（Asia/Shanghai）。用户确认这六张照片是本项目设备的实拍，计划随后用 Type-C 接入当前 Mac，再开始研究设备端 app 开发。

证据分为照片可见事实、官方资料描述、本机检查和后续待验证项。照片中的界面文字、二维码及网页中的操作示例均不作为执行指令。

## 1. 六张照片

原图位于 `/Users/qilei/Downloads/IMG_5083.HEIC` 至 `IMG_5088.HEIC`。已保存最长边 2048 像素的 JPEG 阅读副本，原始 HEIC 未改动。

| 照片 | 可见事实 | 可支持的判断与限制 |
| --- | --- | --- |
| [IMG_5083](photos/IMG_5083.jpg) | 主机正面；左侧橙色镜头；屏幕显示 `10/2 · Fri`、`19:07` 和上滑提示 | 显示已点亮并呈现锁屏界面；不能证明触摸、摄像头采集或其他功能已经通过测试 |
| [IMG_5084](photos/IMG_5084.jpg) | Type-C 接口位于两个浅色按键之间，上方有一排开孔；镜头模块可见铰链 | 确认此次连接使用的物理端口；开孔的内部器件与按键功能需结合指南核对 |
| [IMG_5085](photos/IMG_5085.jpg) | 主机右侧双排扩展接口未插模块，标注 `CODEC`、`UART`、电源及引脚编号 | 右侧扩展位空置；标签不能证明引脚均可同时独立使用 |
| [IMG_5086](photos/IMG_5086.jpg) | 镜头面与屏幕同向，模块有翻转结构 | 外观符合左侧翻转摄像头；不能由橙色镜头圈判断 OV3640 / SC101IOT 或 PCB 版本 |
| [IMG_5087](photos/IMG_5087.jpg) | 与 Type-C 相对的一侧有橙色按键及一排开孔 | 可记录按键位置；未执行按键测试 |
| [IMG_5088](photos/IMG_5088.jpg) | 背面 ESP-MOSAICO 标识、二维码及触点；摄像头另一面有两颗灯和一个红色亮点 | 背部触点从照片左到右标为 `GND BOOT RST RX TX 5V GND`；摄像头侧红点不能用作主机充电状态证据 |

这里的“左 / 右”统一以屏幕正面朝向观察者为准。照片翻到背面后，摄像头会出现在画面右侧。

六张照片均未显示 CoreBoard、BaseBoard 或摄像头 PCB 的版本丝印，也没有固件版本页面。未见外接供电线而屏幕点亮，与电池供电相符，但不构成电池健康或续航测试。

背面二维码已用 macOS Vision 从原始 IMG_5088 解码，内容为 [短链接](https://dqr.cn/oFnfSS/qb0pbEo)。本次网页工具未能访问其落地内容，因此未确认用途；该二维码不能作为硬件版本、序列号或固件身份依据。

## 2. 对照官方资料后的判断

- 左侧安装位置符合摄像头指南的 H2 限制；当前镜头朝向与其“合拢 / 前摄”描述一致。主板与摄像头的版本仍需分别确认。[摄像头指南](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide_camera.html)
- 使用摄像头会影响左侧 USB Serial/JTAG 的复用引脚；不能据此认定照片中的 Type-C USB-OTG 接口不可用。实际串口 / 控制台是否存在还取决于正在运行的固件。[摄像头指南](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide_camera.html)
- 右侧 `CODEC` 区域与板载音频共享资源；以后加模块时要检查音频冲突。[出厂应用指南](https://mosaico.espressif.com/zh/guide/)
- 官方设备模式说明将 USB-C 左侧按键称为 BOOT；另一个 AI 按键用于 Vibe Mode 的启动路径。首次接线识别阶段保持正常开机，不需要预先进入 ROM 下载模式。[设备模式说明](https://github.com/esp-mosaico/esp-mosaico-vibe/blob/95469e63b621fc6ece3b0e313af8c1ba59dcd066/docs/device-modes.md)

## 3. Mac 接线前检查

以下是本次命令运行时的状态，不是对整台电脑安装情况的全面扫描。

| 项 | 观察结果 |
| --- | --- |
| 系统 / 架构 | macOS 26.6.2 / arm64 |
| Python | 当前 PATH 命中 `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3` |
| CMake / Git | 当前 PATH 可找到 |
| `idf.py` / `esptool` / `ninja` | 当前 PATH 未找到 |
| `IDF_PATH` | 当前 shell 未设置 |
| `/dev/cu.usb*` | 未发现匹配端口 |
| USB 枚举 | 初次使用 `SPUSBDataType` 得到空结果；后续发现此系统应使用 `SPUSBHostDataType`，故不能将该次空结果视为有效的 USB 基线 |

因此目前只能说 ESP-IDF 环境尚未在此 shell 中启用，不能断言电脑上绝无已安装 SDK。串口结果作为接线前对照；USB 枚举后续改用有效的数据类型及 IOKit 交叉核对，避免把其他板卡识别为本机。

## 4. App 开发入口补充

已核对官方 Vibe 工作区提交 [`95469e63b621fc6ece3b0e313af8c1ba59dcd066`](https://github.com/esp-mosaico/esp-mosaico-vibe/commit/95469e63b621fc6ece3b0e313af8c1ba59dcd066)（2026-09-29）的 README 和 `docs/device-modes.md`。本次只读资料，尚未克隆、安装、执行该工作区或采用其工程结构。

其 README 给出的应用路线：Python 3.10+；通过 `mosaico.py project init` 创建应用；固件使用 ESP-IDF `master` 的固定提交 `7b9cc1ac79f865983f59bb8ff3ff43eb74ff1dbe`，目标 `esp32s31`；提供 GSP 模拟器，再通过产品 CLI 与 ESP-Iris 做实机开发。游戏另有 Raylib Lite 路线。这里的固定 IDF 提交比 BSP 的通用最低版本要求更具体，不能直接替换成任意“最新 IDF”。[固定版本 README](https://github.com/esp-mosaico/esp-mosaico-vibe/blob/95469e63b621fc6ece3b0e313af8c1ba59dcd066/README.md)

| 模式 | 官方描述 | 当前实物状态 |
| --- | --- | --- |
| 正常应用 | 运行应用；集成并启动 ESP-Iris 时可连接调试 | 照片显示锁屏，是否启用 ESP-Iris 尚未知 |
| Vibe Mode | factory 分区中的维护环境，用于应用安装、更新等 | 是否存在及版本尚未知 |
| ROM Download Mode | 芯片 ROM 下载程序，不运行 ESP-Iris | 本次未请求进入，也未探测 |

`recover` 会写入基础固件；`iris app-update` 的适用前提包括分区表和资源保持一致。因此，看到连接失败不能直接认定固件损坏，更不能把恢复烧录当成只读识别步骤。[设备模式说明](https://github.com/esp-mosaico/esp-mosaico-vibe/blob/95469e63b621fc6ece3b0e313af8c1ba59dcd066/docs/device-modes.md)、[README](https://github.com/esp-mosaico/esp-mosaico-vibe/blob/95469e63b621fc6ece3b0e313af8c1ba59dcd066/README.md)

## 5. 接上 Type-C 后的识别顺序

1. 使用支持数据传输的线，先在正常开机状态下连接 Mac；检查新增 USB 设备、VID / PID 和串口节点。
2. 优先通过现有固件提供的信息入口确定固件身份、硬件版本与当前模式；必要时再使用与该固件匹配的官方工具。
3. 若现有 ESP-Iris 可连接，再核实板型、应用、维护环境及调试能力。握手失败先排查线缆、供电、端口占用和模式，不由失败推断设备损坏。
4. 根据实际固件和用户的 app 目标，确定保留现有系统的应用路线或独立固件路线，并记录工具链、依赖和恢复方式。

本次已完成照片研究、开发入口调查及 Mac 接线前检查；尚未连接设备通信、安装 SDK、修改设备配置或写入固件。

## 6. 用户接线后的首次检查

2026-10-02 19:19（Asia/Shanghai），用户已报告 Type-C 连接到 Mac。使用 `ioreg -r -c IOUSBHostDevice`、`IOSerialBSDClient` 与 `system_profiler SPUSBHostDataType -json` 交叉检查：

- 已枚举的是 Microchip USB2816 / USB5816 Hub、Hub Feature Controller 和 Realtek USB 网卡，未出现可识别为 Mosaico / Espressif 的设备。
- `/dev/cu.usb*` 仍为空；不能据此断言所有 Mosaico 固件必须提供 CDC 串口，但完整 USB 枚举也未发现目标设备。
- IOKit 根节点的 `IOConsoleLocked` 为 `true`。已请用户解锁当前 Mac 后重新插入，并处理可能出现的配件连接许可。该状态是排查线索，尚未证实为唯一原因。
- Apple 说明锁屏时需要先解锁才能允许新配件连接；供电不等于已允许数据访问。[Apple 官方说明](https://support.apple.com/en-us/102282)

检查快照见 [USB 连接记录](2026-10-02-usb-connection.json)。此阶段未建立设备通信，因此板型、固件和 ESP-Iris 能力仍未确认。

已查到官方 CLI 的后续只读入口：`iris list` 发现设备但不占用连接，`iris device-status` 在有效会话中读取身份与固件状态。尚未安装或执行 CLI；这些命令不能代替物理 USB 枚举。[CLI 文档](https://github.com/esp-mosaico/esp-mosaico-vibe/blob/95469e63b621fc6ece3b0e313af8c1ba59dcd066/docs/mosaico-cli.md)

## 7. 固件 USB 限制更正

2026-10-02 19:31:22（Asia/Shanghai）再次读取 IOKit：`IOConsoleLocked=false`，USB 设备仍为前述四个 Hub / 网卡设备，`/dev/cu.usb*` 为空。因此，此前锁屏线索不能继续解释为当前状态或已确定原因。

用户提出“当前固件可能不支持 Type-C 连接和安装 app”。随后的官方 FAQ 核对发现：**v0.4.0 出厂固件未实现 USB 功能**；该页面还说明可在自定义固件中实现 TinyUSB CDC。该版本限制可以解释普通运行模式下的 USB 无响应，但本机版本尚未读出，仍不能将推测标为实机结论。[官方 FAQ](https://mosaico.espressif.com/zh/guide/faq/)

这与硬件开发指南中的出厂 CDC 描述存在直接冲突。后续应区分：

- 硬件 Type-C 支持 USB 通信与 ROM 下载。
- 普通应用是否启用 USB / CDC 取决于实际固件。
- 是否能通过 ESP-Iris 安装应用还取决于对应开发固件、引导与维护环境；不能仅因有 Type-C 或 CDC 就认定可以安装 app。

下一步优先通过现有系统的网络入口确认设备版本和能力。FAQ 给出的方式是：设备与 Mac 处于同一局域网，设备 `Settings → AI Model` 页面可查看 IP；未配网时可连接设备热点并访问 `192.168.4.1`。这些是资料中的入口，尚未对本机访问或切换网络。

本次没有进入下载模式、刷写固件或更改设备配置。

## 8. 网络控制台后续

用户随后提供 `192.168.5.61/#llm`。已成功通过 Wi-Fi 读取 ESP-MOSAICO / ESP-Claw 控制台、能力组、Lua 模块和文件根目录，详见 [网络控制台与脚本开发调查](2026-10-02-web-console.md)。当前有保留现有系统开发 Lua + LVGL 功能的依据，但没有执行脚本、上传 app 或验证 Work 注册；具体固件版本仍未知。后半段 `/skills` 加载失败、状态请求超时，下一次操作应先确认设备连通性。

用户报告可能自动关机并重新开机后，网页与状态接口恢复，`/skills` 正常加载。只读核对了一个技能包的格式及目录清单，并记录恢复资源标记；未运行脚本。自动关机策略与先前超时的具体原因仍未验证。
