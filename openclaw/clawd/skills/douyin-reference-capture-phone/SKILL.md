---
name: douyin-reference-capture-phone
description: "Run an end-to-end Douyin reference-video job through OpenClaw → XIAN-M4-PHONE → ADB from either a research topic or a specific Douyin URL/share text: search or open the logged-in phone app, capture selected evidence, transcribe audio with Gemini 2.5 Flash-Lite, clean and analyze with Luna, and deliver records and documents to Feishu. Use for 对标视频、指定抖音链接转录、近期热点、爆款文案、音频转写、结构拆解、飞书交付. Never use for fake engagement, bulk scraping, CAPTCHA bypass, publishing, or unsolicited messaging."
---

# 抖音对标采集与文案交付

## 目标

把用户的一句研究指令或一个抖音链接独立执行为一条完整流水线：

`主题搜索或直链打开 → 飞书入队 → 获取视频或录制兜底 → 音频切片 → Gemini ASR → Luna 校对/分析 → 飞书文档交付`

这是一个用户可直接调用的 Skill，内部包含确定性脚本和模型判断。不要把步骤重新交给用户操作，也不要在每个候选处等待确认；默认完成一个小批次后统一汇报。涉及验证码、账号风控、权利不清或公开发布时才停下来请求人工处理。

## 多阶段编排（强制）

完整任务不能塞进一个 Agent 回合。Gateway 单轮约 630 秒会超时并触发 fresh fallback，可能重复启动 App。父 Agent 只负责编排，必须先初始化持久状态，然后通过 `sessions_spawn` 把阶段交给独立子任务。每一次 `sessions_spawn` 都必须显式传 `model: "gpt-5.6-luna"`、`thinking: "low"`、`runTimeoutSeconds: 480`，并让 `task` 或 `label` 带上 job_id 和阶段名；不得省略 `model` 后继承系统默认模型，也不得使用 Sol。父 Agent 等待自动 completion event；无事件时调用 `sessions_yield`，不要轮询。

```bash
/usr/local/bin/node /root/clawd-media/skills/douyin-reference-capture-phone/scripts/job-state.mjs init \
  --job-dir <gateway-job-dir> --job-id <job_id> --topic <topic>
```

阶段固定为：

1. `discovery`：识别输入模式；主题模式在手机搜索并选 1–3 条，直链模式解析、打开并核对指定视频；写 `normalized-input.json`、`candidate.json` 和飞书 discovered/shortlisted 记录；
2. `acquisition`：只处理 candidate.json 中入选项，在 Mac 获取或录制并用 ffprobe 验证，写 source evidence；原视频留在 Mac，禁止回传 Gateway；
3. `transcription`：切片、Gemini、manifest、merge，写原始稿和清洗稿；
4. `delivery`：Luna 校对分析、build-delivery、飞书 create→write→read、记录 delivered。

子任务开始和结束都用 `job-state.mjs set` 写状态。后续调用先执行 `show`，只恢复第一个非 completed 阶段。任何 fresh fallback 也必须先读 state：completed 阶段禁止重跑；`acquisition` 已存在 PID/有效源文件时禁止重复录制；已有相同 `job_id + 来源链接` 的飞书记录禁止重复创建。

任何会操作手机的 `discovery` 或 `acquisition` 子任务，开始前必须取得全局手机锁，结束（含 blocked/failed）时释放。拿不到锁就退出并保留 pending，不能与另一会话抢手机：

```bash
/usr/local/bin/node /root/clawd-media/skills/douyin-reference-capture-phone/scripts/phone-lock.mjs acquire --job-id <job_id> --stage <stage>
/usr/local/bin/node /root/clawd-media/skills/douyin-reference-capture-phone/scripts/phone-lock.mjs release --job-id <job_id>
```

```bash
/usr/local/bin/node /root/clawd-media/skills/douyin-reference-capture-phone/scripts/job-state.mjs set \
  --job-dir <gateway-job-dir> --stage discovery --status running
```

## 固定运行环境

- 手机控制节点：`XIAN-M4-PHONE`
- 工作手机绑定：读取 `/root/clawd-media/config/douyin-phone.json`；当前生产设备为 USB `ANGYVB4402004137`（`MAA_AN00`）
- ADB：`/opt/homebrew/bin/adb`
- 手机工件目录：`/private/tmp/openclaw-phone/<job_id>/`
- Gateway Skill：`/root/clawd-media/skills/douyin-reference-capture-phone/`
- ASR：`gemini-2.5-flash-lite-official`，通过 Gateway 上的 ToAPIs 兼容接口调用
- ASR 密钥：只从 `TOAPIS_API_KEY` 或 `/root/.openclaw/credentials/toapis-api-key` 读取，绝不打印或写入工件
- 手机操作、阶段编排、校对、结构分析和原创改写：`gpt-5.6-luna`；所有阶段子任务均在 `sessions_spawn` 中显式指定，禁止默认回落到 Sol
- 队列与交付：飞书多维表格 + 飞书文档；字段约定见 `references/feishu-queue.md`

所有手机命令都走 OpenClaw 的 `node_exec`，目标 node 为 `XIAN-M4-PHONE`。**每次 node_exec 只执行一个绝对路径命令**。不要拼接命令，不要使用 shell 循环、变量、管道、`command -v` 或裸 `adb`；节点审批按可执行文件匹配。二进制发现使用 `nodes` 的 `system.which`。

截图必须通过 `file_fetch` 回传并由视觉模型检查。`uiautomator dump` 只是可选文本辅助；它报 idle-state 错误时，继续使用截图视觉闭环，不能声称 Agent 失明。

## 默认任务合同

### 两个输入入口

- **主题模式**：用户给关键词、研究目标或对标任务；手机搜索、筛选后进入共用流水线。
- **直链模式**：用户消息中含 `douyin.com`、`v.douyin.com`、`iesdouyin.com` 的视频链接或抖音分享文本；只处理该视频，不再搜索相似候选。先运行：

```bash
/usr/local/bin/node /root/clawd-media/skills/douyin-reference-capture-phone/scripts/normalize-input.mjs \
  --input <用户原始消息> --output <job-dir>/normalized-input.json
```

直链的打开、核对和降级规则见 `references/direct-link.md`。Eval 仅在 Skill、模型、API 或设备链路变化后手动执行，不属于每个生产任务；见 `references/eval.md`。

用户未指定时采用：

- 关键词：从用户主题提炼 3–5 组；
- 时效：近 30 天，优先近 7 天；
- 候选：最多 20 条；
- 深加工：评分最高的 3 条；
- 评分：主题相关 35%、开头钩子 25%、可见互动 20%、新鲜度 10%、可迁移结构 10%；
- 输出：候选表、逐字稿、清洗稿、结构拆解、原创改写、风险提示和可试听口播稿。

每发现一个合格候选就立即写入飞书队列，不要等全部搜索完成才批量保存。若飞书暂时失败，先把同样字段保存到 job manifest，恢复后补写。

## 独立执行流程

### 1. 预检和建任务

1. 生成 `job_id`，格式 `dyref-YYYYMMDD-HHMMSS`。
2. 先运行 `normalize-input.mjs`。若 `mode=direct_url`，保存原始链接、解析后链接、视频 ID 和 App URI；若 `mode=topic`，保存主题文本。
3. 读取 `/root/clawd-media/config/douyin-phone.json`，再单独执行 `/opt/homebrew/bin/adb devices -l`。只使用配置中的 `adb_serial`，并核对 `expected_model`。多个 ADB 端点可能是同一手机的 USB/网络镜像，不能选择列表第一台，也不能自动改用另一台。绑定设备离线时报告阻塞。
4. 单独截图、拉回并视觉确认是抖音 App。若是登录、验证码、风控或账号切换页，停止。
5. 创建或读取飞书队列；主题模式状态设为 `searching`，直链模式设为 `opening`。

### 2. 手机搜索和候选入队

直链模式不执行搜索。按 `references/direct-link.md` 用绑定手机打开 `app_uri` 或 `resolved_url`，通过截图核对页面确为视频详情，并至少核对视频 ID、标题、作者三项中的两项。核对失败时不得进入 acquisition。主题模式继续执行下述搜索流程。

使用“截图 → 视觉定位 → 单次 tap/type/swipe → 新截图确认”的循环完成搜索。每次状态变化后重新观察，不复用过期坐标。单个 discovery 子任务最多 8 轮截图；优先用已验证的抖音搜索 deep link 直接进入关键词结果，超出预算则保存当前画面和 `blocked` 原因，等待下一阶段续跑，不能靠 Gateway fallback 从头重启。

候选至少记录：`job_id`、关键词、标题/可见文案、作者、分享链接或分享文本、发布时间、时长、可见互动、评分、入选理由、手机设备、截图证据、状态和错误。

只做研究动作。不得点赞、关注、评论、私信、公开分享、发布、改账号设置或绕过平台限制。

### 3. 获取选中视频

按以下顺序尝试，成功即停止，不反复消耗平台：

1. 使用用户已提供的本地文件；
2. 使用 App 的合法保存/分享能力获得文件或链接；
3. 把分享链接交给现有 Content Clipper/下载器（若环境中已配置）；
4. 在当前登录会话中提取可访问的媒体请求（只处理本次入选项目）；
5. 对选中视频使用 scrcpy 录制手机输出音频与画面作为兜底。

“作者关闭下载”只表示 App 不提供保存按钮，不代表可以绕过访问控制。不得破解 DRM、验证码、付费墙或权限控制。链接解析失败不影响工作流：立即切换到 scrcpy 录制兜底。

录制必须作为后台任务启动，稍后轮询日志和文件，不能因一次 node 超时而重复启动。成品须用 `/opt/homebrew/bin/ffprobe` 验证：时长非零，且同时存在音频流与视频流。

原始视频和视频分片必须留在 `XIAN-M4-PHONE` 的 Mac 文件系统。禁止用 `file_fetch` 把 MP4/MOV 或其他原始视频传回 Gateway，也禁止为了绕过传输大小限制而切视频再传。Gateway 没有 ffmpeg，且约 8–15 MB 的媒体传输可能触发 WebSocket 1006。需要送入 ASR 时，在 Mac 上直接从原视频提取 16 kHz 单声道 WAV 小片段，只回传 WAV、JSON、XML 和截图；单个回传文件以 2 MB 以下为目标。

### 4. 长度分档与音频切片

视频长度只决定“采集策略和分析深度”，ASR 一律使用短切片，避免长音频尾部重复：

| 视频长度 | 采集/分析方式 | ASR 切片 |
|---|---|---|
| 0–3 分钟 | 完整采集、完整拆解 | 30 秒，1 秒重叠 |
| 3–10 分钟 | 完整采集、按章节拆解 | 30 秒，1 秒重叠 |
| 10–20 分钟 | 后台完整采集，分章节处理 | 30–45 秒，1 秒重叠 |
| 20–60 分钟 | 可恢复后台任务，先索引后精析 | 30–45 秒，1 秒重叠 |
| 1–3 小时 | 先全量音频索引，仅精析高价值章节 | 30–45 秒，1 秒重叠 |
| 3 小时以上 | 异步 manifest；按章节检查点恢复 | 30–45 秒，1 秒重叠 |

在 Mac 上用 `/opt/homebrew/bin/ffmpeg` 从 Mac 本地原视频提取 16 kHz、单声道 WAV，并按 30 秒切片。不要在 Gateway 上调用 ffmpeg、ffprobe 或拼接视频。每个 segment 记录 `segment_id`、`source_start`、`source_end`、`status`、`attempt_count`、`local_path`、`gateway_path`。只重试失败片段。Gateway 没有 Python；不要用 Python heredoc 或 node-scoped `file_write` 创建 Gateway manifest，使用随 Skill 部署的 Node 脚本：

```bash
/usr/local/bin/node /root/clawd-media/skills/douyin-reference-capture-phone/scripts/manifest.mjs init \
  --manifest <job-dir>/segments.json --job-id <job_id>

/usr/local/bin/node /root/clawd-media/skills/douyin-reference-capture-phone/scripts/manifest.mjs upsert \
  --manifest <job-dir>/segments.json --segment-id <segment_id> \
  --source-start <seconds> --source-end <seconds> --status transcribed \
  --transcript-path <path> --result-path <path>
```

### 5. Gemini 转写

逐个用 `file_fetch` 把切片传回 Gateway，然后在 Gateway 执行：

```bash
/usr/local/bin/node /root/clawd-media/skills/douyin-reference-capture-phone/scripts/transcribe-gemini.mjs \
  --input <gateway-wav-path> \
  --output-dir <gateway-segment-output-dir> \
  --segment-id <segment_id> \
  --source-start <seconds>
```

脚本会输出 `transcript.txt`、`result.json` 和去密后的 `raw-response.json`。瞬时错误最多重试 3 次；认证、额度或模型路由错误直接记录并停止。禁止把密钥写入命令行。

全部片段完成后执行：

```bash
/usr/local/bin/node /root/clawd-media/skills/douyin-reference-capture-phone/scripts/merge-transcripts.mjs \
  --manifest <segments.json> \
  --output-dir <merged-output-dir>
```

保留 `raw-transcript.txt` 和 `clean-transcript.txt` 两份。清洗稿可以删除切片重叠和明显的无声尾部复读，但不得凭空补字；疑词标 `[听不清]`。

若 Gemini 不可用，降级到 Mac 本地 Whisper，并在交付物标记 `asr_provider=local-whisper-fallback`；不能把降级结果伪装成 Gemini。

### 6. Luna 校对和分析

Luna 只读取清洗稿、原始稿、元数据与关键截图，完成：

1. 轻校对：同音词、标点、分段、专名；
2. 差异清单：所有实质性改字需列出“原文 → 校订 → 依据”；
3. 结构卡：前三秒钩子、痛点、承诺、论据、节奏、CTA；
4. 可迁移模板；
5. 围绕用户主题的原创改写；
6. 事实与合规风险。

不得把原视频逐字稿直接当成可发布原创文案。无音频、字幕或上下文依据时不改实词。

### 7. 飞书交付与收尾

用 `scripts/build-delivery.mjs` 生成交付 Markdown。飞书文档必须分三步完成：先 `feishu_doc action=create` 取得 `doc_token`，再 `action=write` 写入 delivery.md 的完整内容，最后 `action=read` 验证正文非空。`create` 的 `content` 参数不会写正文，禁止把“拿到文档 URL”当成交付成功。验证后再把文档链接写回队列。状态依次为：

`discovered → shortlisted → acquiring → captured → transcribing → proofreading → delivered`

失败状态为 `blocked` 或 `failed`，必须填写 `last_error` 和 `next_action`。最终回复只在以下验收全部通过后说“完成”：

- 手机截图证据存在；
- 源文件或兜底录屏经 ffprobe 验证；
- 所有 ASR 片段状态明确；
- 原始稿与清洗稿都存在；
- Luna 校对/分析存在；
- 飞书记录和交付文档可访问。
- 飞书文档回读包含“清洗后的逐字稿”和“结构拆解与原创改写”，不是只有标题。

## 失败恢复

- 节点审批拒绝：检查是否把多条命令拼在一起，改为一次一个绝对路径命令。
- ADB offline/unauthorized：报告设备状态，不重复重置授权。
- 页面变化：从最新截图恢复，不盲点旧坐标。
- `uiautomator` idle-state：继续截图视觉闭环。
- 下载/解析失败：转 scrcpy，不循环尝试同一解析器。
- 长任务 node 超时：检查既有 PID、日志和产物，不启动重复任务。
- 录屏无音频：确认 scrcpy 使用 `--audio-source=output`；不要用无内录音频的 Android `screenrecord` 冒充成功。
- ASR 尾部重复：保留 raw，清洗稿去重并设 `needs_review=true`。
- 飞书暂不可用：保留本地 manifest 和 delivery.md，恢复后补写。
- Gateway 文件写入失败：使用 Gateway `bash` 调用本 Skill 的 Node 脚本；`file_write` 在 media agent 中可能默认路由到 Mac node。
- 手机锁被占用：不操作手机；等待持有者完成或租约超过 10 分钟后再恢复。禁止并发控制同一设备。
- CAPTCHA、风控、登录挑战、DRM、付费墙：停止并请求人工处理。

## 安全边界

本 Skill 可自动搜索、采集本次入选证据、生成内部研究稿并写入飞书。它不能自动点赞、关注、评论、私信、发布、修改账号或规避访问控制。默认处理小批次，禁止无边界抓取整个信息流。
