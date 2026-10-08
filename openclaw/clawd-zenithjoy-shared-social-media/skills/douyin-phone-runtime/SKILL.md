---
name: douyin-phone-runtime
layer: platform
version: 1.0.0
description: "Adapt generic social-video workflow actions to a tenant-selected logged-in Douyin Android phone through an OpenClaw Node and registered profile controller. Use for safe device preflight, search, screenshots, first-15-seconds playback, comments, recovery, locking, and forced app cleanup without embedding any company's device or account IDs."
---


## 慢命令超时（必读）

- **对 `douyin-phone-adb` 的每一次 exec 调用，一律显式设置 `timeout: 300000`（毫秒），没有例外。**不要按命令名挑——任何命令都可能要读 UI 树，而读树内置重试最坏约 180 秒（0912 实证：`search-video-tab`/`search-video-cards` 因不在旧版「慢命令名单」里而用了默认超时，正在正确重试时被斩断，误报 timed out / UI hierarchy unavailable，整轮发现阶段作废）。其中 `search-time-layer`、`record-start`/`record-stop`、`current-video-link` 是复合宏，正常就要 30-90 秒，禁止用默认超时——默认超时会把正在正确执行的宏拦腰打断并误判为适配器故障。2026-09-12 起读 UI 树内置三波重试（波内 3 次 + 暂停抓取兜底，波间 10s/20s，最坏约 180 秒），因为"已知存在的东西不该一次读不到就放弃"；成功路径仍是 2.8 秒返回（其中 2.7 秒是设备端 uiautomator dump 的地板耗时），重试只在真失败时才花时间。下限从 120000ms 抬到 300000ms 即为容纳这一重试。

## 产出契约（构造 WORKER_RESULT 前逐项自检）

> 本节与 `agentic-workflow-runtime/references/protocol.md` 的「metrics 封闭键集」逐字一致；
> 冲突时以 protocol.md 为准。适用阶段：preflight / cleanup（及各设备动作）。

**metrics 必填**（没发生就填 0，禁止自造键名）：通用 4 键 `external_interactions` `business_reads` `business_writes` `artifact_writes`；本阶段另加 `device_verified` `account_verified` `call_state_idle` `lock_acquired`（preflight，0/1）；`close_app_attempts` `lock_released` `safe_desktop_visible`（cleanup，0/1）。

**真实模式 completed 的最小 evidence**（`evidence` 必须是对象数组，空数组不接受）：
- preflight completed 至少 4 条：`{"type":"preflight",…}`（serial/model/foreground）、`{"type":"call_state",…}`（state=idle）、`{"type":"lock",…}`（owner/lease）、`{"type":"account_home_screenshot",…}`（marker/douyin_id）四项各自就位，不用重复证据凑数
- cleanup completed 至少 2 条：`{"type":"close_app",…}`（前台不再是抖音的验证）、`{"type":"lock_release",…}`（回读 lock-status 为 free）——**实测 cleanup 是空证据重灾区，空 evidence 的 cleanup completed 不被接受**

- preflight / cleanup 的 `artifacts` **必须为 `[]`**：截图、快照属只读 evidence（实测 21% 混放，一律判 retry）。

## 截图回传与节点断连（必读）

- **回传截图一律 `file_fetch` 控制器输出里的 `.jpg`**：截图类命令（`snapshot`、`tap-snapshot`、`swipe-snapshot`、`back-snapshot`、`open-app`、`close-app`、`pull`、`snapshot-evidence`、`tap-evidence`、`swipe-evidence`、`back-evidence`）首行仍是原图 PNG 路径，下一行是 `jpg=<路径>`；复合命令对应 `evidence_jpg=`、`panel_evidence_jpg=`、`selected_evidence_jpg=`、`results_evidence_jpg=`、`before_send_evidence_jpg=`、`sent_evidence_jpg=`。逐字复制 jpg 行给出的路径回传，不得自行把 `.png` 改写成 `.jpg`。
- **禁止 `file_fetch` 原图 PNG**：原图约 3MB（base64 约 4MB），与指令同走一条节点通道，西安上行约 315KB/s → 30 秒超时 → 后续指令排队超时 → 网关判节点 disconnected（0929 实证）。只有任务正文明确要求原图时才可回传 PNG，且该次 `file_fetch` 必须显式放宽超时（不少于 `60000` 毫秒）。
- 输出里没有 jpg 行（转换失败）→ 记录 screenshot inaccessible，按阶段恢复规则重截一次；不得退回去回传 PNG。
- **节点断连先核实、再重试一次**：任一节点调用报 `DISCONNECTED`、`node disconnected` 或 `gateway request timeout` 时，不得直接收尾判失败。先用 `nodes` 工具的 `status`（`nodes status`）确认该节点是否已重连（0929 实测断开约 1 秒即重连）：
  - 已重连 → 把失败的那一步重试**一次**。只读步骤（截图类、`ui-evidence`、`status`、`preflight`、`foreground`、`lock-status`、`evidence-bundle` 等）可直接重试；写操作（`private-message-send` 发私信、发布、`account-switch` 切号、`lock-acquire`/`lock-release`、录制启停等会改变状态的命令）**不得盲目重试**，必须先用只读命令核对上一次是否已生效（私信先截图/读 UI 看气泡是否已发出，锁先 `lock-status` 看 owner），确认未生效才可重做一次，已生效则直接采用该结果。
  - 未重连，或重试一次仍失败 → 按阶段恢复规则收尾，结果里写明断连时间、`nodes status` 回读与重试证据。

# 抖音手机运行适配器

> **当前账号只读子流程熟化：蒸馏**（首次沉淀 · 来源 run rpa-explore-df06801b-c6f6-4df4-90a6-4c028de6d9bf · 更新 1008）
> 判例计数：无新增（来源 findings 为空）；不改变其他流程的熟化状态。

这是平台/设备适配层，不包含关键词、目标人群、视频判定、评论意向或飞书业务逻辑。

当由 `agentic-workflow-runtime` 调用做预检或清理时，结束前必须按其协议返回唯一 `WORKER_RESULT` 或 `N8N_NODE_RESULT`，包含设备/账号/通话/锁或退出桌面验证证据，不得只汇报“已执行”。当 `orchestrator=n8n` 时不得召唤 Commander、其他 Agent 或下一阶段。`contract_test` 只验证 Skill 与节点合同，不调用手机、不取得设备锁，也不执行清理动作。任务给出 `expected_commander_event_id` 时，结果中的 `commander_event_id` 必须逐字、逐字节复制该值；禁止根据 `run_id`、`attempt_id` 或事件序号重新拼接、缩写或推导。

## 租户解析

每次调用必须收到当前租户解析后的：`node、phone_profile、phone_serial、phone_model、adb_controller、screen_size、account_role`。不得设置公司默认值，不得按 ADB 列表顺序挑设备，不得切换到其他 profile 求成功。

调用 `<adb_controller> --profile <phone_profile> status` 后，serial 和 model 必须与租户上下文一致。业务任务账号主页身份必须符合任务角色；独立只读任务仅在可信任务正文明确 `account_role=current_logged_in_readonly` 时允许只报告当前值，交付 `business_identity_verified=false`，不声明业务角色已核验。本独立子流程中的其他角色必须提供并精确匹配预期抖音号；只有租户策略明确授权时才允许切号。

## 快速预检

预检必须走短输出路径，禁止先调用 `help`、`diagnose`、`telecom` 或 `window`，也禁止为了打开 App 而先做一次假关键词搜索：

1. 调用一次 `<adb_controller> --profile <phone_profile> preflight`，从短输出同时验收 profile、serial、model、ADB state、call state 和前台窗口；`call_state` 不是 `idle` 时立即安全停止。
2. 调用 `<adb_controller> --profile <phone_profile> lock-acquire <run_id>`，保存 owner 证据；拿不到锁按下方「手机锁被占（DEVICE_BUSY 约定）」处理，不抢占。
3. 调用 `open-app` 后进入“我”页。一次性检查可优先使用 `snapshot`；循环发现必须为每屏生成安全的唯一 `evidence_id` 并调用 `snapshot-evidence`，不得让后一屏覆盖前一屏。每次截图或复合动作返回 Node 路径后，必须逐字复制控制器本次返回的 jpg 完整路径（`jpg=` 或 `*_jpg=` 行，见「截图回传与节点断连」，禁止回传原图 PNG）并立即用 `file_fetch` 回传；禁止自行拼接、补写、删除扩展名、归一化或猜测任何目录，尤其不得重复添加 `evidence/`。某张截图的 `file_fetch` 一旦成功，必须直接消费该返回内容并继续，禁止对同一截图二次 `file_fetch`，也禁止改成无 `.jpg` / `.png` / `.xml` 扩展名的路径重试。不要再调用 `pull`，控制器已经把图拉到 Mac。Node 的本地路径不是合法 `image_url`，严禁把 `/private/tmp/...`、`/Users/...` 或其他文件路径直接传给视觉输入；只能使用 `file_fetch` 返回的真实 image content/media 对象。若回传内容缺失或格式不受支持，记录 screenshot inaccessible 并按阶段恢复规则处理，不得构造、猜测或重用旧 `image_url`。
4. 搜索结果、评论列表等重复页面可优先调用 `ui-evidence <evidence_id>` 获取不可覆盖的 UI hierarchy XML，并通过 `file_fetch` 读取结构化文本和节点边界；同一屏的 UI XML 和 PNG 共用同一基础 evidence ID，并缓存屏幕指纹。`uiautomator` 在动态视频页可能无法达到 idle state，此时控制器会明确失败且不会返回旧 XML；继续使用同一时刻的新鲜 PNG、前台包证据和视觉模型完成闭环，不得把 XML 失败解释成 App 退回桌面，也不得复用上一次 hierarchy。
5. 先只读取当前主页。主页身份匹配目标 marker 或登记的完整抖音号时，立即视为账号通过，禁止打开账号切换列表。只有主页明确显示为另一个账号时，且 tenant context 明确授权切换，才打开一次切换列表并精确点击目标 marker；切换后必须回到主页复核。视觉不确定时重截一次主页，不得靠打开列表试探，也不得点击其他账号试错。
6. 预检阶段不得搜索关键词、读取评论或写飞书。账号、设备、通话、锁四项全部有证据后立即返回 `WORKER_RESULT`。预检截图属于只读 `evidence`，必须返回 `artifacts: []` 与 `write_fences: []`；不得把截图路径放进 `artifacts`，也不得为只读截图申请 `artifact_write`。

## 当前账号只读与证据留存（独立任务）

只适用于读取当前登录的抖音账号；禁止搜索、切号、发布、点赞、评论、私信或其他平台动作。输入 `mode=standalone_account_read`、`cleanup_authorized=true`、`task_id`、`run_id`、`node`、`phone_profile`、`phone_serial`、`phone_model`、`adb_controller`、`screen_size` 和 `account_role`；缺少独立任务及收尾授权身份即 blocked，不当成多阶段 Worker 执行。`run_id` 逐字取 Brain 当前执行参数，必须与本独立任务绑定，禁止借用其他任务或核验/沉淀材料的来源号。设备、账号不得设默认值。本节仅对独立任务自行收尾；多阶段 Workflow 仍由可信 cleanup 统一清理。 `task_id` 与 `run_id` 均逐字取 Brain 注入的当前执行身份，缺失不猜。执行前只读查询 Brain `/api/brain/tasks/<task_id>`：状态必须为 in_progress，payload.run_id 与当前执行参数相等，qiumi_source.body 里须有一份独立顶层 JSON 块，必需字段为 mode="standalone_account_read"、cleanup_authorized=true、account_role（与输入精确相同）；逐字解析JSON值而非子串推断，不接受引用示例或多份歧义块；其他角色须在此块另提供expected_douyin_id并精确相等，qiumi_route.device_hint 的 serial/profile 与当前设备参数一致；同一任务以 Brain 唯一认领执行，不用会话自报替代此核对。任一条件缺失或不一致即 blocked，不碰手机。

沿用本 Skill 的单命令控制器、300000ms 超时、JPG 回传、断连和锁规则。仅接 payload.timeout_sec<=600 且实际通过 OpenClaw --timeout 下发的原生Codex运行，远端执行明确timeoutSeconds=300；父运行取消后禁止审批后补发。若当前执行通道不能证明父运行600秒硬截止、节点命令300秒执行预算及取消后不新发命令，则blocked，不启动本子流程。lock-status采样后到下一次UI发送若发生审批、排队、其他工具或重连，重新采样，不沿用旧租约。该门禁以整个父运行剩余预算加远端程序预算计算，不把本地超时当成设备已停止证明。所需预算不足只在有效原owner下释放本次新锁。

本独立子流程只接受 Brain 手机派发的固定长度 `^qiumi-[0-9a-f]{8}-[0-9]{13}$` 原运行号，长度28、无冒号或阶段后缀，不能使用 attempt_id 或会被控制器归一化的标识；其他执行体系不套用此子流程。还必须拒绝任何匹配 `[-_]a[0-9]+[-_]` 的片段，避免控制器阶段归一化；不同合法独立运行号等长，互不为前缀；不合法即 blocked，禁止改写运行号。以下租约和通话门禁仅用于 open-app、account-current、snapshot-evidence、ui-evidence、close-app、return-safe-desktop；初次 lock-acquire 按步骤1的free前置，lock-refresh与lock-release按下述各自条件，不套用此前置。每次上述前台/取证命令前、以及断连重连后先只读 preflight 核对 call_state=idle；观察到来电或通话即停止前台操作，不返回桌面或关闭通话页面，此来电安全停止的lock-release豁免call_state=idle要求，仅在有效租约及精确本owner仍可确认时释放自己的锁并报未完成收尾，不碰任何前台命令。再 `lock-status`：owner 必须精确为本 run、stale=false，且 age+1000 小于 ttl（保守覆盖600秒父运行预算、300秒远端程序及100秒余量）。lock-refresh 的前置仅为当前owner精确为本run且stale=false，允许在age+1000预算不足时执行一次并回读，不能用于已过期或他人锁；已过期、owner变化或状态不可确认则停止所有前台、刷新与释放动作，报告已有证据，不冒充已清理。每屏证据 ID 用 `run_id-两位步号-YYYYMMDDTHHmmssSSSZ`（UTC、无冒号），只记控制器实际返回的 JPG/XML 路径，不猜路径或复用旧证据。`account-current` 语义定位“我，按钮”并读号；当前控制器昵称不可读时返回 unknown，旧版本可能回退成抖音号，二者均不能充作已验证昵称；昵称必须由绑定的 JPG 与 XML 另行核实。执行者不得自行用坐标点控件。每对 JPG/XML 记录本会话工具回执的起止时间、节点/profile/运行号、前台包及页面身份；从 snapshot-evidence 调用开始到同证据 ID 的 ui-evidence 返回不超过30秒。两份均须显示本人主页标记（“编辑主页”或“切换账号”，同时没有“私信”按钮）及相同非空昵称、抖音号，节点/profile/运行号一致；这里只核验同一账号主页，不声称两个时刻的全部像素或动态数字相同。超过30秒或绑定条件不齐，丢弃这对证据，最多重采一次。采集间观察到前台或页面变化就丢弃这对证据，最多重采一次，不拼接不同时刻的页面。

| # | 前置 | 动作 | 完成判据 | 证据 | 失败处理 |
|---|---|---|---|---|---|
| 1 | 指定设备在线且锁空闲 | 先 `lock-status` 必须为 free，任何已有 owner（包括同 run_id）均按占用结束，不续租、不清理其锁；`preflight` 核对 profile/serial/model、ADB、空闲通话；`preflight` 在拿锁前仅作只读检查；`lock-acquire <run_id>` 是原子认领，失败不操作前台、不释放锁。`lock-acquire <run_id>` 并记录从 free 到本 owner 的原始回执（含采集时间）；若取得锁回执因断连丢失，仅在已有带时间的 free 回读、本任务唯一执行认领身份且重连后 owner 精确等于本 run 时，可将这两次回读作为已生效证据，不重复获取；否则不操作前台或释放锁，报 owner 待核查；`open-app` 后 `snapshot-evidence <01-id>` 与 `ui-evidence <01-id>` 留同屏 JPG/XML | 抖音前台的 UI 树出现“我，按钮”，锁 owner 为本 run | 01-open JPG/XML、预检与锁回执 | 设备/通话异常停止；锁被占只读回读一次并按 DEVICE_BUSY 结束；已持锁则安全清理 |
| 2 | 新鲜 XML 显示唯一“我，按钮” | `account-current <evidence_id>` 进入本人主页；`snapshot-evidence` 与 `ui-evidence` 留绑定证据 | 30秒内绑定的 JPG/XML 均显示本人主页标记、相同非空昵称和抖音号，抖音号与控制器 douyin_id 一致；若任务提供预期账号号须精确相等，仅 current_logged_in_readonly 可只报告当前值，business_identity_verified=false；其他角色缺预期号即 blocked；无切号面板 | 03-account-read JPG/XML、读数 | 只重截一次；独立证据仍缺失、多义或不一致即失败并清理，不试切号 |
| 3 | 本独立任务新取得本 run 锁，不论读取成功与否 | 先 `close-app` 强制退出抖音并保留 close_app 回执，再 `return-safe-desktop` 核对控制器解析的默认 HOME 桌面；`snapshot-evidence`、`ui-evidence` 留证；核 owner 后 `lock-release <run_id>` 并 `lock-status` | 前台等于 return-safe-desktop 回执中的默认 launcher 包，桌面 JPG/XML 均为该 launcher；回读 `lock=free` | 04-safe-desktop JPG/XML、前台包、锁回读 | 清理失败按既有规则最多重试一次；不释放他人锁；未证实桌面或释放不得报成功 |

### 成功判定

1. 账号页30秒内绑定的新鲜 JPG/XML 均显示本人主页标记、同一非空昵称与抖音号，且抖音号与控制器 douyin_id 一致。
2. 账号页与安全桌面的 JPG、XML 均以本次来源 `run_id` 命名并可读取；安全桌面前台包等于控制器解析的默认 HOME launcher 包。
3. 锁审计证明仅本 `run_id` 持有并释放锁，最终 `lock=free`；命令审计没有对外动作或切号。

由独立 `run-verify` 按原始证据判定，不以执行者自报代替。交付读到的昵称、抖音号、设备标识、证据路径、桌面前台包、锁回读和命令审计摘要；缺任一断言证据不得报成功。

### 契约

- **前置条件**：合法来源 `run_id` 与上述设备参数；登记的控制器入口、设备序列号和型号匹配，ADB 在线、通话空闲、抖音可打开且已登录，本 run 可得锁；可信设备配置须给出 lock_ttl_seconds>1000；取得新锁后回读实际ttl并复核，不满足则只释放本次新锁并blocked，禁止前台动作。仅 `account_role=current_logged_in_readonly` 且 Brain 任务正文明确授权读当前账号时可不提供预期抖音号；交付 business_identity_verified=false。其他角色必须提供并匹配预期抖音号。
- **后置条件**：成功判定三项全真；失败时报告已有读数与证据，并尽力清理自身前台和锁。
- **副作用**：设备前台导航、退出 App、获取/释放本 run 锁，以及 profile 隔离的本地 JPG/XML/审计写入；无平台对外写入或账号切换。
- **失败模式**：设备/账号不符、锁被占、通话非空、未登录或风控、“我”控件缺失/多义、昵称回退、JPG/XML 过期或不一致、节点断连、桌面或锁释放不可证实；按各步安全停止，不用坐标试错。

### 坑

来源 `findings` 为空，无新增判例；控制器昵称 unknown 或回退值不算已验证昵称，须以绑定的 JPG/XML 核对真实昵称。

## 允许动作

- 设备/通话/窗口预检；
- 单次状态检查使用 `snapshot`、`tap-snapshot`、`swipe-snapshot`、`back-snapshot`；
- 循环证据使用 `snapshot-evidence EVIDENCE_ID`、可选的 `ui-evidence EVIDENCE_ID`、`tap-evidence X Y EVIDENCE_ID [WAIT_MS]`、`swipe-evidence X1 Y1 X2 Y2 MS EVIDENCE_ID [WAIT_MS]`、`back-evidence EVIDENCE_ID [WAIT_MS]`；`EVIDENCE_ID` 只能含字母、数字、点、下划线和连字符，并由执行身份、阶段尝试、关键词/视频序号和屏序号组成；
- 搜索结果页的筛选按钮已由新鲜 UI 树确认，但弹出筛选面板不进入 Accessibility 树时，full 模式必须在筛选弹层尚未打开的结果页直接调用 `search-time-layer <time_layer> <evidence_id> <sort> <duration> <scope> <location>`，并逐项传入冻结任务的值。该命令内部语义定位并点击“筛选”，再按当前 profile 屏幕比例选择排序、时间、时长、范围和位置，返回面板、全部选中态和结果页三份证据；双参数形式只保留给旧 contract/兼容调用。Worker 调用前严禁用 `tap`、`tap-evidence` 或其他动作预先点击/打开筛选，也不得用自己猜测的筛选坐标复刻此步骤；
- 搜索、查看视频、从开头播放配置秒数、打开评论和只读主页；
- 当前页面已由新鲜 UI 证据确认是视频详情时，可调用 `current-video-link EVIDENCE_ID`。该控制器命令只语义定位“分享按钮”与“分享链接”，把平台生成的链接复制到本机剪贴板并解析为稳定视频 ID、短链、解析链接和重开 URI；它不选择联系人/应用、不发送、不推荐、不私信，计入 `external_interactions: 0`。Worker 禁止自行点击这些区域或用固定坐标复刻此流程；
- 全文判定与参考转写的**受控录制**：`record-start EVIDENCE_ID [MAX_SECONDS]`（上限 1800s）、`record-status`、`record-stop`（自动 ffprobe 双流验证，**无音频流即失败明报**）、`record-extract-audio`（16kHz 单声道 WAV）。录制大文件留在节点 evidence 目录，不回传 Gateway；仅 qualification 与参考转写类任务使用；**仍以租户控制器为唯一入口，禁止直接调用 scrcpy / ffmpeg**；
- 息屏安全唤醒、一次受控恢复；
- `close-app` 强制停止抖音；独立只读子流程随后使用 `return-safe-desktop` 核对默认 HOME 桌面。

所有节点命令一次只执行一个以租户控制器绝对路径开头的命令。禁止裸 `adb`、Shell 拼接、变量、管道或命令替换。截图只从 profile 隔离的节点路径读取。

租户上下文给出的 `adb_controller` 是唯一可执行入口，必须逐字使用。不得追加或删除 `.zsh`、`.sh` 等后缀，不得替换成 Skill 文档中提到的源码/兼容入口；路径不一致时应返回 `blocked`，不能试探执行。cleanup 同样遵守此规则。

每条节点命令必须严格采用 `<adb_controller> --profile <phone_profile> <command> [args...]`；`--profile` 和 profile 值不得省略、调换或改写。执行前先逐字核对该前缀，前缀不完整时不得调用节点。

## 评论区导航护栏

- 每个视频都必须基于该视频当前截图或可访问性树重新识别评论入口。不得跨视频复用绝对点击坐标，也不得点击评论输入栏、软键盘区域或发送按钮附近来“试探”评论入口。
- 点击评论入口后立即 `snapshot` 并验收评论列表、输入框焦点和软键盘状态；未验收通过前不得滑动、读取或点击评论用户。
- 若仅误聚焦空白评论框，且没有文字、草稿或发送动作，允许执行一次 `back-snapshot` 恢复；确认键盘消失且页面无对外状态变化后，只可重新定位并重试一次。任何文字输入、草稿、发送控件触发，或恢复后仍为输入状态，都按实际互动风险安全停止。
- 评论采集必须按视频落检查点。恢复运行重新做预检和锁校验后，只导航到未完成视频；已经完成的视频不得重复打开。

## 手机锁与清理

同一 Node/设备一次只允许一个前台任务。发现、判定和评论阶段共享同一租户设备锁；拿不到锁不抢占，按下面的 DEVICE_BUSY 约定结束，由 Brain 排队重试。

### 手机锁被占（DEVICE_BUSY 约定）

`lock-acquire` 失败（锁被其他运行、采收/触达 cron 或别的任务持有）时：

1. 只读回读一次 `<adb_controller> --profile <phone_profile> lock-status`，确认当前持有者（owner）；
2. 不重试抢锁、不 `sleep` 等待、不做任何其他手机操作（不 open-app、不截图、不 close-app、不 lock-release）；
3. 最后一行只输出一行标记，然后结束：

   `DEVICE_BUSY owner=<持有者> serial=<序列号>`

Brain 收割器见到这一行会把任务改回排队、5 分钟后自动重试（累计等待有上限，超时才判失败）。不要把它写成「受阻/blocked」的自然语言收尾——那会被当成已完成。由 `agentic-workflow-runtime`/n8n 编排、必须返回 `WORKER_RESULT` 时，照协议返回 `blocked`，并把同一行 `DEVICE_BUSY owner=<持有者> serial=<序列号>` 作为原因原样放进结果。

在多阶段 Workflow 中，成功的预检、发现、判定和评论 Worker 不得各自退出 App 或释放锁；它们把同一 `run_id` 的锁留给下一阶段。无论安全停止、阶段终止、blocked 或 failed，非 cleanup Worker 均只报告事实并保留共享锁；只有可信编排器已进入 manifest 的最终 `stage_id=cleanup`，且close-app前回读锁的归一化run根精确为本run、stale=false、剩余租期覆盖该命令超时预算时，才执行 `close-app`，验证前台包不再是 `com.ss.android.ugc.aweme` 并检查桌面截图。失败只重试一次。

在多阶段 Workflow 中，发现、判定、评论、交付等非 cleanup Worker 即使返回 `blocked` 或 `failed`，也不得自行调用 `close-app` 或 `lock-release`；它只报告事实并把清理权交回可信编排器。只有任务身份明确为 `stage_id=cleanup` 的多阶段 Worker 可以释放锁。独立当前账号只读任务仅在任务明确 `mode=standalone_account_read`、`cleanup_authorized=true` 且有本次从 free 新取得锁的原始回执或本节限定的断连生效证据时，按「当前账号只读与证据留存」自行收尾；不得收尾任何已有锁或其他 Workflow。

多阶段仅可信cleanup、独立仅本节授权收尾者可执行最后的lock-release；安全停止的非cleanup Worker、锁已过期或归属不可确认者只报告事实，不做清场或释放。合格收尾者调用 `<adb_controller> --profile <phone_profile> lock-release <run_id>` 并回读 `lock-status`。只有 App 已退出且锁已释放，清理才算通过。

区分提醒与挑战页：切号后短暂出现“完善安全设置”等 toast、气泡或推荐提示时，等待页面稳定后再截图一次；若提示消失、目标账号主页可正常读取且操作未被遮挡，只记录 warning 并继续。只有提示持续遮挡、跳入安全设置/登录流程、要求验证码/实名/人脸/密码，或页面无法继续时，才返回 `blocked`。登录确认、验证码、实名、人脸和明确风控挑战不得绕过。

## 禁止动作

默认禁止点赞、关注、评论、回复、私信、对外分享、推荐、发布、修改账号、绕过验证码/人脸/风控或清除 App 数据。唯一例外是控制器封装的 `current-video-link` 只读取链动作；它必须在语义节点和回读链接全部验证后才成功，不能扩展为任意分享动作。来电、通话、账号/设备不匹配、登录挑战、连续截图失败立即停止（节点断连不属于截图失败，先按「截图回传与节点断连」核实并重试一次）。

当前控制器实现由部署蓝图中的兼容入口维护；运行时始终逐字使用租户登记的安装路径，Skill 内不保存、推导或补写真实路径及文件后缀。

## 版本记录

- 1.0.0（2026-10-08，首次版本登记）：由独立核验通过的运行沉淀当前账号只读子流程，明确独立任务授权、锁归属、断连、同屏证据和成功判定；其余流程保留。

### 独立任务输出及核验审计来源

本子流程不返回多阶段 preflight 的 WORKER_RESULT；锁被占优先按 DEVICE_BUSY 约定只输出标记，不输出JSON；其余结束情形执行者仅输出 stage="explore" 的JSON：task_id、run_id、claimed_result（success/failed/blocked）、read_values（nickname、douyin_id、business_identity_verified）、trajectory、final_evidence、side_effects、lock_released（布尔）、fail_reason。当前只读角色 business_identity_verified=false；若另有 metrics.account_verified 必须为0，不将“已读到当前账号”计作业务角色核验。success仅是执行者声明，不是独立验收通过；读取、默认桌面、锁释放任一证据缺失即failed或blocked并写真实已有证据。

无对外动作的最终判据由独立审计与run-verify负责。审计员按运行时回执中的agent/session身份，只读该执行宿主 ~/.openclaw/agents/<agent>/agent/openclaw-agent.sqlite（mode=ro），限定本运行窗口，核对完整工具凭证与SDK终态工具计数一致、控制器动作及原owner取得/释放/最终free。审计员将汇总证据写入Brain独立审计任务 result.evidence.audit，并提供audit_task_id；关于命令与锁审计，核验员只GET该独立审计任务；主页、默认桌面与30秒证据绑定仍按final_evidence亲自回传查看原始JPG/XML和采集回执，不读执行会话或轨迹，须确认source_run_id一致、coverage_complete=true、external_platform_write_commands=0、account_switch_commands=0、unknown_device_commands=0和锁回执。执行者不写这份独立审计。无审计指针、运行号不符或覆盖不完整，run-verify判unknown/fail，禁止声称独立验收通过。

独立子流程优先采用本节的绑定证据及审计判据：取证期间也必须持有有效租约，释放前最后一次回读须确认本 owner、stale=false、剩余租期超过本命令预算。lock-release 回执若因断连丢失，free仅证明当前空闲，不能证明由本run释放；没有原owner释放的独立审计凭证时，claimed_result必须failed或blocked，fail_reason写归属证据缺失，不再重复释放，也不宣称核验通过。

独立子流程的 account-current 会导航，断连后不能直接重做：先只读确认前台、当前账号页与有效本owner；若已在本人页只重采证据，尚未进入才可重做一次，页面身份不明即停止，不凭旧坐标操作。

若续租回读仍不能满足age+1000<ttl，禁止继续前台或取证；只在有效精确本owner可确认时释放自身锁，claimed_result=blocked，fail_reason=lease_budget_insufficient，不能声称桌面收尾成功。
