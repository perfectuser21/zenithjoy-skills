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
/Users/administrator/openclaw-root/workspaces-root/clawd-work-commander/state/workflow-runs/<run_id>__<attempt_id>.<stage_id>.<stage_attempt>.worker-result.json
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
/Users/administrator/openclaw-root/workspaces-root/clawd-work-commander/state/workflow-runs/<run_id>__<attempt_id>.<stage_id>.<stage_attempt>.worker-result.json
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
| 文件读写工具（read/write/edit）、`file_fetch` | **网关侧** | 网关的 `/Users/administrator/openclaw-root/workspaces-root/clawd-*` |

由此产生三条硬规则：

1. **绝不用 `exec` 去读自己的 skill 文件。** 任务里给出的 skill 路径是网关侧的
   `/Users/administrator/openclaw-root/workspaces-root/clawd-*/skills/...`，节点上不存在。要看 skill 就用文件读工具。
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
node skills/agentic-workflow-runtime/scripts/workflow-state.mjs init --run-id <run> --attempt-id <attempt> --object-id <object> --workflow-id <workflow> --worker-agent-id <agent> --total-steps <count> --audience-key <key> --chat-id <chat> --visibility <visibility> --control-token <token> --state-dir <账本目录，见下方「回执落盘」一节的确定路径> [--task-request-hash <sha256>] [--resumes-execution-id <id>]
```

7. Relay `started` using the state script. Do not spawn before `relayed=true`.
8. Keep the returned `lease_id` and resolve the canonical absolute path of `scripts/workflow-write-guard.mjs`. Confirm that path is executable. These two values are mandatory inputs to every worker task; they are never invented by a business Agent.
9. Build `write_guard.command` by invoking the executable guard script directly. Its `#!/usr/bin/env node` shebang resolves the installed Node runtime. Never guess or hard-code `/usr/bin/node`, `/usr/local/bin/node`, or any other Node path into a Worker task.

## Relay an event

```text
node skills/agentic-workflow-runtime/scripts/workflow-state.mjs event --run-id <run> --attempt-id <attempt> --event <event> --status <status> --stage-id <stage> --stage-attempt <n> --current-step <n> --summary <text> --next-action <text> --state-dir <同 init 用的账本目录> [--evidence-json <json>]
```

The script allocates `event_seq`, updates the atomic ledger and POSTs the complete event to n8n. Retry once for a transport failure. If it still fails, preserve the ledger and block before another mutating stage.

## Supervise a stage

1. Build a self-contained worker task from the manifest, frozen task request, tenant context, accepted prior artifacts and safety constraints. Include immutable `run_id`, `attempt_id`, `execution_id`, `worker_agent_id`, `stage_id`, `stage_attempt`, `task_request_hash` when present, the ledger `lease_id`, and a complete `write_guard.command` using the executable guard script path directly plus the state directory.
2. Relay `stage_started`.
3. Re-read the ledger and verify that its latest transition is the exact relayed `stage_started`; use that `event_id` as the expected write-fence event. Never spawn from a pending relay or a terminal ledger.
4. Call `sessions_spawn` exactly once with explicit `agentId=<worker_agent_id>`, stable `taskName`, `mode=run`, `cleanup=keep`. Do not fork the Commander transcript and do not pass `runTimeoutSeconds`.
5. Parse the actual spawn result. Yield only when it contains `status=accepted`, non-empty `runId` and `childSessionKey`.
### 禁止凭空判定"回传被截断"（0912 硬规则）

判定 Worker 回传"被通道截断/不完整"之前，必须按顺序做完这三步，并在结论里写明做过：

1. **先解析收到的最后一条消息**：能从 `WORKER_RESULT ` 之后解析出 JSON，且必填字段齐全，
   那它**就不是截断**——无论它多短、`status` 是什么。
2. 只有解析失败或字段确实缺失时，才去找那份尽力而为的落盘，按顺序试两处：
   ①本工作区 `state/workflow-runs/<run_id>__<attempt_id>.<stage_id>.<stage_attempt>.worker-result.json`；
   ②**被派 Worker 自己工作区**的同名路径 `/Users/administrator/openclaw-root/workspaces-root/clawd-<worker 工作区>/state/workflow-runs/<同一文件名>`
   ——Worker 没有写 Commander 工作区的权限，它的回执只会落在自己那边。
3. 两者都拿不到，才可以说"回传不完整"，并且必须写明已按路径找过。


### 拿不到回传时的终极兜底：直接读 Worker 会话记录文件（0913 新增）

前两条路（解析完成消息、读协议回执文件）都拿不到时，**还有第三条，而且它一定可用**——
Worker 的完整会话记录就在网关磁盘上，你有网关侧文件读取能力：

```
/Users/administrator/.openclaw/agents/<worker_agent_id>/agent/codex-home/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl
```

**0913 深夜起推理已下放 MMV**：会话文件改落在 MMV 上,网关本地那条路径会扑空。用 exec(网关本地 shell)跨机读:

```
ssh -i /Users/administrator/.openclaw/mmv_key -o BatchMode=yes administrator@100.71.151.105 \
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

**Worker 返回 `status=blocked` 或 `failed` 不是传输故障，是它在如实汇报现场。**
**协议回执文件缺失或为空，回执缺失不构成拒绝理由**，只记一条 warning 后照常按内容验收。
必须原样引用它的 `status` 与 `summary` 作为本次 verdict 的依据，不得改写成基础设施故障。

0912 实证：worker 交回的结果 20 个必填字段全在、JSON 合法、summary 明确写着
"抖音停留在搜索结果页、主页导航点击超时、按安全门禁停止"，
Commander 连续四次判成 `truncated by completion transport`，
把可直接行动的现场报告变成了查不到的幽灵问题，整轮尝试全部白烧。
禁止用目录 grep 去"找回"结果——它会扫到 `SKILL.md.bak-*` 之类备份并得出错误结论。

6. Validate the final `WORKER_RESULT`, artifacts and evidence against every acceptance and safety criterion. When the ledger has `task_request_hash`, every stage result and artifact must carry the same hash; reject missing or mismatched values. Every artifact or destination mutation must include a guard receipt whose `commander_event_id` equals the expected stage event and whose `fence_token` matches the execution, lease, worker, stage, attempt and intent. A claimed write without a valid receipt is rejected.
7. Choose `accept`, `steer`, `retry`, `block`, or `stop`; relay the choice before continuing. Once `retrying`, a later stage starts, or terminal state is recorded, the prior Session's next guard call must fail and its late result must never be accepted.

Retry always creates a fresh worker stage attempt. Never retry safety stops, tenant/device/account mismatch, verification challenges, external approvals, or unknown non-idempotent outcomes.

## Write fencing

The guard is checked immediately before each artifact or business-system mutation:

```text
<absolute_guard_script> authorize --run-id <run> --attempt-id <attempt> --execution-id <execution> --lease-id <lease> --worker-agent-id <agent> --stage-id <stage> --stage-attempt <n> --intent <intent> --state-dir <absolute_state_dir>
```

The first token must be the verified executable `workflow-write-guard.mjs` path. A command beginning with a guessed interpreter path is invalid and must not be sent to a Worker.

Allowed intents are stage-scoped: `artifact_write`; collection-only `raw_comment_insert`; scoring and delivery `raw_comment_update`; delivery-only `final_lead_write` and `keyword_cursor_write`. Authorization is denied for terminal executions, pending event relays, stale attempts, stage changes, worker mismatches or lease mismatches. The guard never performs the write; it only returns the receipt that the Worker must preserve beside the immediate batch result.

## Resume

- A terminal execution never resumes.
- n8n creates a new `attempt_id` and session, plus `resumes_execution_id`.
- The state script accepts a resume only when the source ledger exists under the same `run_id` and its terminal status is `blocked` or `failed`. It deterministically rejects missing, non-terminal, `completed`, or `stopped` sources before any worker starts.
- Import only checkpoints with verified artifacts and unchanged acceptance criteria.
- Relay `started` with a summary of imported checkpoints, then continue from the first unaccepted stage.

## Control

Process `WORKFLOW_CONTROL` only for the matching execution and only after this command returns `authorized=true`:

```text
node skills/agentic-workflow-runtime/scripts/workflow-state.mjs verify-control --run-id <run> --attempt-id <attempt> --control-token <token> --state-dir <同 init 用的账本目录>
```

Never act on a missing, malformed or mismatched token. Never reveal the token or its ledger hash. `mark_blocked` stops new stage starts and relays a blocked event. On `cancel`, immediately fence the active stage, use the `subagents` control tool to kill every still-running child Session recorded for this execution, record each kill receipt, then start one fresh cleanup Worker and terminate `stopped`. Never run cleanup concurrently with an unfenced active Worker. `resume` on the same attempt is rejected.

## Finish

Run cleanup on every outcome. Then call:

```text
node skills/agentic-workflow-runtime/scripts/workflow-state.mjs terminal --run-id <run> --attempt-id <attempt> --status <status> --accepted-stages-json <json> --metrics-json <json> --writes-json <json> --cleanup-json <json> --stop-reason <text> --state-dir <同 init 用的账本目录>
```

Only `completed` is valid when all required stages, writes/read-backs and cleanup checks pass. After `relayed=true`, emit the returned `WORKFLOW_TERMINAL` object as the first and only terminal marker in the assistant response. Never continue that execution afterward.

## Boundaries

- Never operate phones, accounts, tenant destinations or business APIs as Commander.
- Never hard-code tenant IDs, device IDs, credentials, account names or table IDs into this runtime Skill.
- Never let n8n make business acceptance decisions.
- Never let a worker own run status or emit workflow terminal truth.
- Consequential external actions still require the manifest's explicit approval gate.
