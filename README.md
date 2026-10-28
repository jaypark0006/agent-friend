# Agent Friend (Mosaico Companion Screen)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Firmware](https://img.shields.io/badge/Firmware-v1.1.54-blue.svg)](docs/development/2026-10-29-persistent-flash-font-1.1.54.md)
[![Platform](https://img.shields.io/badge/Platform-ESP32--S31-orange.svg)](https://espressif.com/)

**Agent Friend** 是一款专为 AI 编码助手（Claude Code、Codex、Antigravity、Cursor 等）打造的桌面物理实体伴侣屏幕。

基于 ESP32-S3（ESP-Mosaico Iris）主控与 480×480 高清触控彩屏，搭配交互副板（机械实体左右双键 + 6 颗原生 50Hz 平滑 RGB 流光 LED），为身处数字世界的 AI Agent 提供实体桌面的生命力、进度可视化与人机在环（Human-in-the-Loop）物理裁决能力。

---

## ✨ 核心特性

- 🤖 **此刻页（Now Page · 排他性单任务视觉）**：
  - **等你确认（Waiting Human Touch）**：当 Agent 需要人类决策或方案裁决时，整屏琥珀橙色接管，副板 `alert` 双闪警示，大字号呈现核心问题与触摸胶囊；
  - **13 种 Agent 专属动效面孔（Avatar Matrix）**：9×7 点阵面孔根据当前工作的 Agent 播放专属微表情（支持 Antigravity、Claude、Codex、Gemini、Cursor 等），多 Agent 协同执行时智能轮换；
  - **优雅完成态**：绿色完成笑容常驻，清晰记录单轮任务用时与标题。
- 📋 **任务历史流水线（Tasks Page）**：
  - 任务按执行队列排列，展示进度条、执行状态、历史记录与各 Agent 专属标识；
  - 左右滑动无缝切换此刻、任务、消息、画面 4 大页面。
- 💬 **即时消息流（Messages Page）**：
  - 原生 Noto Sans SC 抗锯齿清晰呈现，Agent 可直接向随身屏推送纯文本通知与备忘录。
- ⚡ **全双工 WebSocket 事件总线（`ws://<IP>/ws/hub`）**：
  - **消灭轮询**：屏幕触屏点击「批准/拒绝」或按压副板左右物理键（L 键批准 / R 键拒绝）时，毫秒级主动向客户端推送 `task.action` 反向事件；
  - 页面手势切换（`page.changed`）与 6 轴体感旋转姿态（`device.orientation`）全量广播。
- 🔤 **SPI Flash 持久化字库与 PSRAM LRU 缓存**：
  - 内置 4,118 常用字符（全 ASCII + GB2312 一级常用字），4bpp 紧凑抗锯齿字模持久化存于 Flash，通过 128 槽位 PSRAM LRU 缓存按需流式提取，内存开销仅 145KB，剩余可用 PSRAM 高达 **9.89 MB**。
- 🌈 **预制 50Hz 原生 LED 情绪灯效**：
  - 思考中（`breathe` 呼吸）、执行构建中（`chase` 流光跑马灯）、等待人类确认（`alert` 琥珀双闪）、交付完成（`success` 双闪波纹常亮）。

---

## 🛠 硬件要求

- **主控平台**：ESP-Mosaico Iris（ESP32-S31，带 16MB Flash / 8MB+ PSRAM）
- **显示屏**：480×480 ST7701S / 圆形或方形触摸屏
- **交互副板**：6 颗 WS2812 RGB LED + 2 颗机械轻触按键（L/R）
- **外壳**：配套多材质 3D 打印外壳模型见 [`hardware/`](hardware/)

---

## 🚀 快速开始

### 1. 克隆仓库与恢复固件开发环境
本仓库采用便携式 Git 归档架构，克隆后只需执行一行脚本即可还原固件工作区与所有关联子模块：

```bash
git clone https://github.com/jaypark0006/agent-friend.git
cd agent-friend

# 一键恢复固件与依赖子模块
python3 scripts/restore-firmware.py
```

### 2. 让 AI Agent 连接随身屏
随身屏内置零依赖的 Agent 客户端脚本，位于 [`skills/mosaico-notify/`](skills/mosaico-notify/)：

```bash
# 上报工作进度（指定专属动效脸与呼吸灯效）
python3 skills/mosaico-notify/scripts/progress.py \
  --title 'Antigravity:功能开发-重构模块' \
  --avatar antigravity \
  --progress 45 \
  --status '正在编译核心逻辑...' \
  --led chase

# 向用户征求意见 / 等待物理确认（整屏橙色接管 + alert双闪，等待屏幕触摸或物理键）
python3 skills/mosaico-notify/scripts/progress.py \
  --title 'Antigravity:功能开发-重构模块' \
  --avatar antigravity \
  --status '是否批准部署到正式环境？' \
  --confirm --btn1 '批准部署' --btn2 '取消' \
  --wait-confirm --timeout 60

# 任务收尾交付（绿色笑容 + 用时统计）
python3 skills/mosaico-notify/scripts/progress.py \
  --title 'Antigravity:功能开发-重构模块' \
  --avatar antigravity \
  --progress 100 --done \
  --status '开发已完成并上线' \
  --led success
```

---

## 📂 项目结构

```text
agent-friend/
├── LICENSE                                    # MIT 开源许可证
├── README.md                                  # 项目说明
├── AGENTS.md                                  # 项目长期参考与交付规范
├── dependencies/
│   └── esp-mosaico-vibe.bundle               # 固件完整提交历史便携包
├── scripts/
│   ├── restore-firmware.py                    # 一键恢复固件工作区与依赖
│   └── save-firmware-history.py               # 固件改动归档刷新脚本
├── skills/
│   └── mosaico-notify/                        # Agent 随身屏交互技能（progress/notify/receipt）
├── hardware/                                  # 3D 打印外壳与导光件建模文件
├── docs/                                      # 协议、设计与历次交付文档
└── vendor/
    └── esp-mosaico-vibe/                      # 固件子仓库（包含 projects/lan_screen）
```

---

## 📄 开源许可证

本项目源码采用 [MIT License](LICENSE) 授权。  
引用的底层 ESP-IDF 与 BSP 驱动遵循 Apache-2.0 许可证，Noto Sans SC 字体资产遵循 SIL Open Font License 1.1。
