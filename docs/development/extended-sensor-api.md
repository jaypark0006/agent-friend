# 扩展传感器 API（1.1.12，2026-10-04）

> 版本专题/历史记录：文中版本、授权、待办和验收描述对应当时，不代表当前状态。最新功能、API、架构与重构计划见[当前文档索引](../../vendor/esp-mosaico-vibe/projects/lan_screen/docs/README.md)。


后续更新（2026-10-04）：已随1.1.15编译、刷入并取得麦克风WAV/摄像头原始帧；本文保留1.1.12开发时设计记录，摄像头下载缓存已改为临时移交所有权，依赖锁已解析更新，右槽已新增交互子板。最新协议、实机结果及限制见[交互子板与统一API](interaction-subboard-api.md)。

本轮仅开发源码，未编译、启动应用、刷机或运行测试。设备仍安装1.1.7；以下新接口需安装新版后才可用。

## 接口

| 方法/路径（设备HTTP端口80） | 数据 |
|---|---|
| GET /api/buttons | AI/BOOT状态、按压时长、累计按压数、最近16条事件 |
| GET /api/microphone | 音量、峰值、削波计数及采集状态 |
| POST /api/microphone | JSON {"enabled":true/false} 控制采集 |
| GET /api/microphone/audio | 最新20ms、48kHz、PCM16、双声道WAV |
| GET /api/camera | 左侧摄像头连接观测、格式、尺寸、采集状态 |
| POST /api/camera | JSON {"enabled":true/false} 控制采集 |
| GET /api/camera/frame | 最新原始UYVY帧 |

原有 `GET /api/sensors` 和 `ws://IP:81/ws/sensors` 增加 `buttons`、`microphone`、`camera`，旧字段保留；WS约10Hz，不需要发送订阅消息。音视频字节通过REST快照获取，WS只推状态、事件与音量。各外设时间戳属于自己的采样，不表示同一时刻采集。

`GET /api/info`自动列出新接口；设备网页新增开启/关闭按钮与状态、下载链接。Python客户端新增 `peripheral(name)`、`enable_peripheral(name, enabled)`、`camera_frame()`、`microphone_audio()`。最后两个方法返回 `(bytes, metadata)`。

## 开关、状态与错误

麦克风、摄像头开机默认关闭，开启只在本次运行有效，不保存NVS。POST严格要求单个enabled布尔值。HTTP202表示接受请求，由独立后台任务操作驱动；不是硬件开启成功。反复POST同样的值可以显式重试，多个快速请求合并为最新目标。

- requested_enabled：请求目标；enabled：已开启采集资源状态。
- request_id / applied_request_id：请求序号及任务已处理的序号。相同序号才表示当前请求处理完成；请求可以合并。
- state：unavailable / pending / disabled / running / error。
- valid：当前请求已处理、请求开启、资源开启、无错误、样本在有效期内。
- sequence / timestamp_us / sample_age_ms：采样序号、启动以来微秒、采样年龄。
- ready：后台任务可以接收请求，不表示已经识别或成功读取硬件。
- error：ESP错误名称；麦克风另含codec_error驱动原始错误。

没有新鲜样本时媒体GET返回503；内存分配失败返回500；POST参数错误400；后台任务不可用503。enabled在关闭/清理失败时可能仍为true；必须结合requested_enabled、error、valid使用。致命读取错误停止采集，保留清理失败的资源句柄，等待明确POST重试，不重置共享I2C/供电，不因外设缺失关闭Wi-Fi或显示。

## 按键

观测板载AI（GPIO7）和BOOT（GPIO61）；通过BSP/button组件建立输入与回调，不增加页面切换、关机或刷机动作。上电时AI进入Vibe、BOOT进入ROM的行为不变。电源开关由硬件控制，不作为普通可读按钮提供。

buttons.ai / buttons.boot：available / error / pressed / held_ms / press_count。事件有 `seq/timestamp_us/button/event`，event为down/up/click/double_click/long_press。最近16条事件按时间顺序随REST/WS重复发送，客户端按seq去重；可保留两次10Hz推送之间的短按，长时间离线或16条缓冲溢出无法补回更旧事件。事件序号和按压次数重启归零。

```js
let last = 0;
const ws = new WebSocket(`ws://${location.hostname}:81/ws/sensors`);
ws.onmessage = ({data}) => {
  const {buttons, microphone, camera} = JSON.parse(data);
  for (const event of buttons.events) {
    if (event.seq > last) { console.log(event.button, event.event); last = event.seq; }
  }
  console.log(microphone.levels, camera);
};
// 设备重启/重新连接时重置last；客户端若需要检测丢失，比较首条seq与last+1。
```

## 麦克风

ES8311 ADC；48kHz、16bit、双I2S通道、30dB输入增益，20ms窗口。levels每通道有rms/peak（归一化0..1）、rms_dbfs（静音下限-120dBFS）、clipped_samples（该窗口达到PCM极值的数量）。不是校准的声压dB，也不是两枚物理麦克风；实际哪路有效需用户后续实机反馈。样本过期250ms/关闭/错误时valid=false，音量数字null。

WAV接口只提供最近20ms片段，header已含采样格式，响应另带X-Sample-Sequence、X-Timestamp-Us。轮询可跳过或重复片段，不能拼接成无损连续录音；没有实现PCM音频WS流或扬声器播放。初始化/读/关闭由同一个音频任务拥有，不在HTTP/显示任务调用codec，暂停不关共享供电。

## 摄像头

模块管理器探测左槽EEPROM，只有合法camera描述符才启动DVP；不启用allow_unidentified，不凭实拍外观指定OV3640或SC101IOT。Kconfig启用驱动已有的两种sensor配置；默认请求UYVY，尺寸由实际传感器默认配置决定。模块元数据含module_presence、camera_identified、board_type、hardware_version和discovery_error，属于模块管理器观测，camera_identified只表示描述符识别，不代表已经出帧。硬件可能尚未探测、缺失、描述符错误或采集失败，不能伪造存在状态。

采集元数据含width/height/bytes_per_line/frame_bytes/sensor_fps/capture_fps，后者为采集任务最近约一秒的完成窗口，不是网络交付帧率。原始帧上限2MiB；关闭或致命错误释放缓存与驱动资源，无法释放时保留句柄供显式重试。没有闪光灯操作。

GET /api/camera/frame返回 `application/octet-stream`，内容是UYVY `U0 Y0 V0 Y1`；按响应头X-Width、X-Height、X-Bytes-Per-Line处理行步长，X-Pixel-Format为UYVY，X-Sample-Sequence和X-Timestamp-Us属于这个帧本身，不需要另查状态配尺寸。过期500ms/驱动错误/关闭/未出首帧时503。帧不是JPEG，不能直接用作显示端/api/frame的输入；上位机须转换/压缩。

硬件帧复制到最新缓存后立即归还；网络下载再持有独立副本，不把驱动帧或状态锁留给慢客户端。不是连续视频流：连续GET可能得到同一帧，也可能跳过帧。帧下载与推图共用HTTP服务/Wi-Fi带宽，建议按需拉取，不承诺同时达到30FPS显示推流目标。

摄像头占用左侧DVP与GPIO33/34，保留独立ESP-Iris USB HS；不重新初始化共享I2C或重置供电。右侧空槽不伪造其他传感器。摄像头SDK开关与分区布局无关，保留完整Recovery集成和分区布局。

## 源码与构建状态

代码分成screen_io生命周期/状态，screen_buttons事件，screen_microphone音量/PCM，screen_camera识别/采集，screen_io_http控制与下载；显示任务不参与音视频采集。锁只保护快照/控制目标/缓冲复制，驱动等待和网络发送都在锁外。摄像头帧先归还再进行后续关闭操作；清理失败不遗失句柄。

板级API以固定BSP a2c985ad698b3f04a21c63e006b43e7e948bc1d7源码为依据。新增本地mosaico_module_camera0.2.0依赖及esp_video固定2.4.1；module_mgr由camera组件引入。当前没有运行组件管理器依赖解析，dependencies.lock仍代表上次构建；下次获授权编译时需要解析新增组件、更新并提交锁文件，并核对缓存sdkconfig的版本与摄像头开关。没有编译、测试、运行应用、刷机或实机采集，不能宣称已验证可用。
