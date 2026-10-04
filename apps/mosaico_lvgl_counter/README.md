# 第一个 Lua + LVGL 示例

> 历史Lua/LVGL计数示例，保留早期ESP-Claw路线调查；当前固件为[原生LAN Screen](../../vendor/esp-mosaico-vibe/projects/lan_screen/docs/README.md)，不将此ZIP作为当前刷机包。


480×480 触摸计数器：点击 `+1 TAP` 增加数字，`Reset` 清零，`Exit` 退出。默认 60 秒自动结束，结束时调用 `lvgl.deinit()`。计数只保存在当前作业内存中。

这是可供部署验证的源代码，尚未上传到设备或通过实机测试。参考 ESP-Claw 提交 `9f92961687df06250df62c187979fa1ff67708f4` 的 [LVGL 文档](https://github.com/espressif/esp-claw/blob/9f92961687df06250df62c187979fa1ff67708f4/components/lua_modules/lua_module_lvgl/README.md) 与 [system 文档](https://github.com/espressif/esp-claw/blob/9f92961687df06250df62c187979fa1ff67708f4/components/lua_modules/lua_module_system/README.md)。实机固件版本仍未知，接口兼容性需要实际运行确认。

## 文件

- `scripts/main.lua`：界面与事件循环。
- `SKILL.md`：供设备 Agent 使用的技能说明；不是 Codex 技能。
- `../../dist/mosaico_lvgl_counter.zip`：上传文件前的交付包，解压后包目录为 `mosaico_lvgl_counter/`；不是已验证的 App 安装格式。

## 实机验证流程

网页上传的逐步说明和 Vibe Mode 官方中文入口见 [上传与模式说明](../../docs/development/upload-and-vibe-mode.md)。ZIP 需要先解压后按目录结构上传；未验证当前控制台支持 ZIP 自动安装。

1. 先确认 `http://192.168.5.61/api/status` 可响应，并核对 IP 是否改变。
2. 将包文件部署到新的 `/nand/skills/mosaico_lvgl_counter/`，保持目录结构；不要覆盖已有技能。Files 页的 `/skills` 是相对存储根目录的路径。
3. 确认固件已发现该技能以及实际支持 `lua_run_script_async`。Web 文件上传成功本身不代表技能已加载，也不代表脚本已经执行。
4. 使用 SKILL.md 中的参数启动作业，保留 job id，读取日志和状态。不要抢占已有屏幕作业。
5. 在实体屏幕上验证显示、连续点击计数、Reset、Exit，以及第二次启动。另做一次等待 60 秒自动结束的验证。
6. 核对作业结束及资源释放；是否自动恢复系统主页需要实机确认。保存到 Work 的流程另行核对。

初始界面使用英文，避免依赖中文字体。如果默认 TTF 可用，会使用较大的字体；否则使用内置字体。内置字体的大小与固件配置有关。

本地 Lua 语法与包元数据检查通过后，也不能据此认定设备 LVGL 绑定、触摸、显示、字体或系统主页恢复已经正常工作。

## 本次检查（2026-10-02）

- 使用 npm 注册表的 `luaparse 0.3.1` 按 Lua 5.3 语法子集解析通过；本脚本不使用 Lua 5.4 专有语法。这是静态语法检查，不是 Lua 5.4 或设备运行测试。解析器仅安装于 `/tmp/mosaico-lua-parser`，没有更改全局 Node 环境。
- JSON frontmatter、技能目录名、唯一 H1 和脚本路径检查通过。
- ZIP 已生成并核对文件列表，无目录逃逸路径。
- 开始制作示例前，设备状态接口仍可响应；尚未上传包或执行作业。
