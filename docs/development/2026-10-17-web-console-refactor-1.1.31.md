# Web 控制台信息架构与交互重构记录 (LAN Screen 1.1.31)

- 日期：2026-10-17
- 版本：LAN Screen 1.1.31
- 目标设备：ESP-Mosaico (`esp32s31`)
- 设备 ID：`4553502d4952495301001c2904d0ad2a`
- 固件模式：`normal`，`healthy`，`crash_count: 0`
- 联网 IP：`192.168.5.192`

---

## 交付背景

根据用户指令对随身屏 Web 管理控制台进行全面重构（"帮我refactor整个网页管理界面，我觉得管理逻辑不合理"）。
原界面存在以下核心交互与架构痛点：
1. **职能分散且重叠**：导航标签包括“设备与看板”、“AI 流水线”、“推送内容”、“摄像头色块”、“HTTP”、“WebSocket”等 6 个平铺项，层级混乱。
2. **设备内容历史深埋**：设备 RAM 内容历史（图片与文字历史）深埋在首屏折叠菜单底部，难以快速回溯。
3. **外设与硬件能力被边缘化**：多功能交互子板（6-LED 原生动效、环境光照、PIR 红外感应、NEC 红外遥控）挤在传感器面板下方的小折叠区域内，缺乏专有控制台。
4. **开发者工具割裂**：HTTP 调试、WebSocket 数据流调试与摄像头色块 Studio 分布在三个顶级菜单，挤占核心用户路径。

---

## 核心实现与架构改动

### 1. 五大清晰职能领域重组 (`api.html` / `console.js` / `console.css`)

将控制台重构为 5 个以任务与业务场景为核心的主导模块：

1. `🖥️ 实时大屏` (`#view`)：
   - 聚焦屏幕实时画面预览（约 2 FPS）、高清截图一键下载、画框占位与加载状态。
   - 设备屏幕主页集中切换（📊 看板 / 🤖 流水线 / 🖼️ 媒体 / 💬 消息 / 📷 镜头 / ⚙️ 设置）。
   - 设备状态概览 HUD（Wi-Fi、局域网 IP、电池电量、重力朝向、屏幕自动旋转角）。
   - 快速设置（收到新图片/文字自动切屏开关）。
   - 渲染性能与吞吐监控（FPS、接收/显示/丢弃计数、解码与 LCD DMA 耗时）。

2. `🤖 AI 流水线` (`#pipeline`)：
   - 多智能体看板监控与队列管理，支持动态流光扫射、状态流转与清空队列。
   - 新增 **快捷 Agent 模板选择器**（Antigravity 翡翠绿协同、Codex 天际蓝设计、Deploy 琥珀金交付），一键自动填充 ID/Title/Status/Progress/Color。
   - 新增 **原生 50Hz LED 动画预制光效快速触发器**（深呼吸 breathe、跑马灯 chase、彩虹 rainbow、警报 alert、成功 success、熄灭 off）。
   - 人机交互确认按钮（Human-in-the-Loop）触控回调响应与状态就地呈现。

3. `📨 内容与历史` (`#send`)：
   - 将此前深埋在首屏底部的设备 RAM 历史无缝集成到内容发送中心。
   - 图片推送：480x480 本地预览、剪贴板截图直接粘贴（⌘V）、拖拽上传、完整显示/居中裁剪、合规 JPEG 自动转换。
   - 文字卡片推送：16–64px 动态字号滑块、对齐方式、时间标记与排版实时预览。
   - 设备内存历史浏览器（图片历史 / 文字历史切页、未读绿点/已读灰勾标记、历史图片回看与一键“显示到设备屏幕”）。
   - 本会话发送记录回执流水。

4. `🎛️ 外设与传感器` (`#interact`)：
   - 独立设立硬件与传感器专属工作台。
   - **6-LED 原生 50Hz 动画控制台**：一键触发 breathe / chase / rainbow / alert / success / off 原生平滑动画，附带 6 颗圆形 LED 拟物灯带实时光效仿真。
   - 手动取色与亮度控制（6 颗常用色块快速选择、十六进制拾色器、单灯/全灯切换、0–64 级平滑亮度滑块）。
   - **交互子板 Sensor HUD**：环境光照度（带动态光强进度条）、人体红外 (PIR) 运动感应指示灯、物理按键状态徽章与输入模式（自动/机械/触控）。
   - **板载传感器矩阵**：六轴姿态 IMU（加速度、角速度、地磁强度）、按键/电池供电（电压、电流、电池温度）、板载麦克风电平指示表与 WAV 快照下载、摄像头原始 UYVY 下载。
   - NEC 红外发射器控制与传感器快照 JSON / WebSocket 数据导出。

5. `🛠️ 开发者工具` (`#devtools`)：
   - 整合高级开发者工具集，采用顶部 Segmented 分段控制器切换三大子面板：
     - **HTTP 接口调试器**：请求示例预设、REST 方法、自定义 Headers、Body、设备/Mock 双目标执行与响应面板。
     - **WebSocket 工作台**：传感器 10Hz 数据流订阅、控制/推送通道双向通信、JSON 示例、收发双向流水与 JSON 导出。
     - **摄像头色块 Studio**：256x256 色块网格渲染控制、目标 FPS（1–30）、合一网格像素配置（1px–64px）与实时 Canvas 预览。
   - 保持向下兼容：访问旧链接 `#try`、`#http`、`#ws`、`#camera`、`#sensors`、`#history` 时，由路由引擎自动映射至对应的顶级域并自动激活子面板。

### 2. 生命周期与资源调度优化 (`console-lifecycle.js` / `console-view.js`)

- `console-lifecycle.js` 扩展支持 `devtools`、`interact`、`send` 领域，自动按需挂载/卸载事件监听器、WebSocket 订阅与轮询任务。
- `console-view.js` 适配新架构：进入 `#send` 自动按需刷新设备历史；进入 `#interact` 自动挂载传感器订阅；进入 `#pipeline` 自动刷新多智能体状态。
- 摄像头预览在处于 `devtools` 的 `camera` 子面板时才激活帧捕获，避免后台页面空耗 PSRAM 资源。

---

## 编译与官方刷入验证

1. **固件编译与打包**：
   - 更新工程版本号至 `1.1.31`（`CMakeLists.txt`、`sdkconfig.defaults`、`build/sdkconfig`、`screen_ui.c`）。
   - 通过 `idf-low-noise-build` 成功编译，将全新 `api.html`、`console.css`、`console.js`、`console-view.js`、`console-lifecycle.js` 嵌入静态数据段。
   - 生成二进制 `lan_screen.bin (5027760 bytes)`，编译用时 30.8 秒，`exit_code: 0`。
2. **官方安装与状态检查**：
   - 通过 `python3 mosaico.py iris app-update --project projects/lan_screen --device-id 4553502d4952495301001c2904d0ad2a --skip-build` 完成刷写。
   - 官方设备状态验证输出：
     - `app_version`: `1.1.31`
     - `firmware_mode`: `normal`
     - `crash_count`: `0`
     - `stale`: `false`
3. **HTTP 接口与 HTML 校验**：
   - `GET /api/status` 实时响应：`{"app":"lan_screen","version":"1.1.31","ip":"192.168.5.192", ...}`。
   - `GET /` 验证返回 5 大职能导航：
     - `🖥️ 实时大屏` (`#view`)
     - `🤖 AI 流水线` (`#pipeline`)
     - `📨 内容与历史` (`#send`)
     - `🎛️ 外设与传感器` (`#interact`)
     - `🛠️ 开发者工具` (`#devtools`)
