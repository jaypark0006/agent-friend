# Mosaico LAN Screen

ESP-Mosaico / ESP32-S31局域网显示固件：图片、推送文字、摄像头三个设备主页面，触屏Wi-Fi设置、自动旋转、RAM历史/未读、屏幕截图、传感器REST/WS和交互子板控制。

最近安装 **1.1.24**（2026-10-04），官方安装确认normal/healthy。最新相机镜像与方向修正已刷入，未进行新一轮画面效果测试。30FPS仍是目标，不能将旧版短测用于当前性能承诺。

- [项目文档总索引](docs/README.md)
- [当前功能与验证边界](vendor/esp-mosaico-vibe/projects/lan_screen/docs/current-state.md)
- [REST / WebSocket接口](vendor/esp-mosaico-vibe/projects/lan_screen/docs/api.md)
- [架构review](vendor/esp-mosaico-vibe/projects/lan_screen/docs/architecture-review.md)
- [分阶段重构计划](vendor/esp-mosaico-vibe/projects/lan_screen/docs/refactor-plan.md)
- [固定依赖、编译与官方刷入](vendor/esp-mosaico-vibe/projects/lan_screen/docs/development.md)
- [最新固件安装记录](docs/development/2026-10-04-camera-mirror-calibration-1.1.24.md)

固件源码在[projects/lan_screen](vendor/esp-mosaico-vibe/projects/lan_screen/README.md)。本仓库保存资料、固件子模块指针和完整Git bundle；固件origin是官方仓库，但我们的提交仅在本地，尚未发布到GitHub。根仓库尚未配置远程。

最近设备地址：[控制台](http://192.168.5.61/)，DHCP地址以设备显示为准。网页查看/控制一页、图片/文字推送一页，另有摄像头、HTTP和WS入口。设备页与网页入口不是同一套页面生命周期。

每个逻辑改动须Git commit。固件提交后在根目录运行 `python3 scripts/save-firmware-history.py`，再提交bundle和指针；新克隆运行 `python3 scripts/restore-firmware.py`。功能改动默认编译、刷入及确认版本；测试仅在当次明确要求时执行。**本轮文档整理和重构计划没有改变运行代码，也没有重刷设备。**
