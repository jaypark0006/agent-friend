# 灯光503初始化修复：LAN Screen 1.1.27

交付日期：2026-10-09（Asia/Shanghai）。用户报告灯光控制返回HTTP503，随后明确授权修复。遵循默认编译/刷入与Git提交要求；本轮没有编写或运行测试、灯光控制试推、浏览器验证、摄像头采集或性能测量。

## 原因和修复

修复前只读诊断：192.168.5.137运行1.1.26，右槽板型22、initialized=true、valid=true、error=ESP_OK，而顶层ready=false、error=ESP_ERR_INVALID_STATE。源码中相机与交互任务都调用共享mosaico_module_mgr_init；BSP在管理器正在启动时返回INVALID_STATE，交互任务只尝试一次并永久保留失败状态。随后发现/打开右槽成功仍不能解除HTTP控制的全局ready门槛。

代码提交609effb：将管理器初始化纳入每500ms发现周期，失败重试，成功后在interact锁下同步发布ready=true/error=ESP_OK；失败期间不访问管理器信息，成功后不重复初始化。保留板型识别、插槽初始化、session保护与HTTP503限制，不绕过管理器或重置扩展供电。同步版本配置、API和架构说明。

## 编译与安装

- 固定ESP-IDF：7b9cc1ac79f865983f59bb8ff3ff43eb74ff1dbe，esp32s31；doctor确认约束和目标支持。
- 构建：20261009-084630-build-22876，exit=0；BIN4,975,408字节。摘要2条警告；完整日志保留SDK私有包含目录、managed_components额外目录与factory分区尺寸提示，没有改变分区布局。
- 第一次沙箱构建因组件管理器读取进程信息被禁止而失败；权限提升后同一固定环境构建成功，没有改SDK或依赖规避。
- 官方iris app-update --skip-build，operation 54dc4c30-3ad9-43d7-abac-4021eef5fed5，succeeded/healthy。开始时已处于Vibe Mode0.1.4，Boot ID1161200027678441840；工具安装后返回正常应用。
- Device ID：4553502d4952495301001c2904d0ad2a，USB location=1-1；安装后1.1.27、normal/healthy、crash_count=0、stale=false。
- 新Boot ID：4813937457542206368。
- ELF SHA256：a34847dbabc405bffb1c83b3df8c60997b70ae823fed84ab69695a271e836b78。
- BIN SHA256：c860e82f4390bdbe177487b53e5f00ab0f70e8f8a888b8efbdd11ad7b4ea3c81。

原始日志（忽略文件）：子仓库.codex-runs/mosaico/20261009T004721Z-install/raw.log、20261009T004809Z-device-status/raw.log；应用.codex-runs/idf-low-noise-build/20261009-084630-build-22876/raw.log。

安装确认只说明版本与交付链路，不代表灯光实际效果已验收；由用户体验反馈。默认mosaico-notify收尾一次，身份匹配192.168.5.137，文字/配图/切页均返回accepted，不作为显示或已读确认。固件与文档提交、根仓库bundle和指针保存；没有推公开远程。
