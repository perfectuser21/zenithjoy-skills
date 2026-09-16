---
name: coding-judge
description: "Coding harness stage `judge`（裁判）worker for the V4 Commander canvas: 独立裁判复核 evaluator 证据，给出 PASS/FAIL；FAIL 回 generate（fix）. Use only when spawned by work-commander with a WORKFLOW_STAGE_REQUEST envelope."
---

# 裁判（stage `judge`）

本 Worker 只执行 coding-harness 工作流的 `judge` 一个有界阶段。目标：独立裁判复核 evaluator 证据，给出 PASS/FAIL；FAIL 回 generate（fix）。

## 铁律
- 只处理信封里显式声明的 `stage_id=judge`；不召唤 Commander、其他 Agent 或下一阶段，不发 `WORKFLOW_TERMINAL`。
- 原样回显信封里的 `run_id`、`attempt_id`、`execution_id`、`object_id`、`workflow_id`、`worker_agent_id`、`lease_id`、`stage_id`、`stage_attempt`、`idempotency_key`、`task_request_hash`；禁止从 run_id 推导任何身份。
- 结束前必须且只能输出一行 `WORKER_RESULT {json}`（schema_version 2，字段见 agentic-workflow-runtime 协议）。

## mode=contract_test
只验证本 skill 与信封可用：仓库、GitHub、Brain、容器全部零读写、零外部互动。返回
`status=completed`，`summary` 写明"contract_test: envelope verified for stage judge"，`metrics={"external_interactions":0,"business_writes":0}`，`artifacts=[]`，`evidence=[{"type":"envelope_check","stage_id":"judge","ok":true}]`，`write_fences=[]`，`recommended_next_action=accept`。

## mode=run（真实执行）
真实执行通过 Cecelia Brain fleet 桥接完成（本容器只发 HTTP，不碰仓库、不跑代码）。完整调用配方、凭据加载、终态映射表见 `/root/clawd-dev/BRAIN_BRIDGE.md`；本阶段 role=`judge`。
**evaluator 权威（必带，Brain ≥1.273.167）**：payload 带 `"evaluate_attempt_id"`=evaluate 阶段结果 evidence 里的 brain_attempt id + `"contract_id"`/`"approved_sha"`（同 generate）——Brain 据此组装 evaluator 裁决权威，缺则 judge_evaluator_authority_mismatch。
**坐标**：派发 payload 的 `candidate` = STAGE_REQUEST 上下文 `candidate_coordinates` 的 {repo, branch, head_sha, source_attempt_id} 原样（repo/source_attempt_id 必带）；**派发必须带 `"run_id": "<candidate_coordinates.bridge_run_id>"` 复用 generate 的共享桥接 run**（候选只活在该 run 的保留工作区）；缺失 → blocked candidate_coordinates_missing，禁自己猜。
流程：POST attempt-run（role=judge，payload 从信封 task_request 取 sprint_dir/base_repo/base_sha/branch）→ 每 30s GET 轮询至终态 → 按 BRAIN_BRIDGE.md 封闭映射表产 WORKER_RESULT。派发/执行失败一律结构化原样上报（evidence 带 attempt_id），禁止在本机模拟或假装完成；Brain 不可达 → `status=blocked`、`summary="brain_bridge_unreachable: stage judge"`、`retryable=true`。


## 验收（Commander 据此判定）
- judge verdict 落记录且引用 evaluate 证据
- FAIL 时 failure_class 明确

## 安全停止
- 裁判无法采信证据

## 第 73 批（Brain ≥1.273.176）
- 派发 evaluate/judge 的 attempt-run 必带 run_id（generate 开的共享 bridge run id），缺失 → 400 role_requires_bridge_run。
- candidate 五坐标与 base_sha 由 Brain 服务端从本 run 的 generator git_candidate 产物权威注入——不要自己抄写这两组值，抄了也会被覆写。
