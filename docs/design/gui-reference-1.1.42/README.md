# Mosaico GUI 重设计参考包

整理日期：2026-10-25（Asia/Shanghai）。对象是这台设备上自行开发的 **LAN Screen 1.1.42**，不是 ESP-Mosaico 出厂 GUI。

固件源码基线：`ad98f5b022073ec5f6fb8d74b366816a51ff11b3`。设备通过官方 Iris 截图命令返回版本 `1.1.42`，与此基线版本一致。

## 给 Claude 的使用顺序

1. 先读 [CLAUDE_PROMPT.md](CLAUDE_PROMPT.md)，可以直接复制其中的任务描述。
2. 看 [截图参考总览](screens-overview.svg)，再看 `screenshots/` 原尺寸图片。**最新截图、历史设备截图、历史模拟器图片已分别标注；不能当作同一版本。**
3. 用下面的页面清单理解当前功能；布局细节以 `source/device/` 中的 1.1.42 源码快照为准。
4. 优先重设计 Dashboard、Pipeline、Messages、Control Center；随后补齐媒体、摄像头、配网和所有空状态。

## 当前典型界面

| 优先级 | 界面 | 当前内容与交互 | 源码入口 |
| --- | --- | --- | --- |
| P0 | **Dashboard／设备总览** | 在线状态、局域网 IP 与 Wi-Fi、供电/温度、姿态与子板、固件信息；控制中心入口 | `source/device/screen_ui.c` → `screen_ui_status_build` |
| P0 | **Pipeline／任务流水线** | 顶部任务统计；纵向任务卡片列表；标题、进度或状态、当前步骤；进行中与已完成历史；待确认卡片 | `source/device/screen_widget.c` → `screen_ui_widget_build`、`build_agent_card` |
| P0 | **Pipeline／待确认** | 同一任务卡片增高，显示 `[L] Approve` / `[R] Cancel`；触屏及交互副板左右实体键均可裁决 | `source/device/screen_widget.c` → `update_agent_card`、`screen_widget_trigger_action` |
| P0 | **Messages／消息列表** | 时间、正文、未读绿点/已读灰勾、未读总数；长消息纵向滚动；字号 16–64px、三种对齐 | `source/device/screen_ui_messages.c` |
| P0 | **Control Center／控制中心** | 亮度滑杆、图片与消息的自动切换开关、休眠说明；Wi-Fi、子板 LED、API Guide、重启入口 | `source/device/screen_ui.c` → `screen_ui_settings_build` |
| P1 | **Media／媒体空状态** | 等待图片/推流、发送入口提示、控制中心入口；本包包含当前 1.1.42 真机截图 | `source/device/screen_ui.c` → `screen_ui_home_empty_build` |
| P1 | **Media／显示图片与历史** | 图片全屏 480×480；上下浏览历史；可选时间/历史序号、已读标记、消息未读角标；支持关闭叠加元素 | `source/device/screen_renderer.c` → `image_caption`、`screen_renderer_badge` |
| P1 | **Camera／本地摄像头** | 进入申请页面采集，离开停止页面采集；独立原始采集请求可继续运行；处理画面与页面状态遵守现有安装旋转/镜像校正 | `source/device/screen_ui.c`、`screen_pages.c`、`screen_camera_service.c` |
| P1 | **Wi-Fi／网络列表** | Back、Scan、状态提示、可滚动 SSID 列表；点击进入密码页 | `source/device/screen_ui.c` → `PAGE_WIFI` |
| P1 | **Join network／密码输入** | 所选 SSID、密码输入框、Join、Cancel、英文软键盘 | `source/device/screen_ui.c` → `PAGE_PASSWORD` |
| P2 | **API Guide／开发信息** | 设备地址与常用 REST 接口提示；Metrics、Sensors 也有保留的诊断页面代码，现有控制中心未直接提供这两项按钮 | `source/device/screen_ui.c` → `PAGE_API`、`PAGE_METRICS`、默认传感器分支 |

### 导航与关键状态

- 五个顶层页面顺序是 **Dashboard → Pipeline → Media → Messages → Camera**，左右滑动循环；顶栏五个圆点支持点击跳页。媒体正在全屏显示图片时走独立像素渲染，不应假定所有顶栏元素都会叠加在图片上。
- 顶边下拉进入设置；设置及子页面有返回按钮和底边上滑返回。源码中的不同返回路径不完全一致，重设计应明确“返回上一页”规则，待用户确认后再实施。
- Pipeline 普通卡片为 `444×84px`，待确认卡片为 `444×116px`；列表区域为 `448×414px`；按当前源码记录，不要求新方案照抄。
- 顶部有常驻电量状态：充电、放电、低电量、暂不可用。不要只靠颜色区分状态。
- Dashboard、Media 空状态和 Pipeline 底部具有 `80×4px` Home Indicator。其他页面仍有文字返回提示，尚未形成统一导航样式。
- 消息与图片独立保留 RAM 历史；图片最多 16 张且总预算 1MiB，消息最多 32 条；重启清空。消息正文静止可见约 1 秒后可标已读。
- 自动切换为持久设置；新内容不应打断设置操作或用户拖动。Pipeline 浏览历史时不应被新进度强行拉走。
- 考虑空队列、多任务、已完成历史、长中文标题、无百分比、待确认、操作结束、无网络、低电量、摄像头启动/不可用等状态。

## 图片来源与使用边界

| 文件 | 来源与时间 | 能说明什么 |
| --- | --- | --- |
| `screenshots/01-media-empty-current-1.1.42.png` | **本次 1.1.42 设备原始截图**；官方 `mosaico.py iris screenshot` | 当前媒体空状态、配色、顶栏电量/页点、底部控制中心与 Home Indicator；截图刚启动时 IP 显示 `0.0.0.0`，不应据此设计固定内容 |
| `screenshots/02-messages-device-historical.png` | 2026-10-04 功能页记录，1.1.18 交付阶段的真实设备截图 | 消息卡片与字体观感；缺少后来新增的顶栏电量与页点 |
| `screenshots/03-media-device-historical.png` | 同上 | 历史图片页的内容占屏与叠加标记，不代表全部当前样式 |
| `screenshots/04-camera-device-historical.png` | 同上 | 历史摄像头画面；其后已修改旋转/镜像和导航，不能当作当前完整界面 |
| `screenshots/05-wifi-simulator-historical.png` | 仓库已有的旧模拟器产物，本次未运行模拟器；精确固件版本未确认 | 网络列表结构；蓝色按钮不代表 1.1.42 配色 |
| `screenshots/06-keyboard-simulator-historical.png` | 同上 | 小屏英文键盘与密码页结构 |
| `screenshots/07-settings-simulator-obsolete.png` | 同上，**布局已过时** | 只作为旧版问题对照；当前控制中心已包含亮度、自动切换及硬件工具，应以源码为准 |

本次只采集到一张最新设备画面，**没有得到 1.1.42 的完整逐页截图**。随后 LAN 读取超时，没有为取图重启、刷机或启动摄像头。没有运行模拟器、浏览器自动验证、功能测试或性能测试；旧图只读取仓库已有文件。

设备截图库证据：Device ID `4553502d4952495301001c2904d0ad2a`；截图 Boot ID `11792535779495099431`；操作 ID `731caa4c-17a8-4169-84f5-3901135638a2`；原图为 480×480 PNG。

## 实现与设计约束

- 设备屏幕为 480×480 触摸屏，现有设备 GUI 使用 **C + LVGL**，不是网页。控制中心和任务列表应围绕小屏快速扫读与手指操作设计。
- 中文字形和缓存资源受限；现有主 UI 常用 Montserrat 14/20/28px，中文回退到内置 16px 字形，消息有独立字号缓存。不要只换一个桌面系统字体就宣称方案可落地。
- 优先使用容器、纯色、简单图标和有限局部动效；避免昂贵模糊、全屏半透明叠层和持续重建卡片。拖动与滚动时应保持动效静默原则。
- 保留任务卡片就地更新、滚动位置记忆、实时传感器及实体键语义。30 FPS 是目标，不能把旧截图、文案中的 `Healthy` 或帧率标签当作本次验收证据。
- 设备原有 `Subboard: Detected`、`8MB PSRAM (Healthy)` 等部分文案是硬编码展示。重设计时建议改为真实状态或中性描述，不把它们当作已核实硬件参数。
- 现有暗底大致为 `#101720`，卡片为 `#141d27` / `#182433`，绿色 `#39e69d`、蓝色 `#4fa3e3`、琥珀色 `#e5c07b`、主文字 `#f0f4fa`。这些是现状，不要求沿用。

## Web 控制台：单独的一套界面

如还要重设计电脑端，`source/web/` 收录当前 HTML/CSS/JS 静态快照。本包没有把旧网页截图冒充 1.1.42。

当前五个工作区：**实时大屏、AI 流水线、内容与历史、外设与传感器、开发者工具**。1.1.42 加入暗色模式与折叠任务注入表单。设备 GUI 与 Web 可共享色彩和状态语义，但需分别输出 480×480 触屏方案与桌面响应式方案。

`source/` 是只读参考快照，不是可以独立编译的工程，不包含 Wi-Fi 密码、设备缓存、构建产物或完整字库。
