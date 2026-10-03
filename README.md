# Mosaico LAN Screen

当前工程：[`vendor/esp-mosaico-vibe/projects/lan_screen`](vendor/esp-mosaico-vibe/projects/lan_screen/README.md)。

触屏配网、手势设置菜单、局域网 JPEG 显示、REST / WebSocket 传感器接口。

- [确认过的需求](docs/development/lan-screen.md)
- [工程、API、构建和测试说明](vendor/esp-mosaico-vibe/projects/lan_screen/README.md)
- [官方硬件参考及版本差异](docs/esp-mosaico-reference.md)

2026-10-03：1.0.0 已在实机运行，6 帧局域网推流通过。1.0.1 增加触摸修复和 API 入口；1.0.2 已增加姿态 API 并运行实机。最新交付证据见 [验证记录](docs/development/lan-screen-validation.md)。

设备当前地址：[API 说明和画面上传](http://192.168.5.61/)。IP 以屏幕实际显示为准。

项目已纳入本地 Git。固件作为子模块独立提交，根仓库附带完整 Git bundle，保存未发布到官方仓库的应用提交。新克隆后运行 `python3 scripts/restore-firmware.py` 恢复固件及两个必要的上游子模块；构建需按工程 README 配置固定版本 ESP-IDF。每次固件修改提交后运行 `python3 scripts/save-firmware-history.py`，再提交根仓库指针和 bundle。

[另一位 AI 的改动复查与本次修复](docs/development/2026-10-03-review-and-fixes.md)。

姿态接口：[GET /api/orientation](http://192.168.5.61/api/orientation)。原传感器 REST 和传感器 WebSocket 也包含 `orientation`。字段、旋转约定、实体标定及实测记录见 [姿态 API](docs/development/orientation-api.md)。
