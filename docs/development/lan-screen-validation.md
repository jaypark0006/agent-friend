# LAN Screen 首版验证记录

日期：2026-10-03（Asia/Shanghai）。**未写入设备。**

## 构建

- ESP-IDF 提交 `7b9cc1ac79f865983f59bb8ff3ff43eb74ff1dbe`；编译 doctor 确认 S31 与 >=6.2 约束满足。
- Hello World 验证构建通过，bootloader、partition-table、hello_world BIN 存在且非空。
- LAN Screen 最终构建：`IDF LOW-NOISE BUILD: OK`，应用 1,839,664 bytes。
- 最终完整日志：`vendor/esp-mosaico-vibe/projects/lan_screen/.codex-runs/idf-low-noise-build/20261003-164537-build-79018/raw.log`。
- 唯一最终构建警告：应用大于保留的 factory 分区（0x1c0000）；目标安装分区是 ota_0（0xcf0000），有足够空间，更新清单不写 factory。不能因此改写保留分区或使用直接 flash。
- Iris 包 1,135,227 bytes，官方 bundle inspect 已读取组件哈希及目标布局；本地无签名开发包，`signature_verified=false`，不是签名验证通过。
- 更新内容为分区表与 ota_0 应用；不包含 bootloader、factory、sysmeta、NVS 或外部 UI 资源镜像。实际设备布局仍需连机检查，不能据此保证与当前 ESP-Claw 数据布局兼容。
- 导出：`dist/lan_screen/`，含应用 BIN、Iris 包和 SHA256SUMS。应用 BIN 不是完整整机 BIN。

## 主机验证

1. 实际 C 手势与 JPEG 头检查：通过 UBSan；包括所有页面全局返回、设置入口、横向分页、截断/错误格式/错误尺寸和 100,000 次随机边界输入。
2. 实际 C 帧池代码：pthread 代替 RTOS mutex，通过最新帧覆盖、解码中缓冲保护、满池错误、20,000 次并发提交。
3. 实际 `screen_ui.c` + LVGL 9.5.0：设置、扫描按钮、选择 SSID、密码校验、Join、开放网络、键盘打开时全局返回、状态三页切换。指针输入英文键盘 q 键也通过。页面截图在工程 `sim/artifacts/`。
4. PC 客户端：2 个 unittest 通过，使用真实本地 WebSocket 与 Pillow JPEG，覆盖并发发送 ACK 对应与拒绝处理。并发编码完成顺序不保证，测试检查 ACK 集合而不假定调用顺序。
5. ASan 在这台 Mac 的运行时初始化阶段停滞，未运行测试逻辑；改用 UBSan。不能声称通过 ASan。

## 设备烧录与运行状态（2026-10-03 20:38）

1. **Vibe Mode 恢复与就绪**：
   - 通过 `mosaico recover` 恢复 base 固件，Vibe Mode 0.1.4 成功就绪（Device ID: `4553502d4952495301001c2904d0ad2a`，Boot ID: `9420797456668110722`）。
   - 抓取实机截图 `docs/hardware/2026-10-03-vibe-mode-screen.png`，屏幕成功点亮并显示“ESP-MOSAICO Vibe Mode - Ready for your next idea”。
2. **系统更新写入**：
   - 执行 `PATH=/opt/homebrew/bin:$PATH python3 mosaico.py iris system-update --project projects/lan_screen --skip-build`。
   - 分区表（0x8000, 4KB）及应用（0x210000, 1.84MB）经 USB Highspeed 传输完成（exit code 0）。
   - 目标固件契约验证通过：`validation: target firmware and system partitions are healthy`。
3. **首版正常运行核验**：
   - 设备自动重启进入 `normal` 模式，项目为 `lan_screen` 1.0.0（新 Boot ID: `7243000534277443063`，reset_reason 3 软件重启，crash_count 0）。
   - 剩余内存充足：Free Internal SRAM 249 KB，Free SPIRAM 13.0 MB。
   - BQ27220 电池计成功上线（SDA 56, SCL 3，实测 4183 mV）。
   - 屏幕背光已设置为 80%，LVGL 启动进入 `PAGE_HOME` 主页面（显示“LAN SCREEN - Set up Wi-Fi to begin”）。
   - 日志观察到 `cst9220: Malformed report header: first=0xab marker=0xab`，触摸交互与配网需实机由用户触摸验证。

## 2026-10-03 20:48 运行与交互优化

1. **真实 Wi-Fi 连通**：
   - 设备成功通过 NVS 自动重连至 `2-3-2G-wifi5`，取得局域网 IP `192.168.5.61`。
   - REST 接口 `http://192.168.5.61/api/status` 与传感器接口正常提供数据。
2. **局域网推流首测**：
   - 经 `client/mosaico_screen.py` 推送 6 帧 480×480 JPEG 测试画面。
   - 统计结果：`received: 6, displayed: 6, dropped: 0, invalid: 0`。
   - 实测硬件解码耗时约 5.3 ms，LCD DMA 耗时约 23.5 ms，整体接收到完成显示延时约 32.3 ms。
3. **触摸卡顿与无响应修复**：
   - 修复 `esp_lcd_touch_cst9220.c`：当没有手指触摸处于空闲状态时，芯片返回 `CST9220_REPORT_ACK`（0xAB），驱动原先将其误判为格式错误并以 200 Hz 频率狂刷警告日志，导致 CPU 占用高、日志丢失且触摸迟钝。已优化为空闲快速返回，彻底消除无用日志。
   - 扩大滑动手势边缘热区：底部返回手势从严格的末尾 32px（y>=448）放宽至底部 80px（y>=400，dy<-36），避免拇指边缘判定失败。
4. **导航防困与回退优化**：
   - 密码输入页增加顶栏 `< Back` 与密码行 `Cancel` 按钮，随时可点击取消退回 Wi-Fi 列表。
   - Wi-Fi 列表页增加顶栏 `< Back` 按钮，并将列表高度缩短防止误触最后一项。
   - 所有二级页面底部统一设置宽幅 `< Tap or Swipe Up to Return >` 按钮，支持轻点或上滑返回主画面。

## 待实机验证项

- 键盘打字输入与多 Wi-Fi 切换交互流畅度。
- 480×480 30 FPS 高帧率推流时的撕裂与网络丢包表现。
- 侧面扩展模块识别与摄像头预览。
