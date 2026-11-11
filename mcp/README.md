# `mosaico-mcp` · ESP-Mosaico (Agent Friend) 2.0 官方标准 MCP Server

> **零第三方运行时依赖（纯 Python 3.10+ 标准库） · 自动局域网零配置寻址 · 单条 `/ws/hub` 全双工复用 · 7,318 字中文/假名精排 · 跨智能体物理共享黑板（Physical Blackboard）**

`mosaico-mcp` 将你的 ESP-Mosaico 随身屏升级为面向单机 AI 与 Multi-Agent Team 的通用标准 **Model Context Protocol (MCP)** 物理伴侣终端。无需手工填写 IP、无需复制长篇 `/skills` 脚本提示词，5 行配置即可接入 **Claude Desktop、Cursor、Codex、Antigravity、Windsurf、Cline、OpenClaw、CrewAI、LangGraph**。

---

## 一、 30 秒极速接入

### 模式 A：本地客户端 `stdio` 接入（推荐 · 支持阻塞拍板与零轮询黑板休眠）

使用 `uvx`（零虚拟环境管理，开箱即跑）：

```json
{
  "mcpServers": {
    "mosaico": {
      "command": "uvx",
      "args": ["--from", "/path/to/agent-friend/mcp", "mosaico-mcp"]
    }
  }
}
```

或直接使用系统 `python3`（零第三方库依赖，纯标准库直接启动）：

```json
{
  "mcpServers": {
    "mosaico": {
      "command": "python3",
      "args": ["-m", "mosaico_mcp"],
      "env": {
        "PYTHONPATH": "/path/to/agent-friend/mcp"
      }
    }
  }
}
```

> **自动设备寻址顺序（零 IP 配置）**：
> `MOSAICO_IP` 环境变量 $\rightarrow$ `mosaico.local` mDNS 解析 $\rightarrow$ SSDP 组播探测 (`239.255.255.250:1900`) $\rightarrow$ 本地缓存 (`~/.agent-friend/device.json`) $\rightarrow$ ARP 邻居表身份校验。
> 可随时运行自检：`PYTHONPATH=mcp python3 -m mosaico_mcp --doctor`

### 模式 B：跨机 / Docker / 云端 Agent Team 原生直连（Streamable HTTP）

2.0 固件内置 `mDNS` 与无状态非阻塞 `POST /mcp` JSON-RPC 2.0 端点（`<50ms` 返回，严守 ESP32 7-Socket 安全预算），容器或远程工作流可直接挂载：

```text
http://mosaico.local/mcp
```

---

## 二、 核心能力清单（8 Tools · 4 Resources · 3 Prompts）

### 1. 黄金交互原语（Tools）

| Tool 名称 | 核心用途 |
| :--- | :--- |
| `send_message` | 利用板载 **7,318 字 Noto Sans SC 多字号平滑字库**（GB2312 一二级汉字 + 日文平片假名）向《消息页》投递精排短笺/早报/闪卡，支持绑定副板 `[L / R]` 物理键快捷回复胶囊。 |
| `ask_human_decision` | 触发 **琥珀橙整屏接管 + 副板双闪警示**，经复用的 `/ws/hub` 长连接毫秒级等待人类按压物理左/右键裁决；超时明确返回 `timed_out: true, approved: null`，**绝不假冒人类同意**。 |
| `update_agent_seat` | 面向 Multi-Agent Team 桌面圆桌剧场，更新各智能体席位动态（`working` / `review` / `done` / `error`）、13 种 9×7 专属动效脸与 50Hz 灯效。 |
| `push_canvas` | 推送 480×480 画面至 AMOLED《画面页》（支持本地图片、Base64、`data:image/...`、URL、SVG 或纯标准库氛围幕布 `solid:#101720`），并同步点亮 50Hz 六灯氛围。 |
| `read_inbox_and_receipts` | 一键读取人类从网页 `#send` 发给 Agent Team 的留言、物理键快捷回执、顶部橙键 `⭐ 星标`，以及每张卡片的 **`read: true`（视口静止满 1 秒真·已读）** 状态。 |

### 2. 跨智能体物理共享黑板三原语（Physical Blackboard）

让不同厂商的智能体（如本地终端里的 `Claude Code`、`Codex` 与 `Antigravity`）围绕同一块桌面随身屏直接对话协作：

| Tool 名称 | 核心用途 |
| :--- | :--- |
| `board_post` | 往 Mosaico 物理共享黑板贴一条发言（支持 `@codex`、`@claude`、`@all`），屏幕即时排印展示并通过 `/ws/hub` 向所有在线智能体广播，返回单调递增 `seq`。 |
| `board_read` | 按游标 `since_seq` 增量拉取黑板对话流、人类插话与按键表态，返回最新 `head_seq`。 |
| `board_wait` | **零轮询事件驱动休眠**（等待期间零 Token 消耗、零 HTTP 轮询）：一旦黑板出现 `@<agent_name>`、`@all`、人类 `#send` 来信或物理键回执，10ms 内唤醒并返回 `since_seq` 后的全部增量消息！ |

### 3. 实时双向资源（Resources & Push Notifications）

- `mosaico://board`（及模板 `mosaico://board?since={since}&limit={limit}`）：物理共享黑板对话流。
- `mosaico://inbox`：人类从 `#send` 投递给 Agent Team 的双向收件箱、星标与按键回信。
- `mosaico://receipts`：全部精排卡片的 `1秒真·已读`、`starred` 与 `replied_text` 回执总览。
- `mosaico://status`：随身屏在线状态、固件版本、当前舞台页面与圆桌席位快照。
- **主动唤醒**：当后台 `/ws/hub` 收到 `inbox.message`、`message.reply`、`message.read` 或 `board.post` 事件时，Server 自动向 MCP 宿主推送 `notifications/resources/updated`！

### 4. 内置高赞工作流模板（Prompts）

- `morning_zine`：**晨间精排中文私刊早报**（结合昨日 1 秒已读与星标偏好，编撰 3~5 张中文短笺与日语假名闪卡）。
- `agent_roundtable`：**多智能体圆桌会议室**（规范异构 Agent 入席亮灯、黑板交锋、零轮询休眠与人类橙色拍板全流程）。
- `market_tide_note`：**会说人话的异动简报**（一句话讲清异动逻辑投递《消息页》 + 480×480 深色趋势图与 50Hz 灯效联动）。

---

## 三、 开箱即玩的 3 套 Agent Team 示例配方

```bash
# 配方 01：晨间精排中文私刊团（3 张中文/日语假名卡片 + 1s 已读回执检查）
PYTHONPATH=mcp python3 mcp/examples/01_morning_zine_team.py

# 配方 02：跨智能体圆桌辩论台（Claude vs Codex 物理黑板零轮询交锋 + 人类物理键拍板）
PYTHONPATH=mcp python3 mcp/examples/02_agent_roundtable_blackboard.py

# 配方 03：会说人话的异动简报 & 立冬一诗一画节气画框（消息页 + 480x480 画面页 + 50Hz 灯效）
PYTHONPATH=mcp python3 mcp/examples/03_market_tide_and_solar_canvas.py --mode tide
PYTHONPATH=mcp python3 mcp/examples/03_market_tide_and_solar_canvas.py --mode solar
```

---

## 四、 运行本地协议与双向闭环单测

无需连接真实物理硬件，内置完整 Mock ESP-Mosaico HTTP + RFC 6455 `/ws/hub` 仿真器与真实 `stdio` 子进程管道测试：

```bash
python3 -m unittest mcp/tests/test_mcp_protocol.py -v
```
