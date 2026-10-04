# WebSocket管理面板（1.1.22）

用户要求管理页提供Postman式WS交互：固定URL、JSON、发送和响应历史三个区块。新增顶栏WS入口，同一页依次为连接栏、消息编辑栏、收发历史；HTTP入口保留。URL按当前设备地址自动生成且只读，通道可选传感器订阅或内容推送/控制，不需要手填地址。

连接开关开启即可连接，传感器通道自动发送订阅JSON。例子选择只填写编辑框，不自动执行控制/推送；手动点击发送或⌘Enter/Ctrl+Enter。历史↑表示浏览器已发出，↓才是设备消息；accepted是入队编号，不等于已显示或已读。可展开完整JSON、关闭接收记录、跟随滚动、清空和导出。历史限100条/256Ki字符，单条接收历史超过64Ki字符会截断；状态断开不清空历史。离开/隐藏页面暂停连接，返回按此前连接开关恢复；不自动重发推送。刷新页面清空本页历史。

## 设备协议

| 通道 | 消息 |
| --- | --- |
| `ws://IP:81/ws/sensors` | `subscribe` / `unsubscribe` / `get`，topic=sensors；`ping`。连接仍默认订阅10Hz完整传感器，兼容旧客户端。取消订阅只影响当前连接，get仍可读一次。命令≤512字节。 |
| `ws://IP/ws/frames` | 原二进制480×480 baseline JPEG及accepted回执保持不变；新增JSON `text` / `view` / `config` / `get` / `ping`，消息≤8192字节。 |

JSON可附request_id：最多64字符字符串或0..2^53−1整数，响应原样回显。网页缺省自动补web序号，完整发送历史包含实际发送的ID。响应为type=response、command、ok，以及request_id；错误含error，不会把本地发送成功当成设备接收成功。

示例订阅：

```json
{"type":"subscribe","topic":"sensors","request_id":"sub-1"}
```

传感器响应包含ok=true/subscribed=true，后续type=sensors/schema_version=2全量快照不变。取消订阅type=unsubscribe。Ping返回message=pong。

文字推送：

```json
{"type":"text","request_id":"text-1","text":"你好，WS消息","font_size":32,"align":"left","time":"20:00"}
```

正文≤1024 UTF-8字节、字号16..64、align=left/center/right、time可选HH:MM，与REST使用同一应用命令函数、历史/已读/自动切换机制。成功返回accepted编号/content_type=text。

其他推送通道JSON：

```json
{"type":"view","page":"camera","request_id":"view-1"}
```

view的page支持image/text/camera/settings；image可附历史id，text可附scroll_y/duration_ms，沿用REST规则。config接受auto_switch布尔，持久化同一NVS配置。get接受topic=status/sensors/orientation，结果在data中；ping返回pong。未知命令或参数错误返回ok=false；不提供任意REST转发或伪造麦克风/摄像头媒体流。

网页“发已准备图片”使用推送页转换后的JPEG，以二进制发送并记录真实回执；不在JSON中塞base64。收到的文字、订阅状态、传感器更新、错误和JPEG回执都进入同一个历史列表。

## 实现与交付范围

文字及切页应用逻辑抽出screen_commands.c，由HTTP与WS共用，保留HTTP响应和校验规则。主HTTP任务复用已有接收缓冲；传感器命令使用独立有界缓冲，订阅槽由遥测HTTP任务独占，握手重置复用fd的订阅状态。无分区/固件恢复契约变化。

本轮只编译、刷入与确认安装身份/版本，没有WS联调、自动推送、浏览器验证、测试代码或性能测量；效果由用户体验。源码提交03f1328，完整原始交付证据保留应用.codex-runs/ws-workbench-1.1.22/。

最终构建：固定ESP-IDF 7b9cc1ac79f865983f59bb8ff3ff43eb74ff1dbe，esp32s31；20261004-200757-build-15651成功，应用BIN 4,963,104字节，2条构建警告为依赖目录额外文件及保留factory分区小于正常应用。分区布局没有修改。原始日志保留应用.codex-runs/idf-low-noise-build/20261004-200757-build-15651/raw.log。

官方app-update完成，同一Device ID `4553502d4952495301001c2904d0ad2a`安装1.1.22，normal、lifecycle_state=2、stale=false、crash_count=0；新Boot ID `17377866210999254905`。operation `cfdae897-116b-481c-8881-86c23578af23` succeeded，healthy=true，设备ELF SHA256 `a6e374fad72cd5367932d37e6f2b27adef8c23aa929ce2ffc6f227a2c07373b4`。未做本轮WS或浏览器效果测试。
