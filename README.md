# Agent Friend · Mosaico 随身屏

Agent Friend 把 AI 助手的任务进度、消息和确认请求放到桌面上的 480×480 触摸屏。你可以在屏幕、交互副板左右按键或网页控制台上处理确认，也可以直接推送文字和图片。

当前设备上机安装版本为 **1.1.59**（2026-11-12，官方 `iris app-update` 刷入 normal/healthy，见[交付记录](docs/development/2026-11-12-mcp-blackboard-1.1.59.md)）；提供本地标准 MCP Server `mcp/`、板载无状态 `POST /mcp`、mDNS `mosaico.local`、物理共享黑板与双向消息收件箱，已完成真机端到端联调全绿验证。

## 开始使用

已经装好固件的设备，接入 Wi-Fi 后即可使用。让电脑或手机连接同一局域网，在浏览器打开设备 IP 或 `http://mosaico.local/`。

本机设备当前入口：**[打开网页控制台](http://192.168.5.42/)**（`http://mosaico.local/`）。IP 变化时，在设备顶栏或下拉控制中心的设备信息中查看新地址。

| 入口 | 用途 |
| --- | --- |
| 此刻 | 看正在做的事、任务列表、待确认请求和随身屏画面 |
| 推送 | 发文字或收件箱留言、查看黑板回复与已读回执、粘贴或选择图片 |
| 设备 | 调整自动跳转、灯光提示、画面角标，控制灯光及查看传感器 |
| 开发者 | HTTP、WebSocket、镜头色块和模拟 Agent 工具 |

完整操作见[使用指南](docs/user-guide.md)。

## 让 AI 助手接入

### 方式一：标准 MCP 极速接入（推荐）

支持 MCP 的客户端（Claude Desktop / Claude Code / Cursor / Codex / Antigravity 等）可通过标准 `stdio` 接入仓库内的零外部依赖 [Python MCP Server](mcp/README.md)（自动通过 mDNS `mosaico.local` 与 SSDP 发现局域网设备，也可设 `MOSAICO_HOST=<设备IP>`）：

```json
{
  "mcpServers": {
    "mosaico": {
      "command": "uvx",
      "args": ["--from", "./mcp", "mosaico-mcp"]
    }
  }
}
```

无 `uvx` 环境可直接将 `command` 设为 `"python3"`、`args` 设为 `["-m", "mosaico_mcp"]`（配合 `PYTHONPATH=./mcp`）。此外，1.1.59 固件内置无状态 Streamable HTTP 端点 `POST http://mosaico.local/mcp`（或 `http://<设备IP>/mcp`），支持远程 HTTP MCP 客户端零安装直连。

提供 8 个标准工具（`send_message`、`ask_human_decision`、`update_agent_seat`、`push_canvas`、`read_inbox_and_receipts`、`board_post`、`board_read`、`board_wait`）与 4 个资源（`mosaico://board`、`mosaico://inbox`、`mosaico://receipts`、`mosaico://status`），支持多 Agent 零轮询共享物理黑板协作与人机双向收件箱。

### 方式二：设备自描述 `/skills` 接入

把下面这段话交给你使用的 AI 助手，并按设备当前地址替换 IP：

> 请读取 http://192.168.5.42/skills 并按其中的协议连接我的 Agent Friend 随身屏。每个新任务使用独立 ID，持续更新同一任务的进度，分别填写 agent、session、title；任务结束标记 done。需要我决定时先建立 WebSocket 监听，再发送待确认任务，并根据实际批准或取消事件继续。不要把超时当作批准。

设备自身提供协议说明，能调用局域网 HTTP / WebSocket 的助手可直接接入。仓库也提供可选的 [Python 通知脚本](skills/mosaico-notify/)；日常使用无需安装 ESP-IDF 或恢复固件源码。

## 设备操作与双向收件箱

- 左右滑动在「此刻 → 任务 → 消息 → 画面」四个主页面间切换，不循环。
- 顶部下拉打开控制中心，调整亮度、Wi-Fi 和设备设置，或进入镜头。
- 待确认或待回看时，按屏上选项、交互副板 L/R 键或网页控制台决定；Agent 必须收到对应任务的事件才能继续。
- **双向消息收件箱与物理黑板**：在网页控制台「推送」页开启「投递到 Agent 收件箱」可向 Agent 发送留言并预设左右快捷回复词；在随身屏「消息」页浏览便签满 1 秒自动回传已读回执（`read: true`），按副板 L/R 键可一键回复便签，短按机身橙色 AI 键可标星收藏（`★`），多 Agent 可通过共享黑板游标（`seq`）实时接力。
- 任务、图片和消息历史在 RAM 中，重启后清空；Wi-Fi 和已保存的配置保留。

硬件基于 **ESP-Mosaico / ESP32-S31**、480×480 CO5300 触摸屏；交互副板提供左右输入和 6 颗 RGB LED。摄像头为可选模块。不能将本项目作为 ESP32-S3 通用固件使用。

## 固件开发与安装

仅在开发或给另一台设备安装时需要恢复源码：

```sh
git clone https://github.com/jaypark0006/agent-friend.git
cd agent-friend
python3 scripts/restore-firmware.py
```

目标为 `esp32s31`，ESP-IDF 固定提交为 `7b9cc1ac79f865983f59bb8ff3ff43eb74ff1dbe`。编译、依赖和安装步骤见[开发与交付](vendor/esp-mosaico-vibe/projects/lan_screen/docs/development.md)。设备写入统一使用 `python3 mosaico.py`：相同完整分区布局的应用更新使用 `iris app-update`；首次安装、新布局或外部资源变更按官方 `recover` / `iris system-update` 流程执行。

导出当前构建产物和校验和：

```sh
python3 scripts/export-release.py
```

导出包保存在 `dist/release-v<版本>/`。本次本地导出不等于已经发布到 GitHub Releases。

## 文档与源码

- [使用指南](docs/user-guide.md)
- [标准 MCP Server 说明与多 Agent 示例](mcp/README.md)
- [当前功能与安装状态](vendor/esp-mosaico-vibe/projects/lan_screen/docs/current-state.md)
- [REST / WebSocket 接口](vendor/esp-mosaico-vibe/projects/lan_screen/docs/api.md)
- [1.1.58 人工验收清单](vendor/esp-mosaico-vibe/projects/lan_screen/docs/acceptance-1.1.58.md)
- [应用文档索引](vendor/esp-mosaico-vibe/projects/lan_screen/docs/README.md)
- [硬件参考](docs/esp-mosaico-reference.md)与[外壳模型](hardware/)
- [贡献指南](CONTRIBUTING.md)

固件源码在 `vendor/esp-mosaico-vibe` 子仓库。每次提交后，外层仓库保存子模块指针和 `dependencies/esp-mosaico-vibe.bundle`，便于恢复本地提交。

项目源码采用 [MIT](LICENSE) 许可。底层依赖按各自许可，字体资产遵循 SIL Open Font License 1.1。
