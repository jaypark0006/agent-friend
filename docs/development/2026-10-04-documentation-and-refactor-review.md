# 文档整理与架构review（2026-10-04）

用户要求更新文档、review架构并形成refactor计划。本轮以1.1.24源码1075a9f/交付文档ce90dd7为基线，只做静态阅读与文档修改；未运行测试、应用、浏览器验证、硬件采样，也未编译或刷机。最近安装仍为1.1.24。

交付统一文档入口、当前状态、API、开发流程、架构审查和重构计划；旧应用README完整归档，外层版本专题/历史记录增加适用范围标识。官方资料仍按原核对日期保留，不宣称重新调查latest。

- [应用文档索引](../../vendor/esp-mosaico-vibe/projects/lan_screen/docs/README.md)
- [架构审查](../../vendor/esp-mosaico-vibe/projects/lan_screen/docs/architecture-review.md)
- [重构计划](../../vendor/esp-mosaico-vibe/projects/lan_screen/docs/refactor-plan.md)

优先事项：共享锁中LVGL/JSON/NVS/大拷贝；相机原始API与设备页控制冲突；图片历史/摄像头缓冲预算；页面状态控制器；协议定义/错误适配；网页生命周期模块。具体证据、触发路径、静态推导与实测边界已区分。推荐从命令/快照边界开始，再收敛相机状态、显示控制器，最后做内存及网页拆分；不一次性换框架。

没有新增功能或执行重构；计划中后续功能批次仍遵守每次commit、编译与官方刷入，测试须当次明确请求。旧测试/模拟器文件保留原样。

固件应用文档提交：`47780a0`。外层仓库随本次提交保存更新后的完整Git bundle与子模块指针；没有公开推送。
