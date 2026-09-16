---
name: social-comment-lead-collector
description: "Exhaust platform-visible comments inside the configured date window for every qualified social video using fair round-robin batches, resumable cursors, and raw-pool checkpoints. Use as the third business stage of the social lead-generation workflow; collect evidence only and do not score or deliver leads."
---




## 如何回到已验证的视频（0913 新增，必读——以前没有这段，三次尝试全废在重走搜索上）

**绝不要用搜索去重新找到目标视频。**搜索结果的综合 tab 是自动播放 feed，UI 树确定性读不到
（0913 实证：collection 三次尝试全部死在"搜索结果层级不可读"）。discovery 的已验收工件里有
`video_id` / `reopen_url`，这就是给你的确定性入口：

```
<adb_controller> --profile <phone_profile> open-video <video_id> <evidence_id>
```

它用平台 deeplink 直开详情页并用分享按钮守卫复验落点，成功输出 `video_opened=1`（实测 7 秒）。

**验证评论者身份：逐字复制，绝不自算。**`collect-comments` 的每一行已带
`tap=<x> <y>`（头像中心坐标）和 `b64=<昵称base64>`，验证时原样拼进命令：

```
<adb_controller> --profile <phone_profile> commenter-identity <tap的x> <tap的y> <b64值> <evidence_id>
```

成功输出 `nickname=`、`douyin_id=`、`account_type=` 三行。**按 account_type 处置（0913 死规则）**：
- `personal`：正常客资，进原始评论池；
- `organization`：企业/组织认证号（主页无抖音号是平台常态）——**几乎必然是同行蹭评论，标记 `non_lead_org` 记录后排除**，不算失败；
- `id_not_visible`：昵称已核验但号不可见，写入时标 `identity_partial`。

**部分成功必须写入（一颗老鼠屎不许毒死整批）**：批内每条评论独立结算——身份验证成功的照常写入原始评论池；
个别评论者验证失败（有界重试后）标 `identity_unverified` 连同评论文本一起写入，绝不因个别失败丢弃整批。
0913 实证：3 条评论 2 个身份已到手，因 1 个企业号提取失败被整批作废，两条真实客资白丢。（0913 真机闭环实证：爱吃猫的鱼、→QQ691824418，3011→666622m）。
自己猜坐标或自己转 base64 是被禁止的——0913 实证 worker 把昵称"3011"当坐标、把 base64 转错，三次尝试全废。
落到详情页后再调 `open-comments <evidence_id>` 进评论区、`collect-comments` 采集。
调用控制器的每一次 exec 一律 `timeout: 300000`。命令名以 `--help` 列出的为准，
不存在 `search`、`open-app douyin` 这类写法——0913 实证 worker 发明命令浪费了整段尝试。


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


## 产出契约（构造 WORKER_RESULT 前逐项自检）

> 本节与 `agentic-workflow-runtime/references/protocol.md` 的「metrics 封闭键集」逐字一致；
> 冲突时以 protocol.md 为准。适用阶段：collection。

**metrics 必填**（没发生就填 0，禁止自造键名）：通用 4 键 `external_interactions` `business_reads` `business_writes` `artifact_writes`；本阶段另加 `comments_collected` `videos_processed` `cursor_updates`。

**真实模式 completed 的最小 evidence**（`evidence` 必须是对象数组，空数组不接受）：
- completed 至少每个已处理视频 1 条：`{"type":"collection","video":…,"rounds":…,"comments":…,"exhausted":true|false}`

- 断点续采：恢复运行只导航到未完成视频，evidence 里注明续采起点。

# 社媒评论窗口穷尽采集

当由 `agentic-workflow-runtime` 调用时，只执行 frozen `task_request.comment_policy`，结束前返回唯一 `WORKER_RESULT`，包含相同 `task_request_hash`、每个视频的采集轮次、实际评论数、游标、是否取光、停止原因、原始池写入和风险状态。哈希缺失或不一致时不得执行。

只读取 `qualification.json` 中唯一结论为 `qualified` 的视频。

## 采集策略

`visible_window_exhaustive` 使用“日期窗口内可见评论穷尽＋公平轮转”：

1. 从 `task_request.comment_policy` 读取 `window`、`batch_size`、`scheduler`、`per_video_limit`和无新增阈值。租户策略只供 Intake 补默认值，Worker 不再读取它覆盖本次合同。
2. 对每个合格视频先采一轮最多 `batch_size` 条，立即写入断点和租户可见原始评论池。
3. 转到下一个合格视频，直到所有视频都完成当前轮。
4. 然后回到 `exhausted=false` 的视频读取下一批 `batch_size` 条，持续轮转。
5. 直到每个视频均因“到达评论时间边界、平台列表结束、连续无新稳定 ID”之一进入 `exhausted=true`，或安全条件要求停止。

`top_n` 仍按相同 round-robin 调度，但每个视频累计达到 `per_video_limit` 后以 `exhaustion_reason=contract_limit_reached` 停止；不得把它误报成平台评论已取光。

“全部评论”始终表示平台对当前账号实际展示、且落入配置日期窗口的全部可见评论。不得声称覆盖平台未展示、已删除或无法访问的评论。

## 每轮必存状态

每批一个 `comment-batch.json`，并原子更新 `comment-leads.json`：

- `video_id`、`batch_no`、`batch_size`、`new_comments`、`total_comments_collected`；
- `next_cursor`、`exhausted`、`exhaustion_reason`、`oldest_comment_observed_at`；
- 评论原文、评论者显示名、稳定用户标识/主页标识、评论 ID、视频 ID、发布时间和截图证据；
- 已写入原始池的稳定 `raw_comment_id` 和回读证据。

评论列表即使有数千或数万条，也不得一次性放入模型上下文。只按批次读取、写入和恢复。

## 页面与安全

- 每次进入评论区后验收评论列表可见、输入框未聚焦、软键盘未弹出。
- 必须从当前截图或可访问性树重新定位评论入口，不复用过期坐标。
- 禁止点赞、关注、回复、私信、输入文字或发送。
- 验证码、登录挑战、账号/设备不匹配、来电、风控或对外互动风险时立即停止并保留游标。

## 去重与恢复

本阶段只做原始对象去重：同一评论 ID 不重复写；同一人在不同视频或批次的评论保留全部来源，不在本阶段当成同一条评论删除。

恢复时只读取同一 `run_id`、租户、设备、账号和 qualification 输入指纹的断点，从最早的 `exhausted=false` 视频下一游标续跑。

## Runtime 写入栅栏与输出

当 `orchestrator=n8n` 时不得召唤 Commander、其他 Agent 或下一阶段。只处理本节点输入并回传相同的执行身份、阶段、幂等键和 `task_request_hash`；由 n8n 验收并推进。`contract_test` 只验证合同，不操作手机、不读取评论、不写原始池。

- 每次更新本地工件前申请 `artifact_write`；每批写原始池前申请 `raw_comment_insert`。
- 每个授权回执只覆盖紧随其后的同一批写入。
- 最终只有全部合格视频都 `exhausted=true`、批次指标可回算、原始池写入已回读，阶段才能 `completed`。

输出 `comment-leads.json` 和批次工件；两者都必须包含 `task_request_hash`。本阶段不评判强/弱意向、同行或广告，不写最终线索表。
