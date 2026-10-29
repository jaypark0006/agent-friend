# 2026-10-29 随身屏网页控制台全量重设计与裁决闭环交付 (1.1.56)

## 交付概述

针对用户反馈「旧网页端丑、跟想象的不一样、不达标」的痛点，本轮完成了随身屏 Web 控制台（Web Console）自 1.1.0 以来最大规模的重构与设计闭环。彻底废弃此前蓝白通用后台模板与 28 KB `console-view.js` 巨石代码，全量对齐用户在 Claude 画布设计的「Agent 伴侣 UI」设计语言（墨色底、米白字、9×7 方块点阵表情、状态语义色）。同时在固件侧打通 `POST /api/widget/decide`，实现网页端裁决向 `/ws/hub` 反向事件总线的确定性毫秒级回传。

本版本固件版本号为 **1.1.56**，固件通过官方 ESP-IDF 6.2 编译，产物大小 11,950,281 字节（含 9.32 MB Flash 持久化字库），所有网页静态资源（14 个文件，170.7 KB）直接自包含嵌入固件，零 CDN、零外链字体，局域网即开即用。

---

## 一、核心变更对照与交付清单

| 模块 | 涉及文件 | 交付内容与架构说明 |
| :--- | :--- | :--- |
| **设计规范与样稿** | `docs/web-console-redesign.md`<br>`docs/design/web-console-mockup.html`<br>`docs/design/antigravity-review.md` | 输出全量设计系统规范、高保真交互样稿及 Antigravity 独立复审报告，对齐 1360px、800px、375px 响应式断点与墨/纸双主题。 |
| **固件裁决接口** | `main/screen_widget.c`<br>`main/screen_widget.h` | 新增 `POST /api/widget/decide` 原生路由；按 ID 精准触发裁决，返回所选按钮文本并以 `trigger: "web"` 广播 `task.action`；非待确认或已裁决卡片返回 HTTP 409 Conflict。 |
| **固件路由与缓存** | `main/screen_network.c`<br>`main/CMakeLists.txt` | 静态资源表从前缀匹配重构为完整 URI 映射表；所有网页资源注入 `Cache-Control: no-cache` 避免 OTA 后浏览器使用旧缓存；支持 `strcspn(uri, "?")` 忽略查询参数匹配。 |
| **外壳与路由** | `main/api.html`<br>`main/console.css`<br>`main/console.js` | 统一为此刻（`#now`）、推送（`#send`）、设备（`#device`）、开发者（`#dev`）4 主页与 14 个旧 Hash 别名平滑重定向；纯 CSS 变量驱动；实现手机端底部悬浮 TabBar。 |
| **点阵表情系统** | `main/console-face.js` | 9×7 方块点阵表情引擎；支持 6 种情绪与 13 种 Agent 专属工作中动画（`claude`, `codex`, `antigravity`, `hermes`, `pi`, `gemini`, `cursor`, `copilot`, `opencode`, `kiro`, `cline`, `goose`, `windsurf`）；单一 rAF 驱动，隐藏标签自动暂停。 |
| **此刻页（主卡与队列）** | `main/console-now.js` | 待确认主卡整屏橙色接管，直连 `POST /api/widget/decide`；工作中展示进度与耗时；列表区分待确认、工作中、可能中断（stale）、今天完成；随身屏画面取 BMP 并支持 600ms 实时节流预览与切页。 |
| **推送与设备预览** | `main/console-send.js`<br>`main/image-upload.js` | 文字推送实时 1024 字节校验与 480×480 等比消息预览；任意位置 ⌘V 粘贴自动转为图片上传；浏览器内直出 480×480 Baseline JPEG；串行拉取画面缩略图。 |
| **设备控制中心** | `main/console-device.js` | 磁贴同步控制中心开关（自动跳转、灯光提示、画面角标）；副板 6 颗独立 RGB LED 实时着色与预制动效；10Hz 传感器 WebSocket 流与三轴加速度/电池/按键实时渲染。 |
| **开发者工作台** | `main/console-dev.js`<br>`main/console-http.js`<br>`main/console-ws.js`<br>`main/console-camera.js` | 模拟 Agent 注入器；HTTP 调试器（语法着色与 Mock）；WebSocket 工作台（事件中枢 /ws/hub 默认且高亮反向事件）；256×256 镜头色块实时调试。 |

---

## 二、架构质量与安全规范验证

1. **防 XSS 注入**：所有动态字符（标题、状态、消息正文、错误日志、设备名称）100% 采用 DOM `textContent`，全项目零 `innerHTML` 拼接。
2. **零行内样式**：`api.html` 剥除全部 150+ 处旧行内样式；动态参数（进度 `--v`、颜色 `--c`、轴向偏移 `--p`、视口缩放 `--s`）全部严格通过 CSS 变量挂载。
3. **资源节制**：
   - 全局网络请求池严格限制同一时刻设备并发请求 ≤ 2；
   - 画面历史缩略图采用严格串行加载；
   - `visibilitychange` 隐藏标签页时立刻停止所有定时轮询与 WebSocket 监听，并在页面切换时释放 Blob `objectURL`。
4. **编译与尺寸闭环**：
   - 网页资源总计 170,696 字节，严格处于 200 KB 固件预算红线以内；
   - ESP-IDF 6.2 编译输出 11,950,281 字节，固件工程描述版本号准确报告为 1.1.56。
