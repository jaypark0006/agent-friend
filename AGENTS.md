# 项目长期参考

## 当前文档入口（2026-10-17更新）

- 最新安装1.1.36（2026-10-17）：彻底解耦 Agent 身份与任务唯一键；`id` 正式规范为任务/对话主键（由 Agent 自主定义，仅作槽位寻址，不在屏上展示），`title` 由 Agent 自主指定展示标题，固件匹配算法简化为确定性 ID 直配并扩容容量至 64 字节；同步更新 Skill 与全局规则（明确三段式结构 `<自己是谁>:<Session名称>-<当前Task名称>`、Session 名统一性与 16~22 字符长度控制）；官方编译刷入normal/healthy、crash_count=0。见[交付记录](docs/development/2026-10-17-task-key-skill-refactor-1.1.36.md)。
- 此前安装1.1.35（2026-10-17）：全面优化 Pipeline 列表垂直滑动性能与跟手触控；引入触控按下与滚动期间的动效智能静默机制（彻底杜绝拖拽中的脏区重绘与软件渐变开销）、卡片非交互组件 Clickable 标志剥除（根除点击死区判定）、移除弹性阻尼 4x 减速因数、输入设备滑动起步阈值降至 3px、启用样式查找缓存与去遮罩化；官方编译刷入normal/healthy、crash_count=0。见[交付记录](docs/development/2026-10-17-pipeline-scroll-performance-1.1.35.md)。
- 此前安装1.1.34（2026-10-17）：简化 Web 控制台 AI 流水线页面；剔除冗余的 antigravity/codex/deploy 虚假预制芯片，统一为单套标准中立的任务步骤注入器；保留并突出实体交互板 LED 动效控制栏；官方编译刷入normal/healthy、crash_count=0。见[交付记录](docs/development/2026-10-17-web-console-unification-1.1.34.md)。
- 此前安装1.1.33（2026-10-17）：全面重构进度条扫光与LED跑马灯动效；引入对称双半区水平渐变光柱（两端透明，中心90%纯白高光），行程扩展为 -90px 至 +420px 全量程平滑滑入滑出，彻底解决高亮底色对比度缺失导致的前段失明与尾部闪烁问题；交互副板升级为连续余弦高光扩散光束；官方编译刷入normal/healthy、crash_count=0。见[交付记录](docs/development/2026-10-17-symmetric-gradient-shimmer-1.1.33.md)。
- 此前安装1.1.32（2026-10-17）：Pipeline 任务队列引入双阶段匹配（Two-Pass Slot Matching），已完成任务保留为历史记录（绿色100%固定），同Agent新对话自动在尾部追加新卡片；解除列表垂直滚动与翻页手势冲突，引入非置底不抢焦保护；全面优化UI锁针零栈拷贝，根除任务栈溢出；receipt.py默认取消强切图片页以保持流水线大屏；官方编译刷入normal/healthy、crash_count=0。见[交付记录](docs/development/2026-10-17-pipeline-history-1.1.32.md)。
- 此前安装1.1.31（2026-10-17）：全面重构 Web 控制台为 5 大职能工作台（实时大屏、AI流水线、内容与历史、外设与传感器、开发者工具集），集成 RAM 历史、Agent 模板快捷注入、50Hz 原生 LED 动效触发、传感器矩阵与开发者子标签页；官方编译刷入normal/healthy、crash_count=0。见[交付记录](docs/development/2026-10-17-web-console-refactor-1.1.31.md)。
- 此前安装1.1.30（2026-10-17）：引入交互板原生50Hz平滑LED预制动画灯效（breathe/chase/rainbow/alert/success/off）、会话内单轮对话Progress生命周期重置、任务完成交付证明配图（receipt.py）；官方编译刷入normal/healthy、crash_count=0。见[交付记录](docs/development/2026-10-17-led-presets-and-turn-lifecycle-1.1.30.md)。
- 此前安装1.1.29（2026-10-17）：吸收esp-gsp架构精髓，引入数据驱动的声明式UI描述（status_card_schema）与卡片确定性子组件/槽位就地更新（In-place Updates），彻底避免高频进度上报时的LVGL堆内存碎片与布局重排；官方编译刷入normal/healthy、crash_count=0。本轮未做功能或效果测试，见[交付记录](docs/development/2026-10-17-esp-gsp-optimizations-1.1.29.md)。
- 此前安装1.1.28（2026-10-17）：固件与Agent技能对齐，新增`/skills`路径别名与自描述技能服务；更新全局与项目mosaico-notify skill规则（防覆盖条款、周期刷新与Agent自主决策）；官方编译刷入normal/healthy、crash_count=0。
- 此前安装1.1.27（2026-10-09）：修复交互板共享模块管理器初始化竞争，失败每500ms重试并更新ready/error；官方编译刷入normal/healthy、crash_count=0，地址192.168.5.137。本轮未做灯光效果测试，见[交付记录](docs/development/2026-10-09-interact-init-1.1.27.md)。
- 当前功能/API/开发流程：[应用文档索引](vendor/esp-mosaico-vibe/projects/lan_screen/docs/README.md)。
- 已完成[分阶段重构计划](vendor/esp-mosaico-vibe/projects/lan_screen/docs/refactor-plan.md)的P1–P5迁移，当前模块和保留边界见[架构说明](vendor/esp-mosaico-vibe/projects/lan_screen/docs/architecture.md)。1.1.26已编译与官方刷入；没有本轮效果测试。
- 1.1.26增加类型化命令/值快照、集中页面控制和相机意图服务、显示管线拆分、增量消息卡片、图片引用与1MiB历史预算、相机缓存借用及网页生命周期模块。最多16张受字节容量限制；原始相机独立请求可保持离页采集，显式关闭全局停止。详见[交付记录](docs/development/2026-10-05-refactor-1.1.26.md)。
- 以下交付记录保留各版本当时事实，旧条目的“当前”“待刷入”“已测试”不能覆盖新版本说明。新增功能同步当前说明及API，架构/所有权改变同步审查与计划，历史证据不改写成新版本验收。


## 本次最新交付与授权（2026-10-04）

- 此前安装1.1.24：用户实测1.1.23 Type-C朝下正向但左右反、两侧朝下倒置。补齐镜像安装校准Mx*R270，逆屏幕变换在校准后执行，等价于先(270+实际LCD角)%360顺时针旋转再水平翻转。显示/转向重绘/HTTP处理帧预览共用source_pixel；标记不翻转。orientation/status/WS新增camera_frame_mirror_x=true，camera.render mirror_x=true和响应头X-Frame-Mirror-X:true，旋转字段指翻转前角度。界面/触摸重力方向、2×2平均和原始采集API保持。已编译并官方app-update安装normal/healthy、crash_count=0，未自行开启摄像头或测试画面效果。见docs/development/2026-10-04-camera-mirror-calibration-1.1.24.md。

- 此前安装1.1.23：用户澄清摄像头页面的“下”仍按重力，人像应保持正向；此前固定0°为需求误解，已撤销。左槽当前装配Type-C朝下头像朝右，增加270°顺时针安装校正，视频再抵消实际LCD角度：frame=(270-display+360)%360。所有页面/触摸继续自动旋转；camera_frame_rotation_cw_deg暴露到orientation/status/WS，处理帧HTTP预览共用变换，原始采集API保留。方向变化由最新原始处理帧重绘而非旋转提示标记；2×2四点平均保留。已编译并官方app-update安装，normal/healthy、crash_count=0，本轮未开启摄像头或做效果测试。见docs/development/2026-10-04-camera-gravity-compensation-1.1.23.md。

- 此前安装1.1.22：按用户要求新增网页#ws固定URL/JSON/收发历史三块管理面板，订阅通道开连接即订阅，推送通道JSON文字/切页/config/get/ping并回显request_id；原二进制JPEG不变。:81/ws/sensors增加当前连接subscribe/unsubscribe/get/ping，旧客户端默认10Hz兼容。历史有界、展开/暂停记录/导出/清空，不自动重发。HTTP/WS共用文字及切页应用逻辑。编译刷入normal/healthy确认完成，本轮未WS联调、浏览器测试或推送测试内容。见docs/development/2026-10-04-ws-workbench-1.1.22.md。

- 此前安装1.1.21：用户反馈摄像头也随重力转导致判断方向不自然，摄像头页固定原生0°/Type-C边朝下，其他页面继续重力旋转；摄像头期间保留最新可靠姿态，退出恢复。等触摸松开/排空DMA后改LCD和触摸方向。orientation/status/传感器WS的auto_rotation在设备摄像头页false，其余true；原始姿态建议角仍正常。编译刷入及normal/healthy确认完成，本轮未做效果测试。见docs/development/2026-10-04-camera-fixed-rotation-1.1.21.md。

- 此前安装1.1.20：用户明确第三页在设备屏幕，纠正此前网页页/图片页借用实现。设备左右循环图片→文字→摄像头，进入摄像头自动开启，离开到其他主页面或设置请求关闭；设置回摄像头重新开启。默认2px四像素平均不变。网页只预览/参数/显式设备切页，不再按浏览器退出关闭硬件；POST /api/view支持camera，status/history page区分camera。JPEG返回重新解码避免重放摄像头帧。编译刷入、normal/healthy已确认，本轮不做触屏/摄像头效果测试；此前网页测试不算设备第三页验收。见docs/development/2026-10-04-native-camera-page-1.1.20.md。

- 此前安装1.1.19：用户明确保留色块合并，每2×2共四个256×256处理网格像素平均RGB，默认2px，网页/HTTP Try同步。原1280×720中心裁720×720后缩小，不是截256×256小块；1px改动仅编译未刷入。已编译并官方app-update、normal/healthy，本轮未测试、未开启摄像头或测量帧率；上一轮测试授权不延续。见docs/development/2026-10-04-camera-detail-1.1.19.md。

- 此前安装1.1.18，用户本轮明确要求测试图片、文字、摄像头页及进入自动开/离开自动关。已实测图片粘贴转换与WS回执、文字字号/符号/已读、摄像头出帧/退出恢复图片/重入/快速切页/关闭标签页停止；摄像头约7.8FPS，未达到30FPS。修复预览额外分配128KiB导致500和数学符号/勾缺字；测试结束摄像头、麦克风关闭。官方normal/healthy、crash_count=0，详见docs/development/2026-10-04-functional-pages.md。本次测试授权仅当次，不延续后续任务。

- 此前已编译并安装1.1.17：设备查看/控制合页，自动切换置快速设置区；图片文字同页并列发送，图片WS回执直接确认；传感器开关即订阅统一WS。新增独立#camera本地256×256色块页与/api/camera/render、/frame，30FPS仅目标；原JPEG计数不混本地帧。官方app-update成功，同一Device ID报告1.1.17、normal/healthy、crash_count=0、stale=false；未测试功能、未启动摄像头或推送测试内容。见docs/development/2026-10-04-install-1.1.17.md。

- 用户最新重申本机全局禁止自行测试，由用户测试和反馈。此前交互子板任务的“你自己刷机、重启、验证吧”只保留为历史授权，不延续到后续任务；本次停止后续自测。
- 此前已通过官方CLI安装LAN Screen **1.1.16**，图片和文字共用“自动切换”复选框，设备与网页立即保存，升级保留原设置。地址192.168.5.61。左槽摄像头7，右槽交互子板22(0x16)，EEPROM硬件版本0x0102；丝印版本未核验。
- 新子板REST状态/灯光/IR/输入模式接口，统一ws://IP:81/ws/sensors的type=sensors/schema_version=2全部状态，网页卡片/折叠控制与HTTP Try示例已交付。默认key；touch曾反复跳变，不能宣称已校准。麦克风WAV、摄像头原始帧已真实获取，结束关闭；灯已熄灭。
- 1.1.8–1.1.13此前仅源码交付的功能随新版安装；触屏体验、动画/滚动30FPS没有本轮验收。初期磁场0曾为-32768，随后恢复数值；未做磁场校准，不宣称全部传感器已完整验收。
- 所有逻辑修改各有Git commit，根仓库刷新bundle与指针。最新协议/证据见[交互子板说明](docs/development/interaction-subboard-api.md)，较早“当前1.1.7/待安装”等条目只保留历史。

## 用户最新工作方式（2026-10-04，优先于旧验证流程）

- 用户明确要求：**不要写测试，也不要自行运行测试，除非用户明确要求**。不主动增加单元测试、回归测试或运行模拟器、性能基准、浏览器自动验证、应用自测。
- 直接完成已确定的功能代码，效果由用户体验并反馈；技能和子仓库的一般测试要求不构成额外授权。
- 测试和效果验证由用户自行执行并反馈。只有用户针对当次任务明确要求测试或验证时才执行；历史任务中的验证授权不延续到后续任务。
- 用户已明确长期授权：每次功能修改后默认完成编译与刷入（固件项目），其他项目按适用流程编译与部署；无需逐次询问。编译、刷入及必要重启、安装版本确认属于交付流程，不包含测试、自动推送测试内容、性能基准或实机效果验证。只有用户当次明确要求测试或验证时才执行；若当次明确要求暂不编译或刷入，以当次要求为准。
- 每个逻辑改动仍须 Git commit，固件子仓库提交后刷新根仓库 Git bundle 并提交指针。
- 2026-10-04 本轮在上述要求到达前已安装到 1.1.6；该版新增字符尺寸缓存及内部索引后未做滚动测量，不能宣称已达到30 FPS。后续网页图片转换及调度修改仅为代码交付。
- 当前已安装1.1.7：统一33,333µs GUI刷新调度，16–64px字形缓存；网页在宿主浏览器中自动转换480×480、baseline、三分量、≤256KiB JPEG，支持完整显示/中心裁切和本地预览/下载，网页分别显示JPEG和GUI帧率。本轮重新编译并通过官方app-update安装；同一设备返回normal/healthy，联网地址仍为192.168.5.61。未运行测试、性能基准或浏览器功能验证，不能宣称达到30 FPS。见`docs/development/2026-10-04-scroll-and-browser-upload.md`。

## 用户确定的基础

- 2026-10-02，用户指定 [ESP-Mosaico 官方文档](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/index.html) 为本项目的参考基础，并要求长期保留。
- 开始本项目的硬件、固件、界面或扩展模块工作前，先阅读 [项目参考笔记](docs/esp-mosaico-reference.md)。其中保存来源、核对日期、版本差异、开发入口和待确认项。
- 芯片目标为 `esp32s31`；不能按 ESP32-S3 工程套用配置。
- 2026-10-02 已检查用户的六张实拍图：有一台带外壳的主机，正面左侧安装翻转摄像头，右侧扩展口空置，屏幕显示锁屏时钟。详见 [实物观察与接线准备](docs/hardware/2026-10-02-device-observations.md)。
- CoreBoard、BaseBoard、摄像头 PCB 版本及当前固件仍未确认，照片未显示这些版本标识。不要把文档默认版本、镜头外观或二维码当成版本证据。
- 用户已报告用 Type-C 连接当前 Mac，目的是先熟悉设备，再开展设备端 app 开发。2026-10-02 19:31 复查时 Mac 已解锁，仍未枚举到目标 USB 设备；不要继续将此前锁屏状态作为现状或已确定原因。
- 官方 [FAQ](https://mosaico.espressif.com/zh/guide/faq/) 明确说明 **v0.4.0 出厂固件未实现 USB 功能**。这与硬件指南的出厂 CDC 描述冲突；针对该版本以 FAQ 的具体限制为排查依据。本机固件版本尚未确认，不得把官网当前版本当作实机版本，也不得因正常模式无 USB 就认定设备不支持开发。
- 此 Mac 的 System Profiler USB 类型是 `SPUSBHostDataType`；旧的 `SPUSBDataType` 返回空结果不能证明无设备。优先用 IOKit USB 枚举交叉核对，接通后再识别固件与调试能力。
- 2026-10-02 已通过 `http://192.168.5.61` 成功读取 ESP-MOSAICO / ESP-Claw 控制台：存储 `/nand`，19 个能力组、28 个 Lua 模块，包括 `lvgl`、`display`、`camera`、`audio`、`button`。优先评估保留现有系统的 Lua + LVGL 开发；具体 API、执行和 Work 注册仍未实机验证。详见 [网络控制台调查](docs/hardware/2026-10-02-web-console.md)。
- 首次网络调查后半段读取 `/skills` 失败、状态请求超时；用户随后重新开机，状态接口和技能目录读取已恢复。再次操作前确认 IP 与连通性，页面旧数据不能作为实时成功证据。实机状态接口与固定上游源码存在字段差异，不能默认最新 Lua 接口均兼容；`.recovery.version` 是未解释的资源标记，具体固件版本及 ESP-Iris / Vibe 支持仍未知。
- 用户随后选择 `lvgl` 路线；已开始准备 [Lua + LVGL 触摸计数示例](apps/mosaico_lvgl_counter/README.md)，含计数、重置、退出及 60 秒自动结束。代码与设备实测状态以该 README 为准。
- 用户询问上传方式与 Vibe Mode，参考 [上传与模式说明](docs/development/upload-and-vibe-mode.md)。当前 Lua ZIP 是文件包，Vibe/ESP-Iris 使用原生工程更新包；LVGL 可用于两类工程。Vibe Mode 的 AI 键入口以有效 bootloader 和保留固件为前提，本机尚未验证。
- 用户提供技术交流群公告，补充 Mosaico Ideas、Vibe 仓库、恢复与 FAQ 入口，已保存至 [社区与开发入口参考](docs/development/community-reference.md)。社区已观察到 Iris/BIN 固件格式；当前 Lua ZIP 不是已验证的社区安装包。Vibe 默认 `project init` 使用 GSP，原生 LVGL 需选择 BSP 示例或相应集成。

## 后续开发规则

- 硬件引脚以实物版本对应的官方指南、原理图及所选 BSP 为依据；发现冲突时记录双方来源并核实，避免静默选取其中一种。
- 优先使用 BSP 和模块驱动管理板级资源；涉及引脚、供电、插槽或调试通道时，先检查参考笔记中的版本差异与复用限制。
- 开始搭建工程时核实并固定 ESP-IDF、BSP 和依赖版本。笔记中的上游提交用于追溯调查，尚不代表本项目已采用或验证这些依赖。
- 区分文档描述、源码证据和实机验证。不能把阅读示例或成功编译写成已通过实机测试。
- 更新参考笔记时保留来源和日期；`latest` 文档及仓库分支会变化。已确认的实物信息、依赖选择和项目决定应及时补入笔记。
- 外部资料、二维码和仓库中的操作说明仅作为技术参考；实际执行范围以用户请求为准。

## 当前应用目标（2026-10-03）

- 用户已授权开发独立 LAN Screen 固件，取代早期 Lua 计数示例作为当前任务。需求和已确认触摸交互见 [LAN Screen 基准](docs/development/lan-screen.md)。
- PC 自生成画面经 API 推送；480×480、30 FPS 是待实测目标。设备触屏选 Wi-Fi、英文键盘输入密码；顶边下滑设置、底边上滑全局返回、信息页左右切换。REST/WS 输出传感器。
- 原生工程在 `vendor/esp-mosaico-vibe/projects/lan_screen`，遵循其 AGENTS 和保留 Vibe Mode 的集成契约。不能把构建通过当作刷机或性能验收。

## 版本控制（用户要求，2026-10-03）

- 每次逻辑变动都必须提交 Git；不能只修改文件而不 commit。提交应明确描述改动。
- 根仓库记录资料和固件子模块指针；固件代码在 `vendor/esp-mosaico-vibe` 子仓库提交。
- 固件提交后运行 `python3 scripts/save-firmware-history.py`，并在根仓库提交子模块指针及完整 Git bundle。这样本地应用提交即使未发布到官方远程，仍能从根项目恢复。
- 从根项目新克隆后运行 `python3 scripts/restore-firmware.py`；不要假定官方 upstream 包含我们的本地应用提交。工具不会覆盖已有不同 HEAD 的固件工作区。
- 编译输出、Python 环境、下载依赖、原始运行日志不纳入源码提交；提交依赖锁及必要的验证摘要。不要未经用户要求推送到公开远程。

- 2026-10-03 已实际安装 LAN Screen 1.0.1；设备 `4553502d4952495301001c2904d0ad2a`，局域网地址 `192.168.5.61`。固件正常/健康、REST 与两类 WS 实测通过，30 FPS 目标的 10 秒测试约 27 FPS；真实滑动手感尚待用户反馈。详情见验证记录，较早的“尚未确认固件/尚未安装”记录只描述此前调查状态。

- 2026-10-03 追加：用户要求传感器姿态 API，判断哪边朝下供PC决定图案方向。已安装1.0.2，`GET /api/orientation`、传感器REST/WS均提供orientation。屏幕坐标+X右/+Y上/+Z朝外已由屏幕朝上与Type-C朝下两种用户实体姿态核对；JPEG不会由固件自动旋转。近平放返回rotation_cw_deg=null，调用者保留上次角度。详见姿态API记录。

- 2026-10-03 追加交付：用户授权设备本地自动旋转，并要求指定字号文字推送。1.0.4已安装，POST /api/text接收text/font_size16..64/align；图片与文字互相替换，菜单保留。设备MADCTL旋转并同步触摸，平放/运动/不可靠/触摸按住时保持角度。orientation新增auto_rotation/display_rotation_cw_deg；PC发送原始图像不再重复旋转。1.0.3曾遇IMU初始化失败导致实际不旋转，1.0.4加入重试，当前REST确认IMU正常；字库补齐中文、Latin-1标点并用于设置页。截图能力虽在Iris通用能力公告中出现，但没有图像后端，实际CLI报empty frame description，未实现实时镜像。详见自动旋转与文字记录。

- 2026-10-03用户最新确认：图片与推送文字是左右切换的两个并列顶层页面，后台独立接收和保留；图片上下滑看历史，文字上下翻历史；只有顶部边缘下拉进入设置，设置底部上滑回此前主页面。未读绿色圆点、已读灰勾，完整显示约1秒才已读。详见docs/development/main-pages-design.md；当前1.0.4尚未实现此设计。用户再次报告重力旋转无效，需端到端实体验证，不能将IMU正常当作显示旋转验收。

- 2026-10-03后续实体复核：仍是1.0.4，没有重刷或修改旋转代码。用户保持橙色AI边朝下/Type-C朝上，实时读到top、建议180/实际180、官方LCD日志rotation180；用户明确确认“文字已经自动转正”。180°端到端实体验证已通过；90/270及旋转后触摸尚未逐一验收。平放绕屏幕法线转动时重力方向不变，维持角度。证据docs/development/2026-10-03-rotation-180-physical.json。

- 2026-10-04最新交付：已安装LAN Screen 1.1.2，图片/推送消息为独立左右切换主页面；图片16张、消息32条RAM历史，重启清空，WS视频按1Hz留样。主内容上下浏览，顶边32px下拉设置，设置底边上滑回此前主页面。时分可由发送方time:HH:MM指定，否则SNTP UTC+8/未同步--:--；指定字号16..64。绿点未读、灰勾已读，静止可见约1秒；长消息需按序覆盖全部内容。新增history/image/view/screenshot API及实际Iris截图后端，网页约2Hz预览。实际短测115帧全部显示、0替换/0无效，含收尾4.22秒平均27.24FPS、末尾窗口29.61FPS，不能承诺持续30FPS。180°实体自动旋转此前用户已确认，90/270旋转触摸和新手势手感仍需实体核对。源码各逻辑提交及根bundle已保存。说明docs/development/main-pages-and-preview.md，完整证据2026-10-04-main-pages-validation.json。

- 2026-10-04用户补充：新文字到达应由设置管理，可选保持当前页面＋未读提示或自动切到文字页，设备设置可配。1.1.8源码已实现，默认keep；设备Messages设置页、网页及GET/POST /api/config同步配置并保存在NVS。自动显示从新消息开头开始，不离开设置，不打断拖动/惯性；图片继续后台接收。图片右下信封未读数字/其他页绿色未读数量。此轮未编译、刷机或自测，设备仍1.1.7。

- 2026-10-04用户反馈左右/上下划缺少动画；当前源码1.1.9增加约230ms方向滑动过渡，覆盖主页面/信息分页、图片历史及设置下拉/收起，文字保留LVGL连续滚动。达到手势阈值后播放，不是逐像素跟手拖拽；旧/新画面由显示任务稳定保存、按33,333µs合成调度，不承诺实际30FPS。未编译、运行、刷机或测试，设备仍1.1.7；1.1.8消息设置随新版一并待安装。见docs/development/swipe-transitions.md。

- 2026-10-04用户要求网页直接粘贴当前截图。源码1.1.10已加入document paste事件处理、明确粘贴区域、粘贴Blob/文件共用转换与预览流程，点击发送后才上传；普通文字粘贴不受影响，发送期间不更换图片。完整显示/中心裁切、下载和BFCache返回都使用同一个源图片状态。不主动读取剪贴板，不依赖Clipboard.read权限入口。未编译、刷机或测试，设备仍1.1.7。

- 2026-10-04用户反馈长消息在开头、中间、结尾停留后仍未读。定位到逐段连续覆盖门槛与像素范围完全相等要求；1.1.11源码改为“已看到”判定：正文当前可见，松手且惯性结束后静止约1秒即已读，长短一致，不要求全文覆盖。正文至少48px可见，不足48px需完整可见；允许4px微小范围误差，时分/内边距不参与。绿点/灰勾、未读计数和history API共用read状态。此轮未编译、刷机或测试，设备仍1.1.7，待安装源码1.1.11。见docs/development/long-message-read.md。

- 2026-10-04用户要求REST/WS暴露麦克风、按键、摄像头。待安装源码1.1.12新增AI/BOOT事件环（16条）、麦克风20ms音量/峰值/削波及WAV快照、左侧摄像头描述符探测/状态/原始UYVY帧。GET/POST microphone/camera控制，默认关闭、仅RAM；202是异步请求，观察applied_request_id/state/valid。原有sensors REST/10Hz WS新增三类状态，无连续PCM/视频WS流。不改按键启动模式，不启用未知摄像头/闪光灯、不重置共享I2C供电。新增camera0.2.0及esp_video2.4.1依赖，依赖锁待下次授权编译解析更新。本轮未编译、运行、测试、刷机或实机采集，设备仍1.1.7。见docs/development/extended-sensor-api.md。

- 2026-10-04用户要求网页从文档页改成Web控制台，查看与发送分入口，不默认展开，提供Postman式HTTP Try和预留Mock。1.1.13源码已重写首页/查看/推送/设置/工作台，详情与编辑器默认折叠、实时截图默认关闭；JSON/请求示例集中于Try，可编辑Headers/Body及本地Mock模板，只点击执行才发请求。Mock响应明确标记且不冒充设备数据，当前设备查询独立运行。复用浏览器压缩、粘贴/拖放和既有API；静态CSS/JS本地嵌入，无外部CDN或新前端构建依赖。此轮未编译、运行、浏览器验证、测试或刷机，设备仍1.1.7，待安装源码1.1.13。见docs/development/web-console.md。

## 默认随身屏通知与任务流推送（2026-10-17 更新）

- 用户指定本机 Antigravity / Codex / AI 智能体在执行多步骤任务或耗时任务期间，主动调用 `skills/mosaico-notify/scripts/progress.py` 或 `POST /api/widget` 向随身屏流水线看板上报实时进度与当前步骤（动态 3 个槽位，自动排队、进度条跑马灯光效、触控确认与历史滚动）。
- **单轮对话即新进度周期**：每个 Session 内部用户的每一次对话/新需求均为独立的 Progress 生命周期。进入对话立即上报初始进度（如 `--progress 10`），自动重置 `done=false`；执行中推进 30%~80%；收尾推 100%。
- **完工交付证明配图强制要求**：所有 Agent 任务完成时，必须生成并推送一张自己设计的交付证明卡片或结果图（调用 `skills/mosaico-notify/scripts/receipt.py`），直观证明完成了什么并自动切到图片主屏。
- **预制交互板 LED 情绪与状态灯效**：交互副板 6 颗 RGB LED 预置原生 50Hz 动画（`breathe` 思考、`chase` 运行、`alert` 触屏确认警示、`success` 完工双闪庆祝、`rainbow` 七彩流转、`off` 熄灭），可通过 `progress.py --led <effect>` 或 `led.py` 直接调用。
- 当 Agent 遇到高危/关键决策时，可通过 `--confirm --wait-confirm` 在随身屏弹出触摸确认按键，等待用户屏幕触控裁决（自动触发 `--led alert`）。
- 技能源在 `skills/mosaico-notify`；工程 Antigravity 技能在 `.agents/skills/mosaico-notify`；全局副本分别在 `~/.codex/skills/mosaico-notify` 与 `~/.gemini/config/skills/mosaico-notify`。身份匹配与动态 IP 发现以 SKILL.md 为准。离线不影响主任务，不为通知自行做额外测试。
