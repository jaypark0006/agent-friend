# 交互子板与统一传感器接口

2026-10-04：按用户当次授权编译、刷机、重启并检查实机。最终安装 LAN Screen **1.1.15**，地址 **192.168.5.61**。此前1.1.8–1.1.13的消息设置、动画、粘贴截图、已读修复、音视频接口和新网页控制台一起安装；没有新增测试文件或运行单元测试、模拟器、性能基准。

## 硬件与入口

依据[官方交互子板指南](https://docs.espressif.com/projects/esp-dev-kits/zh_CN/latest/esp32s31/esp-mosaico/user_guide_interact.html)和固定 BSP `a2c985ad698b3f04a21c63e006b43e7e948bc1d7` 的 `mosaico_module_interact` 驱动。

实机 EEPROM：左槽摄像头 `board_type=7`，右槽交互子板 `board_type=22 (0x16)`，两者描述符 `hardware_version=258 (0x0102)`；这是描述符记录，不等于已检查每块PCB丝印。支持左右槽自动探测，不将缺失或其他板型当作交互子板启动。

网页：[控制台](http://192.168.5.61/) → 查看设备 → 传感器与采集 → 多功能交互子板。插槽可选；实时读数、RGB灯、红外、模式与停用控制均已提供，操作区默认折叠。HTTP Try新增四组真实请求与明确标注的本地Mock模板，选择示例不会执行。

| 硬件 | 查询/控制 | 数据与限制 |
|---|---|---|
| GL5506光敏电阻 | GET /api/interact | light_raw原始ADC、light_level相对明暗0–100，不是lux |
| AS312 PIR | GET /api/interact | motion_detected运动检测电平，不保证静止人体存在 |
| 两路按键/触摸焊盘 | GET /api/interact、POST /api/interact/config | 左右触发、按压累计数、按住毫秒数、最近16条边沿事件；机械/电容共用两路引脚，不能分别识别触摸和机械来源 |
| 六颗WS2812 | POST /api/interact/leds | 全部、单颗、六颗独立RGB，brightness0–64 |
| 红外发射管 | POST /api/interact/ir | 一次NEC命令，38kHz、8bit地址/命令；没有红外接收器 |
| EEPROM/驱动状态 | GET /api/interact | 插槽、板型、模式、初始化、采样有效性、错误和控制执行结果 |

按键left/right指子板自身标记；右槽安装相对左槽旋转180°，不将名称解释成当前屏幕坐标的左右。LED索引0–5使用BSP顺序，顶部四颗为0–3，另外两颗在按键下方。

## REST

HTTP端口80，POST使用 `Content-Type: application/json`。光敏、PIR、两路输入位于 `/api/interact` 的 `slots.left/right`；同一个对象也在 `/api/sensors` 和统一WS的 `interact` 中。

```http
GET /api/interact

POST /api/interact/leds
{"slot":"right","color":[0,80,255],"brightness":32}

POST /api/interact/leds
{"slot":"right","index":2,"color":[255,80,0]}

POST /api/interact/leds
{"slot":"right","colors":[[255,0,0],[0,255,0],[0,0,255],[255,80,0],[0,0,0],[0,0,0]],"brightness":24}

POST /api/interact/leds
{"slot":"right","brightness":16}

POST /api/interact/leds
{"slot":"right","color":[0,0,0]}

POST /api/interact/ir
{"slot":"right","address":0,"command":0}

POST /api/interact/config
{"slot":"right","enabled":true,"input_mode":"key"}

POST /api/interact/config
{"slot":"right","enabled":false}
```

RGB分量0–255；index0–5，仅和color搭配；color与colors二选一，colors必须六组。brightness可单独修改，发送值按brightness/255缩放，保守限制最大64；led_colors返回未缩放的设定值。颜色与亮度在工作线程按队列顺序合成，单灯设置不会覆盖此前已处理的其他灯。初始六灯熄灭、brightness32。

input_mode支持 `key`、`touch`、`auto`。开机默认key；BSP的auto优先touch，失败才退回GPIO。切换时关闭并重建该插槽驱动，不重置共享I2C或供电；所有子板设置只在本次开机有效。此次自动触摸模式出现右输入反复跳变，机械模式观测为稳定松开；未将触摸跳变认定为用户真实按压，也未声称触摸已校准。

控制响应HTTP202：`{"accepted":1,"status":"queued"}`。它表示已排队，**不表示操作成功**。随后读REST或WS中的 `interact.results`，按 `id` 匹配，确认 `error="ESP_OK"`；结果含slot、operation，保留最近16项。队列容量8，满时429；非初始化插槽的灯/红外503；未知字段、重复字段、格式/范围错误400；JSON上限512B。

config结果表示目标设置已处理、旧驱动已关闭；重新探测/初始化异步发生，继续观察requested_input_mode/input_mode/initialized/error。LED/IR命令绑定收到请求时的session，插槽驱动被替换后旧命令失败，不误发给新会话。

各槽字段：

- presence/identified/board_type/hardware_version：实际模块观测；initialized表示驱动可操作，enabled是请求的启用目标。
- valid：已初始化、读取无错、样本年龄小于250ms；无有效样本时输入数字/布尔值为null，不能把缺失理解成零或松开。
- sequence/timestamp_us/sample_age_ms：输入采样序号、启动以来微秒、年龄；正常后台约20ms采样，发现周期约500ms。
- left/right_pressed、left/right_press_count、left/right_held_ms：当前输入和累计统计；计数重启归零，模式重建可能改变基线。
- events：每槽最近16条输入变化，按时间排序，字段seq/timestamp_us/input/active，input为left/right/pir；10Hz推送间的短变化可以从事件环读到，但溢出更旧记录无法补回。
- led_colors/led_brightness、ir_sent、output_error：已成功应用的灯光值、成功提交的IR次数和最近控制错误；不是光学测量或红外接收确认。

## 一个统一WS

```
ws://192.168.5.61:81/ws/sensors
```

连接后自动约10Hz推送完整JSON快照，无需订阅消息。`GET /api/sensors` 为同结构REST快照。顶层 `type="sensors"`、`schema_version=2`；保留旧字段，增加交互子板。

包含加速度、角速度、磁场、电池、重力姿态、板载AI/BOOT按钮、麦克风音量和状态、摄像头状态与元数据、两侧交互子板及控制结果。各传感器用自己的采样时间，10Hz网络发送不意味着同步采样。WS没有提供控制指令、连续PCM或摄像头媒体流：控制通过REST，音视频字节按需获取快照。

```js
const ws = new WebSocket('ws://192.168.5.61:81/ws/sensors');
let previousTime = 0;
let lastInputEvent = 0;
ws.onmessage = ({data}) => {
  const sensors = JSON.parse(data);
  if (sensors.type !== 'sensors') return;
  // 时间倒退意味着新一次启动；断线重连但未重启时保留去重序号。
  if (sensors.timestamp_us < previousTime) lastInputEvent = 0;
  previousTime = sensors.timestamp_us;
  const board = sensors.interact.slots.right;
  if (board.valid) console.log(board.light_level, board.motion_detected);
  for (const event of board.events) {
    if (event.seq > lastInputEvent) {
      console.log(event.input, event.active);
      lastInputEvent = event.seq;
    }
  }
  console.log(sensors.orientation, sensors.microphone, sensors.camera);
};
```

重连首次也可能携带旧事件，可根据用途只接收连接后的事件；seq重启清零，两槽各自去重。不要用每次快照重复出现的results/events触发重复控制。

Python客户端 `projects/lan_screen/client/mosaico_screen.py` 提供 `interact()`、`control_interact()` 和已有统一 `sensors()`，传感器WS接收上限增至16KiB。

## 摄像头与内存修复

图片历史仍最多16张，但改为收到图片时按实际JPEG长度分配，释放了空历史预占的4MiB。内存不足时不加入该次历史，实时帧队列继续处理；历史不持久化。

本机实际摄像头1280×720 UYVY，原始帧1,843,200B、行步长2560。1.1.14采集正常但下载另复制整帧时HTTP500；1.1.15将最新缓存的所有权交给HTTP响应，不再额外分配整帧。发送期间该缓冲区只读，采集任务继续归还/丢弃新驱动帧；状态snapshot_in_progress=true、valid=false，发送完成后恢复缓存并采新帧。关闭/重新开启期间不提前释放HTTP拥有的缓冲区，也不在网络等待时持有状态锁或驱动帧。

GET /api/camera/frame返回原始UYVY而不是JPEG；参数来自该响应的X-Width/X-Height/X-Bytes-Per-Line/X-Pixel-Format。驱动bytesperline=0时，仅在缓冲长度与紧密UYVY尺寸严格一致的情况下补足width×2。不承诺摄像头连续视频速率。麦克风仍是最新20ms、48kHz、PCM16双通道WAV，不是连续录音。

## 实机记录

见[完整记录](2026-10-04-interact-validation.json)，其中区分1.1.14首次检查和最终1.1.15检查。

- 官方app-update安装成功，最终设备ID `4553502d4952495301001c2904d0ad2a`，normal/healthy，Boot ID `4153831802261709925`，crash_count=0，stale=false；Wi-Fi和保留Recovery分区未改。
- 右槽交互子板初始化/读取ESP_OK、valid=true；最终读到光敏约21–22/100、PIR=false、两路机械输入松开。没有实际人体移动/按压的用户确认，不能据此验收感应距离、真实触摸和按键手感。
- 1.1.14全灯、单灯与IR命令都得到ESP_OK；最终1.1.15单灯及全熄灭也得到ESP_OK。IR只确认驱动成功发射，不确认外部电器收到；灯光只核对命令结果与驱动状态，未进行光学验证。
- 1.1.14统一WS连续20条包含完整字段，1.1.15再收到6条，右槽采样序号继续增长；最终默认key，事件计数0，不再出现此前touch跳变。
- 麦克风取得真实非零音量和3,884B WAV。最终摄像头GET帧HTTP200、1,843,200B、参数正确，下载后序号2→5、valid恢复true；两类采集结束已关闭，灯光已熄灭。
- 新网页已在现有浏览器重新加载，确认首页双入口及查看页右槽实时卡片、折叠控制区；未执行Mock自动请求、图片/文字发送或手势效果验收。
- 初期磁场0曾返回-32768三轴值，后续恢复普通数值；本轮未做磁场校准，不能把全部板载传感器都宣称已完整验收。后续WS/REST还记录到PIR触发与释放事件，未测感应距离/误报率。

最终构建 `20261004-103841-build-74359`，二进制4,911,680B，ESP-IDF精确固定7b9cc1a，完整分区表未变化；factory大小警告对应保留Recovery，应用写入既有ota_0且安装兼容校验通过。其他警告为组件目录/依赖可见性提示，无编译错误。没有新增测试或公开推送Git。
