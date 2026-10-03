# Lua 示例上传与 Vibe Mode

核对日期：2026-10-02。用户询问如何传到设备，并希望找到社交媒体提及的 Vibe Mode 文档。本页是操作参考；未执行上传、模式切换或固件写入。

## 当前 Lua 示例

[示例源码](../../apps/mosaico_lvgl_counter/README.md) 使用设备现有固件的 Lua LVGL 绑定。ZIP 只是文件交付包，不是已验证的原生 App 安装包，也没有证据表明当前 Files 页面会自动解压 ZIP。

按以下结构上传解压后的两个必需文件：

```text
Files 页面（相对 /nand）          设备上的绝对路径
/skills/mosaico_lvgl_counter/     /nand/skills/mosaico_lvgl_counter/
├── SKILL.md
└── scripts/
    └── main.lua
```

1. Mac 上解压 `dist/mosaico_lvgl_counter.zip`，或直接使用 `apps/mosaico_lvgl_counter/`。
2. 访问 [Files](http://192.168.5.61/#files)，启用 Dev Mode 后，进入 `/skills`。
3. 新建 `mosaico_lvgl_counter` 目录，上传 `SKILL.md`；在其中新建 `scripts` 目录，再上传 `main.lua`。有目录上传按钮时可上传完整包目录；不要仅将 ZIP 当作一个普通文件上传后期待自动安装。
4. 通过设备 Agent 调用运行能力，并核对作业日志及实体屏幕。把文件上传到 Skills 目录，不代表已经注册到 Work 或启动。

可以自行向设备 Web Chat 发送以下请求：

> 读取 /nand/skills/mosaico_lvgl_counter/SKILL.md，按其中参数运行 scripts/main.lua，持续 60 秒，不替换已有屏幕任务。返回 job id、状态和实际日志；如果接口不可用，报告错误。

这只是待实机核对的执行方法，不是已经完成的测试结果。Skill 目录扫描、工具参数兼容及 Work 注册仍需实机验证。

依据：[ESP-Claw Web 配置文档](https://legacy.docs.esp-claw.com/zh-cn/tutorial/web-config/)、[固定参考版 Files 页面实现](https://github.com/espressif/esp-claw/blob/9f92961687df06250df62c187979fa1ff67708f4/application/edge_agent/components/http_server/frontend_source/src/pages/FilesPage.tsx)。实机已确认有 Files 与 Dev Mode 入口，但未启用 Dev Mode 查看其写入控件，具体按钮文字可能随版本和语言变化。

## Vibe Mode 文档位置

详细文档在官方 Vibe 工作区，而不在硬件引脚指南中：

- [中文设备模式说明](https://github.com/esp-mosaico/esp-mosaico-vibe/blob/main/docs/device-modes_CN.md)
- [中文 CLI 参考](https://github.com/esp-mosaico/esp-mosaico-vibe/blob/main/docs/mosaico-cli_CN.md)
- [中文文档索引](https://github.com/esp-mosaico/esp-mosaico-vibe/blob/main/docs/README_CN.md)
- [官网 VibeCoding 概览](https://mosaico.espressif.com/zh/guide/vibe-coding/)

2026-10-02 再次查询上游默认分支，最新提交仍为 `95469e63b621fc6ece3b0e313af8c1ba59dcd066`（2026-09-29），与先前调查固定点一致。

| 名称 | 含义 / 入口 |
| --- | --- |
| LVGL | 界面库；可以使用 Lua 绑定，也可以集成到原生 C/C++ 工程 |
| VibeCoding | PC Agent、模拟器、工具链、实体设备协作的开发流程 |
| Vibe Mode | `factory` 分区里的保留维护固件，运行 ESP-Iris，提供应用更新、Wi-Fi 配置和 Download Ideas |
| ROM Download Mode | 芯片 ROM 下载程序，不运行 ESP-Iris；与 Vibe Mode 不同 |

官方的物理入口前提是设备已有有效 Mosaico bootloader 和保留固件：关机，按住 AI 键开机，待 Vibe Mode 启动后松开。通过这一临时入口启动时不修改 OTA 选择；松开 AI 键再次重启，沿用有效的原 OTA 启动选择。USB-C 左侧的 BOOT 键进入的是 ROM 下载模式。是否安装了有效维护环境，尚未在本机验证。

`python mosaico.py iris test enter-recovery` 可从已连接且运行 ESP-Iris 的正常应用切换到已有 Vibe Mode；`python mosaico.py recover` 会写入基础固件，不能将其当作单纯切换模式的命令。

CLI 区分新应用/资源/分区布局变化的 `iris system-update` 与分区表一致时仅更新应用代码的 `iris app-update`。这些用于匹配的原生工程和更新包，不能把当前 Lua ZIP 直接传给它们。具体命令、工具链和打包要求以固定版本文档为准。

正常 ESP-Claw 应用没有枚举 USB，不能据此证明 Vibe Mode 也没有 USB。后续若选择独立原生 LVGL 工程，先验证 Vibe Mode 与 ESP-Iris，再配置工作区与更新包；当前没有必要为了试 Lua 示例而刷写基础固件。
