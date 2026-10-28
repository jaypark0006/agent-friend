# 贡献指南 (Contributing to Agent Friend)

感谢你关注并愿意为 **Agent Friend** 贡献代码与创意！无论是提交 Bug 报告、优化界面排版、增加新的 Agent 动效脸，还是扩展外设传感器支持，我们都非常欢迎你的 Pull Request。

---

## 🚀 快速上手与本地环境

### 1. 前置依赖
在开始之前，请确保你的开发机已准备好：
- **Python 3.10+**
- **Git 2.30+**
- **ESP-IDF v5.3+**（推荐官方安装路径，并配置好环境变量 `IDF_PATH`）

### 2. Fork 与克隆
```bash
# 1. 克隆你 Fork 的仓库
git clone https://github.com/<your-username>/agent-friend.git
cd agent-friend

# 2. 一键还原固件历史与依赖（核心步骤）
python3 scripts/restore-firmware.py
```

> 💡 **架构说明**：本项目采用便携式 Git 归档架构，核心固件仓库由 `dependencies/esp-mosaico-vibe.bundle` 追踪。执行 `restore-firmware.py` 会自动解包并配置好 `vendor/esp-mosaico-vibe` 子仓库及其相关驱动。

---

## 🛠 开发与构建流程

### 1. 固件逻辑修改
固件主程序位于 `vendor/esp-mosaico-vibe/projects/lan_screen/`：
- `main/screen_ui_now.c`：此刻页（排他性任务与状态展示）
- `main/screen_ui_tasks.c`：任务历史看板
- `main/screen_ui_messages.c`：消息推送页
- `main/screen_ws.c`：全双工 WebSocket Hub 与反向事件总线
- `main/screen_avatar.c`：9×7 点阵面孔动画矩阵
- `main/screen_network.c`：HTTP REST API 与 UPnP 描述
- `main/skill.md`：局域网自包含 Skill 说明书

### 2. 编译验证
在 `vendor/esp-mosaico-vibe` 目录下执行编译：
```bash
cd vendor/esp-mosaico-vibe

# 方式 A：使用内置低噪音构建工具（推荐）
python3 submodule/esp-mosaico-utils/mosaico-tools/skills/idf-low-noise-build/scripts/idf_low_noise_build.py \
  --project projects/lan_screen build

# 方式 B：使用标准 ESP-IDF
cd projects/lan_screen
idf.py build
```
编译系统会在构建后自动将 6.17 MB Flash 紧凑点阵字模包（`screen_font_pack.bin`）追加至 `lan_screen.bin` 尾部，生成约 8.52 MB 的最终完整固件。

### 3. 烧录与实机验证
连接 ESP32-S3 设备至电脑：
```bash
# 通用 esptool 烧录
esptool.py --chip esp32s3 -b 921600 write_flash 0x140000 dist/release-v1.1.54/lan_screen_v1.1.54.bin

# 或使用 idf.py 烧录
cd vendor/esp-mosaico-vibe/projects/lan_screen
idf.py -p /dev/ttyUSB0 flash
```

---

## 📦 提交代码与刷新归档（关键！）

由于固件子仓库是通过 Git Bundle 便携追踪的，当你修改了固件代码后，请务必执行以下双阶段提交流程：

### 步骤 1：在子仓库提交你的代码改动
```bash
cd vendor/esp-mosaico-vibe
git add .
git commit -m "feat(ui): add new agent avatar for Windsurf"
```

### 步骤 2：在根目录刷新便携式 Bundle 归档
```bash
cd ../.. # 回到 agent-friend 根目录
python3 scripts/save-firmware-history.py
```
该脚本会自动校验子仓库状态，并将最新的提交历史打包刷新到 `dependencies/esp-mosaico-vibe.bundle`。

### 步骤 3：提交根仓库并推送 PR
```bash
git add dependencies/esp-mosaico-vibe.bundle vendor/esp-mosaico-vibe
git commit -m "feat(firmware): sync bundle for windsurf avatar"
git push origin feature/my-feature
```
随后即可在 GitHub 上发起 Pull Request！

---

## 📝 提交信息与代码规范

- **Commit Message**：推荐遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：
  - `feat(...)`: 新功能或新特性
  - `fix(...)`: Bug 修复
  - `docs(...)`: 文档更新
  - `refactor(...)`: 代码重构（不改变功能）
  - `style(...)`: 代码格式调整
- **代码规范**：
  - 遵循标准 C99/C11 风格，保持现有的紧凑清晰排版；
  - 内存敏感：PSRAM 分配优先，严禁在渲染高频路径进行动态堆内存申请；
  - 保持 UTF-8 编码与文档完整性。

再次感谢你让 Agent Friend 变得更出色！
