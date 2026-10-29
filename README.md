# Agent Friend · Mosaico 随身屏

Agent Friend 把 AI 助手的任务进度、消息和确认请求放到桌面上的 480×480 触摸屏。你可以在屏幕、交互副板左右按键或网页控制台上处理确认，也可以直接推送文字和图片。

当前交付 **1.1.58**（2026-10-29）。已通过官方更新流程安装并确认版本与健康状态；本版效果验收尚未执行，见[交付记录](docs/development/2026-10-29-delivery-1.1.58.md)。

## 开始使用

已经装好固件的设备，接入 Wi-Fi 后即可使用。让电脑或手机连接同一局域网，在浏览器打开设备 IP。

本机设备当前入口：**[打开网页控制台](http://192.168.5.92/)**。IP 变化时，在设备顶栏或下拉控制中心的设备信息中查看新地址。

| 入口 | 用途 |
| --- | --- |
| 此刻 | 看正在做的事、任务列表、待确认请求和随身屏画面 |
| 推送 | 发文字、粘贴或选择图片、查看内容历史 |
| 设备 | 调整自动跳转、灯光提示、画面角标，控制灯光及查看传感器 |
| 开发者 | HTTP、WebSocket、镜头色块和模拟 Agent 工具 |

完整操作见[使用指南](docs/user-guide.md)。

## 让 AI 助手接入

把下面这段话交给你使用的 AI 助手，并按设备当前地址替换 IP：

> 请读取 http://192.168.5.92/skills 并按其中的协议连接我的 Agent Friend 随身屏。每个新任务使用独立 ID，持续更新同一任务的进度，分别填写 agent、session、title；任务结束标记 done。需要我决定时先建立 WebSocket 监听，再发送待确认任务，并根据实际批准或取消事件继续。不要把超时当作批准。

设备自身提供协议说明，能调用局域网 HTTP / WebSocket 的助手可直接接入。仓库也提供可选的 [Python 通知脚本](skills/mosaico-notify/)；日常使用无需安装 ESP-IDF 或恢复固件源码。

## 设备操作

- 左右滑动在「此刻 → 任务 → 消息 → 画面」四个主页面间切换，不循环。
- 顶部下拉打开控制中心，调整亮度、Wi-Fi 和设备设置，或进入镜头。
- 待确认时，按屏上选项或交互副板 L/R 键决定；Agent 必须收到对应任务的事件才能继续。
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
- [当前功能与安装状态](vendor/esp-mosaico-vibe/projects/lan_screen/docs/current-state.md)
- [REST / WebSocket 接口](vendor/esp-mosaico-vibe/projects/lan_screen/docs/api.md)
- [1.1.58 人工验收清单](vendor/esp-mosaico-vibe/projects/lan_screen/docs/acceptance-1.1.58.md)
- [应用文档索引](vendor/esp-mosaico-vibe/projects/lan_screen/docs/README.md)
- [硬件参考](docs/esp-mosaico-reference.md)与[外壳模型](hardware/)
- [贡献指南](CONTRIBUTING.md)

固件源码在 `vendor/esp-mosaico-vibe` 子仓库。每次提交后，外层仓库保存子模块指针和 `dependencies/esp-mosaico-vibe.bundle`，便于恢复本地提交。

项目源码采用 [MIT](LICENSE) 许可。底层依赖按各自许可，字体资产遵循 SIL Open Font License 1.1。
