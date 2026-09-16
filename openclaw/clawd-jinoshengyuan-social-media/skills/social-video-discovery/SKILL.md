---
name: social-video-discovery
description: "Discover, link, and deduplicate platform-visible social videos by executing the immutable search policy in a validated task_request, including selectable sort, time, duration, scope and location filters. Use as the first business stage of a social lead-generation workflow, including an explicitly requested bounded discovery_smoke profile."
---




## 点击卡片：只用 search-video-cards 返回的坐标（0913 死规则）

`search-video-cards` 每行输出 `x<TAB>y<TAB>时长<TAB>标题`，点击就是：

```
<adb_controller> --profile <phone_profile> tap-evidence <x> <y> <evidence_id>
```

**禁止**用 `locate-tap`/视觉描述去定位卡片，**禁止**对标题做 base64 或任何转码再喂给定位器——
0913 实证：worker 把标题转码成乱码「全安宇人品人务卡布员布务员布…」喂给视觉模型，连拒 3 次，
最后一次尝试整个作废。坐标已经在手里了，定位器没有任何存在必要。

## 评论数前置闸（0913 主理人拍板：零评论的视频不许流向后续任何工序）

我们要的是**评论区里的人**，不是视频本身。所以：

1. 每个候选进入详情页验证时，**必须从当前详情页 UI 树读评论数**：
   节点形如 `content-desc="评论3，按钮"` / `content-desc="评论736，按钮"`（数字即评论数）；
   若只有 `content-desc="评论评论，按钮"` 这类**不含数字**的形态，即评论数为 0（0913 真机实证：零评论视频就是这个形态）。
   控制器 `open-video` 的输出会带 `comment_count=`，直接采用；用 `current-video-link` 路径进入的，从 detail 证据 XML 里读。
2. `comment_count=0` 的候选：记为 `excluded_no_comments`（带证据），**不写入 candidates、不交给判定阶段**，
   在 `video_limit` 边界内继续扫下一张卡。这是确定性排除，同 note/图文一样合法，不得因此 blocked。
3. 每个写入 candidates 的候选**必须携带 `comment_count` 字段**（>0），验收方按此核对。

理由：录屏 90 秒 + ASR 是全链路最贵的工序，评论数是树上零成本的字段。0913 实证：一条合格视频
完整走完录屏+转写+判定后才发现零评论，整轮白跑——最贵的工序被放在了最便宜的过滤器前面。


## 交结果之前先落盘（尽力而为，绝不因它阻塞）

输出最后一行 `WORKER_RESULT {json}` 之前，先用**网关侧文件写工具**（不是 `exec`）把**完全相同**的 JSON
写到这个确定路径：

```
/root/clawd-work-commander/state/workflow-runs/<run_id>__<attempt_id>.<stage_id>.<stage_attempt>.worker-result.json
```

这条路径是可写的（0913 实证：preflight 第 3 次正是靠它写成、Commander 读到、阶段才通过）。
偶尔 `file_write` 会失败——那时记一条 warning 就好，见下。

**这份落盘是尽力而为的备份，不是验收条件。**写失败就在 `warnings` 里记一句然后照常返回你真实的
`status` 与 `recommended_next_action`。**任何情况下都不得因为"回执没写成"而把 `status` 改成 `blocked`**——
那会把一次成功的阶段变成失败。它不需要 write-guard、不计入 `business_writes` / `artifact_writes` / 外部交互计数。

## 调用手机控制器的超时（必读，没有例外）

对 `douyin-phone-adb` 的**每一次** exec 调用都显式设置 `timeout: 300000`（毫秒）。
不要按命令名挑、不要凭"这条看起来很快"估一个值：任何命令都可能要读 UI 树，
而读树内置重试最坏约 180 秒；连 `lock-release` 这种瞬时命令也会因链路排队而超过十几秒。

0912 实证：worker 自行给 `current-video-link` 估了 70000ms、给 `lock-release` 估了 15000ms，
两条都在正确执行的半途被掐断，报成 `gateway timeout`。
整轮 discovery 的第 4 次（也是最后一次）尝试就断送在这里——
筛选已应用、四张相关卡片已识别、详情页已打开，只差取链接这一步。


## 构造 WORKER_RESULT 的第一步：先数 candidates，再定 status

| 本次 candidates 数 | status | retryable | recommended_next_action |
|---|---|---|---|
| ≥ 1 | completed | — | accept |
| = 0（正式获客模式） | **failed** | **true** | **retry** |

**零候选时禁止以「扫描边界完整 / 证据齐全」为由报 completed** —— 扫描完整只说明你扫完了，
不代表获客目标达成。此表优先级高于本文其他一切表述。
（`contract_test` 与显式 `discovery_smoke` 不适用此表。）

## 产出契约（构造 WORKER_RESULT 前逐项自检）

> 本节与 `agentic-workflow-runtime/references/protocol.md` 的「metrics 封闭键集」逐字一致；
> 冲突时以 protocol.md 为准。适用阶段：discovery。

**metrics 必填**（没发生就填 0，禁止自造键名）：通用 4 键 `external_interactions` `business_reads` `business_writes` `artifact_writes`；本阶段另加 `keywords_processed` `screens_scanned` `candidates`。

**真实模式 completed 的最小 evidence**（`evidence` 必须是对象数组，空数组不接受）：
- completed 至少每个候选 1 条：`{"type":"discovery","video":…,"url":…,"comment_count":…}`

- status 由文首「先数 candidates」决策表决定，本节不重复。

# 社媒视频发现

只负责从关键词生成可重新打开的视频链接集合；不做视频合格判定，不读评论，不写原始评论、最终线索或关键词游标。

## 输入与边界

读取可信任务中的租户、平台适配器、目标人群、执行 profile，以及经过 Intake 校验并冻结的 `task_request`。所有平台动作只通过已登记的 `platform_adapter`；禁止点赞、关注、评论、私信、对外分享、推荐或发布。允许适配器内部的 `current-video-link` 只读取链动作，因为它不选择联系人、不发送且有语义节点与链接回读双重验证。

当 `stage_attempt > 1` 时，任务必须携带 Manager 从上一轮耐久裁决生成的 `manager_feedback`。先逐项核对它属于同一 execution、stage 和紧邻的上一 attempt，再只在未改变 frozen `task_request` 的范围内修复清单；禁止无反馈地重复上一轮路径。最终 `WORKER_RESULT` 必须返回 `manager_feedback_ack`，逐项列出 `resolved`、`unresolved` 及本 attempt 的新鲜证据；仍有未解决项时不得声称 completed。

普通 `full` profile 必须逐项执行 `task_request.keywords` 和 `task_request.search_policy`，不得在运行中自行优化或改写。可执行值为：

- 排序：`comprehensive | latest | most_liked | most_commented | most_favorited`；
- 发布时间层：`one_day | one_week | six_months`，可按任务数组顺序执行一层或多层；
- 视频时长：`unlimited | under_one_minute | one_to_five_minutes | over_five_minutes`；
- 搜索范围：`unlimited | following | recently_viewed | not_viewed`；
- 位置：`unlimited | same_city`。

如果用户未指定，Intake 可以写入推荐默认值：`most_commented`、`[one_week, six_months]`、`unlimited`、`unlimited`、`unlimited`。默认值必须出现在 `defaults_applied` 和任务卡中；Agent 自己不得补默认值。

对每个时间层继续向下扫描，直到平台结果结束或连续无新稳定视频 ID。多时间层按合同顺序执行；后续层中已出现的视频按视频 ID/解析链接去重，仅合并新证据，不重复创建候选。

任务只声明一个排序时，不擅自添加第二排序通道。可见点赞、评论和收藏数始终作为候选元数据保存。

每一屏先用同一份新鲜 UI XML 与截图对全部可见卡片做一次相关性初筛，再决定是否进入详情。`exhaust_visible_results=true` 要求每个可见卡片都有明确处理结论，不等于每个卡片都必须执行分享取链：

- 对每个可见卡片记录屏号、屏内序号、可见标题/文案、作者、发布时间/时间标签、可见互动数、`relevant | irrelevant | non_video | uncertain` 结论、理由和当前屏证据；
- 标题/文案可直接证明与冻结目标人群无关的卡片，记为 `irrelevant` 后继续，不打开详情、不调用 `current-video-link`；这类带理由的排除项已满足该卡片的穷尽责任；
- UI 已明确标为图文/note 的卡片可记为 `non_video`；若内容类型不能从结果页可靠确认，则必须记为 `uncertain` 并进入详情，禁止猜测排除；
- `relevant` 和 `uncertain` 才进入详情并执行后续稳定链接验证；不能因为相关卡片取链较慢而把未处理卡片写成已穷尽；
- 最终工件必须同时列出 `visible_items`、`excluded_items`、`candidates` 和停止条件。只要每个可见卡片都有上述结论、所有相关/不确定卡片均完成详情判定，且滚动停止条件成立，就可声明可见结果穷尽；不得把“无关卡片未取稳定链接”列为 unresolved。

当抖音筛选弹层的选项不进入 Accessibility 树时，完整筛选必须通过已登记适配器命令 `search-time-layer <time_layer> <evidence_id> <sort> <duration> <scope> <location>` 选择，并逐项传入冻结任务中的筛选值。该命令从“筛选弹层尚未打开”的搜索结果页开始，内部负责语义定位并点击“筛选”，依次选择排序、时间、时长、范围和位置，验收浮层、全部选中态及返回结果页；仅为旧 contract/兼容调用保留双参数形式，真实 full 模式不得省略四个筛选参数。Worker 调用前严禁用 `tap`、`tap-evidence` 或其他动作预先打开/点击筛选，否则会造成二次点击关闭弹层。Worker 只可用新鲜 UI 证据确认当前处于搜索结果页，然后直接调用一次 `search-time-layer`；禁止自己猜测筛选坐标。对控制器返回的 panel / selected / results 三张新鲜证据各执行一次且仅一次 `file_fetch`，并验收 selected 证据与全部冻结筛选值一致后才读取结果。

只有任务同时显式声明 `mode=discovery_smoke` 和 `tenant_context.smoke_test.enabled=true` 时，才使用有界测试 profile：

- 处理任务指定的全部 smoke 关键词；
- 每个关键词最多读取 `max_screens_per_keyword` 屏，默认 1 屏；
- 最多保留 `max_candidates_total` 个带稳定 ID 和日期证据的观察候选，默认 5 个；
- 停止原因写为 `smoke_boundary`，不得声称完成正式全量发现；
- 只写本地测试工件，业务系统写入、游标更新和外部互动必须全部为 0。

## 发现证据

每个经过相关性初筛后进入详情的视频候选必须记录平台视频 ID、分享链接/解析链接、标题/文案、作者、发布时间、可见评论/点赞/收藏数、命中排序通道和截图证据。结果页已带明确理由排除的 `irrelevant` / `non_video` 卡片不属于视频候选，不要求稳定链接，但必须保留初筛结论和屏幕证据。没有可重新打开的链接时，当前视频对象不得作为已完成候选；允许保留为 `link_pending` 并由当前 Agent 在发现阶段恢复。

候选进入详情并由新鲜 UI 证据确认后，逐个调用一次且仅一次 `<adb_controller> --profile <phone_profile> current-video-link <evidence_id>`。控制器显式返回 `content_type=note`、`excluded_non_video=true` 和稳定 `note_id` 时，必须记为 `excluded_non_video`并继续扫描；禁止把 `note_id` 复制、改名或映射到 `video_id`，禁止把 note 写入 `candidates`。取链内部为回读剪贴板使用的临时搜索框不是安全停止条件；排除 note 后若不在结果页，立即用 `open-search` 重新打开同一个冻结关键词，重施完全相同的冻结筛选，从可见边界继续；这是 note 排除后的允许恢复，不得因此 blocked。note 不是视频候选、不是 `link_pending`，不得仅因搜索结果中出现图文/note 而中止本阶段，也不得将其交给后续 ASR 判定。对 `content_type=video` 只接受控制器同时返回并能相互校验的 `video_id`、`short_url`、`resolved_url` 与 `reopen_url`；缺任何一项都把该视频保留为 `link_pending`，不得伪造 ID、散列标题充当平台 ID或声称发现完成。Worker 不得自行点击分享/收藏区域，不得用固定坐标拼装取链步骤。

只把发布日期落入窗口的对象计为候选；日期未知时记录为排除项。同一视频仅保留一次，并合并命中关键词、排序通道和所有证据。

输出按 `task_request.search_policy.time_layers` 分组，后续组只保留去重后的增量对象；组内保留任务所选排序的可见顺序。输出必须附带 `task_request_hash` 和实际筛选证据，证明执行参数与冻结合同一致。

### 证据提取与性能

- 每一屏使用不可覆盖的 `evidence_id`，至少包含 `execution_id`、`stage_attempt`、关键词序号和页序号；禁止把循环中的所有截图写到同一路径。
- 控制器或复合动作返回证据路径后逐字原样传给 `file_fetch`；禁止手工补目录、重复添加 `evidence/`、把本地路径当 `image_url`，或在失败后复用旧媒体对象。
- 适配器支持可访问性树/UI hierarchy 时，先提取结构化文本和节点边界，再用截图补充视觉信息。不得因为结构化提取可用仍重复让视觉模型识别同一屏。
- 滚动动作优先使用“动作 + 唯一证据截图”的复合命令，避免一次滚动拆成多个远程往返。
- 同一屏只解析一次并缓存屏幕指纹、稳定 ID、日期与证据路径。屏幕指纹不变时不重新调用模型；累计连续无新增次数后按配置停止。
- 图片或 UI 结构单次失败可对当前屏重取一次；仍失败则返回可重试证据，禁止用空候选伪装成正常零结果。
- 正式阶段结束前，使用本阶段所有 `evidence_id` 的共同前缀调用一次已登记适配器命令 `evidence-bundle <evidence_prefix>`。逐字采用控制器返回的独立 `bundle_archive`、`archive_kib` 和 `archive_sha256`，对该 `.tar.gz` 归档调用一次且仅一次 OpenClaw 现有 `file_fetch`；禁止 shell/scp、自造上传协议或拉取整个 profile 历史 evidence 目录。归档是非图片文件，`file_fetch` 必须返回 Gateway media store 的 `localPath`。**回读按执行体分工，不要在网关路径上跑 shell**——`exec` 跑在执行节点（如 XIAN-M4-PHONE），Gateway 的 `localPath` 在节点上不存在，对它跑 `sha256sum` / `tar -tzf` 必然失败（0912 实证：整轮发现阶段因这一条恒为 unresolved 而被拖成 retry）。正确做法是三段：①在**节点侧**（归档诞生地，用 exec）对控制器返回的 `bundle_archive` 跑一次只读 `sha256sum` 与 `tar -tzf`，验收 SHA 与控制器一致、成员数与 `files + manifest.sha256` 一致、所有成员都位于本阶段前缀目录且归档小于 15 MiB；②`file_fetch` 成功返回 Gateway `localPath` 即视为已送达网关侧；③把节点侧 SHA、成员摘要与该 Gateway `localPath` 一并写进 `evidence`，由 Commander（本就跑在网关侧）自行读取该路径完成最终核对。最终 `evidence` 必须列出这个 Gateway `localPath`、SHA 和归档成员摘要（可同时保留 Node 原始路径作为 provenance）；只返回 `/private/tmp/...` Node 路径不得声称 completed。归档 `file_fetch`、SHA 或成员回读失败，或 Commander 不能读取该 Gateway `localPath` 时返回可重试结果。

## Runtime 写入栅栏

当阶段信封声明 `orchestrator=n8n` 时，禁止召唤其他 Agent 或 Commander。使用 n8n 提供的 `execution_id`、`stage_attempt`、`idempotency_key` 和 `task_request_hash`；只返回本阶段结果，由 n8n 决定后续节点。`contract_test` 不操作手机、不写工件或业务系统，只验证合同并返回零动作结果。

旧 Commander 兼容模式必须在 Worker 任务中传入 `run_id`、`attempt_id`、`execution_id`、`lease_id`、`worker_agent_id`、`stage_id=discovery`、`stage_attempt`、完整 frozen `task_request`、`task_request_hash` 和 `write_guard.command`。写入或替换发现工件前调用一次 `artifact_write` 授权；授权失败时不得写文件，并返回 stale/fenced 的失败结果。最终 `WORKER_RESULT` 必须带上相同 `task_request_hash` 以及授权回执中的 `fence_token` 与 `commander_event_id`。

正式模式的 discovery 工件和 guard receipt 必须写到 Commander 可读的网关侧绝对路径 `/root/clawd-work-commander/artifacts/discovery/`。**写入必须用 OpenClaw 的文件写工具（write/edit，它们落在网关侧文件系统）；严禁用 exec 在执行节点上写**——exec 跑在远程节点（如 XIAN-M4-PHONE），节点上不存在 `/root/clawd-work-commander`，会得到 read-only/ENOENT（0912 实证：attempt2 用 exec 写失败，attempt3 改用文件工具写即 accepted）。禁止返回 `artifacts/...` 相对路径或只在 Worker Session 中存在的临时路径。先用文件工具创建该精确目录，再执行 `write_guard.command`，把完整授权回执写成与工件同 basename 的 `.guard.json`，随后写发现 JSON；两者都必须立即按绝对路径回读并验证非空、`task_request_hash` 与当前执行一致、guard 的 `commander_event_id` / `fence_token` 与本阶段授权一致。最终 `artifacts` 和 `write_fences` 只能列这些已回读的绝对路径；Commander 读不到任一路径时不得声称 completed。

`stage_id=discovery` 无论返回 `completed | blocked | failed`，都严禁调用 `close-app` 或 `lock-release`；非 cleanup Worker 没有清理权，必须把 App 和同 run 锁留给编排器。若 `stage_attempt > 1` 且上一个 discovery Worker 违规导致同 run 锁为 free，本次允许且仅允许一次同 `run_id` 恢复：运行 `preflight`、`lock-acquire <run_id>`、`open-app` 并重新验收设备/通话；账号身份若本 run 的 preflight 阶段已验证且期间锁从未被其他 owner 持有，视为仍然有效，**禁止为复核账号而离开当前搜索上下文导航到账号页**（搜索结果页导航去「我」页失败率高，是已知死因）。然后继续当前 discovery；不得抢占其他 owner 的锁。这不是新的 preflight 阶段，不改动 n8n 阶段和裁决协议，只是对上一次违规清理的同阶段安全恢复。

若 `stage_attempt > 1`、控制器锁仍由当前同一 `run_id` 持有，但 `preflight` 或 `foreground` 明确显示注册设备处于 `AOD` / `NotificationShade`，不得把正常息屏直接当作 discovery 业务阻塞。只允许一次受控恢复：保存恢复前证据，调用 `wake` → `unlock`，再调用一次 `preflight`；确认没有 PIN、密码、人脸、登录确认、安全设置或风控挑战后才 `open-app`；账号身份沿用本 run preflight 的验证结论（锁连续持有即有效），**不得为复核账号强行导航离开搜索上下文**，直接继续冻结关键词与筛选边界。恢复后仍为系统锁屏/通知栏、出现任何挑战、账号不符且租户策略未授权精确切换，或锁 owner 不是当前 `run_id` 时立即返回 blocked。不得循环唤醒，不得绕过系统挑战，也不得释放锁或新造 n8n 阶段。

`artifacts` 只列经过 `artifact_write` 围栏授权并已实际写入的发现 JSON 等工件；手机截图、UI XML 和控制器取链截图全部列入 `evidence`，不得混入 `artifacts`。没有受控工件写入时必须返回 `artifacts: []` 与 `write_fences: []`。

## Worker Result v2

结束时最终可见回复必须只有一条 `WORKER_RESULT` JSON。`status` 只能是 `completed | blocked | failed`，绝不使用 `success`。正式获客模式必须至少返回 1 个满足全部证据要求的候选；即使扫描边界完整，零候选也不代表获客目标完成，必须返回 `status=failed`、`retryable=true` 和 `recommended_next_action=retry`，由 Commander 与 n8n 在既有 V4 重试机制中处理。`contract_test` 的零动作结果和显式 `discovery_smoke` 的有界观察不受此最低候选规则影响。

```json
{
  "type": "WORKER_RESULT",
  "schema_version": 2,
  "run_id": "required",
  "attempt_id": "required",
  "execution_id": "required",
  "task_request_hash": "required SHA-256",
  "stage_id": "discovery",
  "stage_attempt": 1,
  "tenant_id": "required",
  "worker_agent_id": "required",
  "status": "completed",
  "summary": "required",
  "metrics": {
    "keywords_processed": 0,
    "screens_scanned": 0,
    "candidates": 0,
    "external_writes": 0,
    "external_interactions": 0
  },
  "artifacts": [],
  "evidence": [],
  "warnings": [],
  "retryable": false,
  "recommended_next_action": "accept"
}
```

## video_limit 优先（限量任务的停止条件）

当冻结任务的 `search_policy` 携带 `exhaust_visible_results=false` 且给出整数 `video_limit`（1..10）时，**以 `video_limit` 为唯一停止条件，不追求可见结果穷尽**：
- 按同一冻结筛选正常扫描，累计到 `video_limit` 个已完成稳定链接验证的 `candidates` 后立即停止扫描，声明 `stop_reason=video_limit_reached`。
- 不要求 `visible_items` 全部有结论，不要求滚动到结果底部，`exhaustion` 字段填 `not_required`（不是 unresolved）。
- 已扫描但未处理的可见卡片记为 `not_reached`，不算违规。
- `exhaust_visible_results=true`（或未给 `video_limit`）时，维持原「穷尽可见结果」规则不变。
