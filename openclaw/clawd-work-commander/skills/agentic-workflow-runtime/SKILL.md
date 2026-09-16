---
name: agentic-workflow-runtime
description: "Run manifest-driven multi-step workflows with either n8n as the deterministic workflow owner or Work Commander as the dynamic reasoning owner. Provides immutable attempts, isolated OpenClaw Agent nodes, evidence validation, lifecycle events, Feishu card projection, retries and resumable checkpoints. Use for OPC workflows with two or more dependent stages."
---

# Agentic Workflow Runtime v3

n8n always owns intake, run/attempt identity, event ingress, callback routing and card projection. For a manifest with `orchestrator.type=n8n`, n8n also owns stage order and terminal truth. For a legacy manifest with `commander`, Work Commander owns dynamic reasoning and terminal truth. Business Agents always own only one bounded stage. Feishu cards are projections, never workflow truth.

### WORKER_RESULT 必须同时耐久落盘（0912 新增）

Worker 在输出最后那一行 `WORKER_RESULT {json}` **之前**，必须先用**网关侧文件写工具**
把**完全相同**的 JSON 写到账本目录的确定路径：

```
/root/clawd-work-commander/state/workflow-runs/<run_id>__<attempt_id>.<stage_id>.<stage_attempt>.worker-result.json
```

理由：会话完成通道不保证把最后一条消息完整送到 Commander。0912 实证——worker 自己会话里
记录的 WORKER_RESULT 完整且能解析（2190 / 3580 字符），Commander 却连判两次
"truncated by completion transport"，退化成在目录里 grep，扫到的还是 `SKILL.md.bak-*` 备份文件，
两次 discovery 尝试白烧。**有一份确定路径的落盘，这一类失败就整类消失。**

这一次写入是协议回执，不是业务写：不需要 write-guard 回执，不计入 `business_writes`、
`artifact_writes` 或任何外部交互计数，也不得写到业务工件目录里。
用 `exec` 写这个文件是错的（exec 在执行节点，节点上没有这个路径）——见「执行体分工」。



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


## 执行体分工（exec 跑在节点，文件工具跑在网关——记死这条）

Worker 手里有两类工具，它们**在不同机器上**：

| 工具 | 实际执行位置 | 看得见的文件系统 |
|---|---|---|
| `exec` / `node_exec` | **执行节点**（如 XIAN-M4-PHONE，macOS） | 节点的 `/Users/<用户>/clawd-*` |
| 文件读写工具（read/write/edit）、`file_fetch` | **网关侧** | 网关的 `/root/clawd-*` |

由此产生三条硬规则：

1. **绝不用 `exec` 去读自己的 skill 文件。** 任务里给出的 skill 路径是网关侧的
   `/root/clawd-*/skills/...`，节点上不存在。要看 skill 就用文件读工具。
   0912 实证：某次 discovery worker 用 `sed` 读 `/root/.../social-video-discovery/SKILL.md`
   失败后改用 `rg`（节点没装）、再 `find /` 满盘搜，60 秒超时，整次尝试作废且回传被截断。
2. **绝不把网关侧路径交给 `exec`，也绝不把节点侧临时路径当成网关可读的产物。**
   工件要落网关就用文件写工具；要在节点上算哈希/列归档就用 `exec` 对节点路径算。
3. **节点是裸环境**：没有 `rg`，`pwd` 可能为空，`PATH` 不继承网关配置。
   只用 POSIX 基础命令（`grep`/`sed`/`find` 限定目录）并始终写绝对路径。

搞不清某个路径属于哪一侧时，**不要用 `find /` 去猜**——满盘扫描必然超时，
把本该用来干活的那次尝试烧掉。直接按上表判断，或请求 Commander 澄清。


## n8n-owned fixed workflows

Use this mode when stage order is declared in the manifest.

1. n8n validates and freezes `task_request`, calculates `task_request_hash`, creates `run_id`, `attempt_id`, `execution_id` and a unique stage idempotency key.
2. n8n calls the tenant Worker directly through `/v1/responses` with explicit `x-openclaw-agent-id`; each stage uses an isolated Session key.
3. The stage envelope contains `orchestrator=n8n`, immutable execution identity, `stage_id`, `stage_attempt`, `skill`, frozen task request and hash, accepted prior artifacts, allowed actions, idempotency key and execution mode.
4. The Worker must not call `sessions_spawn`, Work Commander, another Agent, the n8n run webhook, or the next stage. It returns exactly one `N8N_NODE_RESULT` or compatible `WORKER_RESULT`.
5. n8n validates identity, hash, stage and status before projecting `stage_accepted` and starting the next node. Retry creates a new `stage_attempt`; a terminal attempt never resumes.
6. Run Cleanup from every success, failure, timeout and cancellation branch. Emit terminal only after cleanup verification.
7. In `contract_test`, Workers only verify that the requested Skill and envelope are usable; phone, business reads/writes and external interactions must all remain zero.

## n8n-driven Commander stages (commander_supervision)

Use this mode when the manifest's `orchestrator` object contains `commander_supervision.enabled=true`. n8n still owns intake, run/attempt identity, **stage order**, stage-level retry counting and card projection invocation; Work Commander supervises every single stage: it spawns the bounded tenant Worker, validates evidence, decides, and reports one verdict per request. The Commander never chooses the next stage; n8n never makes a business acceptance decision. The Commander session is `agent:work-commander:workflow-<run_id>-attempt-<attempt_id>`, one per attempt.

Three request kinds arrive as single messages. Each expects **exactly one reply line**: `COMMANDER_STAGE_RESULT {json}` — one JSON object echoing `run_id`, `attempt_id`, `execution_id`, `stage_id`, `stage_attempt`, `idempotency_key`, `task_request_hash`, `nonce`, plus `verdict`, `summary`, `metrics`, `artifact_refs`, `warnings` (and `terminal_status` for finalize). The verdict vocabulary is closed: `accepted | retry | blocked | stopped`. Any other word, a missing field, or extra terminal markers will be rejected by the n8n schema gate and will block the run — never improvise fields.

This line must be the assistant's sole final message for the request. Persisting it in the ledger or printing it inside tool output is not a reply. After the ledger decision is durable, read back the exact recorded line and return it verbatim. `NO_REPLY`, empty output, prose, and a final tool call are forbidden for all three request kinds.

1. `WORKFLOW_RUN_INIT {json}` — full frozen identity, `task_request`, `task_description`, `control_token`, declared stage list. Validate identity/manifest/tenant binding exactly as in Start (steps 1–6), run the task-contract validator, calculate `task_request_hash`, initialize the v2 ledger, persist the validated `task_request` JSON into the run state directory beside the ledger (later stage requests carry only the hash; reload it from there after any session loss), relay exactly one `started` event. Do **not** spawn any worker. Reply with `request_kind=init`, `verdict=accepted`, and the calculated `task_request_hash` (n8n stores it and stamps it into every later envelope). The renderer output is the canonical `task_description`: if the request-supplied description differs, adopt the renderer output and proceed — a prose mismatch is not a rejection reason; the contract is the frozen `task_request` and its hash.
2. `WORKFLOW_STAGE_REQUEST {json}` — one stage envelope with `stage_def`, `stage_attempt`, `idempotency_key=<execution_id>:<stage_id>:<stage_attempt>`, `task_request_hash` and trimmed `accepted_prior_results` — it does NOT carry the full task_request; load the persisted copy from the run state directory and verify its hash matches before spawning.
   - Serialize that verified frozen `task_request` JSON directly inside the bounded Worker `task` string. Include the envelope's exact `object_id`, `workflow_id` and `idempotency_key` with every other immutable identity field; the Worker must echo the supplied trusted values and must never derive them from `run_id`. Never pass `attachments` to `sessions_spawn` and never tell the Worker that the task request is attached; spawn attachments are disabled in this Gateway and are not part of the V4 calling convention.
   - **Manager feedback on retry:** when `stage_attempt > 1`, load the immediately preceding attempt's recorded `COMMANDER_STAGE_RESULT`, decision event and validated Worker evidence from the durable ledger. Require that prior decision to be the same execution and stage with verdict `retry`. Build and serialize a literal `manager_feedback` JSON object into the new Worker task with `source_stage_attempt`, `source_idempotency_key`, prior summary, warnings, failed acceptance criteria, reusable verified artifacts and an explicit correction checklist. Do not rely on transcript memory or `accepted_prior_results` for rejected-attempt feedback. The feedback may only correct execution within the unchanged frozen task request; it may not broaden or rewrite the task. Require `WORKER_RESULT.manager_feedback_ack` to echo the source attempt and contain `resolved[]`, `unresolved[]` and fresh evidence for each resolution. Missing retry lineage is invalid; do not spawn a context-free retry.
   - **Idempotent replay:** if the ledger already records a decision for this exact `idempotency_key`, re-emit that recorded result verbatim. Never spawn again, never relay duplicate lifecycle events. This makes duplicate delivery from n8n retries safe. If the request arrives while the same stage attempt is already in progress in this session (stage_started relayed, worker spawned, no decision recorded yet), do NOT spawn again and do NOT answer NO_REPLY: continue supervising the existing worker and emit the COMMANDER_STAGE_RESULT once the decision is recorded.
   - Otherwise: relay `stage_started`, then run "Supervise a stage" unchanged (spawn exactly once, validate `WORKER_RESULT`, evidence and write fences). On retry attempts, acceptance additionally requires a matching `manager_feedback_ack`, no unresolved correction, and fresh evidence for every claimed resolution. Decide and map to the reply verdict: accept→`accepted`, retry→`retry`, block→`blocked`, stop→`stopped`. `steer` stays internal to the current spawn and never surfaces as a verdict.
   - **Retry ownership:** in this mode do not spawn a second worker inside the same stage attempt. Surface `retry` to n8n; the canvas owns the retry counter and will send a new `WORKFLOW_STAGE_REQUEST` with `stage_attempt+1`. Record every decision under its idempotency key before replying.
   - Relay the decision event before replying. Late results from fenced prior sessions are rejected exactly as in the Commander-owned mode.
3. `WORKFLOW_RUN_FINALIZE {json}` — `desired_status` `completed` or `abort` (abort carries `halt_context` {verdict, stage_id, summary}). For `completed`: verify every required stage is accepted, run Finish (cleanup verification, terminal relay, one `WORKFLOW_TERMINAL`). For `abort`: fence any orphan worker of the halted stage, run abort cleanup — release every platform lock via the adapter and verify release — then write the terminal matching `halt_context.verdict`: blocked stays `blocked` (resumable by a new attempt), stopped stays `stopped`, anything else becomes `failed`. If no ledger exists because init never completed, reply `verdict=stopped`, `terminal_status=failed`, noting nothing to clean. A finalize on an already-terminal attempt re-emits the recorded terminal result idempotently. Reply with `terminal_status` in every case.

Safety rules of the Commander-owned mode apply unchanged: never operate tenant devices or business APIs yourself, never accept a result whose `task_request_hash` mismatches, never revive a terminal attempt, and reject any envelope whose identity does not match the session's run and attempt.

Keep the Commander-specific protocol below only for manifests that still declare `commander`.

Read [protocol.md](references/protocol.md) before every run. Validate the selected package manifest with `scripts/validate-manifest.mjs`.

## Start

1. Require `run_id`, `attempt_id`, `execution_id`, `object_id`, `workflow_id`, `workflow_skill`, `worker_agent_id`, `tenant_context`, `card_target`, `objective`, `mode` and a 32+ character `control_token` from trusted n8n ingress. If the selected manifest declares `task_contract`, also require the complete normalized `task_request`; run its validator and renderer before creating the ledger. Never echo or expose the token in cards, lifecycle events, terminal output or status responses.
2. Verify session key is `agent:work-commander:workflow-<run_id>-attempt-<attempt_id>` and that `execution_id=<run_id>:<attempt_id>`.
3. Reject `main` as a tenant worker and reject any tenant/worker mismatch. A reusable manifest uses `worker_agent_binding=trusted_tenant_context.agent_id`; resolve it only from n8n's registered tenant route and require `worker_agent_id=tenant_context.agent_id`. A dedicated manifest may instead contain one literal `worker_agent_id`.
4. Load the Workflow Package from this workspace and validate its manifest. Do not ask the worker to supply or reinterpret the manifest, and never replace a trusted tenant binding with a default company or device.
5. For a manifest with `task_contract`, calculate the validator-returned SHA-256, require the rendered human description to be present on the Workflow card, and freeze both under the Intake object. A resume may reuse the same hash only; any task change creates a new run, not a new attempt.
6. Initialize the ledger:

```text
node skills/agentic-workflow-runtime/scripts/workflow-state.mjs init --run-id <run> --attempt-id <attempt> --object-id <object> --workflow-id <workflow> --worker-agent-id <agent> --total-steps <count> --audience-key <key> --chat-id <chat> --visibility <visibility> --control-token <token> [--task-request-hash <sha256>] [--resumes-execution-id <id>]
```

7. Relay `started` using the state script. Do not spawn before `relayed=true`.
8. Keep the returned `lease_id` and resolve the canonical absolute path of `scripts/workflow-write-guard.mjs`. Confirm that path is executable. These two values are mandatory inputs to every worker task; they are never invented by a business Agent.
9. Pre-issue the fence tokens yourself on this host; never send a guard script path to the Worker. The Worker may execute on a different machine (e.g. `XIAN-M4-PHONE`), where neither the guard script nor the Commander ledger exists — run `social-keyword-leadgen-20260907222632-jino-final6` was blocked four times by exactly that assumption (`guard path was unavailable in the worker environment`) after Discovery had already found a valid candidate. For every write intent that is legal in this stage, invoke the executable guard script yourself (its `#!/usr/bin/env node` shebang resolves the installed Node runtime; never hard-code a Node path) and collect each returned receipt into a `write_guard.tokens` object keyed by intent. Authority is unchanged: each receipt is still bound to the exact active stage event, so a receipt issued for a superseded attempt is rejected at acceptance time.

## Relay an event

```text
node skills/agentic-workflow-runtime/scripts/workflow-state.mjs event --run-id <run> --attempt-id <attempt> --event <event> --status <status> --stage-id <stage> --stage-attempt <n> --current-step <n> --summary <text> --next-action <text> [--evidence-json <json>]
```

The script allocates `event_seq`, updates the atomic ledger and POSTs the complete event to n8n. Retry once for a transport failure. If it still fails, preserve the ledger and block before another mutating stage.

## Supervise a stage

1. Build a self-contained worker `task` string from the manifest, frozen task request, tenant context, accepted prior artifacts and safety constraints. Serialize the complete frozen `task_request` JSON inline in that string. Include the exact immutable `run_id`, `attempt_id`, `execution_id`, `object_id`, `workflow_id`, `worker_agent_id`, `stage_id`, `stage_attempt`, `idempotency_key`, `task_request_hash` when present, the ledger `lease_id`, and the pre-issued `write_guard.tokens` map (intent -> receipt) produced in Step 9. For `stage_attempt > 1`, also include the durable same-stage `manager_feedback` object defined above and require its acknowledgement. Require the Worker to echo those supplied values without inference in exactly one literal `WORKER_RESULT {json}` line, **and require in the task text itself that the Worker also writes that identical JSON, using a gateway-side file write tool (never `exec`), to `<the Worker own workspace>/state/workflow-runs/<run_id>__<attempt_id>.<stage_id>.<stage_attempt>.worker-result.json`** — state the exact absolute path in the task, inside the Worker own workspace (a Worker cannot write into the Commander workspace). **Say explicitly in the task that this receipt is best-effort and must never change the Worker `status`**: 0913 实证，一次四证全过的 preflight 因为写不进回执而被 Worker 自己改判 blocked——把备份写成闸门，等于亲手废掉成功的阶段。这份落盘只是会话回传拿不到时的兜底（`sessions_history` 曾返回 forbidden），不需要 write-guard、不计入 business/artifact 计数。 Never use `attachments` for any part of this payload.
2. Relay `stage_started`.
3. Re-read the ledger and verify that its latest transition is the exact relayed `stage_started`; use that `event_id` as the expected write-fence event. Never spawn from a pending relay or a terminal ledger.
4. Call `sessions_spawn` exactly once with explicit `agentId=<worker_agent_id>`, `taskName=v4-<nonce>-<stage_id>-<stage_attempt>`, `mode=run`, `cleanup=keep`, and the fully self-contained inline `task`. Before spawning, require `taskName` to be 1–64 characters and match `[a-z][a-z0-9_-]*`. Do not pass `attachments`, do not fork the Commander transcript and do not pass `runTimeoutSeconds`.
5. Parse the actual spawn result. Yield only when it contains `status=accepted`, non-empty `runId` and `childSessionKey`.
### 禁止凭空判定"回传被截断"（0912 硬规则）

判定 Worker 回传"被通道截断/不完整"之前，必须按顺序做完这三步，并在结论里写明做过：

1. **先解析收到的最后一条消息**：能从 `WORKER_RESULT ` 之后解析出 JSON，且必填字段齐全，
   那它**就不是截断**——无论它多短、`status` 是什么。
2. 只有解析失败或字段确实缺失时，才去找那份尽力而为的落盘，按顺序试两处：
   ①本工作区 `state/workflow-runs/<run_id>__<attempt_id>.<stage_id>.<stage_attempt>.worker-result.json`；
   ②**被派 Worker 自己工作区**的同名路径 `/root/clawd-<worker 工作区>/state/workflow-runs/<同一文件名>`
   ——Worker 没有写 Commander 工作区的权限，它的回执只会落在自己那边。
3. 两者都拿不到，才可以说"回传不完整"，并且必须写明已按路径找过。


### 拿不到回传时的终极兜底：直接读 Worker 会话记录文件（0913 新增）

前两条路（解析完成消息、读协议回执文件）都拿不到时，**还有第三条，而且它一定可用**——
Worker 的完整会话记录就在网关磁盘上，你有网关侧文件读取能力：

```
/root/.openclaw/agents/<worker_agent_id>/agent/codex-home/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl
```

**0913 深夜起推理已下放 MMV**：会话文件改落在 MMV 上,网关本地那条路径会扑空。用 exec(网关本地 shell)跨机读:

```
ssh -i /root/.openclaw/mmv_key -o BatchMode=yes administrator@100.71.151.105 \
  "ls -t /Users/administrator/.codex-gwremote/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl | head -5"
```

取最近修改的几个文件逐个用同款 ssh cat 读,找 payload.type==task_complete 的 last_agent_message,
用 run_id/idempotency_key 核对是不是本阶段那条。**先试 MMV 路径,再试网关本地路径**(两处都可能有历史)。
```

取最近修改的那个 rollout 文件，找 `payload.type == "task_complete"` 那一行，
它的 `last_agent_message` 就是 Worker 交付的那一整行 `WORKER_RESULT {json}`，逐字完整。
用 `run_id` / `idempotency_key` 核对是不是本阶段本次尝试的那一条，再照常验收。

**为什么必须有这条**：0912-0913 实测，`sessions_history` 先是返回
`{"status":"forbidden"}`（跨 agent 可见性受限），修了权限之后又返回
`Gateway is draining; new tasks are not accepted`；同期网关每分钟刷 8 次
`[agents/subagent-registry] requester settle wake failed`——**完成回传这条通道本身不可靠**。
而同一时刻 Worker 的 rollout 文件里，WORKER_RESULT 完整且可解析（实测 1603/1990/2681/3580 字符，
字段 20/20 齐全，其中不止一次是 `recommended_next_action=accept` 的成功结果）。
只要还没读过这个文件，就不许下"回传被截断"的结论。


### 现场知识库：开工必读、收工必写（0913 新增，这是你的跨尝试记忆）

你每一次 stage attempt 都是一个新会话，只带得到上一次的 `manager_feedback`——
这意味着你**天然记不住前几次学到的东西**，会在同一个坑上反复跌倒四次然后 blocked。
所以有一份持久文件替你记：

```
/root/clawd-work-commander/state/FINDINGS.md
```

- **每次开工（收到 stage 请求后、派 Worker 之前）先完整读一遍。**
  里面是已经用真机证据钉死的事实与已被证伪的路，照着做可以少走一整轮。
  凡与它冲突的猜测，以它为准；要推翻它必须有新的现场证据。
- **每次 stage 结束，若学到任何"下次能少走一步"的事实，追加一条**：
  日期 ｜ 现象 ｜ 确定性判据 ｜ 处置。已有的别重复写；发现旧条目被推翻就改写它并注明推翻依据。
- 把有用的结论也写进给 Worker 的任务正文——Worker 同样是每次新会话，同样没有记忆。

这份文件不是工件、不需要 write-guard、不计入任何 metrics。它是你唯一的长期记忆，别让它荒着。

**Worker 返回 `status=blocked` 或 `failed` 不是传输故障，是它在如实汇报现场。**
**协议回执文件缺失或为空，回执缺失不构成拒绝理由**，只记一条 warning 后照常按内容验收。
必须原样引用它的 `status` 与 `summary` 作为本次 verdict 的依据，不得改写成基础设施故障。

0912 实证：worker 交回的结果 20 个必填字段全在、JSON 合法、summary 明确写着
"抖音停留在搜索结果页、主页导航点击超时、按安全门禁停止"，
Commander 连续四次判成 `truncated by completion transport`，
把可直接行动的现场报告变成了查不到的幽灵问题，整轮尝试全部白烧。
禁止用目录 grep 去"找回"结果——它会扫到 `SKILL.md.bak-*` 之类备份并得出错误结论。

6. Validate the final `WORKER_RESULT`, artifacts and evidence against every acceptance and safety criterion. Before any semantic acceptance, require numeric `schema_version=2`, `status` in `completed | blocked | failed`, and `recommended_next_action` in `accept | retry | stop | request_approval`; Manager verdict words (`accepted | retry | blocked | stopped`) are not valid Worker statuses, and `proceed` is not a valid next action. Reject and return a retry verdict for any Worker-protocol mismatch even when identity and zero-action evidence are otherwise valid. Require `run_id`, `attempt_id`, `execution_id`, `object_id`, `workflow_id`, `tenant_id`, `worker_agent_id`, `lease_id`, `stage_id`, `stage_attempt`, `idempotency_key`, `commander_event_id`, and `task_request_hash` to exactly equal the trusted stage envelope. When the ledger has `task_request_hash`, every stage result and artifact must carry the same hash; reject missing or mismatched values. Every artifact or destination mutation must include a guard receipt whose `commander_event_id` equals the expected stage event and whose `fence_token` matches the execution, lease, worker, stage, attempt and intent. A claimed write without a valid receipt is rejected. For retry attempts, reject acceptance unless `manager_feedback_ack` matches the prior durable retry decision, has an empty `unresolved[]`, and every `resolved[]` item is supported by fresh current-attempt evidence.
   - **证据型阶段（preflight / cleanup）的验收边界（0912 修正）：**这两个阶段的合同是"验证与释放"，不产出业务工件。验收只看 evidence（preflight：设备/账号/通话/锁四证；cleanup：close_app 前台验证 + lock_release 回读 free + 桌面截图）与 protocol.md 规定的 metrics；其 `artifacts` 必须为 `[]`（与 douyin-phone-runtime 的适配器合同一致）。**不得把 guarded artifact、gateway readback 或哈希回读作为 preflight/cleanup 的验收条件**——那是业务工件阶段（discovery/qualification/collection/scoring/delivery/outreach）的模式。0911 实证：run `...161428` 七格全绿、物理清理全部完成并验证，唯 cleanup 因被索要协议中不存在的"guarded cleanup JSON artifact"而 blocked——把工件模式过度泛化到证据型阶段是发明验收标准，不是执行合同。
7. Choose `accept`, `steer`, `retry`, `block`, or `stop`; relay the choice before continuing. Once `retrying`, a later stage starts, or terminal state is recorded, the prior Session's next guard call must fail and its late result must never be accepted.

Retry always creates a fresh worker stage attempt. Never retry safety stops, tenant/device/account mismatch, verification challenges, external approvals, or unknown non-idempotent outcomes.

## Write fencing

The guard is checked immediately before each artifact or business-system mutation:

```text
<absolute_guard_script> authorize --run-id <run> --attempt-id <attempt> --execution-id <execution> --lease-id <lease> --worker-agent-id <agent> --stage-id <stage> --stage-attempt <n> --intent <intent> --state-dir <absolute_state_dir>
```

The first token must be the verified executable `workflow-write-guard.mjs` path. A command beginning with a guessed interpreter path is invalid and must not be sent to a Worker.

Allowed intents are stage-scoped: `artifact_write`; collection-only `raw_comment_insert`; scoring and delivery `raw_comment_update`; delivery-only `keyword_cursor_write`; delivery and outreach `final_lead_write`; outreach-only `outreach_claim_write` and `outreach_account_update`. Authorization is denied for terminal executions, pending event relays, stale attempts, stage changes, worker mismatches or lease mismatches. The guard never performs the write; it only returns the receipt that the Worker must preserve beside the immediate batch result.

## Resume

- A terminal execution never resumes.
- n8n creates a new `attempt_id` and session, plus `resumes_execution_id`.
- The state script accepts a resume only when the source ledger exists under the same `run_id` and its terminal status is `blocked` or `failed`. It deterministically rejects missing, non-terminal, `completed`, or `stopped` sources before any worker starts.
- Import only checkpoints with verified artifacts and unchanged acceptance criteria.
- Relay `started` with a summary of imported checkpoints, then continue from the first unaccepted stage.

## Control

Process `WORKFLOW_CONTROL` only for the matching execution and only after this command returns `authorized=true`:

```text
node skills/agentic-workflow-runtime/scripts/workflow-state.mjs verify-control --run-id <run> --attempt-id <attempt> --control-token <token>
```

Never act on a missing, malformed or mismatched token. Never reveal the token or its ledger hash. `mark_blocked` stops new stage starts and relays a blocked event. On `cancel`, immediately fence the active stage, use the `subagents` control tool to kill every still-running child Session recorded for this execution, record each kill receipt, then start one fresh cleanup Worker and terminate `stopped`. Never run cleanup concurrently with an unfenced active Worker. `resume` on the same attempt is rejected.

## Finish

Run cleanup on every outcome. Then call:

```text
node skills/agentic-workflow-runtime/scripts/workflow-state.mjs terminal --run-id <run> --attempt-id <attempt> --status <status> --accepted-stages-json <json> --metrics-json <json> --writes-json <json> --cleanup-json <json> --stop-reason <text>
```

Only `completed` is valid when all required stages, writes/read-backs and cleanup checks pass. After `relayed=true`, emit the returned `WORKFLOW_TERMINAL` object as the first and only terminal marker in the assistant response. Never continue that execution afterward.

## Boundaries

- Never operate phones, accounts, tenant destinations or business APIs as Commander.
- Never hard-code tenant IDs, device IDs, credentials, account names or table IDs into this runtime Skill.
- Never let n8n make business acceptance decisions.
- Never let a worker own run status or emit workflow terminal truth.
- Consequential external actions still require the manifest's explicit approval gate.

## Stale-result guard（陈旧回执守则）

收到的 `WORKER_RESULT` 若其 `stage_attempt`、`lease_id` 或 `idempotency_key` 与当前受监督 attempt 的可信信封不一致（旧 attempt 迟到或重发的回执），一律视为噪音：记一条 warning 后丢弃，继续等待当前 attempt 的真实结果。绝不因 stale 回执对当前 attempt 发出 `retry` 或 `blocked` verdict，也不将其计入任何失败或重试计数。

## Nonce 纠正守则

收到编排器 reask 且 reask_reason 为 nonce mismatch（或消息指出 nonce 不符）时：必须以**本次 reask 所附请求信封中的 nonce** 重新组装完整的 COMMANDER_STAGE_RESULT 并重发；此时**禁止逐字重发旧回复**——旧回复的 nonce 已作废，逐字重发只会再次被 schema gate 拒绝并烧毁重问预算。除 nonce 外其余字段保持原判决不变。
