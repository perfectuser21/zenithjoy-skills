---
name: douyin-leadgen-phone
description: "通过 XIAN-M4-PHONE 的 adb 操控已登录抖音 App，按飞书关键词配置搜索热点视频、从热门评论识别潜在客户、查重并写入飞书线索表。用于人工指令或 OpenClaw 定时采集；支持工作手机通话避让、限量运行和风控退出。"
---

# 抖音手机获客

这是独立的手机端 Skill，不依赖 Web 版 `douyin-leadgen`。执行前读取 [业务规则](references/business-rules.md)。

## 执行通道

- Agent：`media`，模型优先使用 Luna。
- Node：`XIAN-M4-PHONE`。
- 唯一目标手机：荣耀 MAA-AN00，USB 序列号 `ANGYVB4402004137`，抖音已登录。M4 同时连接多台手机，严禁自动选择其他 USB 或无线 adb 设备。
- 专用控制器：`/Users/jinnuoshengyuan/.local/bin/douyin-phone-adb`。它内部锁死目标序列号并限制允许动作。
- 所有手机命令都通过 `exec host=node node=XIAN-M4-PHONE` 执行。
- 只用截图识别界面，不依赖 UIAutomator 树。
- 每次 node exec 只执行一条以 `/Users/jinnuoshengyuan/.local/bin/douyin-phone-adb` 开头的命令。禁止直接调用 adb，也禁止在节点命令里使用 `set`、Shell 变量、管道、`&&`、`||` 或命令替换；需要多步时分成多次 exec。

## 默认运行策略

定时任务默认采用 `采集模式`：只搜索、判断、查重、写表，不点赞、不关注、不评论、不私信。只有用户明确授权“放开触达”时，才允许执行触达；验证码、风控页或账号异常时仍必须立即停止。

每轮默认上限：

- 按当前时段轮换选取最多 2 个启用关键词；
- 每个关键词查看最多 2 条热点视频；
- 每条视频查看热门评论前 30 条；
- 最多新增 10 条去重后的线索；
- 总时长达到 18 分钟立即收尾，不为凑数延长。

关键词轮换：把启用关键词按优先级降序排列；上午从第 1 条开始，下午从第 3 条开始，晚上从第 5 条开始，越界后循环。人工指令指定关键词或业务线时，以指令为准。

## 一轮执行

### 1. 安全预检

1. 执行 `/Users/jinnuoshengyuan/.local/bin/douyin-phone-adb status`，结果必须为 `ANGYVB4402004137 device MAA-AN00`。否则结束，绝不改用其他设备。
2. 单独执行 `/Users/jinnuoshengyuan/.local/bin/douyin-phone-adb telecom`，从返回文本判断是否正在通话；再单独截图确认是否显示来电界面。正在通话/来电就跳过本轮，不接听、不挂断、不解锁。
4. 截图确认屏幕可操作。锁屏且无法安全进入时跳过，不尝试密码。
5. 记录本轮开始时间和运行时段。时段一律按 `Asia/Shanghai` 判断；运行提示里的 UTC 时间要先加 8 小时。

截图：

```text
/Users/jinnuoshengyuan/.local/bin/douyin-phone-adb screencap
/Users/jinnuoshengyuan/.local/bin/douyin-phone-adb pull
```

`pull` 成功后，必须调用 `file_fetch`，参数固定为 `node=XIAN-M4-PHONE`、`path=/private/tmp/openclaw-phone/douyin-leadgen-shot.png`、`maxBytes=4000000`，用返回的图片做视觉判断。禁止让 `file_fetch` 读取 `/sdcard/...`；那是手机内部路径，不在 Mac 节点的允许读取目录中。

点击和滑动：

```text
/Users/jinnuoshengyuan/.local/bin/douyin-phone-adb tap <x> <y>
/Users/jinnuoshengyuan/.local/bin/douyin-phone-adb swipe <x1> <y1> <x2> <y2> <毫秒>
```

### 坐标换算（真机固定要求）

原始手机截图是 `1200×2664`，`file_fetch` 交给模型观看时通常缩放为 `923×2048`。不得把缩放图坐标直接发给 adb：

- `真机 x = round(缩放图 x × 1200 / 923)`
- `真机 y = round(缩放图 y × 2664 / 2048)`
- 当前两轴倍率约为 `1.30`。

每次点击后重新截图确认；如果 file_fetch 返回的观看尺寸变化，按新的观看尺寸重新计算，不沿用旧倍率。

### 2. 读取配置

飞书脚本位于 OpenClaw 容器，不在 M4。必须调用工具名为 `bash` 的网关本地执行工具，并以 `/root/clawd-media` 为 cwd；禁止用 `node_exec` 或 `exec host=node` 运行飞书脚本。使用下面两个完整命令读取关键词表和线索表，参数为位置参数，禁止改成 flags，也禁止无参数运行脚本：

```text
node /root/clawd-media/skills/douyin-leadgen-phone/scripts/feishu-bitable.mjs list H3OrbAH49aLNebs7XvOcpS1enec tblyKCp5vc7y2S40
node /root/clawd-media/skills/douyin-leadgen-phone/scripts/feishu-bitable.mjs list SMxlbynYqapWwWsBguzcmonkn2c tbltRdCwVMBNT40P
```

筛选启用项，按业务线和优先级应用本轮轮换。没有启用关键词时正常结束。

### 3. 搜索热点视频

用 deeplink 进入搜索：

```text
/Users/jinnuoshengyuan/.local/bin/douyin-phone-adb open-search <URL编码关键词>
```

等待页面稳定后截图，切到“视频”，选择近期且互动量明显较高的视频。每次点击、返回或滑动后重新截图确认，不凭旧坐标连续操作。

Deeplink 有时只把关键词填进搜索框，不会自动提交。如果截图显示“关键词已填入、键盘仍展开、正文空白”，在本机 `1200×2664` 分辨率下点击右上角搜索按钮中心约 `(1070,155)`，等待页面加载后重新截图；不要再次点击搜索框，也不要用未换算的缩放图坐标。连续两次提交仍无结果才结束本轮。

### 4. 筛选评论线索

打开热门评论区，只看前 30 条。按业务规则分成强意向、弱意向、同行、无关、广告异常五类；只保留强意向和弱意向，并排除反讽、抬杠、重复机器人评论。

点进评论者主页获取昵称和可用的主页标识。页面空白时重开最多两次；仍失败只跳过本条，不把用户永久排除。

### 5. 查重并写表

按“抖音昵称/主页链接”查重。不存在时用下面的完整形式写入线索表，状态设为“待触达”，同时保存业务线、命中关键词、评论原文和判断理由：

```text
node /root/clawd-media/skills/douyin-leadgen-phone/scripts/feishu-bitable.mjs create SMxlbynYqapWwWsBguzcmonkn2c tbltRdCwVMBNT40P '<FIELDS_JSON>'
```

写入后重新读取并核验。

### 6. 收尾与汇报

返回搜索前的安全页面或抖音首页，不停留在私信输入框。汇报：运行时段、关键词数、视频数、评论数、新增线索数、重复数、跳过原因、风控状态和飞书表地址。没有新增也要如实报告，不把零结果当失败。

## 强制退出条件

- 来电或通话开始；
- 验证码、滑块、账号限制或异常风控提示；
- adb 断开，连续两次截图失败；
- 页面连续两次与预期不符；
- 达到本轮数量或时间上限。

退出时禁止硬闯、禁止切换账号继续、禁止在不确定的输入框发送任何内容。
