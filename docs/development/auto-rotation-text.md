# 自动旋转与文字 API 交付

2026-10-03，ESP-Mosaico LAN Screen，当前1.0.4。用户授权设备本地重力旋转、指定字号文字API；所有代码和验证摘要提交Git，根仓库存完整固件bundle。

## 当前功能

- 设备对图片、LVGL菜单与文字做CO5300 MADCTL硬件旋转，并由BSP同步逆变换触摸坐标；PC发送原始方向JPEG即可。默认自动模式，API返回auto_rotation与实际display_rotation_cw_deg。
- IMU稳定侧边朝下时应用0/90/180/270；平放、运动、模糊/过期结果或按住触屏时保留角度。启动默认0。切换前排空LCD DMA，静态照片即使停止推送也会重绘。传感器姿态见原orientation-api.md。
- POST /api/text：JSON text（UTF-8≤1024字节）、font_size（整数16–64，默认32）、align（left/center/right，默认left）。设备直接排版，换行、自动折行，432×384区域，超出高度裁切；16px位图字形放大，非任意矢量字体。
- 基础汉字、ASCII、Latin-1（含·）、常用中英文标点、全角字符有嵌入字库；设置页也使用完整CJK后备字库。Emoji、扩展区汉字等未覆盖字符可能显示占位，不承诺所有Unicode字形。
- 文字和图片互相替换；最新文本丢弃排队旧JPEG，正在解码图片提交前检查模式；菜单不会被推送关闭，上滑回到最新内容。status的content_generation与displayed_content_generation可确认文字已绘制；图片逐帧完成继续看displayed。Python有post_text/send_text。
- 设备首页有文字输入、字号、对齐和发送控件。

## 已发现并修复的实机问题

首次1.0.3刷入与文字/WS验证通过，但用户指出六方向不旋转。实际orientation=unavailable；官方Iris日志BMI270 initialization failed: sensor_result=-9 load_status=0x00。此为配置加载失败，不能把健康重连当作旋转验收。旧传感器任务只初始化一次，失败永久不再读取。

1.0.4增加2秒间隔IMU初始化/启动重试；连续10次读取失败重建该IMU设备，不重置触摸/电池共享电源或I2C总线。API提供imu_init_attempts/imu_error。当前实机第1次初始化成功、ESP_OK，恢复有效重力姿态；未故意注入配置加载失败，重试路径不是故障注入实测。

首次字库缺少演示的中间点·，设置页仍为旧子集。1.0.4补充Latin-1/通用标点，并复用新字库；模拟器直接检验换、！、·、—在文字与设置后备字体均非占位字形，排版PNG已检查。

## 验证与边界

UBSan通过六面姿态、运动/自由落体/无效/时钟回绕、旋转策略（触摸/平放/过期保持）、UTF-8与字号边界、真实最新帧池20,000并发提交。共享LVGL模拟器通过四向触摸映射的键盘/边缘手势，以及16/32/48/64字体、文字返回与切回图片。3项Python客户端测试、页面脚本Node语法检查通过。

最终构建20261003-231759-build-20343成功，4,555,040字节，2条构建警告，未修改保留分区布局。原始日志位于固件工程.codex-runs/idf-low-noise-build对应目录。图像解码和菜单是共用同一个显示任务，截图模拟不代替实体手势体验。

设备4553502d4952495301001c2904d0ad2a；更新操作fdc14454-7a00-49a7-82ec-ce2eb8d7a2f2。normal Boot 12958330531850462200 → Vibe Boot 17497417470943231150 →1.0.4 normal Boot 17801389767245043844；healthy=true、crash_count=0，ELF SHA b63dcb3eb04e5527bee8da6eb2e14f24fecc65c28ee95daf7a522b6218b506cb与设备匹配。

实机4个字号请求/显示版本推进通过，6种非法输入HTTP400，空文本清屏通过，10次WS带自动旋转字段。文字演示后恢复姚明照片；invalid=0。当前姿态back/screen_up，角度建议null、实际角度0，符合平放保留规则。

4秒重复静态姚明JPEG推流回归：收到27帧，实际显示27帧，平均6.11 FPS。这是60KB照片的局域网短时测试，和较小的PC生成JPEG不是同等负载。随后约4秒运行现有生成画面demo，接收并显示94帧（约23FPS），invalid=0，解码约5.33ms、LCD约23.47ms；不承诺持续30 FPS。

用户被请求重新竖立侧边测试，但目前保存的60秒真实姿态序列只有平放与实际0°，90/180/270物理显示/触摸仍待反馈。不能据此声称已实物逐一验收四方向；1.0.3用户失败反馈已记录，上述修复对应1.0.4。

## 截图核查

现有LAN Screen未注册esp_iris_screen_backend_t。虽然通用能力公告有screen，官方mosaico.py iris screenshot实际返回screen mirror has an empty frame description。本次未添加截图或实时屏幕镜像，不能直接实时看到设备实际像素。模拟器PNG仅是UI排版证据。

## 证据

- [1.0.4更新记录](2026-10-03-rotation-text-1.0.4-update.json)
- [1.0.4文字与REST/WS](2026-10-03-rotation-text-1.0.4-validation.json)
- [短时推流回归](2026-10-03-1.0.4-stream-regression.json)
- [当前姿态观察](2026-10-03-auto-rotation-live.json)
- [1.0.3历史验证](2026-10-03-rotation-text-validation.json)
- [1.0.3历史更新](2026-10-03-rotation-text-1.0.3-update.json)

固件提交：自动旋转76ab69e；文字与字库d39b714；IMU恢复0569389；标点/设置字库ee66145。文档更新不改变已安装代码与ELF SHA。

## 后续实体复核：180° 已通过

用户再次报告“重力感应依然没有”，本轮没有修改或重刷旋转代码，设备仍是1.0.4。初次记录只出现平放与Type-C朝下（角度0），未捕捉到应改变角度的姿态，不能凭此把功能认定为失效。重新请用户保持橙色AI键朝下、Type-C朝上、屏幕竖直的倒立姿态，连续记录明确得到accel Y约−0.98g、down_face=top、建议180°、实际已应用180°，官方Iris日志确认CO5300 rotation set to 180 (touch synchronized)。

用户反馈“文字已经自动转正”，因此180°旋转链路从实际传感器、算法、LCD驱动到人眼看到文字转正已验证。IMU本轮始终ESP_OK，无新Boot/更新。实体90°/270°以及旋转后的触摸仍未逐一验收。平放只绕屏幕法线转动不能改变重力平面内方向，现有实现保持之前角度；本功能不是磁北罗盘。

结构化记录：[180° 实体确认](2026-10-03-rotation-180-physical.json)。此前“待实体反馈”描述前一阶段，现在新增180°验收，不应删掉1.0.3失败的历史记录。
