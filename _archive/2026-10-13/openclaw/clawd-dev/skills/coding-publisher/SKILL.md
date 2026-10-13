---
name: coding-publisher
description: "Coding harness stage `publish`（发布）worker for the V4 Commander canvas: 把 judge PASS 的精确候选 sha 发布为 PR，上报发布结果；CI 轮询与红后重试由独立的 ci-watch 阶段负责，本 worker 不自行轮询、不召唤 generator-fix. Use only when spawned by work-commander with a WORKFLOW_STAGE_REQUEST envelope."
---

# 发布（stage `publish`）

本 Worker 只执行 coding-harness 工作流的 `publish` 一个有界阶段。目标：把 judge PASS 的精确候选 sha 发布为 PR，上报发布结果；CI 轮询与红后重试属于独立的 ci-watch 阶段，不在本 worker 职责内。

## 铁律
- 只处理信封里显式声明的 `stage_id=publish`；不召唤 Commander、其他 Agent 或下一阶段，不发 `WORKFLOW_TERMINAL`。
- 原样回显信封里的 `run_id`、`attempt_id`、`execution_id`、`object_id`、`workflow_id`、`worker_agent_id`、`tenant_id`、`lease_id`、`stage_id`、`stage_attempt`、`idempotency_key`、`task_request_hash`、`commander_event_id`（与 emit-worker-result.mjs 的 ECHO_FIELDS 一致）；禁止从 run_id 推导任何身份。
- 结束前必须且只能输出一行 `WORKER_RESULT {json}`（schema_version 2，字段见 agentic-workflow-runtime 协议）。

## mode=contract_test
只验证本 skill 与信封可用：仓库、GitHub、Brain、容器全部零读写、零外部互动。返回
`status=completed`，`summary` 写明"contract_test: envelope verified for stage publish"，`metrics={"external_interactions":0,"business_writes":0,"business_reads":0,"artifact_writes":0}`，`artifacts=[]`，`evidence=[{"type":"envelope_check","stage_id":"publish","ok":true}]`，`write_fences=[]`，`recommended_next_action=accept`。

## mode=run（真实执行）
本阶段调 Brain 的开 PR 端点（Brain ≥1.273.168），不派容器、不碰仓库：

```bash
. /Users/administrator/openclaw-root/workspaces-root/clawd-dev/.brain-bridge.env
curl -s -m 60 -X POST "$BRAIN_BRIDGE_URL/api/brain/harness/attempt-run/publish-pr" \
  -H "Authorization: Bearer $BRAIN_INTERNAL_TOKEN" -H "Content-Type: application/json" \
  -d '{"branch":"<candidate_coordinates.branch>","head_sha":"<candidate_coordinates.head_sha（必须=judge 裁过的那个头）>","title":"Harness approved candidate <workflow run_id>","body":"<一段话：合同标题+judge PASS 摘要+run_id>","source_attempt_id":"<candidate_coordinates.source_attempt_id>"}'
```

- 坐标来源：STAGE_REQUEST 上下文的 `candidate_coordinates`（judge accepted 之后 Commander 转交）；缺失 → blocked candidate_coordinates_missing。
- 200 {ok,pr_url,pr_number} → completed，evidence 必含 `{"type":"published_pr","pr_url":...,"pr_number":...,"head_sha":...}`（merge 人审卡片要用）。existing:true 表示幂等命中既有 PR，同样算成功。
- 409 publish_head_mismatch → blocked（候选头漂移，禁止发布），detail 原样上报。
- 409 candidate_workspace_unavailable → blocked（候选工作区已释放，无法推送），detail 原样上报。
- **绝不请求 auto-merge**：merge 公章属于画布人审线。


## 验收（Commander 据此判定）
- PR 存在且 head == 候选 sha
- PR 存在且 head == 候选 sha（CI 结果由独立 ci-watch 阶段验收，不在本阶段验收范围）
- 其余未枚举的HTTP状态码、超时或网络错误 → status=failed，retryable=true，evidence带原始状态码/错误信息，禁止默认当作成功或直接吞掉。

## 安全停止
- PR DIRTY 三次未解
- 分支保护拒绝
