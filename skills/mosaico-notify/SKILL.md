---
name: mosaico-notify
description: 向用户的 ESP-Mosaico 随身显示器推送任务过程进度、完成/失败通知及配图。用户已指定它为本机默认任务进度与完成通知设备；Codex/Agent 在长任务或多步执行期间上报实时进度，并在任务收尾时发送最终交付状态。
---

# Mosaico 随身通知与任务进度流

用户已授权：本机 Codex / AI 智能体在执行任务时，可将当前进度推送到随身屏；在完成有实际交付的任务时，向随身屏发送简短完成消息并生成配图。

## 一、任务执行过程中的进度推送（多 Agent 看板流水线）

在多步骤代码编写、重构、编译、测试等耗时任务期间，Agent 应当使用随附的 `progress.py` 上报当前步进度，随身屏会自动将进度按队列推送到屏幕看板（最多同时展示 3 个动态活跃进度，完成任务自动向上推入历史）：

```sh
# 上报执行中步骤（例如进度 50%）
python3 SKILL_DIR/scripts/progress.py --id 'codex' --title 'Codex' --status '正在修改代码与重构...' --progress 50 --color '#39e69d'

# 任务完成时标记 100% DONE
python3 SKILL_DIR/scripts/progress.py --id 'codex' --title 'Codex' --status '功能代码已全部交付并刷入' --progress 100 --done
```

* `id`：当前 Agent 或任务唯一标识符（如 `codex`、`backend`、`tester`）。
* `title`：任务或 Agent 名称。
* `status`：当前正在执行的一行简短描述（≤64 字节）。
* `progress`：0..100 整数（-1 隐藏进度条）。
* `color`：主题十六进制颜色（例如绿色 `#39e69d`、蓝色 `#4fa3e3`、黄色 `#e5c07b`）。
* `done`：标记为已完成。

## 二、触屏人工决策与交互授权（Human-in-the-Loop）

当 Agent 遇到关键步骤（如高危命令、生产部署、删除操作或方向选择）需要用户决策时，可以在随身屏弹出触摸按钮，并等待用户直接在屏幕上触控批准或取消：

```sh
# 屏幕弹出确认按钮，并在终端阻塞等待用户点击（输出 JSON 决策结果）：
python3 SKILL_DIR/scripts/progress.py --id 'deploy' --title '生产部署' \
  --status '准备发布到生产环境，请点屏幕确认' --progress 85 \
  --confirm --btn1 '批准' --btn2 '拒绝' --wait-confirm
```

* `--confirm`：在卡片下方渲染两个触控实体按钮；
* `--btn1` / `--btn2`：主按钮（默认 `Approve`）与副按钮（默认 `Cancel`）文本；
* `--wait-confirm`：自动轮询等待用户点击屏幕，用户触控后随身屏会给出翡翠绿/琥珀色闪烁反馈，并返回形如 `{"ip": "...", "decision": "批准"}` 的 JSON。

## 三、任务收尾通知（状态卡片与配图）

当有实际交付的任务最终收尾时，调用 `notify.py` 发送最终总结卡片：

```sh
python3 SKILL_DIR/scripts/notify.py --title '任务已完成' --text '已更新控制界面。已编译刷入；未做功能测试。' --status done
```

* status 为 done/error/attention。摘要 ≤1024 UTF-8 字节。
* 字体自动选择本机 PingFang 或 STHeiti。
* 用户要求不打断当前屏幕时加 `--keep-view`。

## 四、网络发现与设备边界

* 固定目标硬件 MAC `1c:29:04:d0:ad:2a`。
* 优先使用 ARP、成功缓存和当前局域网网段动态发现，可通过 `--ip` 指定候选 IP。
* 设备端已内置自描述技能端点 `http://<IP>/skill`，新接入的 Agent 亦可直接读取该端点自动获得完整 API 契约。

## 五、维护与全局副本

* 跟踪源：`/Users/qilei/mosaico/skills/mosaico-notify`
* 全局安装副本：`~/.codex/skills/mosaico-notify`
* 修改本技能时同步更新全局副本。
