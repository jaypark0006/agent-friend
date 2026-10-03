# Mosaico LAN Screen

当前已安装版本：**1.1.2**（2026-10-04）。

当前工程：[`vendor/esp-mosaico-vibe/projects/lan_screen`](vendor/esp-mosaico-vibe/projects/lan_screen/README.md)。

触屏配网、图片与推送消息双主页面、历史和已读状态、设备自动旋转、实时截图预览、REST / WebSocket 传感器接口。

- [确认过的需求](docs/development/lan-screen.md)
- [工程、API、构建和测试说明](vendor/esp-mosaico-vibe/projects/lan_screen/README.md)
- [官方硬件参考及版本差异](docs/esp-mosaico-reference.md)

2026-10-03：1.0.0 已在实机运行，6 帧局域网推流通过。1.0.1 增加触摸修复和 API 入口；1.0.2 增加姿态 API；1.0.4 已安装，提供设备自动旋转、可指定字号的中文/英文文字 API，并修复 IMU 初始化失败不重试和字库缺失。这是早期版本记录；最新双主页面功能见 [使用说明](docs/development/main-pages-and-preview.md)。

设备当前地址：[API 说明和画面上传](http://192.168.5.61/)。IP 以屏幕实际显示为准。

项目已纳入本地 Git。固件作为子模块独立提交，根仓库附带完整 Git bundle，保存未发布到官方仓库的应用提交。新克隆后运行 `python3 scripts/restore-firmware.py` 恢复固件及两个必要的上游子模块；构建需按工程 README 配置固定版本 ESP-IDF。每次固件修改提交后运行 `python3 scripts/save-firmware-history.py`，再提交根仓库指针和 bundle。

[另一位 AI 的改动复查与本次修复](docs/development/2026-10-03-review-and-fixes.md)。

姿态接口：[GET /api/orientation](http://192.168.5.61/api/orientation)。原传感器 REST 和传感器 WebSocket 也包含 `orientation`。字段、旋转约定、实体标定及实测记录见 [姿态 API](docs/development/orientation-api.md)。

文字推送：`POST /api/text`，JSON `{"text":"你好，Mosaico！\n第二行","font_size":32,"align":"center"}`。字号16–64，刷新设备首页可直接发送。可带 time:"HH:MM"，消息追加保留历史。屏幕截图：GET /api/screenshot；网页可启动约2Hz实时预览。最新交付见 [双主页面与截图](docs/development/main-pages-and-preview.md)，早期记录见 [自动旋转与文字](docs/development/auto-rotation-text.md)。
