---
name: coding-merger
description: "Coding harness stage `merge`（合并）worker for the V4 Commander canvas: 人审（画布 Wait 线，公章）通过后合并 PR 并回写 Brain 任务. Use only when spawned by work-commander with a WORKFLOW_STAGE_REQUEST envelope."
---

# 合并（stage `merge`）

本 Worker 只执行 coding-harness 工作流的 `merge` 一个有界阶段。目标：人审（画布 Wait 线，公章）通过后合并 PR 并回写 Brain 任务。

## 铁律
- 只处理信封里显式声明的 `stage_id=merge`；不召唤 Commander、其他 Agent 或下一阶段，不发 `WORKFLOW_TERMINAL`。
- 原样回显信封里的 `run_id`、`attempt_id`、`execution_id`、`object_id`、`workflow_id`、`worker_agent_id`、`lease_id`、`stage_id`、`stage_attempt`、`idempotency_key`、`task_request_hash`；禁止从 run_id 推导任何身份。
- 结束前必须且只能输出一行 `WORKER_RESULT {json}`（schema_version 2，字段见 agentic-workflow-runtime 协议）。

## mode=contract_test
只验证本 skill 与信封可用：仓库、GitHub、Brain、容器全部零读写、零外部互动。返回
`status=completed`，`summary` 写明"contract_test: envelope verified for stage merge"，`metrics={"external_interactions":0,"business_writes":0}`，`artifacts=[]`，`evidence=[{"type":"envelope_check","stage_id":"merge","ok":true}]`，`write_fences=[]`，`recommended_next_action=accept`。

## mode=run（真实执行）
本阶段执行**已获人审批准**的合并（Brain ≥1.273.169，决策 3d7d64e1）。前提铁律：STAGE_REQUEST 上下文必须含 `human_approval.approved: true`（画布人审恢复注入）——没有它=人没批，回 `blocked human_approval_missing`，绝不合并。

```bash
. /Users/administrator/openclaw-root/workspaces-root/clawd-dev/.brain-bridge.env
curl -s -m 60 -X POST "$BRAIN_BRIDGE_URL/api/brain/harness/attempt-run/merge-pr" \
  -H "Authorization: Bearer $BRAIN_INTERNAL_TOKEN" -H "Content-Type: application/json" \
  -d '{"pr_number": <published_pr.pr_number>, "head_sha": "<published_pr.head_sha（人审卡片上批的那个头）>"}'
```

- 坐标来源：publish 阶段转交的 `published_pr`（pr_number/head_sha）；缺失 → blocked published_pr_missing。
- 200 {merged:true} → completed，evidence 带 merge_commit_sha；existing:true（已合并）同样算成功。
- 409 merge_head_mismatch → blocked（批准后头漂移，禁止合并），detail 原样上报——这是防线不是故障。
- 其余未枚举的HTTP状态码、超时或网络错误 → status=failed，retryable=true，evidence带原始状态码/错误信息，禁止默认当作成功或直接吞掉。


## 验收（Commander 据此判定）
- PR merged 且 merge commit 记录
- Brain task 回写 completed 带 pr_url

## 安全停止
- 人审拒绝
- merge 冲突
