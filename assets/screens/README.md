# 已完成界面

`completed-yao-source.png` 使用内置 imagegen 生成；`completed-yao-480.jpg` 是供 ESP-Mosaico 显示的 480×480 RGB baseline JPEG，质量 90、4:2:2，29,684 bytes。源 PNG 保存在项目内，生成目录的原图也保留。

设计：深蓝黑背景、绿色圆形白色勾选、清晰的“已完成”和“即将显示姚明照片”，底部满进度条。适合小 OLED 屏幕，无设备外框。

完整生成提示词：

> Use case: ui-mockup. Asset: a final flat full-screen success interface image to display directly on a 480x480 square OLED device. Create a crisp minimalist polished device UI, square 1:1, no device frame, no perspective, no photograph, no watermark. Near-black navy background #101720 with subtle dark concentric circles centered around a large emerald green circular success icon and a simple high-contrast white check mark. Generous negative space, balanced vertically centered layout. Small uppercase white heading 'LAN SCREEN' at the upper left, a tiny emerald status dot at the upper right. Below the check mark render exact large clean bold Chinese text '已完成'. Below it render exact smaller white Chinese text '即将显示姚明照片'. A thin green progress bar near the bottom, fully filled, and very small muted label 'READY'. All typography accurately rendered and legible after downscaling to 480x480. Keep all text and graphics within a 36-pixel safe margin at target resolution. No other text. The result must be a flat actual UI bitmap, ready to send to a real device.

顺序推送：`scripts/push-completed-then-photo.py`。等待设备的 LCD 显示计数增加后才开始 3 秒停留计时，然后推送姚明 JPEG；接收 ACK 不视为显示完成。
