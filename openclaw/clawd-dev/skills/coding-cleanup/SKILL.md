---
name: coding-cleanup
description: "Coding harness stage `cleanup`（清理）worker for the V4 Commander canvas: 释放候选工作区、容器与预览环境，验证无残留. Use only when spawned by work-commander with a WORKFLOW_STAGE_REQUEST envelope."
---

# 清理（stage `cleanup`）

本 Worker 只执行 coding-harness 工作流的 `cleanup` 一个有界阶段。目标：释放候选工作区、容器与预览环境，验证无残留。

## 铁律
- 只处理信封里显式声明的 `stage_id=cleanup`；不召唤 Commander、其他 Agent 或下一阶段，不发 `WORKFLOW_TERMINAL`。
- 原样回显信封里的 `run_id`、`attempt_id`、`execution_id`、`object_id`、`workflow_id`、`worker_agent_id`、`lease_id`、`stage_id`、`stage_attempt`、`idempotency_key`、`task_request_hash`；禁止从 run_id 推导任何身份。
- 结束前必须且只能输出一行 `WORKER_RESULT {json}`（schema_version 2，字段见 agentic-workflow-runtime 协议）。

## mode=contract_test
只验证本 skill 与信封可用：仓库、GitHub、Brain、容器全部零读写、零外部互动。返回
`status=completed`，`summary` 写明"contract_test: envelope verified for stage cleanup"，`metrics={"external_interactions":0,"business_writes":0}`，`artifacts=[]`，`evidence=[{"type":"envelope_check","stage_id":"cleanup","ok":true}]`，`write_fences=[]`，`recommended_next_action=accept`。

## mode=run（真实执行）
本阶段收尾桥接资源，不派容器：对上下文里出现过的每个共享桥接 run（candidate_coordinates.bridge_run_id 等）：

```bash
. /root/clawd-dev/.brain-bridge.env
curl -s -m 30 -X POST "$BRAIN_BRIDGE_URL/api/brain/harness/attempt-run/close" \
  -H "Authorization: Bearer $BRAIN_INTERNAL_TOKEN" -H "Content-Type: application/json" \
  -d '{"run_id":"<bridge_run_id>"}'
```

- 每个 close 的响应进 evidence（{"type":"bridge_run_closed","run_id":...,"run_closed":...}）；
- 没有待收尾的共享 run 也算 completed（evidence 说明 nothing_to_close）；失败 → blocked 带原因。


## 验收（Commander 据此判定）
- worktree/容器/预览已释放且验证
- 运行账本终局记录

## 安全停止
- 无额外条件

## 终局交接单（reporter 职责回归——Alex 07-06 拍板三入口统一终态，V4 曾遗失）
cleanup 无论 run 成败都必须在 WORKER_RESULT 的 evidence 里追加一条机器可读交接单：
{"type":"run_handoff","verdict":"PASS|FAIL","done":[本 run 真正交付了什么],"not_done":[未完成/中止原因],"next_steps":[没有则写 完成，无下一步],"artifacts":{"pr_url":"<有则填>","branch":"<候选分支>"}}
- PASS 与 FAIL 都写；FAIL 必须写清死在哪格、死因一句话。
- 内容从台账/各格信封提炼，禁止套空话。
