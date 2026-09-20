---
name: douyin-reference-capture-phone
description: "Turn one Douyin URL or share text into a complete, evidence-backed ASR transcript and one verified Feishu document link through the tenant-bound phone. Use for 指定抖音链接转写、全文案采集、音频转写或 when another workflow needs a full-video transcript artifact. This Skill does not judge, proofread, analyze, rewrite, publish, or interact with users."
---

# 抖音链接全文案转写





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


## 编排契约

当由 `agentic-workflow-runtime` 调用时，本 Skill 是一个有界阶段的 Worker：不得召唤 Commander、
其他 Agent 或下一阶段，也不得发出 `WORKFLOW_TERMINAL`。结束前必须且只能输出一行
`WORKER_RESULT {json}`（`schema_version` 为 2，`status` 只填一个词（`completed` / `blocked` / `failed` 三选一），
`recommended_next_action` 只填一个词（`accept` / `retry` / `stop` / `request_approval` 四选一）），逐字回显 Commander 传入的
`run_id`、`attempt_id`、`execution_id`、`object_id`、`workflow_id`、`worker_agent_id`、
`lease_id`、`stage_id`、`stage_attempt`、`idempotency_key` 与 `task_request_hash`，
禁止从 `run_id` 推导任何身份。哈希缺失或不一致时不得执行。

飞书文档写入与工件落盘前，必须先用 Commander 传入的 `write_guard.command` 取得授权回执，
并把回执随工件一并回传到 `write_fences`；无回执的写入一律视为未发生。
`contract_test` 模式只验证 Skill 与信封可用：不碰手机、不调 ASR、不写飞书，
返回 `metrics={"external_interactions":0,"business_writes":0}`。

## 唯一合同

输入一个抖音链接或分享文本，输出一个完整 ASR 工件和一个已回读验证的飞书文档链接（**被 V4 qualification 阶段调用时例外：仅交付全文转写工件，不写飞书**——该阶段写权限仅 `artifact_write`，越权写会被 write-guard 拒绝）：

`链接归一化 → 原视频核对 → 全长获取/录制(3倍速) → 整段 ASR(通义) → 飞书文档`

本 Skill 不做 Luna 校对、内容分析、资格判定、结构拆解、原创改写或线索分类。需要判定时，下游 Skill 读取本 Skill 的全文工件和飞书链接后单独处理。

## 输入与输出

输入必须包含：

- `source_url` 或含 `douyin.com` / `v.douyin.com` / `iesdouyin.com` 的分享文本；
- 当由 Workflow 调用时，同时传入 `candidate_id`、预期标题/作者/视频 ID 中至少两项；
- 可信租户与设备上下文。

成功输出 `transcript-package.json`：

```json
{
  "source_url": "required",
  "resolved_url": "required",
  "video_id": "required",
  "duration_seconds": 0,
  "captured_seconds": 0,
  "coverage": "full",
  "asr_provider": "qwen-audio-3.0-asr-flash",
  "raw_transcript_path": "required",
  "merged_transcript_path": "required",
  "segment_manifest_path": "required",
  "feishu_doc_url": "required",
  "feishu_readback_verified": true
}
```

`coverage` 只有在实际录制/获取时长覆盖完整视频、所有音频分片状态明确时才能写 `full`。任何部分样本都不得冒充全文。

## 四阶段执行

1. `discovery`：归一化链接，打开原视频，用视频 ID、标题、作者中至少两项核对身份。
2. `acquisition`：优先使用 App 合法保存/分享能力；失败时使用**租户控制器的 `record-start` / `record-stop` 子命令**录制手机画面与音频（内部封装 scrcpy；**禁止直接调用 scrcpy**——控制器是节点唯一可执行入口）。必须覆盖整条视频。
3. `transcription`：用控制器 `record-extract-audio` 在节点上提取 16 kHz 单声道 WAV，**整段直发通义 qwen-audio-3.0-asr-flash，不分片、不降速**：`node ~/.local/asr-tools/transcribe-gemini.mjs --input <wav> --output-dir <dir> --speed 3 --api-key-file ~/.config/openclaw/dashscope-api-key`。2026-09-11 TTS ground truth 横评实测：3 倍速录制音频下 gemini-2.5-flash-lite 字级仅 70.7%、业务关键词 2/9，且会整段改写题材（把「人工智能训练师考证」听成「职场生存/数据报表」）；通义同一份音频 100%、9/9，6.3 分钟长稿 89.8% 且中文专名/数字/钩子零失误。**不要再分片**（126 秒音频单发即可，分片反而破坏时间戳连续性）；**不要降速**（通义下 3x 与 3x+降速 准确率相同，降速却慢 2.9 倍、按音频秒计费贵 3 倍）。`--speed 3` 告知录制倍速，返回的 `sentences[]` 时间戳即视频真实时刻。返回除 `transcript` 外还含 `words[]`（逐词毫秒）与 `sentences[]`（断句+时间），可直接用于钩子定位（如「评论区扣」出现在第几秒）与结构拆解。
4. `delivery`：只做机械去重叠和顺序合并，生成飞书文档，执行 create → write → read 回读验证，返回文档链接。

用 `scripts/job-state.mjs` 持久化四阶段。完成阶段不重跑；已有有效录制 PID 或经 ffprobe 验证的源文件时不得重复录制。

## 全长获取和 ASR

- 不因视频时长截断转写。长视频转为异步、可恢复任务，而不是只处理开头样本。
- 原视频和视频分片留在租户绑定 Mac；Gateway 只接收小型 WAV、JSON、XML 和截图。
- 每个 ASR 分片记录 `segment_id`、`source_start`、`source_end`、`status`、`attempt_count`、工件路径。只重试失败分片。
- `merge-transcripts.mjs` 只允许删除分片重叠和明显的无声尾部复读；不修改实词，不用模型润色。
- 通义不可用时可降级回 gemini（`--provider gemini`）或 Mac 本地 Whisper，必须如实标记 `asr_provider`。

## 飞书文档

每个输入链接交付一个文档。文档只包含：

- 标题、作者、来源链接、视频 ID、时长、采集时间、ASR 模型；
- 合并后的 ASR 全文；
- 折叠的原始分片转写，作为审计证据。

文档不包含 Luna 校对、内容评分、结构拆解、改写或合格结论。文档正文回读非空且包含“ASR 全文”后，才能回传 `feishu_readback_verified=true`。

## 运行与安全边界

- 通过 `douyin-phone-runtime` 解析可信的 `tenant_id → profile → Node → serial → model`，不使用默认公司或默认设备。
- 手机操作前获取全局锁，成功、失败或阻塞收尾时都释放。
- 每次 Node 调用只执行一个登记的绝对路径控制器命令，不调用裸 `adb`。
- 只允许打开、合法获取/录制和转写本次指定视频。禁止点赞、关注、评论、私信、发布、批量无边界抓取或规避访问控制。
- 验证码、风控、登录挑战、DRM、付费墙或身份核对失败时停止，不产生伪全文。

## 完成验收

同时满足才能汇报完成：

- 原视频身份已核对；
- 源文件经 ffprobe 验证同时存在音视频流；
- `captured_seconds` 覆盖 `duration_seconds`，或有可审计的容差说明；
- 所有 ASR 分片状态明确，原始稿和合并稿都存在；
- 飞书文档 create/write/read 完成，文档链接和回读证据已写入 `transcript-package.json`。

## ASR 转写 runbook（qualification 唯一转写路径，照抄执行，禁止自研）

1. 停止录制后提取音频：控制器 `record-extract-audio <recording_id>` → 节点 evidence 目录得到 16kHz 单声道 `<id>.16k.wav`。
2. 将 wav 取回 Gateway 本地（file 传输）。
3. 转写（脚本内置纯 JS 分片 20 秒/片 + 复读清洗，无需 ffmpeg，大音频自动处理）：
   `node "$HOME"/.local/asr-tools/transcribe-gemini.mjs --input /绝对路径/<id>.16k.wav --segment-id <候选ID> --api-key-file "$HOME"/.config/openclaw/dashscope-api-key`
   **路径必须是执行节点上的路径**（`exec` 跑在节点，不是网关）。不要把"本 skill 目录"解析成
   `/Users/administrator/openclaw-root/workspaces-root/clawd-*/skills/...`——那是网关侧路径，节点上不存在，会得到 `MODULE_NOT_FOUND`
   （0913 实证：judgment 阶段连续四次因此失败，而节点上 `~/.local/asr-tools/transcribe-gemini.mjs`、
   `~/.config/openclaw/dashscope-api-key`、`ffmpeg`、`node` 其实一应俱全）。
   - API key 自动读 `/Users/administrator/.openclaw/credentials/toapis-api-key`，无需任何配置。
   - 成功输出：stdout 单行 JSON（ok=true、chars、transcript_preview）；完整全文在同目录 `<候选ID>.transcript.txt` 与 `.transcript.json` 的 `transcript` 字段。
4. 失败时读 stdout JSON 的 error 后重试本条；禁止直发 toapis 原始 HTTP 请求、禁止 ffmpeg 切片、禁止改写本脚本。
