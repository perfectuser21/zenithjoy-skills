# 抖音直链入口

## 输入归一化

运行 `scripts/normalize-input.mjs`，只接受抖音域名。结果为 `direct_url` 时必须保存 `normalized-input.json`，并把 `original_url`、`resolved_url`、`video_id`、`app_uri` 写入候选证据。

短链解析失败时仍可把原短链交给抖音 App 打开，但证据标记 `resolution_status=unresolved`。不得把非抖音 URL 当作直链任务。

## 手机打开与核对

1. 取得手机锁并核对绑定设备。
2. 有 `app_uri` 时，通过绑定设备执行单条 ADB VIEW intent 打开；否则打开 `resolved_url` 或 `original_url`。
3. 等待页面稳定后截图并回传视觉检查。截图必须按三条独立命令执行：先在 Android 写 `/sdcard/<job_id>-direct.png`，再用 `adb pull` 拉到 Mac 白名单目录 `/private/tmp/openclaw-phone/<job_id>-direct.png`，最后让 `file_fetch` 读取这个 Mac 路径。不得让 `file_fetch` 读取 Android 路径，也不得用 `adb shell mkdir` 创建 Mac 目录。遇到浏览器选择页，可选择已登录的抖音 App；遇到登录、验证码或风控立即 blocked。
4. 核对视频详情，不接受首页、搜索页、广告落地页或推荐流中的其他视频。视频 ID、标题、作者三项至少两项一致才通过；只有视频 ID 可验证时，以视频 ID 为强证据。
5. 写 `candidate.json`，`input_mode=direct_url`，候选数量固定为 1。然后进入共用 acquisition、transcription、delivery。

## 获取顺序

Mac 优先使用解析后的 `video_id` 和现有无登录浏览器/CDP 解析器取流；失败后尝试已登录 Chrome，仍失败再用手机内部音频/录屏兜底。作者关闭“保存本地”不改变此顺序，但不得绕过 DRM、付费墙、验证码或访问权限。

## 验收证据

保留输入归一化 JSON、打开后的手机截图、页面核对结论、媒体 ffprobe、ASR 分片、原始稿、清洗稿、飞书记录和文档回读结果。
