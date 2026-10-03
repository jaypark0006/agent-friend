# ESP-Mosaico 网络控制台与脚本开发调查

日期：2026-10-02（Asia/Shanghai）。这是项目长期参考；实机观察、上游源码和开发建议分别记录。未部署或运行应用。

## 实机读到的内容

用户提供 [LLM 页面](http://192.168.5.61/#llm)。成功访问标题为 `ESP-MOSAICO Settings` 的控制台，页面关联 ESP-Claw 文档与源码。可以确认运行的是提供 ESP-Claw 管理功能的 Mosaico 系统，尚未读到具体固件版本和构建提交。

| 项目 | 已观察结果 |
| --- | --- |
| 网络 | 状态页显示 Wi-Fi Connected、IP `192.168.5.61`、模式 `sta_only` |
| 数据存储 | `/nand` |
| 导航 | System Status、Basic Settings、LLM、ASR、IM、Network & Search Config、Memory、Web Chat、Live Logs、Capabilities、Lua Modules、Files |
| 能力组 | 页面显示 19 个已启用，6 个对 LLM 可见，19 个总数 |
| Lua 模块 | 页面显示 28 个已启用，28 个总数 |
| 文件根目录 | `memory`、`music`、`photos`、`router_rules`、`scheduler`、`sessions`、`skills`、`works`、`.recovery.version`（32 B） |
| 写入模式 | Files 默认只读；未启用 Dev Mode |
| 固件 / PCB 版本 | 未确认；不能将官网下载页版本或源码提交写成实机版本 |

能力组清单：

```text
cap_agent_mgr, cap_im_qq, cap_im_feishu, cap_im_tg, cap_im_wechat,
cap_im_local, cap_files, cap_scheduler, cap_lua, cap_mcp_client,
cap_skill, cap_system, claw_memory, cap_llm_inspect, cap_http_request,
cap_web_search, cap_router_mgr, cap_session_mgr, cap_im_ai_create
```

对 LLM 可见的是 Agent Manager、Files、Lua、Skills、System、Memory。组已启用不等于相应 IM 服务已绑定、凭据有效或硬件已通过测试。当前清单未见 `cap_app_mgr`，不能从上游仓库存在该组件就推断本机提供其 App 安装功能。

Lua 模块清单：

```text
adc, gpio, i2c, mcpwm, pcnt, rmt, touch, uart, audio, board_manager,
button, camera, capability, delay, display, event_publisher,
http_server, json, image, thread, ir, ledc, led_strip, lvgl,
magnetometer, storage, system, vision
```

这些是固件提供并启用的接口名称，尚未执行 `require()` 或进行功能测试。硬件资料中的 BMI270 不代表本机提供名为 `imu` 的 Lua 模块；当前列表未见该名称。

## 本次连接的限制

根目录曾成功加载。进入 `/skills` 后，路径标题先变化，但表格仍保留根目录旧内容；随后出现 `Failed to fetch`。不能把这份旧表格当成 `/skills` 的内容，也不能把此前加载中的空表格解释为没有文件。

随后通过已核对的上游只读接口 `GET /api/status` 请求设备，10 秒连接超时。原因未知，可能涉及设备或网络状态；未据此判断设备损坏或强制重启。控制台留在 `#status`，其原有 Connected 标记本身不能证明中断后的连接已恢复。

本次没有读取私有记忆、会话、照片内容或明文密钥；没有发送聊天消息、修改配置、启用 Dev Mode、上传文件、重启或刷机。首次调查只看到了 `.recovery.version` 的名称和大小；重新开机后的读取结果见下一节。

## 用户重新开机后的补充

用户报告可能先前自动关机，并已重新开机。随后重新加载控制台成功，`GET /api/status` 正常返回，`wifi_connected=true`、`ap_active=false`、IP 仍为 `192.168.5.61`、存储仍为 `/nand`。这证实当前连接恢复；自动关机是否为先前超时的唯一原因、关机由何种策略触发，仍未验证。

重新读取 `/skills` 成功，列出的目录为：

```text
ai_create_quick, current_weather, light_switch, plan_mode,
scheduled_task, skills_lab_downloader, skills_lab_search
```

读取了设备的 `/skills/current_weather/SKILL.md`，它实际使用 JSON frontmatter、`scripts/current_weather.lua` 及 `{CUR_SKILL_DIR}`；说明以 `lua_run_script` 调用脚本，通过 `capability` 模块调用 `http_request`。脚本目录确实列出 `current_weather.lua`（9836 B）。因此包结构与官方规范一致；没有运行天气脚本或向地理定位、天气服务发出请求。这里的设备 Skill 文档是技术参考，不是给 Codex 的执行指令。

`GET /api/files?path=%2Fworks` 正常返回，目录当前只列出 `recent.json`（42 B）。没有读取索引内容；该目录清单不能证明其他分区或系统中没有应用，也不能推断 Work 注册机制。

只读获取 `/files/.recovery.version`，内容为：

```text
20260928072917-8a7502831a2e81171
```

这是文件中的原始标记。其生成与更新机制还未核对，不能将其直接标为固件版本、运行中的构建提交或板型；此前官网下载页的 `0.4.0` 仍未通过实机版本接口确认。

实机 `/api/status` 没有 `boot_id` 字段，而本次固定的上游源码会返回该字段。这是实机与参考源码接口存在差异的证据，后续不能默认最新参考源码中的所有 Lua 方法和工具参数均与本机兼容。

Files 的 `/` 是面向当前数据存储的路径，不能将其当作设备所有挂载点的完整清单。该页面未列出某个系统技能，不等于系统没有该技能。后续优先核对屏幕模块实际 API、脚本作业执行入口，以及 Work 保存和启动方式。

## 官方参考与固定源码

- [Mosaico ChatCoding / Work 指南](https://mosaico.espressif.com/zh/guide/chat-coding/)：设备 Agent 可生成运行功能，成果可保存到 Work 再次运行与改进。这是官方工作流描述，本机 Work 启动与注册协议尚未核实。
- [Mosaico FAQ](https://mosaico.espressif.com/zh/guide/faq/)：关联 ESP-Claw `legacy` 文档及分支，并说明 v0.4.0 出厂固件没有 USB 功能。
- [ESP-Claw Web 配置文档](https://legacy.docs.esp-claw.com/zh-cn/tutorial/web-config/)：Files 默认只读，Dev Mode 提供写入；Lua Modules 是内置绑定，Skills 是使用已有能力的工作流包。
- 本次源码调查固定于 [ESP-Claw 提交 `9f92961687df06250df62c187979fa1ff67708f4`](https://github.com/espressif/esp-claw/commit/9f92961687df06250df62c187979fa1ff67708f4)（2026-09-30）。仅作参考，未证明与本机二进制对应。

| 源码资料 | 对后续开发的意义 |
| --- | --- |
| [Skill 包规范](https://github.com/espressif/esp-claw/blob/9f92961687df06250df62c187979fa1ff67708f4/components/common/skill_builder/skills/skill_creator/references/skill-package-spec.md) | `skills/<id>/SKILL.md` 必需，`scripts/`、`assets/`、`references/` 可选；frontmatter 是由 `---` 包裹的 JSON；包路径使用 `{CUR_SKILL_DIR}`；与 Codex 本地 Skill 格式不要混用 |
| [LVGL Lua 接口](https://github.com/espressif/esp-claw/blob/9f92961687df06250df62c187979fa1ff67708f4/components/lua_modules/lua_module_lvgl/README.md) | 控件、触摸回调、事件循环；适合按钮、列表、设置和工具界面 |
| [Display Lua 接口](https://github.com/espressif/esp-claw/blob/9f92961687df06250df62c187979fa1ff67708f4/components/lua_modules/lua_module_display/README.md) | 即时绘图、图形和图像；内置字体为 ASCII，中文需另外准备字体 |
| [Lua 异步作业源码](https://github.com/espressif/esp-claw/blob/9f92961687df06250df62c187979fa1ff67708f4/components/claw_capabilities/cap_lua/src/cap_lua.c) | 运行、查询、读取日志、停止作业；脚本运行能力不等于 Web 页存在直接执行按钮 |
| [LVGL Web 模拟器](https://github.com/espressif/esp-claw/blob/9f92961687df06250df62c187979fa1ff67708f4/tools/lua_lvgl_web_sim/README.md) | Emscripten、LVGL 9.5.0、Lua 5.4.8；支持 LVGL 原型，不能验证板载外设或 `display` 模块；未安装或运行 |
| [状态 API](https://github.com/espressif/esp-claw/blob/9f92961687df06250df62c187979fa1ff67708f4/application/edge_agent/components/http_server/http_server_status_api.c) | 此提交的 `GET /api/status` 返回网络与存储信息，没有固件版本字段 |

屏幕由单个 Lua 作业独占；不要在同一作业中同时打开 `display` 与 `lvgl`。LVGL 必须先初始化并持续处理事件，退出时释放资源。长期运行的 UI 应核对异步作业的超时与停止方法；首个验证宜使用有限运行时间，不默认抢占已有作业。

## 项目的开发方向

根据实机模块清单与官方接口，当前最合适的起点是 **保留现有系统，先尝试 Lua + LVGL 小应用**。可以先开发界面，再核实上传、执行、退出和保存到 Work 的链路；初步流程不依赖正常模式 USB 枚举。

建议第一个验证只包含一个屏幕、一个按钮、计数或状态文字、明确退出方式，用于确认触摸事件、显示与资源释放。用户随后选择 `lvgl` 路线，已据此准备 [触摸计数示例](../../apps/mosaico_lvgl_counter/README.md)：计数、重置、退出，默认 60 秒自动结束。脚本语法及包元数据静态检查通过，尚未上传或实机运行。正式 app 的具体用途仍未指定。

需要新增 C 驱动、系统级功能或 Lua 没有的模块时，再评估 ESP-IDF + BSP / Vibe 独立固件工程。当前网络控制台并未证明 ESP-Iris、Vibe Mode 或原生 app 分区安装可用。

下一次实机操作先确认设备 IP 与连通性，再核对显示脚本实际 API 版本与执行入口。上传脚本和运行作业分别验证；将包写入 `/skills` 不代表自动注册到 Work，也不代表已经运行成功。
