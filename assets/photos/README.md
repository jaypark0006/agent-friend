# 科比照片推送

- 摄影：Keith Allison。
- 来源：[Kobe Bryant 2014.jpg — Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Kobe_Bryant_2014.jpg)。Commons 文件包含此前的颜色/亮度调整。
- 图片许可：[CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/)。原图与本目录的尺寸转换图沿用此许可；不影响项目代码许可。
- `kobe-original.jpg`：从上述 Commons 下载的 2060×1963 JPEG。
- `kobe-480.jpg`：居中裁成正方形，等比缩小到 480×480，RGB baseline JPEG，质量 90、4:2:2，61,273 bytes。
- 2026-10-03，通过 `POST http://192.168.5.61/api/frame` 推送。accepted=282；设备 displayed 从 281 增至 282，invalid 未增加，确认 LCD 传输完成。结果见 `kobe-push-result.json`。
