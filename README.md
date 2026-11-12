# Agent Friend · Mosaico 桌面智能体随身伴侣

Agent Friend 是一款专为开发者与 AI 智能体设计的物理桌面伴侣终端。它通过一块 480×480 高清触控彩屏与实体交互按键，将 AI 助手的任务进度、关键决策人机审批、双向收件箱及多智能体协作黑板带到现实桌面。

当前物理设备运行版本为 **1.1.61**（官方通道刷入 normal/healthy，详见[交付记录](docs/development/2026-11-12-fix-home-black-and-readme-1.1.61.md)）。

---

## 核心亮点

- **高清触控与原生排版**：480×480 CO5300 触控彩屏，内置 7,318 汉字与假名点阵字库（Noto Sans SC 20/24/32px 原生点阵，SPI Flash 存储与动态 LRU 缓存），排版清晰跟手。
- **6 颗高亮 RGB 情绪光环**：50Hz 原生硬件动效，实时呈现工作流水、推理呼吸、成功庆祝与警示双闪等动态光效。
- **板载零安装标准 HTTP MCP**：固件内置原生 Streamable HTTP 端点（`http://mosaico.local/mcp`），主流 AI 客户端免装环境秒级直连。
- **多智能体物理共享黑板（Shared Blackboard）**：支持跨智能体异步发布与订阅（`board_post` / `board_read`），多 Agent 无缝协作。
- **人机在环物理裁决**：屏幕触控与副板实体按键（L / R）双模裁决，告别网页来回切换；机身橙色按键支持一键星标收藏与唤醒。
- **全双工 WebSocket 事件总线**：毫秒级反向事件推送，裁决动作、切页与姿态变化即时直达。

---

## 开机即用（浏览器控制台）

将设备接入局域网 Wi-Fi 后，在同网络电脑或手机的浏览器中打开：

👉 **[http://mosaico.local/](http://mosaico.local/)**（或访问设备顶栏显示的局域网 IP）

| 控制台入口 | 主要功能 |
| --- | --- |
| **此刻 (`#now`)** | 聚焦当前最重要任务、待审批主卡、任务列表与屏幕实时镜像 |
| **推送 (`#send`)** | 发送高排印文字信笺、双向收件箱留言、查看黑板回复与回执、拖拽图片 |
| **设备 (`#device`)** | 控制开关、6 颗 RGB 情绪灯光工作台、设备网络状态与折叠硬件诊断抽屉 |
| **开发者 (`#dev`)** | REST API 测试台、WebSocket 实时总线、模拟智能体工作流 |

完整交互与界面说明请参阅 **[使用指南](docs/user-guide.md)**。

---

## 让 AI 助手接入

### 方式一：板载原生 HTTP MCP 直连（推荐，零安装）

任何支持 Streamable HTTP MCP 的客户端（如 Claude Code、Cursor、Antigravity、Dify 等），均可直接填入设备的本地端点进行配置：

```json
{
  "mcpServers": {
    "mosaico": {
      "url": "http://mosaico.local/mcp"
    }
  }
}
```

内置丰富工具与资源：
- **消息与收件箱**：`send_message`（投递富文本信笺与快捷回信胶囊）、`read_inbox_and_receipts`（读取人类回信与已读状态）；
- **人机在环裁决**：`ask_human_decision`（触发整屏待确认态，等待人类实体键或触屏审批）；
- **多智能体黑板**：`board_post`（在物理共享黑板发布结构化便签）、`board_read`（读取黑板内容）；
- **智能体座席与画布**：`update_agent_seat`（注册 Agent 点阵面孔与任务状态）、`push_canvas`（投送 480×480 图片画布）。

*注：若你的客户端仅支持本地标准输入输出（`stdio`）通道或需要长连接阻塞监听，请参阅可选桥接模块文档 [`mcp/README.md`](mcp/README.md)。*

### 方式二：一句话自描述接入（`/skills`）

向你的 AI 助手发送以下提示词（若未配置 mDNS，可将 `mosaico.local` 替换为设备屏幕顶栏 IP）：

> 请读取 `http://mosaico.local/skills` 并连接我的桌面随身屏。在每个新任务中上报进度；需要我决策或审批时，使用待确认卡片并在随身屏呈现选项，等待我通过实体按键或屏幕触控裁决。

---

## 设备交互指南

- **主界面滑动手势**：四主页水平滑动切换，依次为：
  `此刻`（Now） ⇄ `任务`（Tasks） ⇄ `消息`（Messages） ⇄ `画面`（Canvas）
- **控制中心**：从屏幕顶部边缘往下滑动，呼出全屏控制抽屉，可调节背光亮度、查看 Wi-Fi 信号及进入相机模式。
- **实体左右按键（L / R）**：在待确认任务时分别对应「批准 / 取消」；在消息界面对应便签底部的两个快捷回复胶囊。
- **侧边橙色按键**：短按为当前浏览的消息打上星标收藏（`★`），或在屏幕休眠时即刻唤醒。

---

## 硬件规格

- **核心主控**：ESP-Mosaico 架构芯片（`esp32s31`），集成高主频双核处理器与硬件加密引擎。
- **显示模组**：480×480 CO5300 触控显示屏，支持全视角高刷新率渲染与硬件 DMA 传输。
- **存储配置**：板载 16MB Flash 与高速 PSRAM。
- **交互外设**：6 颗高亮 RGB LED 氛围灯珠、左右双物理按键、侧边按键、红外避障与体感姿态传感器。
- **网络连接**：2.4GHz Wi-Fi 与低功耗蓝牙，原生支持 mDNS 域名解析与 SSDP 服务发现。

---

## 固件升级与二次开发

- **固件升级**：普通用户可直接从 [GitHub Releases](https://github.com/jaypark0006/agent-friend/releases) 或仓库 `dist/` 目录下载打包好的最新固件二进制文件进行更新。
- **二次开发**：固件源码、系统分区表、编译工具链及底层调试流程请参考 **[开发指南](vendor/esp-mosaico-vibe/projects/lan_screen/docs/development.md)** 与 **[贡献指南](CONTRIBUTING.md)**。

---

## 文档索引

- **[使用指南](docs/user-guide.md)**：日常功能使用与界面操作详解。
- **[本地 MCP 模块说明](mcp/README.md)**：本地桥接工具与多智能体实战示例。
- **[当前功能与交付状态](vendor/esp-mosaico-vibe/projects/lan_screen/docs/current-state.md)**：实机运行版本与功能演进记录。
- **[REST 与 WebSocket API](vendor/esp-mosaico-vibe/projects/lan_screen/docs/api.md)**：设备网络协议完整规范。
- **[硬件设计参考](docs/esp-mosaico-reference.md)** 与 **[外壳 3D 模型](hardware/)**：结构尺寸与 3D 打印模型。
- **[贡献指南](CONTRIBUTING.md)**：项目规范与代码贡献说明。

---

## 开源许可

本项目源码采用 [MIT License](LICENSE) 许可协议。第三方依赖组件遵循各自开源协议，字体资产遵循 SIL Open Font License 1.1。
