# 社区公告与官方开发入口

> 版本专题/历史记录：文中版本、授权、待办和验收描述对应当时，不代表当前状态。最新功能、API、架构与重构计划见[当前文档索引](../../vendor/esp-mosaico-vibe/projects/lan_screen/docs/README.md)。


日期：2026-10-02。用户提供了一条 ESP-Mosaico 技术交流群欢迎公告，作为项目补充资料。消息发帖者身份未核验；以下区分用户转贴内容与实际网页核对结果。没有执行报名、发布、下载固件或烧录。

## 公告中的入口

| 入口 | 链接 | 项目用途 |
| --- | --- | --- |
| 入门指南 | https://mosaico.espressif.com/zh/guide/ | 设备使用、ChatCoding、VibeCoding |
| 应用社区 | https://mosaico-ideas.espressif.com/ | 发现应用，核对固件格式、安装方式与后续分发要求 |
| Vibe Coding 参考 | https://github.com/esp-mosaico/esp-mosaico-vibe | PC 开发工作区、工具链、模拟器、ESP-Iris、安装与维护 |
| 恢复出厂固件 | https://mosaico.espressif.com/zh/firmware-update/ | 恢复入口；实际执行前评估当前数据与固件写入范围 |
| 最新 FAQ | https://mosaico.espressif.com/zh/guide/faq/ | 具体版本限制与常见操作 |

公告称平台会综合参考 Spark 值和下载量，为优秀创意提供奖品。奖品及评选规则仅作用户提供的活动信息，不作为开发目标；若以后参与，应另行核对当时的正式活动规则。

## 本次网页核对

1. 官方入门指南实际链接到 Mosaico Ideas，介绍设备对话生成技能、PC 构建应用与社区发现应用三类入口。
2. Mosaico Ideas 首页标题为「ESP-Mosaico 固件分享平台」，列表有 `Iris` 与 `BIN` 类型标签。
3. 检查了 [Hello World 详情](https://mosaico-ideas.espressif.com/firmware/2756ff12-1eb1-4d4f-9db0-a28c3195199a)：标注 `Iris 1.0.0`、目标 ESP-Mosaico，提供在线烧录、有线烧录、下载 Iris 包、下载完整 BIN。页面说明完整 BIN 用于首次安装，会覆盖固件与设置；已有 Iris 设备可使用在线烧录更新。
4. 未点击固件下载或执行烧录，不能据上述页面认定本机已有 Iris、在线更新可用或社区包与本机兼容。

本次网页工具无法直接解析社区站点，但通过浏览器实际读取了首页与上述详情页。网页类型标签、按钮与详情是本次证据，不以无法解析网页推断站点不可用。

## 对本项目开发路线的影响

- 当前 `apps/mosaico_lvgl_counter` 是现有 ESP-Claw 固件使用的 Lua + LVGL 示例，ZIP 是目录文件交付包，尚未部署或实机验证。
- 若目标是类似社区作品的独立应用，应评估官方 Vibe 工作区的原生工程、更新包和 ESP-Iris / Vibe Mode；不能将当前 Lua ZIP 自动等同于社区 Iris 包或完整 BIN。
- LVGL 是界面库，可以用于 Lua 绑定和原生工程；安装方式由工程与固件框架决定。
- 官方 Vibe README 的 `project init` 默认 Hello World 路线使用可移植 C UI 与 GSP 1.5.1 场景，不是自动创建一个 LVGL 工程。继续采用原生 LVGL 时，要选择相应 BSP 示例或完成组件集成；不能把 GSP 模拟器预览称为本项目 LVGL 的已验证预览。
- 本机是否具备有效 Vibe Mode 与 ESP-Iris 尚未知。后续选定独立应用路线时，先验证现有维护环境，再配置工程和更新链路。

## 「每个 App 像一个系统」的理解

用户观察社区作品后提出这一问题。按当前官方更新文档，社区原生 App 应理解为独立的正常应用固件：安装目标固件后重启并运行它，其界面、功能及所需组件由该工程提供。ESP-Claw 出厂环境本身也是一种正常应用固件；换成另一原生作品后，是否仍有 Claw、相机、聊天等功能，取决于新固件是否集成这些功能。

Vibe Mode 是另外保留的维护固件。文档描述的是进入维护环境、安装目标固件、再启动目标应用，不能据此宣称存在类似手机桌面的多原生 App 共存启动器。应用固件更新也不等于每次覆盖全部 Flash，具体范围由更新包与更新方式决定。

Lua / Skill / Work 属于另一层：在 ESP-Claw 宿主固件中增加和执行脚本功能，无需为每个脚本替换宿主固件。当前计数器示例走的是这一路线，仍未实机验证。用户是否希望保留现有出厂系统，还是做独立整机应用，尚未明确决定。

依据：[官方 CLI 更新说明](https://github.com/esp-mosaico/esp-mosaico-vibe/blob/main/docs/mosaico-cli_CN.md)、[ChatCoding / Work 指南](https://mosaico.espressif.com/zh/guide/chat-coding/)。

参考：[官方入门指南](https://mosaico.espressif.com/zh/guide/)、[Vibe 工作区 README](https://github.com/esp-mosaico/esp-mosaico-vibe)、[中文设备模式](https://github.com/esp-mosaico/esp-mosaico-vibe/blob/main/docs/device-modes_CN.md)、[本项目上传与模式说明](upload-and-vibe-mode.md)。上游 Vibe 调查固定点仍为 `95469e63b621fc6ece3b0e313af8c1ba59dcd066`；社区详情与活动信息属于当日观察，会变化。
