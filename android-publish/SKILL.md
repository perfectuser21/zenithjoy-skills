---
name: android-publish
description: "安卓真机多平台发布公共底座：设备锁、素材传输、中文输入、内容安全和结果验收。用于手机发布及 agent-android 发布功能开发；平台操作序列查对应 android-平台-publish。"
---

# 安卓真机多平台发布 · 公共底座

## 核心原则：不绑机型

**所有平台 skill 的步骤以 UI 语义锚点为准**（"点击文本『下一步』的按钮"），坐标只是
小龙虾（1200x2664）上的实测参考。换设备时：截图 + `uiautomator dump` 按文字找控件算中心点再点。
⚠️ dump 会抓错窗口（实测抓到过 Agent 界面），必须先 `dumpsys window | grep mCurrentFocus` 验证前台，
截图 ground truth 永远优先（RPA 死规则）。

## 设备通道（发布机不唯一，先寻机再干活）

发布机 = 任何登了目标平台账号、ADB 在线的安卓机。领单后先确认 platform → 查下表选机，
机器不在线/账号不对 → 停下报告，禁在错误账号上发。

| 机器 | 序列号 | 宿主 | 命令模板 |
|---|---|---|---|
| 小龙虾（HONOR 100，家里） | `ANGYVB4311010223` | **xian-m1（macOS，0917 实测更新）**，历史曾在 xian-rog（Windows），会跨机移动，用前先 `adb devices` 确认当前宿主 | `ssh xian-m1 "adb -s <serial> <cmd>"` |
| 金诺机（HONOR MAA-AN00，办公室） | `ANGYVB4227006983` | xian-m4（macOS） | `ssh xian-m4 "adb -s <serial> <cmd>"` |

- 小龙虾：2026-08-29 起 USB ADB 可用（HONOR Suite 官方驱动，详见 memory machines.md）；
  WiFi 备份 `192.168.1.96:5555`；看门狗 `ZJPhone4Watchdog` 每5分钟自愈。
  rog 的 adb server 随 SSH 会话死，自动重启属正常。
- 截图回传循环（每步必做）——rog（Windows 宿主）走文件中转：
  ```
  ssh xian-rog "adb -s <serial> shell screencap -p /sdcard/s.png & adb -s <serial> pull /sdcard/s.png C:\Users\Public\s.png"
  scp xian-rog:C:/Users/Public/s.png <本地> && Read 看图再决定下一步
  ```
  m4（macOS 宿主）走 base64 管道更快（0909 实战）：
  ```
  ssh xian-m4 "adb -s <serial> shell screencap -p /sdcard/s.png; adb -s <serial> pull /sdcard/s.png /tmp/s.png 1>&2; base64 -i /tmp/s.png" 2>/dev/null | base64 -d > <本地>.png
  ```
  ⚠️ 管道里混入其他 stdout 行（ime set 的回显等）会毒化 base64 流——动作命令与截图命令分开跑，或把杂音重定向到 stderr。
- 启动 App 用 `monkey -p <pkg> -c android.intent.category.LAUNCHER 1`；不生效时先 `input keyevent 3`
  回桌面清场再 `am start -n <pkg>/<activity>`。任务栈里多个 App 会互抢前台（实测快手点配乐时被抖音抢走），
  操作前必验 `mCurrentFocus`。

## 内容安全铁律（主理人拍板 2026-08-30，违反=封号风险）

1. 测试内容必须像真人随手发：禁彩条测试图、禁"测试/自动化/test"字样。
   模板：ffmpeg 治愈系渐变视频 + 生活化文案（"今日份的治愈色"）。
2. **所有平台自动配乐一律取消**——我们的视频是剪好的成品，再叠 BGM 就乱了（主理人原话）。
   小红书/快手会自动配乐（须手动去掉，法子见各自 skill），抖音/头条/微博/B站不会。
3. 测试视频文件名采用 `VID_<yyyymmdd>_<hhmmss>.mp4`。发布前读回「私密／仅自己可见」。B 站视频应按平台 Skill 检查投稿「更多设置」，无法确认私密时暂停。
4. 手机相册既有照片是私人照片，绝不当素材、绝不外传（0830 实证）。
5. 发布中断不确定 → 落"待人工核实"，禁自动重发；平台风控报"频繁"→ 存草稿撤退，等冷却，不硬刚。

## 素材下发（正式发布 = 从发布包下载，全平台通用）

正式任务的素材**只来自发布包 media[].url**（COS 现签 URL，TTL 1 小时，超时重领包），禁现编：

```bash
# 1. 领包后取 media[0].url / file_name，下载到执行机宿主
ssh <宿主> "curl -sL -o /tmp/<file_name> '<media.url>'"
# 2. push 到手机相册 + 媒体扫描（文件名保持相机风格：IMG_<yyyymmdd>_<hhmmss>.jpg / VID_..._.mp4）
ssh <宿主> "adb -s <serial> push /tmp/<file_name> /sdcard/DCIM/Camera/<file_name>; \
  adb -s <serial> shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/DCIM/Camera/<file_name>"
# 3. 相册选中后必须核验选的是这张（0909 实证误选旧图）：截图后按素材已知配色/内容比对（PIL 抽像素色即可）
```

蹚路/演练造测试素材（无作业单时才用）：
```
ffmpeg -y -f lavfi -i "gradients=size=720x1280:speed=0.013:duration=10:nb_colors=4:c0=0xFFB6C1:c1=0x87CEEB:c2=0xFFDAB9:c3=0xE6E6FA" \
  -f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=44100" -t 10 -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest out.mp4
# 本机 ffmpeg 无 drawtext（缺 freetype）；产物 scp 到宿主再按上面 push
```

## 中文输入（ADBKeyboard，已装）

```
adb shell ime enable com.android.adbkeyboard/.AdbIME   # ⚠️ ime reset 会禁用它，用前必须先 enable
adb shell ime set com.android.adbkeyboard/.AdbIME
adb shell input tap <文本框>                             # 先聚焦
adb shell am broadcast -a ADB_INPUT_B64 --es msg $(printf '中文' | base64)   # 必须 base64
# 收尾恢复：adb shell ime reset（回百度输入法）
```
额外招：小红书标题可直接点平台推荐的标题 chip，免输入法且更自然。

## 通用验收法（发完必做，"没报错"≠成功）

回"我"页反查：作品/笔记计数 +1、列表第一格=新视频、日期=今天，截图存档。
各平台成功信号不同：小红书/快手有"发布成功"提示，抖音/微博静默回信息流（必须反查计数）。

## 发布类动作单次铁律（2026-09-12 补，防重复发布）

"发布/发作品/发送/投稿"类按钮，**同一个任务生命周期内只能点一次**——尤其是抖音/微博/快手这类
"静默回信息流、无成功提示"的平台，最容易被误判成"没反应=没点中"进而重新点击，而实际后台已经在处理，
在状态未知时再次点击可能重复发帖。

点完发布按钮后按此顺序处理，**任何情况下都不重新点发布/发作品/发送按钮**：
1. 按上方「通用验收法」反查计数是否 +1。
2. 计数没变化 → 不要重新点。等 10-20s（可能只是转码/列表刷新延迟）→ 再截图反查一次。
3. 仍没变化 → 落"待人工核实"（同「内容安全铁律」第5条），按「领单协议」回 `failed` +
   detail 写清楚现场（卡在哪一步、截图看到什么），禁止自行判断"再点一次试试"。

## 平台状态索引（2026-09-09 更新：账号按机器分列，领单后按 platform+机器在线情况选行）

小龙虾（0830 蹚路机，账号如下）：

| 平台 | skill | 账号 | 状态 |
|---|---|---|---|
| 抖音 | android-douyin-publish | 秦军餐饮 perfect21xx | ✅ 全链路验证（私密作品263） |
| 小红书 | android-xiaohongshu-publish | 徐先生企业自媒体 xuxiansheng_lzc | ✅ 全链路验证（私密笔记207+1） |
| 快手 | android-kuaishou-publish | 徐先生聊职场 | ✅ 全链路验证（私密） |
| 头条 | android-toutiao-publish | 大湖卓越成长（抖音一键登录） | ✅ 全链路验证（仅我可见，作品23） |
| 微博 | android-weibo-publish | 再见PerfectXX | ✅ 全链路验证（仅自己可见，微博6） |
| B站 | android-bilibili-publish | 新号未设昵称 | 上传成功，投稿被「过于频繁」拦截，草稿已保留。视频私密能力以当前账号的「更多设置」为准 |
| 微信视频号 | （待通） | 大湖成长之路-Ai+（微信zenithjoyai） | ⛔ 发表需绑手机号，等主理人定号码 |
| 知乎 | （待通） | 大湖-企业AI方案（微信授权登录） | ⛔ 发布功能需绑手机号，等主理人定号码 |

金诺机（0909 起领单协议实战机，两单均全链路含中台回执）：

| 平台 | 账号 | 状态 |
|---|---|---|
| 抖音 | 躺赢AI学姐 langzi63485 | ✅ 领单协议首单（0909《傍晚的调色盘》，私密） |
| 快手 | 茂辰养老护理服务 快手号2819032020 | ✅ 领单协议第二单（0909《云朵滤镜》，私密作品1→2） |

## 领单协议（2026-09-09 起，刀1-3a 已通：发布内容从中台发布包拿，禁执行器现编）

发布任务来自中台「作品→发布任务」链（PR#1791/#1795/#1800）。执行器（AI+skill）每次发布按此协议走，**标题/文案以发布包为准，一字不加不改**：

```bash
API='ssh hk-vps curl -s http://127.0.0.1:5201'   # staging；生产 promote 后换生产地址
TOKEN='<租户 license，主理人=ZJ-E-ALEX5211>'

# 1. 发现作业单（只看排队中的）
$API/api/publish-tasks?status=queued -H "X-Upload-Token: $TOKEN"
# 2. 领包（现签素材 URL，1 小时内完成下载）
$API/api/publish-tasks/<task_id>/package -H "X-Upload-Token: $TOKEN"
#    → {title, body, content_type, platform, media:[{url,file_name,mime_type}]}
# 3. 下载 media → scp 到执行机 → adb push 到手机相册（见上方「素材下发」，文件名相机风格）
# 4. 按 platform 对应的 android-<平台>-publish skill 序列发布：标题=title，文案=body
# 5. 回执（做完必回，成功失败都回）
$API/api/publish-tasks/<task_id>/receipt -X PATCH -H "X-Upload-Token: $TOKEN" \
  -H 'Content-Type: application/json' -d '{"result":"success","detail":"作品可见,计数+1"}'
#    失败: {"result":"failed","detail":"<现场一句话:哪一步/什么现象>"}
```

协议铁律：
1. **不确定成功绝不回 success**——按「通用验收法」反查计数+1 才算；拿不准回 failed + detail 留现场，宁可人工复核。
2. 回执幂等：任务已终态时重复回执返回当前态不改写（服务端 CAS），断线重试安全。
3. 领单前任务已不是 queued → 别发（别人领走或已撤）。
4. 回执落库后，Notion「发布编排台」会自动把每平台 ✅/❌ 写回主理人那一行——执行器不用碰 Notion。

## 对应立项

Brain journey `24987ee5`（line01）· 任务 `e4fd8c69` · 决策 `9f297223`。
phase3 = 把已验证序列固化进 services/agent-android（/dev，新增 publish 任务类型——现有安卓端无任何发布路由，
WS 只认 collect_task，HTTP 心跳 queued_tasks 无 publish 分支，全要新写）。

## 熟化流水线（0910 主理人拍板——每一跑都要迭代，不许盲跑）

**回流铁律**：每单发布后，踩到的新坑**必须当场回流对应平台 skill 并 commit**（新版坐标、新弹窗、新流程差异）；零新坑的单也是数据——它给该平台的熟化计数 +1。运行台账 = 中台 `publish_tasks` 回执（platform/machine/result 全在），不另建账本。

**熟化判据（固化触发器）**：同平台**连续 3 单零新坑、且跨 ≥2 台机器** → 该平台进入"可固化"状态 → 点火刀B，把序列写进 agent-android（Kotlin）。

**固化三层刀法**（流程死、定位活、视觉兜底）：
1. **流程层**（步骤顺序/前台校验/铁律/验收/回执）→ Kotlin 状态机，死代码，机型无关。
2. **定位层**→ **无障碍树语义查询优先**（按文本/desc/resource-id 找控件取 bounds 中心，天然跨分辨率）——本表的参考坐标只是无障碍树不可用时的回退；获客线 0909 实证连视频页图标都有真实 bounds+clickable，绝大多数控件不需要视觉。
3. **视觉兜底**→ 树里找不到的自绘控件/改版瞬间，截图问 AI 定位（on-call 模式，获客线同款），结果缓存进该设备坐标表，下次免问。

**固化后**：平台 skill 不删，降级为 AI on-call 救场手册。

熟化进度（0910 基线）：douyin 4单/3机 | kuaishou 1单 | xiaohongshu/weibo/toutiao/bilibili/zhihu/shipinhao 各1单 | wechat=纯代码通道已固化。

## 运行阶段协议（0910——每本平台 skill 头部必须带「熟化阶段」块，执行 AI 照阶段定姿态）

执行任何平台 skill 前，先读它头部的阶段块，按对应姿态跑；收尾时**更新阶段块**（这是回流铁律的一部分）：

- **EXPLORE**（第1单/新形态）：目标=蹚通。允许试错/绕路/重试；每步截图存档；收尾必须产出完整序列写进手册，阶段翻 VALIDATE。
- **VALIDATE**（第2单起）：目标=验证手册。**严格照手册执行，禁止即兴发挥**——手册坐标/锚点/预期与实际不符本身就是本次最重要的产出，必须回流。零偏差→计数+1；有偏差→修手册+计数清零。计数格式：`连续零新坑 N/3（机器清单）`。
- **HARDEN**（计数满 3/3 且 ≥2 台机）：目标=固化预备。本单照常发，但每步顺手 `uiautomator dump` 记录控件语义锚点（text/content-desc/resource-id），收尾产出"固化规格"（步骤×锚点清单）交刀B。
- **FROZEN**（已 Kotlin 化）：手册降级救场用。只在代码执行失败被 on-call 时打开，按现场截图处置，处置经验回流手册。

阶段块模板（放平台 skill 标题下第一段）：
```
> **熟化阶段：VALIDATE** · 连续零新坑 1/3（realme✅）· 上次更新 0910
> 本次姿态：严格照下表执行，任何偏差=发现→回流。
```

## 拟人纪律（0910 主理人拍板——对抗自动化画像，每单必须遵守）

**时间维度**：
1. 同一台机器上**两个平台的发布之间隔 ≥15 分钟**（随机 15-40 分钟更好）；绝不多平台秒级连发。
2. 发布时间贴人类作息：09:00-23:00 之间；同平台同账号**单日 ≤3 单**，测试期 ≤1 单。
3. 定时单排期时自动加 ±5 分钟抖动（编排台填 20:00，实发 19:57/20:04），避免整点齐射画像。

**操作维度**：
4. tap 坐标加 ±5px 随机抖动（别每次都点在同一个像素上）。
5. 步骤间 sleep 随机化：2-6 秒为常态，每 3-4 步夹一次 8-12 秒"犹豫"（人会看一眼再点）。
6. 长列表用变速滑动（swipe 时长 300-800ms 随机），不用等距匀速。
7. 文字输入后停 2-3 秒再进下一步（人打完字会检查一眼）。

**行为维度**：
8. 启动 App 后先停 3-5 秒（人不会 0 秒直奔发布按钮）；发完**别立刻退 App**，刷信息流 10-20 秒再走。
9. 偶尔混入无害闲逛动作（看一条视频滑走、进我页看一眼）——每 2-3 单一次即可，别每单都同一套。
10. 输入法用完即还原（已是铁律）；同机切换不同 App 账号操作之间留 ≥5 分钟冷却。

**画像自查**：如果回看今天的操作日志，一个真人做得出来吗？做不出来的模式（秒级跨App、像素级重复点击、凌晨3点发布）就是要消灭的特征。参考获客线频控实证：私信间隔 120-180s 随机、fail-open 教训。

## 设备锁协议（0917 生效——防多任务互抢手机，Brain device_locks 表纳管）

四台手机已按 serial 纳管进 Brain `device_locks`（migration 448，生产 v1.302.0 起）。**任何自动化占用手机前必须过锁**，两条路径：

**路径A：Brain 派发的任务（首选，全自动）**
建单时 payload 带 `device_serial`（即上方设备通道表的 serial），锁全自动：派发前抢锁（被占→留队列下轮重试；serial 未注册→任务判死+告警）、终态自动释放、超时 30 分钟 TTL 自愈。**除了建单带字段，什么都不用做。**

```bash
curl -s -X POST localhost:5221/api/brain/tasks -H "Content-Type: application/json" -d '{
  "title": "...", "task_type": "...",
  "payload": {"device_serial": "ANGYVB4311010223", "device_ttl_minutes": 60}
}'
# device_ttl_minutes 可选，默认 30，clamp [1,240]——预计超 30 分钟的长发布单自己带够
```

**路径B：有头/人肉直接操作手机（SOP 约束）**
开工前抢锁、收工释放；抢不到=有别的任务在用这台机，**换机或等待，禁止硬抢**：

```bash
# 抢锁（locked_by 用自由身份如 manual-alex；只受 TTL 管，不会被对账秒扫）
curl -s -X POST localhost:5221/api/brain/device-locks/acquire -H "Content-Type: application/json" \
  -d '{"device_name":"<serial>","locked_by":"manual-<who>","ttl_minutes":60}'
# → {"acquired":true,...} 才能动手机；{"acquired":false,"locked_by":...} = 被占，换机/等

# 收工释放（忘了释放 = 白占到 TTL 过期，别人干等）
curl -s -X POST localhost:5221/api/brain/device-locks/release -H "Content-Type: application/json" \
  -d '{"device_name":"<serial>","locked_by":"manual-<who>"}'
```

**辅助**：查占用 `GET localhost:5221/api/brain/device-locks`；新手机/换宿主幂等注册 `POST /api/brain/device-locks/register` body `{"device_name","host","device_type":"phone"}`。

**铁律**：①锁按 serial 键，宿主机只是登记信息——寻机（`adb devices`）之后、动手之前抢锁；②一次只锁自己要用的那台，用几台锁几台；③长任务锁被人抢不走（持有任务 in_progress 期间过期也不可抢），但收工必须释放，别靠 TTL 兜底。

## 触发范围与原运行约束

安卓真机多平台自动发布——公共底座（设备通道/素材下发/中文输入/内容安全铁律/通用验收法/各平台状态索引）。 各平台具体发布序列见独立 skill：android-douyin-publish / android-xiaohongshu-publish / android-kuaishou-publish / android-toutiao-publish / android-weibo-publish / android-bilibili-publish。 触发场景：安卓端发布视频 / 手机发布 / android publish / 小龙虾发布任务 / agent-android 发布功能开发。 2026-08-30 首轮真机蹚路：抖音/小红书/快手/头条/微博 5 平台全链路验证通过（决策 9f297223，任务 e4fd8c69）。
