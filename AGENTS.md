# 项目长期参考与开发准则

## 1. 文档与架构入口

- **当前基线版本**：`1.1.60`（见最新交付记录 [2026-11-12-touch-scroll-fix-1.1.60.md](docs/development/2026-11-12-touch-scroll-fix-1.1.60.md) 与 [2026-11-12-mcp-blackboard-1.1.59.md](docs/development/2026-11-12-mcp-blackboard-1.1.59.md)）。
- **历史演进归档**：历次版本交付摘要已归档至 [版本交付与历史演进归档](docs/development/release-history.md)，不再堆积于本文件。
- **核心架构与 API**：
  - 固件工程目录：`vendor/esp-mosaico-vibe/projects/lan_screen`
  - 应用文档索引：[docs/README.md](vendor/esp-mosaico-vibe/projects/lan_screen/docs/README.md)
  - 模块边界与架构说明：[docs/architecture.md](vendor/esp-mosaico-vibe/projects/lan_screen/docs/architecture.md)
  - MCP Server 包：`mcp/`（零外部依赖 `mosaico-mcp` 标准包）
  - 硬件与官方参考：[ESP-Mosaico 参考笔记](docs/esp-mosaico-reference.md)、[交互子板说明](docs/development/interaction-subboard-api.md)、[终端用户使用指南](docs/user-guide.md)

## 2. 开发与验证工作准则

- **测试与验证边界**：未经用户当次明确要求，不要编写、新增或修改测试，也不要自行运行模拟器、性能基准或自动化测试。历史任务中的验证授权不延续到后续任务。
- **默认编译与刷入授权**：每次固件功能修改后，默认完成编译与官方 `iris app-update` 刷入、重启及 `normal/healthy` 状态确认，无需逐次询问（若用户当次明确要求暂不编译或刷入，以当次要求为准）。
- **事实与证据边界**：严格区分源码完成、编译刷入成功与实机效果验收；未执行的测试或实机体验如实说明，不得将刷入成功表述为效果验收通过。
- **硬件与构建规范**：
  - 芯片目标固定为 `esp32s31`（不可套用 ESP32-S3 配置），左槽为翻转摄像头（ID `7`），右槽为交互副板（ID `0x16`）。
  - 优先使用 BSP 与模块驱动管理板级资源；网页静态资源严格遵守 `< 200KB` 预算、零 `innerHTML` 与零行内 `style=`。
  - 升级固件版本号时，除更新源文件与 `sdkconfig.defaults` 外，必须同步已有 `build/sdkconfig` 中的 `CONFIG_APP_PROJECT_VER`，并在刷入前核对 `build/project_description.json` 的 `project_version`。

## 3. 版本控制与子仓库同步

- **单逻辑单提交**：每次逻辑变动必须提交 Git commit，清晰描述改动内容。
- **双仓同步契约**：固件代码在 `vendor/esp-mosaico-vibe` 子仓库提交后，必须在根仓库运行 `python3 scripts/save-firmware-history.py` 刷新 `dependencies/esp-mosaico-vibe.bundle` 并提交子模块指针（新克隆可用 `python3 scripts/restore-firmware.py` 恢复）。
- **仓库卫生**：编译产物、Python 虚拟环境、临时日志不纳入源码提交；未经用户要求不得推送至公开远程仓库。

## 4. 随身屏进度广播与人机在环准则

- **单轮对话即新任务周期**：
  - 每次新对话/新需求使用全新的 `--id`，显式传入 `--avatar <agent_key>`（如 `antigravity`、`codex`、`claude`）及拆分后的 `--agent`、`--session`、`--title` 上报初始进度（如 `--progress 10 --led breathe`）。
  - 执行与编译刷机期间复用同一 `--id` 推进至 `30%~80%`（`--led chase`），长耗时任务每 5 分钟内保持心跳更新。
- **人机在环（Human-in-the-Loop）**：当向用户提问、方案二选一或等待审批而暂停时，严禁挂普通进度条等待，必须立即推送 `--confirm`（设置明确的 `--btn1` / `--btn2`，触发琥珀橙色接管与 `alert` 双闪灯效）。
- **分级收尾（禁止无脑刷图）**：
  - **常规任务与日常轮次**：不生成、不推送图片，仅推进至 `--progress 100 --done --led success`。
  - **重大里程碑与大功能闭环**：仅在重要功能完整落地或大版本里程碑时，制作并推送符合当前 Agent 设计语言的 480×480 成果配图。
- **技能入口**：工程内技能位于 `skills/mosaico-notify`（及 `.agents/skills/mosaico-notify`），权威接口规范以设备端 `http://<DEVICE_IP>/skills` 与 `SKILL.md` 为准。
