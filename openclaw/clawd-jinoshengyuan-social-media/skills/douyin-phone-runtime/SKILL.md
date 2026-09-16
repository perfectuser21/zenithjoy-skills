---
name: douyin-phone-runtime
description: "Adapt generic social-video workflow actions to a tenant-selected logged-in Douyin Android phone through an OpenClaw Node and registered profile controller. Use for safe device preflight, search, screenshots, first-15-seconds playback, comments, recovery, locking, and forced app cleanup without embedding any company's device or account IDs."
---


## 慢命令超时（必读）

- **对 `douyin-phone-adb` 的每一次 exec 调用，一律显式设置 `timeout: 300000`（毫秒），没有例外。**不要按命令名挑——任何命令都可能要读 UI 树，而读树内置重试最坏约 180 秒（0912 实证：`search-video-tab`/`search-video-cards` 因不在旧版「慢命令名单」里而用了默认超时，正在正确重试时被斩断，误报 timed out / UI hierarchy unavailable，整轮发现阶段作废）。其中 `search-time-layer`、`record-start`/`record-stop`、`current-video-link` 是复合宏，正常就要 30-90 秒，禁止用默认超时——默认超时会把正在正确执行的宏拦腰打断并误判为适配器故障。2026-09-12 起读 UI 树内置三波重试（波内 3 次 + 暂停抓取兜底，波间 10s/20s，最坏约 180 秒），因为"已知存在的东西不该一次读不到就放弃"；成功路径仍是 2.8 秒返回（其中 2.7 秒是设备端 uiautomator dump 的地板耗时），重试只在真失败时才花时间。下限从 120000ms 抬到 300000ms 即为容纳这一重试。

## 产出契约（构造 WORKER_RESULT 前逐项自检）

> 本节与 `agentic-workflow-runtime/references/protocol.md` 的「metrics 封闭键集」逐字一致；
> 冲突时以 protocol.md 为准。适用阶段：preflight / cleanup（及各设备动作）。

**metrics 必填**（没发生就填 0，禁止自造键名）：通用 4 键 `external_interactions` `business_reads` `business_writes` `artifact_writes`；本阶段另加 `device_verified` `account_verified` `call_state_idle` `lock_acquired`（preflight，0/1）；`close_app_attempts` `lock_released` `safe_desktop_visible`（cleanup，0/1）。

**真实模式 completed 的最小 evidence**（`evidence` 必须是对象数组，空数组不接受）：
- preflight completed 至少 4 条：`{"type":"preflight",…}`（serial/model/call_state/foreground）、`{"type":"lock",…}`（owner/lease）、`{"type":"account_home_screenshot",…}`（marker/douyin_id）各就位
- cleanup completed 至少 2 条：`{"type":"close_app",…}`（前台不再是抖音的验证）、`{"type":"lock_release",…}`（回读 lock-status 为 free）——**实测 cleanup 是空证据重灾区，空 evidence 的 cleanup completed 不被接受**

- preflight / cleanup 的 `artifacts` **必须为 `[]`**：截图、快照属只读 evidence（实测 21% 混放，一律判 retry）。

# 抖音手机运行适配器

这是平台/设备适配层，不包含关键词、目标人群、视频判定、评论意向或飞书业务逻辑。

当由 `agentic-workflow-runtime` 调用做预检或清理时，结束前必须按其协议返回唯一 `WORKER_RESULT` 或 `N8N_NODE_RESULT`，包含设备/账号/通话/锁或退出桌面验证证据，不得只汇报“已执行”。当 `orchestrator=n8n` 时不得召唤 Commander、其他 Agent 或下一阶段。`contract_test` 只验证 Skill 与节点合同，不调用手机、不取得设备锁，也不执行清理动作。任务给出 `expected_commander_event_id` 时，结果中的 `commander_event_id` 必须逐字、逐字节复制该值；禁止根据 `run_id`、`attempt_id` 或事件序号重新拼接、缩写或推导。

## 租户解析

每次调用必须收到当前租户解析后的：`node、phone_profile、phone_serial、phone_model、adb_controller、screen_size、account_role`。不得设置公司默认值，不得按 ADB 列表顺序挑设备，不得切换到其他 profile 求成功。

调用 `<adb_controller> --profile <phone_profile> status` 后，serial 和 model 必须与租户上下文一致。账号主页身份必须符合任务角色；只有租户策略明确授权时才允许切号。

## 快速预检

预检必须走短输出路径，禁止先调用 `help`、`diagnose`、`telecom` 或 `window`，也禁止为了打开 App 而先做一次假关键词搜索：

1. 调用一次 `<adb_controller> --profile <phone_profile> preflight`，从短输出同时验收 profile、serial、model、ADB state、call state 和前台窗口；`call_state` 不是 `idle` 时立即安全停止。
2. 调用 `<adb_controller> --profile <phone_profile> lock-acquire <run_id>`，保存 owner 证据；拿不到锁就返回 blocked，不抢占。
3. 调用 `open-app` 后进入“我”页。一次性检查可优先使用 `snapshot`；循环发现必须为每屏生成安全的唯一 `evidence_id` 并调用 `snapshot-evidence`，不得让后一屏覆盖前一屏。每次截图或复合动作返回 Node 路径后，必须逐字复制控制器本次返回的完整路径并立即用 `file_fetch` 回传；禁止自行拼接、补写、删除扩展名、归一化或猜测任何目录，尤其不得重复添加 `evidence/`。某张截图的 `file_fetch` 一旦成功，必须直接消费该返回内容并继续，禁止对同一截图二次 `file_fetch`，也禁止改成无 `.png` / `.xml` 扩展名的路径重试。不要再调用 `pull`，控制器已经把图拉到 Mac。Node 的本地路径不是合法 `image_url`，严禁把 `/private/tmp/...`、`/Users/...` 或其他文件路径直接传给视觉输入；只能使用 `file_fetch` 返回的真实 image content/media 对象。若回传内容缺失或格式不受支持，记录 screenshot inaccessible 并按阶段恢复规则处理，不得构造、猜测或重用旧 `image_url`。
4. 搜索结果、评论列表等重复页面可优先调用 `ui-evidence <evidence_id>` 获取不可覆盖的 UI hierarchy XML，并通过 `file_fetch` 读取结构化文本和节点边界；同一屏的 UI XML 和 PNG 共用同一基础 evidence ID，并缓存屏幕指纹。`uiautomator` 在动态视频页可能无法达到 idle state，此时控制器会明确失败且不会返回旧 XML；继续使用同一时刻的新鲜 PNG、前台包证据和视觉模型完成闭环，不得把 XML 失败解释成 App 退回桌面，也不得复用上一次 hierarchy。
5. 先只读取当前主页。主页身份匹配目标 marker 或登记的完整抖音号时，立即视为账号通过，禁止打开账号切换列表。只有主页明确显示为另一个账号时，且 tenant context 明确授权切换，才打开一次切换列表并精确点击目标 marker；切换后必须回到主页复核。视觉不确定时重截一次主页，不得靠打开列表试探，也不得点击其他账号试错。
6. 预检阶段不得搜索关键词、读取评论或写飞书。账号、设备、通话、锁四项全部有证据后立即返回 `WORKER_RESULT`。预检截图属于只读 `evidence`，必须返回 `artifacts: []` 与 `write_fences: []`；不得把截图路径放进 `artifacts`，也不得为只读截图申请 `artifact_write`。

## 允许动作

- 设备/通话/窗口预检；
- 单次状态检查使用 `snapshot`、`tap-snapshot`、`swipe-snapshot`、`back-snapshot`；
- 循环证据使用 `snapshot-evidence EVIDENCE_ID`、可选的 `ui-evidence EVIDENCE_ID`、`tap-evidence X Y EVIDENCE_ID [WAIT_MS]`、`swipe-evidence X1 Y1 X2 Y2 MS EVIDENCE_ID [WAIT_MS]`、`back-evidence EVIDENCE_ID [WAIT_MS]`；`EVIDENCE_ID` 只能含字母、数字、点、下划线和连字符，并由执行身份、阶段尝试、关键词/视频序号和屏序号组成；
- 搜索结果页的筛选按钮已由新鲜 UI 树确认，但弹出筛选面板不进入 Accessibility 树时，full 模式必须在筛选弹层尚未打开的结果页直接调用 `search-time-layer <time_layer> <evidence_id> <sort> <duration> <scope> <location>`，并逐项传入冻结任务的值。该命令内部语义定位并点击“筛选”，再按当前 profile 屏幕比例选择排序、时间、时长、范围和位置，返回面板、全部选中态和结果页三份证据；双参数形式只保留给旧 contract/兼容调用。Worker 调用前严禁用 `tap`、`tap-evidence` 或其他动作预先点击/打开筛选，也不得用自己猜测的筛选坐标复刻此步骤；
- 搜索、查看视频、从开头播放配置秒数、打开评论和只读主页；
- 当前页面已由新鲜 UI 证据确认是视频详情时，可调用 `current-video-link EVIDENCE_ID`。该控制器命令只语义定位“分享按钮”与“分享链接”，把平台生成的链接复制到本机剪贴板并解析为稳定视频 ID、短链、解析链接和重开 URI；它不选择联系人/应用、不发送、不推荐、不私信，计入 `external_interactions: 0`。Worker 禁止自行点击这些区域或用固定坐标复刻此流程；
- 全文判定与参考转写的**受控录制**：`record-start EVIDENCE_ID [MAX_SECONDS]`（上限 1800s）、`record-status`、`record-stop`（自动 ffprobe 双流验证，**无音频流即失败明报**）、`record-extract-audio`（16kHz 单声道 WAV）。录制大文件留在节点 evidence 目录，不回传 Gateway；仅 qualification 与参考转写类任务使用；**仍以租户控制器为唯一入口，禁止直接调用 scrcpy / ffmpeg**；
- 息屏安全唤醒、一次受控恢复；
- `close-app` 强制停止抖音并返回桌面。

所有节点命令一次只执行一个以租户控制器绝对路径开头的命令。禁止裸 `adb`、Shell 拼接、变量、管道或命令替换。截图只从 profile 隔离的节点路径读取。

租户上下文给出的 `adb_controller` 是唯一可执行入口，必须逐字使用。不得追加或删除 `.zsh`、`.sh` 等后缀，不得替换成 Skill 文档中提到的源码/兼容入口；路径不一致时应返回 `blocked`，不能试探执行。cleanup 同样遵守此规则。

每条节点命令必须严格采用 `<adb_controller> --profile <phone_profile> <command> [args...]`；`--profile` 和 profile 值不得省略、调换或改写。执行前先逐字核对该前缀，前缀不完整时不得调用节点。

## 评论区导航护栏

- 每个视频都必须基于该视频当前截图或可访问性树重新识别评论入口。不得跨视频复用绝对点击坐标，也不得点击评论输入栏、软键盘区域或发送按钮附近来“试探”评论入口。
- 点击评论入口后立即 `snapshot` 并验收评论列表、输入框焦点和软键盘状态；未验收通过前不得滑动、读取或点击评论用户。
- 若仅误聚焦空白评论框，且没有文字、草稿或发送动作，允许执行一次 `back-snapshot` 恢复；确认键盘消失且页面无对外状态变化后，只可重新定位并重试一次。任何文字输入、草稿、发送控件触发，或恢复后仍为输入状态，都按实际互动风险安全停止。
- 评论采集必须按视频落检查点。恢复运行重新做预检和锁校验后，只导航到未完成视频；已经完成的视频不得重复打开。

## 手机锁与清理

同一 Node/设备一次只允许一个前台任务。发现、判定和评论阶段共享同一租户设备锁；拿不到锁就等待或保留 pending，不抢占。

在多阶段 Workflow 中，成功的预检、发现、判定和评论 Worker 不得各自退出 App 或释放锁；它们把同一 `run_id` 的锁留给下一阶段。只有安全停止、阶段终止，或可信编排器已进入 manifest 的最终 cleanup 时，才执行 `close-app`，验证前台包不再是 `com.ss.android.ugc.aweme` 并检查桌面截图。失败只重试一次。

发现、判定、评论、交付等非 cleanup Worker 即使返回 `blocked` 或 `failed`，也不得自行调用 `close-app` 或 `lock-release`；它只报告事实并把清理权交回可信编排器。只有任务身份明确为 `stage_id=cleanup` 的 Worker 可以释放锁。

最终清理或安全停止最后调用 `<adb_controller> --profile <phone_profile> lock-release <run_id>` 并回读 `lock-status`。只有 App 已退出且锁已释放，清理才算通过。

区分提醒与挑战页：切号后短暂出现“完善安全设置”等 toast、气泡或推荐提示时，等待页面稳定后再截图一次；若提示消失、目标账号主页可正常读取且操作未被遮挡，只记录 warning 并继续。只有提示持续遮挡、跳入安全设置/登录流程、要求验证码/实名/人脸/密码，或页面无法继续时，才返回 `blocked`。登录确认、验证码、实名、人脸和明确风控挑战不得绕过。

## 禁止动作

默认禁止点赞、关注、评论、回复、私信、对外分享、推荐、发布、修改账号、绕过验证码/人脸/风控或清除 App 数据。唯一例外是控制器封装的 `current-video-link` 只读取链动作；它必须在语义节点和回读链接全部验证后才成功，不能扩展为任意分享动作。来电、通话、账号/设备不匹配、登录挑战、连续截图失败立即停止。

当前控制器实现由部署蓝图中的兼容入口维护；运行时始终逐字使用租户登记的安装路径，Skill 内不保存、推导或补写真实路径及文件后缀。
