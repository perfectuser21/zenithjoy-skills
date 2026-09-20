---
name: coding-planner
description: "Coding harness stage `plan`（计划）worker for the V4 Commander canvas: 从冻结的 thin_prd 产出 sprint-prd（范围、Golden Path 步骤、验收断言），不写代码. Use only when spawned by work-commander with a WORKFLOW_STAGE_REQUEST envelope."
---

# 计划（stage `plan`）

本 Worker 只执行 coding-harness 工作流的 `plan` 一个有界阶段。目标：从冻结的 thin_prd 产出 sprint-prd（范围、Golden Path 步骤、验收断言），不写代码。

## 铁律
- 只处理信封里显式声明的 `stage_id=plan`；不召唤 Commander、其他 Agent 或下一阶段，不发 `WORKFLOW_TERMINAL`。
- 原样回显信封里的 `run_id`、`attempt_id`、`execution_id`、`object_id`、`workflow_id`、`worker_agent_id`、`lease_id`、`stage_id`、`stage_attempt`、`idempotency_key`、`task_request_hash`；禁止从 run_id 推导任何身份。
- 结束前必须且只能输出一行 `WORKER_RESULT {json}`（schema_version 2，字段见 agentic-workflow-runtime 协议）。

## mode=contract_test
只验证本 skill 与信封可用：仓库、GitHub、Brain、容器全部零读写、零外部互动。返回
`status=completed`，`summary` 写明"contract_test: envelope verified for stage plan"，`metrics={"external_interactions":0,"business_writes":0}`，`artifacts=[]`，`evidence=[{"type":"envelope_check","stage_id":"plan","ok":true}]`，`write_fences=[]`，`recommended_next_action=accept`。

## mode=run（真实执行）
真实执行通过 Cecelia Brain fleet 桥接完成（本容器只发 HTTP，不碰仓库、不跑代码）。完整调用配方、凭据加载、终态映射表见 `/Users/administrator/openclaw-root/workspaces-root/clawd-dev/BRAIN_BRIDGE.md`；本阶段 role=`planner`。
**WORKER_RESULT 的 artifacts 条目必须带 hash 字段**（复现 3 次的硬考点）：产出登记形如 `{"type":"sprint_prd","path":"<sprint_dir>/sprint-prd.md","branch":"<planner 分支>","head_sha":"<40位>","task_request_hash":"<信封里的 hash 原样>"}`——正文有 hash 不够，Commander 严格校验 artifact 条目对象本身；漏字段 = 本轮白烧。
**派发 description 必须显式注入两条要求**（连续三发金丝雀实证 fleet planner 不知道 V4 合同）：①「sprint-prd.md 正文必须包含一行 task_request_hash: <信封里的 task_request_hash>」；②「产出后禁止额外外部交互」。否则第一枪必被 Commander 以 missing frozen hash 退回，白烧一轮。
流程：POST attempt-run（role=planner，payload 从信封 task_request 取 sprint_dir/base_repo/base_sha/branch）→ 每 30s GET 轮询至终态 → 按 BRAIN_BRIDGE.md 封闭映射表产 WORKER_RESULT。派发/执行失败一律结构化原样上报（evidence 带 attempt_id），禁止在本机模拟或假装完成；Brain 不可达 → `status=blocked`、`summary="brain_bridge_unreachable: stage plan"`、`retryable=true`。


## 验收（Commander 据此判定）
- sprint-prd 工件存在且引用了冻结 task_request_hash
- 每条验收断言可被测试文件覆盖
- 不包含范围外事项

## 安全停止
- thin_prd 与 base_repo 不一致
- 仓库不可访问
