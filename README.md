# Mosaico LAN Screen

当前已编译并安装：**1.1.19**（2026-10-04）。摄像头默认每2×2共四个处理像素平均合为一个色块，保留合并效果，比原8px更细；网页新增2px选项。已通过官方app-update安装并确认normal/healthy，本轮未做效果测试或帧率测量。见[色块细化与安装记录](docs/development/2026-10-04-camera-detail-1.1.19.md)。此前三个功能页的实测见[1.1.18记录](docs/development/2026-10-04-functional-pages.md)。

此前交付：**1.1.16**（2026-10-04）。图片和文字共用一个“自动切换”复选框，设备与网页立即保存；后续测试由用户执行。右侧交互子板已识别，统一WS、RGB控制、麦克风WAV与摄像头原始帧已收到实机响应；没有新增测试或运行单元测试、模拟器、性能基准。

当前工程：[`vendor/esp-mosaico-vibe/projects/lan_screen`](vendor/esp-mosaico-vibe/projects/lan_screen/README.md)。

触屏配网、图片与推送消息双主页面、历史和已读状态、设备自动旋转、实时截图预览、REST / WebSocket 传感器接口。

- [确认过的需求](docs/development/lan-screen.md)
- [工程、API和构建说明](vendor/esp-mosaico-vibe/projects/lan_screen/README.md)
- [本轮编译与安装记录](docs/development/2026-10-04-install-1.1.17.md)
- [用户开发工作方式](docs/development/agent-work-preferences.md)
- [官方硬件参考及版本差异](docs/esp-mosaico-reference.md)

2026-10-03：1.0.0 已在实机运行，6 帧局域网推流通过。1.0.1 增加触摸修复和 API 入口；1.0.2 增加姿态 API；1.0.4 已安装，提供设备自动旋转、可指定字号的中文/英文文字 API，并修复 IMU 初始化失败不重试和字库缺失。这是早期版本记录；最新双主页面功能见 [使用说明](docs/development/main-pages-and-preview.md)。

设备当前地址：[网页控制台](http://192.168.5.61/)。IP 以屏幕实际显示为准。

项目已纳入本地 Git。固件作为子模块独立提交，根仓库附带完整 Git bundle，保存未发布到官方仓库的应用提交。新克隆后运行 `python3 scripts/restore-firmware.py` 恢复固件及两个必要的上游子模块；构建需按工程 README 配置固定版本 ESP-IDF。每次固件修改提交后运行 `python3 scripts/save-firmware-history.py`，再提交根仓库指针和 bundle。

[另一位 AI 的改动复查与本次修复](docs/development/2026-10-03-review-and-fixes.md)。

姿态接口：[GET /api/orientation](http://192.168.5.61/api/orientation)。原传感器 REST 和传感器 WebSocket 也包含 `orientation`。字段、旋转约定、实体标定及实测记录见 [姿态 API](docs/development/orientation-api.md)。

文字推送：`POST /api/text`，JSON `{"text":"你好，Mosaico！\n第二行","font_size":32,"align":"center"}`。字号16–64，刷新设备首页可直接发送。可带 time:"HH:MM"，消息追加保留历史。屏幕截图：GET /api/screenshot；网页可启动约2Hz实时预览。最新交付见 [双主页面与截图](docs/development/main-pages-and-preview.md)，早期记录见 [自动旋转与文字](docs/development/auto-rotation-text.md)。

1.1.7增加浏览器图片自动转换：在宿主机上将图片绘制为480×480，编码并压缩到256 KiB内的baseline JPEG，发送前可预览、保存，并可选择完整显示或中心裁切。文字滚动已加入字形缓存、内部DMA双缓冲与统一刷新调度；30 FPS为目标，本版未测量滚动帧率。刷新设备首页即可使用新版上传界面。

1.1.8–1.1.13的消息到达设置、滑动动画、粘贴截图、长文字已读修复、扩展音视频接口和新Web控制台已随1.1.15安装。之前各功能文档保留当时“仅源码交付”的历史状态，以本页和最新交付记录为准。

1.1.15增加多功能交互子板：环境光、PIR运动、两路按键/触摸状态及事件；六颗RGB全灯/单灯控制、NEC红外、模式和启用开关。统一 `ws://192.168.5.61:81/ws/sensors` 返回所有传感器状态，REST同结构 `/api/sensors`。网页“查看设备 → 传感器与采集”提供实时数据与折叠控制，HTTP Try有请求示例及本地Mock。

[交互子板API与最新实机记录](docs/development/interaction-subboard-api.md)。[新网页控制台设计](docs/development/web-console.md)。本机touch模式观测到跳变，默认采用机械key；摄像头和麦克风默认关闭，按需开启。IR只确认驱动发射，未确认外部电器接收；手势/30FPS没有本轮验收。
