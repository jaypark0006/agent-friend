# 1.1.61 画面页全黑屏防御与 README 产品级重构交付

## 一、 背景与根因剖析

### 1. 缺陷现象
用户实机测试中发现：在设备无任何历史图片时，如果切至「画面页（`PAGE_HOME`）」，屏幕可能彻底变黑，原本常驻展示的 Wi-Fi 连接向导二维码与界面完全丢失，且之后再怎么滑动或点击画面页均呈现死锁黑屏。

### 2. 核心根因核查（`replay_picture` 覆盖纯黑显存并置位 `stream_visible`）
在 `screen_display.c:407-415` 的主循环处理 `PAGE_HOME` 时：
```c
} else if(a->page==PAGE_HOME) {
    screen_display_wait(a); bool changed=false;
    screen_lock(a); int i=screen_history_find(&a->images,a->image_display_id);
    if(i>=0 && !a->touch_state.down && !a->transition_preparing) changed=screen_entry_expose(&a->images.entries[i],0,480,480,now);
    else screen_history_hide(&a->images);
    if(a->image_notice_unread!=screen_history_unread(&a->messages)) changed=true;
    screen_unlock(a);
    if(changed) { screen_renderer_badge(a,a->pixels[a->output_index^1]); replay_picture(a); }
}
```
1. 当设备从未接收过图片（`a->have_frame == false`），但系统收到了未读信笺（`message_unread > 0`）时，`a->image_notice_unread != screen_history_unread(&a->messages)` 判定为 `true`，触发 `changed = true`。
2. 随后调用了 `screen_renderer_badge` 和 `replay_picture(a)`。
3. `replay_picture(a)` 将未初始化的空显存缓冲区 `a->pixels[a->output_index^1]`（全 0 纯黑）通过 DMA 刷到了屏幕面板上，同时置位 `a->stream_visible = true`。
4. `a->stream_visible = true` 会导致 LVGL GUI 刷新被跳过（因为逻辑认为正在播放相机或图片全屏流），导致 LVGL 的二维码与 UI 永远无法重绘，屏幕陷入全黑状态！

---

## 二、 修复方案与验证

### 1. 固件防御补丁
在 `screen_display.c` 中：
1. `replay_picture(struct screen_app *a)` 首行加入前置拦截：
   ```c
   static void replay_picture(struct screen_app *a)
   {
       if(!a->have_frame) return;
       ...
   }
   ```
2. 在 `screen_display_task` 的 `else if(a->page==PAGE_HOME)` 块中严格以 `if(a->have_frame)` 隔离：
   ```c
   } else if(a->page==PAGE_HOME) {
       if(a->have_frame) {
           screen_display_wait(a); bool changed=false;
           screen_lock(a); int i=screen_history_find(&a->images,a->image_display_id);
           if(i>=0 && !a->touch_state.down && !a->transition_preparing) changed=screen_entry_expose(&a->images.entries[i],0,480,480,now);
           else screen_history_hide(&a->images);
           if(a->image_notice_unread!=screen_history_unread(&a->messages)) changed=true;
           screen_unlock(a);
           if(changed) { screen_renderer_badge(a,a->pixels[a->output_index^1]); replay_picture(a); }
       } else {
           screen_lock(a); screen_history_hide(&a->images); screen_unlock(a);
       }
   }
   ```
当 `!a->have_frame` 时，绝不调用 `replay_picture`，`stream_visible` 始终保持 `false`，LVGL 负责完整渲染页面二维码与提示文字。

### 2. 根目录 `README.md` 产品级重构
按用户体验与 Agent 接入规范全面重构根目录 `README.md`：
- **纯正产品视角**：面向智能体与桌面伴侣硬件，突出即插即用、全双工 WebSocket、板载 HTTP MCP（`/mcp`）与物理共享黑板。
- **零 Python 规范**：严格剔除所有 Python 环境依赖说明与脚本指令，`grep -i python README.md` 返回 0 匹配（退出码 1）。

---

## 三、 版本升级与工程构建

- 版本从 `1.1.60` 升级为 **`1.1.61`**（同步 `version.txt`、`CMakeLists.txt`、`agent_friend.py`）。
- 采用官方低噪音构建脚本（`idf_low_noise_build.py`），C 编译器 0 警告通过。
- 完整 BIN 大小：`12,097,737` 字节。
- ELF SHA-256：`b45b5f02a169c5e142f8995672d77caa4cfeb53b0ad1d994c81a29180de27a78`
- BIN SHA-256：`3d593a75d8662bcb27740dd8c9e3777ea68d17bb9e5ebc948504cb9fe654f78d`
- 子仓库提交：`f0d0dbc`
- 便携归档：`dependencies/esp-mosaico-vibe.bundle` 刷新并校验通过（4384 objects）
- 发行产物：`dist/release-v1.1.61/lan_screen_v1.1.61.bin`

---

## 四、 官方实机刷写与真机实测证据

### 1. 官方刷写（`iris app-update`）
通过官方 `iris app-update --skip-build` 成功刷入 USB 连接设备 `4553502d4952495301001c2904d0ad2a`：
```json
{
  "command": "device-status",
  "device_id": "4553502d4952495301001c2904d0ad2a",
  "boot_id": 1741174477194995284,
  "app_version": "1.1.61",
  "firmware_sha256": "b45b5f02a169c5e142f8995672d77caa4cfeb53b0ad1d994c81a29180de27a78",
  "firmware_mode": "normal",
  "crash_count": 0,
  "stale": false
}
```

### 2. 真机全黑屏防御验证
1. 投递未读信笺制造 `message_unread > 0` 且 `image_history_count == 0` 的触发条件：
   ```sh
   curl -s -X POST http://192.168.5.42/api/text \
     -H "Content-Type: application/json" \
     -d '{"text":"1.1.61 画面防黑屏测试：无图片但有未读信笺时，画面页二维码应当完好保留。","title":"系统自检","from":"scroll-fixer"}'
   ```
2. 切换至画面页：
   ```sh
   curl -s -X POST http://192.168.5.42/api/view -H "Content-Type: application/json" -d '{"page":"home"}'
   ```
3. 抓取实机显存截图 `http://192.168.5.42/api/screenshot` 检验像素数据：
   - 图像尺寸：480 × 480 16-bit BMP（460,800 字节像素）
   - 非零像素占比：**100.00%**（460800 / 460800），画面显示完整 UI 与引导内容，彻底杜绝纯黑死锁！
