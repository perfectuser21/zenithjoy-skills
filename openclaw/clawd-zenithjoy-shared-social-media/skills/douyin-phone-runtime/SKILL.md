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

本节只适用于已经拥有手机节点权限的受信OpenClaw工位，执行Brain原子派发的独立当前账号只读任务，不作为任意调用者的权限授予或进程认证接口。禁止搜索、切号、发布、点赞、评论、私信和其他平台动作。输入mode=standalone_account_read、cleanup_authorized=true、task_id/run_id及租户设备与account_role参数，设备账号不得默认；task_id/run_id逐字取Brain原执行消息，不从员工正文组装，不重放历史运行。进程续接只核对/交报告，不重做已完成手机动作。

授权由工位真实手机节点权限及主理人的phone_rpa_dispatch范围决定，员工正文cleanup_authorized不能扩大范围。执行前只读GET `/api/brain/kv/phone_rpa_dispatch`确认enabled=true、设备名称在devices且任务创建时间不早于since；GET `/api/brain/tasks/<task_id>`确认状态in_progress、payload.run_id精确等于当前run、task_type=qiumi_task、execution_mode=single、无workflow_ref/qiumi_workflow_ref或stage_id、payload.source=notion_gtd并有notion_page_id/notion_zh_page_id。payload.qiumi_source.body必须有一份无歧义顶层JSON块，其mode、cleanup_authorized和account_role精确匹配；其他角色另须expected_douyin_id；qiumi_route.device_hint的serial/profile精确匹配。任一不满足即blocked不碰手机。以上是受信工位内的运行状态与授权范围核对，不宣称它们能独立认证任意进程身份。锁的真实互斥及精确owner在控制器强制执行。本节只清理本任务从free新取得的锁，不清理任何已有锁；每个执行会话必须独立调用lock-acquire-new取得原始acquired回执，禁止跨会话复制回执或凭同run的owner直接执行，不并行派生手机执行者；该原子新认领在同一guard内拒绝所有已有锁（包括同run和过期锁），重复会话拿不到新认领不得做UI或释放。新认领在同一真实guard内以O_EXCL写本设备/本run的一次性认领记录；记录留在锁目录之外，释放锁不删除记录，因此同run完成后也不能再次新认领。新认领先准备独立临时目录，owner、时间戳和标记全部写成后，在持有guard期间原子发布为设备锁目录；部分写入失败不发布设备锁、不碰UI。一次性claim已经写成则保留，原run blocked并写Brain失败事实，禁止重试认领、删claim或自行换run；只有Brain后续明确登记的新任务/新run才可再次执行。进程中断残留的准备目录不是设备锁，不被通用回收器使用；由已登记的运维恢复任务核对无存活进程后删除残留准备目录，保留claim。run already claimed必须blocked报告原run待跟踪，不改运行号、不当作DEVICE_BUSY重试；该记录是本控制器执行门禁，任务事实仍写Brain。lock-acquire-new会写standalone_review_required标记；lock-reap遇标记直接保留，通用lock-acquire也拒绝认领或过期回收；通用lock-release和wrapper lock-cleanup遇标记拒绝，锁状态明确reclaimable=false。标记随本任务已验证的lock-release-exact删除；未清理的锁由Brain原run继续跟踪，不能当普通过期锁自动清场。该约束适用于遵守原子派发和本流程的受信工位，不向绕过流程的任意已授权进程提供认证保证；多阶段Workflow仍只由可信cleanup统一收尾。

开始任何锁或前台动作前，GET `/api/brain/skills?search=douyin-phone-runtime`选名称逐字等于douyin-phone-runtime的唯一记录，读取metadata.standalone_account_read.controller_release_task_id；GET该发布任务，状态必须completed_no_pr且result.evidence.deployment.complete=true，固定审核提交及三文件发布回读证据完整。调用 `<adb_controller> --profile <phone_profile> runtime-contract`（不带--lock-owner），读取当前安装目录三个文件真实SHA256与路径；按任务node/设备匹配发布证据中的节点和已登记controller绝对目录，三个哈希均须等于该发布记录的after_sha256且记录自身与审核源哈希一致。contract_version常量不是版本证明，只有真实字节哈希匹配才通过；无发布指针、未完成、节点/目录不匹配、缺文件、任一哈希不符均blocked，不能用候选源码或正文自报替代。该预检是每次任务的运行前版本门禁，不宣称排除受信运行范围外的恶意本机改写。open-app允许从桌面打开抖音；close-app允许抖音退出，return-safe-desktop随后核对HOME，均不套用account-current专属的抖音前台要求。

独立子流程的本段命令前缀优先于全局逐字前缀检查，允许在--profile之后插入--lock-owner；校验必须保留该参数，不能删掉以套旧前缀。本独立子流程每次前台/取证调用使用 `<adb_controller> --profile <phone_profile> --lock-owner <run_id> COMMAND [ARGS]`，控制器在同一互斥guard内读取精确owner及剩余租期并保持guard至命令结束；锁操作无法在此期间插队。只读runtime-contract、lock-status、preflight、foreground，以及新获取lock-acquire-new、精确释放lock-release-exact，均使用不带--lock-owner的接口；foreground只读返回当前窗口，不改变前台。只支持本节允许的六类前台/取证命令。沿用本 Skill 的单命令控制器、300000ms 超时、JPG 回传、断连和锁规则。仅接 payload.timeout_sec<=600 且实际通过 OpenClaw --timeout 下发的原生Codex运行，远端执行明确timeoutSeconds=300；带--lock-owner的控制器helper对整个复合命令设置280秒终止触发点（包含内部所有ui-evidence重试）；超时先TERM、0.2秒后KILL原进程组，再以最长2秒ps查询验证无活成员、最长2秒wait根进程并回读owner不变，正常约285秒以内返回124且保留原owner锁。根进程正常退出也先真实ps核验原组无活成员并回读原owner；存在活孩子、进程查询失败或owner不符时返回失败、保留锁，不能当可信终态。终止或owner回读无法证实时返回失败，不能当可信终态。父取消后，根进程仍未回收时终止原进程组；取消与根进程自然退出重叠且根已回收时不向可能复用的PID发信号，只回读原组无活成员及owner，证明齐全才返回143/130，否则报终止未证实并保留锁。启动前已观察取消则不创建孩子；与发起调用重叠的取消按在途调用终止，不承诺瞬时零导航副作用。该受信终态回执只证明旧命令已终止，不证明桌面已归位或可释放锁；执行者须报failed/blocked，不重做读取；只有原调用可信终止、父运行尚有收尾预算、有效精确本owner及通话空闲时才可做安全清理并留证，任何条件不满足就保留原锁交Brain跟踪。父运行取消后禁止审批后补发。若当前执行通道不能证明父运行600秒硬截止、节点命令300秒执行预算及取消后不新发命令，则blocked，不启动本子流程。lock-status采样后到下一次UI发送若发生审批、排队、其他工具或重连，重新采样，不沿用旧租约。该门禁以整个父运行剩余预算加远端程序预算计算，不把本地超时当成设备已停止证明。所需预算不足即停止并保留本锁，交Brain跟踪原run；未证实安全桌面不得释放。

本独立子流程只接受 Brain 手机派发的固定长度 `^qiumi-[0-9a-f]{8}-[0-9]{13}$` 原运行号，长度28、无冒号或阶段后缀，不能使用 attempt_id 或会被控制器归一化的标识；其他执行体系不套用此子流程。控制器必须部署支持完整qiumi运行号、原子新认领lock-acquire-new及原子 `lock-release-exact` 的版本，旧版本不执行此子流程；不同合法独立运行号等长，互不为前缀；不合法即 blocked，禁止改写运行号。以下租约和通话门禁仅用于 open-app、account-current、snapshot-evidence、ui-evidence、close-app、return-safe-desktop；初次 lock-acquire-new 按步骤1的free前置，lock-release按下述条件，不套用此前置。每次上述前台/取证命令前、以及断连重连后先只读 preflight 核对 call_state=idle；观察到来电或通话即停止前台操作，不返回桌面或关闭通话页面，保留自身锁并报未完成收尾，不碰任何前台命令，不释放锁。再 `lock-status`：owner 必须精确为本 run、stale=false，且 age+1000 小于 ttl（保守覆盖600秒父运行预算、300秒远端程序及100秒余量）。独立子流程不调用lock-refresh；预算不足即停止前台操作、保留本锁并报告lease_budget_insufficient；已过期、owner变化或状态不可确认则停止所有前台、刷新与释放动作，报告已有证据，不冒充已清理。每屏证据 ID 用 `run_id-两位步号-YYYYMMDDTHHmmssSSSZ`（UTC、无冒号），只记控制器实际返回的 JPG/XML 路径，不猜路径或复用旧证据。`account-current` 已在本人主页时直接读号，否则语义定位唯一“我，按钮”进入本人主页；初始页面须为抖音本人页或有唯一我按钮的主页。仅带--lock-owner的account-current入口先精确核对前台包为抖音，其他App或包名子串不符即停止，不隐式重开抖音；再重新读取当前UI，遇他人主页或始终没有唯一我按钮即拒绝导航，不调用多阶段通用入口的逐步返回恢复；初始证据没有本人页或唯一我按钮也停止，不探索未知页面；当前控制器昵称不可读时返回 unknown，旧版本可能回退成抖音号，二者均不能充作已验证昵称；昵称必须由绑定的 JPG 与 XML 另行核实。执行者不得自行用坐标点控件。每对 JPG/XML 记录本会话工具回执的起止时间、节点/profile/运行号、前台包及页面身份；从 snapshot-evidence 调用开始到同证据 ID 的 ui-evidence 返回不超过30秒。两份均须显示本人主页标记（“编辑主页”或“切换账号”，同时没有“私信”按钮）及相同非空昵称、抖音号，节点/profile/运行号一致；这里只核验同一账号主页，不声称两个时刻的全部像素或动态数字相同。慢读本身不判设备损坏；超过30秒只表示该证据对不满足鲜度，丢弃这对证据，最多重采一次；再次超期按evidence_freshness_unproven报告，不能报账号或设备失效。采集间观察到前台或页面变化就丢弃这对证据，最多重采一次，不拼接不同时刻的页面。

| # | 前置 | 动作 | 完成判据 | 证据 | 失败处理 |
|---|---|---|---|---|---|
| 1 | 指定设备在线且锁空闲 | 先 `lock-status` 必须为 free，任何已有 owner（包括同 run_id）均按占用结束，不续租、不清理其锁；`preflight` 核对 profile/serial/model、ADB、空闲通话；`preflight` 在拿锁前仅作只读检查；`lock-acquire-new <run_id>` 是原子认领，失败不操作前台、不释放锁。`lock-acquire-new <run_id>` 并记录从 free 到本 owner 的原始回执（含采集时间）；若取得新锁的原始acquired回执丢失，不能用owner相同认领，保留原run并blocked，不操作前台或释放锁；`open-app` 后 `snapshot-evidence <01-id>` 与 `ui-evidence <01-id>` 留同屏 JPG/XML | 抖音前台为本人主页，或 UI 树出现唯一“我，按钮”；锁 owner 为本 run | 01-open JPG/XML、预检与锁回执 | 设备/通话异常停止；锁被占只读回读一次；仅确认不同owner持锁才按DEVICE_BUSY结束；free、unknown、回读失败或同owner旧锁均报告真实lock_acquire_failed/ownership_unknown，不冒充设备忙；已持锁则安全清理 |
| 2 | 新鲜XML已显示本人主页标记，或显示唯一“我，按钮” | `account-current <evidence_id>` 进入本人主页；`snapshot-evidence` 与 `ui-evidence` 留绑定证据 | 30秒内绑定的 JPG/XML 均显示本人主页标记、相同非空昵称和抖音号，抖音号与控制器 douyin_id 一致；若任务提供预期账号号须精确相等，仅 current_logged_in_readonly 可只报告当前值，business_identity_verified=false；其他角色缺预期号即 blocked；无切号面板 | 03-account-read JPG/XML、读数 | 只重截一次；独立证据仍缺失、多义或不一致即失败并清理，不试切号 |
| 3 | 本独立任务新取得本 run 锁，不论读取成功与否 | 先 `close-app` 强制退出抖音并保留 close_app 回执，再 `return-safe-desktop` 核对控制器解析的默认 HOME 桌面；`snapshot-evidence`、`ui-evidence` 留证；桌面JPG/XML同一证据ID的调用起止不超过30秒，前后只读foreground的实际包名均精确等于默认HOME且未观察到页面变化；前台改变即丢弃重采一次，仍不一致即保留锁并failed。桌面证据齐全、核owner及租期后 `lock-release-exact <run_id>` 并 `lock-status`；控制器在同一锁guard内原子核对owner逐字相等才释放，owner变化即拒绝 | 回执foreground_package精确等于return-safe-desktop回执中的默认launcher包，桌面 JPG/XML 均为该 launcher；回读 `lock=free` | 04-safe-desktop JPG/XML、前台包、锁回读 | 清理失败按既有规则最多重试一次；不释放他人锁；未证实桌面或释放不得报成功 |

### 成功判定

1. 账号页30秒内绑定的新鲜 JPG/XML 均显示本人主页标记、同一非空昵称与抖音号，且抖音号与控制器 douyin_id 一致。
2. 账号页与安全桌面的 JPG、XML 均以本次来源 `run_id` 命名并可读取；安全桌面前台包等于控制器解析的默认 HOME launcher 包。
3. 锁审计证明本 `run_id` 新取得并精确释放其owner锁，最终 `lock=free`；命令审计没有对外动作或切号。

由独立 `run-verify` 按原始证据判定，不以执行者自报代替。交付读到的昵称、抖音号、设备标识、证据路径、桌面前台包、锁回读和命令审计摘要；缺任一断言证据不得报成功。

### 契约

- **前置条件**：合法来源 `run_id` 与上述设备参数；登记的控制器入口、设备序列号和型号匹配，ADB 在线、通话空闲、抖音可打开且已登录，本 run 可得锁；可信设备配置须给出 lock_ttl_seconds>=1800；以Brain started_at及实际timeout_sec计算父剩余时间，初次获取新锁前须至少400秒（280秒读命令及120秒常规取证/收尾预算）；正常预检取证也计入父预算，不声称任意慢读或超时均可成功。取得新锁后回读实际ttl>=1800并复核，不满足则保留本次新锁并blocked，禁止前台动作。仅 `account_role=current_logged_in_readonly` 且 Brain 任务正文明确授权读当前账号时可不提供预期抖音号；交付 business_identity_verified=false。其他角色必须提供并匹配预期抖音号。
- **后置条件**：成功判定三项全真；失败时报告已有读数与证据；仅有效租约、原调用已终止且通话空闲才清理前台，安全桌面证据齐全后才原子释放本锁；其他情况保留锁交Brain跟踪原run。
- **副作用**：设备前台导航、退出 App、获取/释放本 run 锁，以及 profile 隔离的本地 JPG/XML/审计写入；ui-evidence在无法取树时可能暂停/恢复媒体播放，属于设备播放状态副作用，调用中断可能来不及恢复，必须如实记录，不能一律side_effects=[]；无平台对外写入或账号切换。
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

多阶段节点命令必须严格采用 `<adb_controller> --profile <phone_profile> <command> [args...]`；多阶段cleanup的close-app同样带刚核对的精确--lock-owner；其他多阶段命令沿用原前缀。独立只读子流程的六类动作严格采用 `<adb_controller> --profile <phone_profile> --lock-owner <run_id> <command> [args...]`，这是本节逐字前缀检查的明确例外，不能删除owner参数。`--profile` 和 profile 值不得省略、调换或改写。执行前先逐字核对该前缀，前缀不完整时不得调用节点。

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

在多阶段 Workflow 中，成功的预检、发现、判定和评论 Worker 不得各自退出 App 或释放锁；它们把同一 `run_id` 的锁留给下一阶段。无论安全停止、阶段终止、blocked 或 failed，非 cleanup Worker 均只报告事实并保留共享锁；只有可信编排器已进入 manifest 的最终 `stage_id=cleanup`，且close-app前回读锁的归一化run根精确为本run、stale=false、剩余租期覆盖该命令超时预算时，才把刚读取的原始owner逐字作为--lock-owner传入 `close-app`；本版多阶段cleanup也使用同一原子guard，命令开始时精确复核owner及租期（age+1000<ttl），不足即blocked保留锁，不删除owner参数以套旧入口。既有未带owner的close-app入口也会在真实guard内执行，独立标记锁下直接拒绝，整个旧关闭期间阻止新认领；这不声明其他旧业务动作都已迁移到原子owner入口。随后验证前台包不再是 `com.ss.android.ugc.aweme` 并检查桌面截图。失败只重试一次。

在多阶段 Workflow 中，发现、判定、评论、交付等非 cleanup Worker 即使返回 `blocked` 或 `failed`，也不得自行调用 `close-app` 或 `lock-release`；它只报告事实并把清理权交回可信编排器。只有任务身份明确为 `stage_id=cleanup` 的多阶段 Worker 可以释放锁。独立当前账号只读任务仅在任务明确 `mode=standalone_account_read`、`cleanup_authorized=true` 且有本次从 free 新取得锁的原始回执时，按「当前账号只读与证据留存」自行收尾；不得收尾任何已有锁或其他 Workflow。

多阶段仅可信cleanup、独立仅本节授权收尾者可执行最后的lock-release；安全停止的非cleanup Worker、锁已过期或归属不可确认者只报告事实，不做清场或释放。多阶段合格收尾者调用 `<adb_controller> --profile <phone_profile> lock-release <run_id>`；独立子流程只在默认桌面证据齐全后调用 `lock-release-exact <run_id>`。二者均回读 `lock-status`。只有 App 已退出且锁已释放，清理才算通过。

区分提醒与挑战页：切号后短暂出现“完善安全设置”等 toast、气泡或推荐提示时，等待页面稳定后再截图一次；若提示消失、目标账号主页可正常读取且操作未被遮挡，只记录 warning 并继续。只有提示持续遮挡、跳入安全设置/登录流程、要求验证码/实名/人脸/密码，或页面无法继续时，才返回 `blocked`。登录确认、验证码、实名、人脸和明确风控挑战不得绕过。

## 禁止动作

默认禁止点赞、关注、评论、回复、私信、对外分享、推荐、发布、修改账号、绕过验证码/人脸/风控或清除 App 数据。唯一例外是控制器封装的 `current-video-link` 只读取链动作；它必须在语义节点和回读链接全部验证后才成功，不能扩展为任意分享动作。来电、通话、账号/设备不匹配、登录挑战、连续截图失败立即停止（节点断连不属于截图失败，先按「截图回传与节点断连」核实并重试一次）。

当前控制器实现由部署蓝图中的兼容入口维护；运行时始终逐字使用租户登记的安装路径，Skill 内不保存、推导或补写真实路径及文件后缀。

## 版本记录

- 1.0.0（2026-10-08，首次版本登记）：由独立核验通过的运行沉淀当前账号只读子流程，明确独立任务授权、锁归属、断连、同屏证据和成功判定；其余流程保留。

### 独立任务输出及核验审计来源

本子流程不返回多阶段 preflight 的 WORKER_RESULT；仅已确认不同owner持锁时按 DEVICE_BUSY 约定只输出标记，不输出JSON；已有同run锁、锁归属不明或新取得回执丢失，按本节步骤1报告blocked JSON并保留锁跟踪原run，优先于通用DEVICE_BUSY建议；其余结束情形执行者仅输出 stage="explore" 的JSON：task_id、run_id、claimed_result（success/failed/blocked）、read_values（nickname、douyin_id、business_identity_verified）、trajectory、final_evidence、side_effects、lock_released（布尔）、fail_reason。当前只读角色 business_identity_verified=false；若另有 metrics.account_verified 必须为0，不将“已读到当前账号”计作业务角色核验。success仅是执行者声明，不是独立验收通过；读取、默认桌面、锁释放任一证据缺失即failed或blocked并写真实已有证据。

无对外动作的最终判据由独立审计与run-verify负责。审计员按运行时回执中的agent/session身份，只读该执行宿主 ~/.openclaw/agents/<agent>/agent/openclaw-agent.sqlite（mode=ro），限定本运行窗口，核对完整工具凭证与SDK终态工具计数一致、控制器动作及原owner取得/释放/最终free。审计员将汇总证据写入Brain独立审计任务 result.evidence.audit，并提供audit_task_id；关于命令与锁审计，核验员只GET该独立审计任务；主页、默认桌面与30秒证据绑定仍按final_evidence亲自回传查看原始JPG/XML和采集回执，不读执行会话或轨迹，须确认source_run_id一致、coverage_complete=true、external_platform_write_commands=0、account_switch_commands=0、unknown_device_commands=0和锁回执。执行者不写这份独立审计。无审计指针、运行号不符或覆盖不完整，run-verify判unknown/fail，禁止声称独立验收通过。

独立子流程优先采用本节的绑定证据及审计判据：取证期间也必须持有有效租约，桌面证据也必须遵守30秒内同ID配对、前后前台包精确等于默认HOME且页面未变化，释放前再次只读foreground确认桌面；失败就保留本锁。释放前最后一次回读须确认本 owner、stale=false、剩余租期超过本命令预算。lock-release-exact 回执若因断连丢失，free仅证明当前空闲，不能证明由本run释放；没有原owner释放的独立审计凭证时，claimed_result必须failed或blocked，fail_reason写归属证据缺失，不再重复释放，也不宣称核验通过。

独立子流程的 account-current 会导航，断连后不能直接重做：原远端调用无可信终态即保留锁并停止；有可信终态后才只读确认前台、当前账号页与有效本owner；若已在本人页只重采证据，尚未进入才可重做一次，页面身份不明即停止，不凭旧坐标操作。

若锁回读不能满足age+1000<ttl，禁止继续前台或取证；保留自身锁并交Brain跟踪原run，claimed_result=blocked，fail_reason=lease_budget_insufficient，不能声称桌面收尾成功。

### 异常锁的受信复核与恢复

保留锁是当前未满足清理证据的安全状态，不是永久封锁结论。独立探路执行者不续租、不夺锁；由已有手机节点权限的受信运维会话负责复核，先在Brain登记原task_id/run_id的恢复任务并记录actor、触发原因和证据，员工正文不得自行取得运维权限。只读核对原Brain任务、原远端调用真实终态及终止证据；CLI退出、超时或仅查不到同名进程都不能代替原命令及其子进程已终止的证据。不能证明则保持标记和锁，恢复任务报告blocked及缺失证据，不声称已回收。

证据证明原调用与子进程已终止、控制器guard空闲、锁owner逐字等于原run、设备/通话预检匹配且idle后，运维会话可只对原owner调用lock-refresh恢复收尾租约（不运行新业务、不修改owner）；随即重新核对精确owner、stale=false、age+1000<ttl。恢复会话须有至少400秒有界父预算，六类动作仍带原run的--lock-owner；只执行close-app、return-safe-desktop和桌面JPG/XML取证，不重做读取或切号。默认HOME证据、前后前台和原owner齐全后仅lock-release-exact原run，再读free；成功/失败、原命令终止证据、续租和释放回执全写回Brain恢复任务。不满足任何条件就保留并记录具体原因，不能让通用巡检代替复核。本节是受信运维的明确例外，不套用独立探路必须新认领/不续租的规则；lock-refresh在实际guard内原子复核本run归属，成功回执才证明当次取得guard，忙或失败就停止，不以lock-status证明guard空闲。此受信运维例外只恢复原独立锁；不改变多阶段Workflow清理授权。

### 独立子流程的最终证据结构

`final_evidence` 使用对象数组。账号页与桌面各一项：`{kind:"account_home"|"safe_desktop", run_id, node, profile, evidence_id, jpg_path, xml_path, started_at, ended_at, foreground, identity:{nickname,douyin_id,own_profile_markers}}`；账号页填写实际读数和本人标记，桌面identity可为空对象。started_at/ended_at为本对JPG/XML采集的真实UTC工具时间；路径逐字来自回执。锁证据分别为 `{kind:"lock_acquire"|"lock_release"|"lock_status", run_id, observed_at, receipt}`，receipt保存原始服务回执。独立审计任务指针由审计/核验阶段补充；执行者没有独立审计时如实标缺，不自行填造审计结论。

### 独立子流程的断连优先规则

本节优先于共享动作的“未生效重做”建议：任何前台或取证命令发生断连、超时或结果不确定，均不重发；只读状态不是首次命令已终止的证明。原远端调用尚无真实终态时停止发新命令、保留自身锁、返回blocked及已有证据，交Brain跟踪原run，不释放锁、不另造运行号重做。仅取得原远端调用已终止的可信服务回执后，才可在有效精确本owner下做清理；不能证明就报告cleanup_unproven、lock_released=false。

通话预检是采样门禁，不承诺执行全程的原子来电保护；每次前台调用前后采样，观察到来电/通话即停止新前台动作。若采样间发生通话干扰，报告call_interrupted及已有证据，不把本次执行判为成功；正在执行或结果未知的旧调用沿用上述不重发、不提前放锁规则。
