# 项目文档索引

更新：2026-10-29。当前基线 **LAN Screen 1.1.54**。已全面落地 SPI Flash 持久化字库与 PSRAM LRU 缓存系统、13 种 Agent 专属动效脸、全双工 WebSocket Hub 及 Agent 伴侣界面。

---

## 核心固件与协议文档

- [当前功能与交付状态（1.1.54）](../vendor/esp-mosaico-vibe/projects/lan_screen/docs/current-state.md)
- [REST 与 WebSocket API 规范](../vendor/esp-mosaico-vibe/projects/lan_screen/docs/api.md)
- [固件系统架构说明](../vendor/esp-mosaico-vibe/projects/lan_screen/docs/architecture.md)
- [交互子板（按键与 50Hz 原生 LED）接口规范](development/interaction-subboard-api.md)
- [开发、编译与刷机交付指南](../vendor/esp-mosaico-vibe/projects/lan_screen/docs/development.md)

---

## 最新版本交付记录

- [1.1.54 SPI Flash 持久化字库与 PSRAM LRU 动态按需缓存系统](development/2026-10-29-persistent-flash-font-1.1.54.md)
- [1.1.53 Agent 专属工作中表情动效（13 种面孔与轮换）](development/2026-10-28-agent-avatars-1.1.53.md)
- [1.1.48 Claude 设计 Agent 伴侣界面全新重构](development/2026-10-28-agent-companion-ui-1.1.48.md)
- [1.1.47 卡片索引与 WebSocket RFC 合规性修复](development/2026-10-25-fix-card-index-and-ws-rfc-1.1.47.md)
- [1.1.46 确认卡片索引精准定位与 LED 槽位寻址](development/2026-10-25-confirm-card-index-led-slot-1.1.46.md)
- [1.1.45 全双工 WebSocket Hub 事件总线与反向直推](development/2026-10-25-websocket-hub-event-bus-1.1.45.md)
- [1.1.44 稳定性与防假死/重启修复](development/2026-10-25-fix-freeze-reboot-1.1.44.md)
- [1.1.43 Claude UI 设计稿一期落地](development/2026-10-25-claude-ui-design-v1.1.43.md)
- [1.1.42 UX 体验与代码健壮性重构](development/2026-10-25-ux-code-refactor-1.1.42.md)
- [1.1.41 SSDP / UPnP 局域网服务发现](development/2026-10-19-ssdp-upnp-discovery-1.1.41.md)
- [1.1.40 顶栏电池死锁修复](development/2026-10-19-gui-deadlock-fix-1.1.40.md)
- [1.1.39 电量计自愈与电池指示](development/2026-10-19-battery-ui-gauge-recovery-1.1.39.md)

---

## 硬件与建模

- [ESP-Mosaico 实物观察与硬件接线](hardware/2026-10-02-device-observations.md)
- [多材质外壳与双色导光板 3D 打印模型](../hardware/interaction-shell-multimaterial-diffuser/)
- [六轴 IMU 姿态校准参数](development/orientation-calibration.json)
