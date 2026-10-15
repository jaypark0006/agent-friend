---
name: mosaico-notify
description: 向用户的 ESP-Mosaico 随身显示器推送任务过程进度、完成/失败通知及配图。用户已指定它为本机默认任务进度与完成通知设备；Antigravity / Codex / AI 智能体在长任务或多步执行期间上报实时进度，并在任务收尾时发送最终交付状态。
---

# Mosaico 随身通知与任务进度流

用户已授权：本机 Antigravity / Codex / AI 智能体在执行任务时，可将当前进度推送到随身屏；在完成有实际交付的任务时，向随身屏发送简短完成消息并生成配图。

## 一、任务执行过程中的进度推送（多 Agent 看板流水线）

在多步骤代码编写、重构、编译、测试等耗时任务期间，Agent 应当使用随附的 `progress.py` 上报当前步进度，随身屏会自动将进度按队列推送到屏幕看板（最多同时展示 3 个动态活跃进度，完成任务自动向上推入历史）：

```sh
# 上报执行中步骤（例如进度 50%）
python3 SKILL_DIR/scripts/progress.py --id 'antigravity' --title 'Antigravity' --status '正在修改代码与重构...' --progress 50 --color '#39e69d'

# 任务完成时标记 100% DONE
python3 SKILL_DIR/scripts/progress.py --id 'antigravity' --title 'Antigravity' --status '功能代码已全部交付并刷入' --progress 100 --done

# 移除指定 Agent 卡片
python3 SKILL_DIR/scripts/progress.py --id 'antigravity' --delete
```

* `id`：当前 Agent 或任务唯一标识符（如 `antigravity`、`codex`、`backend`、`tester`）。
* `title`：任务或 Agent 名称。
* `status`：当前正在执行的一行简短描述（≤64 字节）。
* `progress`：0..100 整数（-1 隐藏进度条；0..99 触发跑马灯流动光效）。
* `badge`：状态胶囊文本（如 `RUNNING`、`DONE`、`REVIEW` 等）。
* `color`：主题十六进制颜色（例如绿色 `#39e69d`、蓝色 `#4fa3e3`、黄色 `#e5c07b`）。
* `done`：标记为已完成。
* `delete`：从屏幕看板中移除对应任务卡片。

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

## 四、网络发现与设备端 REST API

* 固定目标硬件 MAC `1c:29:04:d0:ad:2a`。
* 优先使用 ARP、成功缓存和当前局域网网段动态发现，可通过 `--ip` 指定候选 IP。
* 设备端直接提供自描述端点与轻量 REST 接口：
  - `GET /skill`：返回设备自描述 Markdown 契约与使用示例；
  - `POST /api/widget`：直接推送多 Agent 进度（格式同 `progress.py` 发送的 JSON）；
  - `GET /api/widget`：查询当前活跃 Agent 列表、历史与状态；
  - `POST /api/text`：向消息流页面追加文字消息；
  - `GET /api/screenshot`：获取当前屏幕实时渲染帧（480x480 BMP）；
  - `GET /api/status`：获取当前设备运行状态、IP、Wi-Fi 与渲染帧率；
  - `GET /api/sensors`：获取姿态 IMU、电池电量、按键与交互子板状态。

## 五、维护与多 Agent 平台副本

本技能支持 Antigravity 与 Codex 多平台自动发现：
* 跟踪源：`/Users/qilei/mosaico/skills/mosaico-notify`
* Antigravity 工程级技能：`/Users/qilei/mosaico/.agents/skills/mosaico-notify`
* Antigravity 全局技能：`~/.gemini/config/skills/mosaico-notify`
* Codex 全局技能：`~/.codex/skills/mosaico-notify`
* 修改本技能时同步更新上述所有副本。
