# 摄像头页停止重力旋转（1.1.21，历史策略）

> 版本专题/历史记录：文中版本、授权、待办和验收描述对应当时，不代表当前状态。最新功能、API、架构与重构计划见[当前文档索引](../../vendor/esp-mosaico-vibe/projects/lan_screen/docs/README.md)。


**后续更正：** 用户澄清界面仍须依重力定“下”，视频需安装方向校正及逆屏幕旋转补偿。1.1.21固定0°是需求误解，已由[1.1.23方案](2026-10-04-camera-gravity-compensation-1.1.23.md)替代。下文保留当时交付事实。

用户反馈设备摄像头页也跟随重力旋转，改变了画面坐标方向。本轮摄像头页固定屏幕原生0°，Type-C所在边作为底部；不再把通用界面重力角套到摄像头画面。摄像头自身仍按原传感器坐标采样，不附加图像旋转或镜像。

图片、文字及设置页继续自动旋转。摄像头期间保留最近可靠的重力角，离开摄像头恢复其他页方向；平放或姿态数据缺失时保持最近可靠角。改变角度等待触摸松开并排空LCD DMA，再通过BSP同时更新LCD与触摸坐标，不在拖动中改变手势坐标。

orientation/status及统一传感器WS中的auto_rotation在设备摄像头页为false，其他页为true；display_rotation_cw_deg始终是实际角度。IMU采样和orientation.rotation_cw_deg建议角不变，设备相机自动开关与2px四像素平均不变。

源码提交4520872。按用户长期授权编译刷入，只确认安装身份、版本和健康；本轮未启动摄像头、实测旋转或浏览器验证，不延续此前测试授权。

固定ESP-IDF 7b9cc1ac79f865983f59bb8ff3ff43eb74ff1dbe，esp32s31；构建20261004-195411-build-12297成功，应用BIN为4,947,104字节，2条构建警告沿用依赖目录额外文件及保留factory分区小于正常应用，未改分区契约。原始构建日志保留在应用.codex-runs/idf-low-noise-build/20261004-195411-build-12297/raw.log；安装身份证据保留在应用.codex-runs/camera-fixed-rotation-1.1.21/。

已通过官方app-update安装1.1.21，同一Device ID `4553502d4952495301001c2904d0ad2a`，normal、lifecycle_state=2、stale=false、crash_count=0，新Boot ID `7403752047002902845`。operation `ee6e177b-7cbc-411f-8f2a-9d1bfc5264d6` succeeded，healthy=true；设备ELF SHA256 `39d05943a8def1dbf8e74123b4e671a65f12a252da322cee4c3023acb4b0c36a`。未做本轮效果测试。
