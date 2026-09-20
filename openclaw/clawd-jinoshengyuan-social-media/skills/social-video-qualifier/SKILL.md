---
name: social-video-qualifier
description: "For every discovered social-video link, obtain the complete ASR transcript through douyin-reference-capture-phone, let Luna correct the transcript conservatively, and make one final qualified/rejected/review decision for comment-lead collection. Use as the second business stage of the social lead-generation workflow; never use a separate metadata-plus-15-second verdict."
---





## 零评论候选不做转写（0913 主理人拍板）

收到的候选若 `comment_count=0`（或证据 XML 里评论按钮无数字），**不录屏、不提音、不调 ASR**，
直接返回该候选 `skipped_no_comments`（带详情页证据）。评论区没人，判定它讲什么毫无意义——
后续采集阶段无货可采。这是确定性跳过，不算失败、不烧重试。


## 视频没有人声时怎么办（0913 新增，不要当成故障）

通义返回 `400 {"code":"CLIENT_ERROR","message":"ASR_RESPONSE_HAVE_NO_WORDS"}` **不是基础设施故障**，
它的字面意思就是这段音频里没有可识别的语音。抖音上大量视频是纯背景音乐 / 图文轮播，这是常态。

判别只需一步（别猜）：
```
ffmpeg -hide_banner -i <wav> -af volumedetect -f null /dev/null 2>&1 | grep mean_volume
```
- `mean_volume` 高于约 -50 dB ⇒ **音频是有内容的**，那么 NO_WORDS 就是「这条视频没人声」的结论，
  不是录制失败、不是静音、不是凭据问题。0913 实证：判定阶段那条候选 mean −36.3 dB、分段 RMS 稳定在 −37~−40 dB，
  同一台机同一套参数另一条视频转写出 193 字干净文本，可见链路完好。
- `mean_volume` 低于 −80 dB（近乎数字静音）才去查静音/取消静音那条路。

**处置**：把该候选记为 `no_speech`，用可得的其它信号（标题、文案、画面文字）完成判定，
或明确标记为不合格并继续下一条候选。**绝不因此消耗阶段重试预算，也不得把它报成 ASR 不可用。**


## 交结果之前先落盘（尽力而为，绝不因它阻塞）

输出最后一行 `WORKER_RESULT {json}` 之前，先用**网关侧文件写工具**（不是 `exec`）把**完全相同**的 JSON
写到这个确定路径：

```
/Users/administrator/openclaw-root/workspaces-root/clawd-work-commander/state/workflow-runs/<run_id>__<attempt_id>.<stage_id>.<stage_attempt>.worker-result.json
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
> 冲突时以 protocol.md 为准。适用阶段：qualification。

**metrics 必填**（没发生就填 0，禁止自造键名）：通用 4 键 `external_interactions` `business_reads` `business_writes` `artifact_writes`；本阶段另加 `candidates_judged` `qualified`。

**真实模式 completed 的最小 evidence**（`evidence` 必须是对象数组，空数组不接受）：
- completed 至少每个已判定候选 1 条：`{"type":"qualification","video":…,"verdict":…,"confidence":…}`

- `candidates_judged` 必须等于输入候选数；漏判一个都不许报 completed。

# 社媒视频全文案单次判定

当由 `agentic-workflow-runtime` 调用时，必须读取 Commander 传入的 frozen `task_request`，确认 `qualification_policy` 与本阶段兼容。结束前按协议返回唯一 `WORKER_RESULT`，覆盖每个输入候选的全文工件、唯一结论、证据、置信度、可重试性和相同的 `task_request_hash`。哈希缺失或不一致时不得执行。

## 处理范围

对 `discovery.json` 中每个日期合格且已取得链接的视频逐条处理。不允许只挑高点赞或方便打开的视频；所有候选都必须产生结论。

每个视频只判定一次，不再拆成“元数据判定＋前 15 秒判定”。

## 执行

1. 调用 `douyin-reference-capture-phone`，传入原始链接、视频 ID、预期标题/作者和可信租户上下文。
2. 验收 `transcript-package.json`：`coverage=full`（**coverage=full 定义：视频时长≤5分钟为全片覆盖；>5分钟为前5分钟即300秒全覆盖——与「5分钟封顶」铁律一致，不得因未覆盖300秒之外的内容判 coverage 不足**）、视频身份匹配、所有 ASR 分片状态明确、全文转写工件已按 write-guard（`artifact_write`）落盘并回读。**V4 阶段内不以飞书文档为验收条件**——qualification 的写权限仅 `artifact_write`，文档投影归独立 capture / delivery 流程（工件是真相，文档是投影）。部分样本不得进入正常判定。
3. Luna 读取原始分片、合并稿、标题、作者和关键截图，做一次保守校正：处理标点、分段、明显同音错误；没有音频/字幕依据的实词不改，保留 `[听不清]`。
4. Luna 基于完整校正稿做一次最终判定，不再输出中间通过结论。

## 唯一结论

每个视频输出：

- `qualified`：主题和目标人群匹配，评论区有真实需求线索价值；
- `rejected`：无关、主要吸引同行/娱乐围观、纯招商、异常广告或其他不值得采评论的内容；
- `review`：全文覆盖、身份或语义证据不足，不得强行合格。

同时保存：`corrected_transcript`、实质校正差异、`audience_match`、`comment_lead_value`、`confidence`、`reason`、`transcript_doc_url`（仅独立 capture 流程产生；V4 阶段内为 null 属正常）和完整证据引用。

## 输出与写入栅栏

当 `orchestrator=n8n` 时不得召唤 Commander、其他 Agent 或下一阶段。只处理本节点输入并回传相同的执行身份、阶段、幂等键和 `task_request_hash`；由 n8n 验收并推进。`contract_test` 只验证 Skill、输入和返回合同，手机、飞书和业务写入必须为零。

写 `qualification.json`。只有 `qualified` 视频进入评论采集。`rejected` 和 `review` 都不打开评论区。

写入或替换工件前，必须使用 Commander 传入的完整执行身份和 `write_guard.command` 申请 `artifact_write`，其中 `stage_id=qualification` 且 `stage_attempt` 与当前 Commander ledger 一致。`qualification.json` 和最终 `WORKER_RESULT` 回传相同 `task_request_hash`、`fence_token` 和 `commander_event_id`。

本 Skill 不读评论、不写原始评论池或最终线索表。

## 重试盘点（checkpoint 式续跑，重试必读）

重试 attempt 的第一动作是**盘点上一 attempt 留下的工件**，已验证有效的工件必须复用，禁止重做：
1. 录像：若 `<EVIDENCE_ROOT>/<候选录制ID>.rec.mkv` 已存在，先用控制器 `record-stop`（幂等，无进程时仅做校验与救活）确认双流与时长有效；有效则**跳过重录**，直接进入音频提取/转写。
2. 音频：`.16k.wav` 已存在且时长匹配 → 跳过提取。
3. 转写：飞书表已能回读到本候选完整 transcript → 跳过 ASR，直接进入判定。
4. 只对第一个缺失/无效的环节开始重做；盘点结论（复用了什么、从哪一步续）必须写入 WORKER_RESULT 的 evidence。

## 三倍速录制转写（提速，录屏路必用）

复开候选视频后、`record-start` 之前，必须先调控制器 `set-playback-speed 3.0 <evidence_id>` 把详情页播放设为 3 倍速（长按调菜单→视觉定位倍速档→点，机型通吃）。
- **5分钟封顶（铁律）**：判意向只需视频**前 5 分钟**（获客视频核心信息都在开头），超过 5 分钟的视频只录前 5 分钟，不许全录。
- 录制时长按 `ceil(min(视频时长秒, 300) / 3) + 5` 秒给（3 倍速下 68 秒视频约 23 秒录完，多给 5 秒缓冲收尾；最长视频也只需约 105 秒）。控制器 record-start 默认 110 秒、硬顶 320 秒，超发会被钳制。
- 3 倍速音频经实测 Gemini ASR 转写清晰完整，正常判定；ASR 明显残缺时才降级回 1.0 倍速重录该条。
- 单手机、零登录依赖，不假设多设备并行。
