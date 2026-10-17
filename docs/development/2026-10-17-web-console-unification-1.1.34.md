# LAN Screen 1.1.34 交付记录：Web 控制台 AI 流水线去冗余与统一注入器

日期：2026-10-17
固件版本：1.1.34
目标设备：ESP-Mosaico (`esp32s31`)
Device ID: `4553502d4952495301001c2904d0ad2a`
局域网地址：`http://192.168.5.192`

---

## 1. 核心需求背景

用户指出：
> “网页控制台的AI流水线这一页 做一个就行了 antigravity来一个 codex来一个... 这俩能有啥区别呀 真的是。”

在 1.1.33 及之前版本中，AI 流水线页面顶部放置了多个特定 Agent 名称的“快捷模板”按钮（Antigravity、Codex、Deploy），其底层逻辑仅仅是将不同的字符串填入同一个注入表单，制造了不必要的冗余和视觉混淆。所有 AI Agent（无论是 Codex、Antigravity 还是用户自动化脚本）在本质上均遵循相同的 `/api/widget` 协议结构。

---

## 2. 优化与改动细节

1. **剔除冗余模板按钮（Eliminate Redundant Templates）**：
   - 彻底移除了 `api.html` 中的 `antigravity / codex / deploy` 快捷芯片；
   - 删除了 `console-view.js` 中无实际意义的 `agentPresets` 字典及对应的 DOM 点击绑定代码。
2. **流水线注入器统一与精简（Unified Pipeline Step Injector）**：
   - 保留一套标准、中立的注入表单：
     - **ID**：默认为 `agent`（支持任意自定义）
     - **Title**：默认为 `AI Agent`
     - **Status**：默认为 `正在执行任务并同步进度...`
     - **Progress**：0%~100% 进度滑块
     - **Color / Confirm**：调色板与人机交互物理确认
3. **保留并突出实体交互板 LED 动效控制栏**：
   - 页面顶栏直接呈现 `深呼吸 / 跑马灯 / 彩虹 / 警报 / 成功 / 熄灭` 预制灯效快捷触发，操作更加直接纯粹。

---

## 3. 刷机与运行状态

- **编译生成**：`lan_screen.bin` (5028112 bytes)。
- **刷入验证**：官方 CLI 安装成功，`firmware_mode: normal`，`version: 1.1.34`，`crash_count: 0`。
- **页面检验**：直接从设备 HTTP 验证已生效，去除了全部冗余模板代码。
