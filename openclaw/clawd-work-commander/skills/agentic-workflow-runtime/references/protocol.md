# Commander protocol v2

## Identity

Every marker requires `schema_version=2`, `run_id`, `attempt_id`, `execution_id`, `object_id`, `workflow_id`, `worker_agent_id`, monotonic `event_seq`, unique `event_id` and `dedupe_key`.

Every run also has a caller-held `control_token`. The ledger stores only its SHA-256 hash. The token is transport-private control authority: it never appears in lifecycle markers, cards, status responses or terminal output. A control message is ignored until `workflow-state.mjs verify-control` authorizes it against the exact attempt ledger.

- `execution_id` is `<run_id>:<attempt_id>`.
- `event_id` is `<execution_id>:<event_seq>`.
- `dedupe_key` equals `event_id` unless a stricter business key is supplied.

## Event line

```text
WORKFLOW_EVENT {"schema_version":2,"run_id":"...","attempt_id":"a1","execution_id":"...:a1","object_id":"...","workflow_id":"...","worker_agent_id":"...","event_seq":1,"event_id":"...:a1:1","dedupe_key":"...:a1:1","event":"stage_started","stage_id":"...","stage_attempt":1,"status":"running","summary":"...","evidence":[],"next_action":"...","current_step":1,"total_steps":5,"owner_lease":{"owner":"work-commander","lease_id":"...","expires_at":"ISO-8601"},"card_target":{"audience_key":"vps-status","chat_id":"oc_...","visibility":"internal"},"observed_at":"ISO-8601"}
```

`event_seq` is allocated by the local run ledger. Relay each event to n8n before the next mutating stage.

## Terminal line

```text
WORKFLOW_TERMINAL {"schema_version":2,"run_id":"...","attempt_id":"a1","execution_id":"...:a1","object_id":"...","workflow_id":"...","worker_agent_id":"...","event_seq":9,"event_id":"...:a1:9","dedupe_key":"...:a1:9","status":"completed","accepted_stages":[],"metrics":{},"writes":{},"cleanup":{"attempted":true,"verified":true},"stop_reason":"","card_target":{"audience_key":"vps-status","chat_id":"oc_...","visibility":"internal"},"finished_at":"ISO-8601"}
```

Terminal state is immutable per `execution_id`. Recovery creates a new `attempt_id`, records `resumes_execution_id`, and imports only explicitly accepted checkpoints.

## Worker result

```text
WORKER_RESULT {"schema_version":2,"run_id":"...","attempt_id":"a1","execution_id":"...:a1","object_id":"...","workflow_id":"...","worker_agent_id":"...","lease_id":"...","stage_id":"...","stage_attempt":1,"idempotency_key":"...:a1:stage:1","task_request_hash":"...","status":"completed","summary":"...","metrics":{},"artifacts":[],"evidence":[{"type":"..."}],"write_fences":[],"warnings":[],"retryable":false,"recommended_next_action":"accept"}
```

Workers echo every trusted immutable identity value supplied by Commander exactly; they never infer `object_id`, `workflow_id`, `idempotency_key` or any other identity from `run_id`. Workers never emit `WORKFLOW_TERMINAL`. Mutation success requires both read-back evidence and a matching guard receipt in `write_fences`; read-only stages may return an empty array only when they created no artifact.

Each write-fence receipt contains `execution_id`, `worker_agent_id`, `stage_id`, `stage_attempt`, `intent`, `commander_event_id` and `fence_token`. The Commander accepts it only for the exact active stage event. A receipt from an earlier retry, another worker or a terminal execution is invalid even if the external write later succeeds.

The Worker receives the canonical executable `workflow-write-guard.mjs` path and invokes it directly. The script's `#!/usr/bin/env node` shebang selects the available Node runtime; Commander and Worker must never guess an interpreter path such as `/usr/bin/node`.

## Spawn receipt

Use deterministic `taskName=v4-<nonce>-<stage_id>-<stage_attempt>` and validate it before spawning: 1–64 characters matching `[a-z][a-z0-9_-]*`.

Before yielding, the Commander must possess:

```json
{"status":"accepted","runId":"non-empty","childSessionKey":"non-empty"}
```

<!-- enum-note -->
> **上面模板里的枚举字段填法**：模板给的是**示例值**，不是可选项列表。
> 每个字段只填**一个词**，不要把候选词连着竖线整串填进去。
>
> - `status`：`completed`（阶段完成）/ `blocked`（安全停止，可由新 attempt 恢复）/ `failed`（确定性失败）
> - `recommended_next_action`：`accept` / `retry` / `stop` / `request_approval`
> - `schema_version`：数字 `2`，不是字符串，也不是 `"v4"`
>
> 实测曾有 18.6% 的返回把整串候选词（连着竖线的那一长串）当成了值填进 status，
> 这类返回一律判 retry。**本说明刻意不写出那个错误形态，以免被照抄。**

> **evidence 与 artifacts 的三条硬规则**（实测 30% 的 completed 证据为空、14% 形态错、21% 混放）：
> 1. `evidence` 必须是 **JSON 数组**，每个元素是对象（如 `[{"type":"preflight","serial":"…"}]`），
>    不要写成单个对象。
> 2. 真实模式（非 contract_test）的 `status=completed` 至少要有 **1 条** evidence，空数组不接受。
> 3. 只读产物（截图路径、快照、UI XML）属于 `evidence`；`artifacts` 只放**申请过 write guard、
>    有 receipt** 的业务产物。预检/清理类阶段的 `artifacts` 应为 `[]`。

## metrics 封闭键集（禁止自造键名）

实测同一 stage 的 metrics 出现过 **119 种**不同键名，验收方无法机械读取产出量。自此约定：

**所有 stage 必填 4 键**（值一律为数字）：
`external_interactions` `business_reads` `business_writes` `artifact_writes`

**各 stage 附加必填键**：

| stage | 附加必填键 |
|---|---|
| preflight | `device_verified` `account_verified` `call_state_idle` `lock_acquired`（0/1） |
| discovery | `keywords_processed` `screens_scanned` `candidates` |
| qualification | `candidates_judged` `qualified` |
| collection | `comments_collected` `videos_processed` `cursor_updates` |
| scoring | `comments_scored` `strong_intent` `weak_intent` `peer` `irrelevant` `spam` |
| delivery | `leads_written` `duplicates_skipped` `readback_verified` `cursor_updates` |
| outreach | `contacts_made` `claims_acquired` |
| cleanup | `close_app_attempts` `lock_released` `safe_desktop_visible`（0/1） |

必填键**必须全部出现**（没发生就填 0）。其它想说明的信息写进 `evidence` 或 `summary`，
**不要发明新的 metrics 键**。

If any field is missing, no worker exists and yielding is forbidden.

## Decisions

- `accept`: all acceptance and evidence checks pass.
- `steer`: a live worker can be corrected without changing scope.
- `retry`: the manifest allows it, the action is idempotent, and attempts remain.
- `block`: approval or unavailable external state is required.
- `stop`: safety, identity mismatch, policy violation or unknown non-idempotent outcome.

Every retry states the failed criterion, prior evidence, changed instruction and unchanged safety boundary.
