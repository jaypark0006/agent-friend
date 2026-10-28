# 1.1.54 随身屏持久化字库与按需 LRU 缓存系统

## 交付背景与目标
针对 1.1.48/1.1.49 期间界面汉字缺失导致退回 16px 粗糙放大点阵字库（同一行字一半清晰一半发虚、马赛克锯齿严重）的痛点，按照用户提出的根本解思路，在持久存储（SPI Flash）中部署包含 4,118 字符的完整高精度字库，运行期按需动态读取字形并由 PSRAM LRU 缓存复用，彻底根除字库发虚问题，同时大幅释放系统内存。

## 核心架构实现（100% 应用层，零改动第三方库）
1. **全字符集与离线字库打包（`tools/gen_all_chars.py` & `tools/gen_flash_font.js`）**：
   - 提取包含 ASCII 全字符、通用标点、箭头数学符号、GB2312 一级常用汉字（3,755 字）及全部固件界面字面量，总计 4,118 个字符。
   - 使用 Node.js 离线调用 `lv_font_conv` 引擎为 5 套 UI 字体（20px Regular、24px Regular、24px Bold、32px Regular、32px Bold）生成 4bpp 紧凑抗锯齿字模数据包（`screen_font_pack.bin`，共 6.17 MB）。
   - 生成 281 KB 轻量只读元数据与 CMAP 升序索引表（`screen_font_tables.c/.h`），提供 $O(\log N)$ 二分查找字形度量。
2. **Flash 镜像追加构建机制（`tools/pack_flash_font.py`）**：
   - 编写无损固件镜像解析与打包工具，通过 CMake `POST_BUILD` 钩子在 `lan_screen.bin` 头部解析各 ELF 段后，在 4KB 扇区对齐处追加字库二进制，实现与 OTA 分区一体化烧录，不占用 PSRAM 加载空间。
3. **按需流式提取与 PSRAM LRU 缓存（`main/screen_font_flash.c/.h`）**：
   - 开机挂载 Flash 字体包（Magic `0x544E464D` 校验）。
   - 在 PSRAM 中分配 128 槽位 LRU 缓存（单槽最大支持 33×35 像素 A8 解码，总开销仅 145 KB）。
   - 接入 LVGL 9 标准外部字体回调：`get_glyph_dsc` 快速返回度量信息并正确处理 1/16 子像素换算（`adv_w = (m->adv_w + 8) >> 4`）；`get_glyph_bitmap` 命中缓存直接返回，未命中则实时自 Flash 读取 4bpp 点阵并解码为 A8 格式存入槽位。
   - 启用 LVGL `static_bitmap = 1` 快速混合路径。
4. **移除旧字库臃肿依赖**：
   - 彻底移除原 9.9 MB 源码 / 1.6 MB PSRAM 的 `screen_font_cjk_16.c` 及各散落字体文件；
   - 剩余可用 PSRAM 由 5.7 MB 大幅提升至 **9.89 MB**（净增加 >2 MB PSRAM）。

## 交互协同与人机在环（Human-in-the-Loop）规范
- **此刻页（Now Page）层级**：明确「等你确认 › 1 分钟内完成/出错 › 工作中 › 空闲时钟」设计层级。
- **征求意见/等待决策时机**：当 Agent 在会话中需要用户反馈、裁决或选择时，随身屏必须立即推送 `--confirm`（琥珀橙色整屏接管、大字号问题标题、副板 `alert` 双闪），严禁在等待人类时停留在普通的百分比进度条。

## 固件与验证
- 官方低噪音构建：`idf_low_noise_build.py` 耗时 36.8s，产物 `lan_screen.bin`（8,922,661 字节，含 6.17 MB SPI Flash 字库包），版本 1.1.54。
- 官方更新刷入：`mosaico.py iris app-update` 成功安装，设备上报 `mode: normal`，`crash_count: 0`，`app_version: 1.1.54`，`free_spiram: 9893328`。
- 实机截图验证通过：
  - 设备信息页（20px/24px）水平规整、抗锯齿清晰；
  - 任务与此刻页（32px/24px）排版正常；
  - 消息页实测汉字「界面字库恢复完整，排查默认设置无误」告别发虚与 16px 降级；
  - 触屏按键裁决已实机体验并回传成功。
