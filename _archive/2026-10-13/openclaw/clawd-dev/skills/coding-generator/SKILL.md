---
name: coding-generator
description: "Coding harness stage `generate`（实现）worker for the V4 Commander canvas: 按冻结合同 RED→GREEN 实现：先提交失败测试再提交实现，产出候选分支. Use only when spawned by work-commander with a WORKFLOW_STAGE_REQUEST envelope."
---

# 实现（stage `generate`）

本 Worker 只执行 coding-harness 工作流的 `generate` 一个有界阶段。目标：按冻结合同 RED→GREEN 实现：先提交失败测试再提交实现，产出候选分支。

## 铁律
- 只处理信封里显式声明的 `stage_id=generate`；不召唤 Commander、其他 Agent 或下一阶段，不发 `WORKFLOW_TERMINAL`。
- 原样回显信封里的 `run_id`、`attempt_id`、`execution_id`、`object_id`、`workflow_id`、`worker_agent_id`、`tenant_id`、`lease_id`、`stage_id`、`stage_attempt`、`idempotency_key`、`task_request_hash`、`commander_event_id`（与 emit-worker-result.mjs 的 ECHO_FIELDS 一致）；禁止从 run_id 推导任何身份。
- 结束前必须且只能输出一行 `WORKER_RESULT {json}`（schema_version 2，字段见 agentic-workflow-runtime 协议）。

## mode=contract_test
只验证本 skill 与信封可用：仓库、GitHub、Brain、容器全部零读写、零外部互动。返回
`status=completed`，`summary` 写明"contract_test: envelope verified for stage generate"，`metrics={"external_interactions":0,"business_writes":0,"business_reads":0,"artifact_writes":0}`，`artifacts=[]`，`evidence=[{"type":"envelope_check","stage_id":"generate","ok":true}]`，`write_fences=[]`，`recommended_next_action=accept`。

## mode=run（真实执行）
真实执行通过 Cecelia Brain fleet 桥接完成（本容器只发 HTTP，不碰仓库、不跑代码）。完整调用配方、凭据加载、终态映射表见 `/Users/administrator/openclaw-root/workspaces-root/clawd-dev/BRAIN_BRIDGE.md`；本阶段 role=`generator`。
**合同身份（Brain ≥1.273.165，必带）**：派发 payload 必须含 `"contract_id"`=sealed_contract.contract_id、`"approved_sha"`=sealed_contract.approved_sha、`"contract_version"`=sealed_contract.contract_version——Brain 据此装配冻结合同（缺则 prepare 400）。timeout 用默认（不传 timeout_seconds）。
**坐标（金丝雀 #19 案卷）**：派发 payload 的 `branch` 必须= STAGE_REQUEST 上下文里 `seal_coordinates.branch`（被封印的合同分支——工作区从它起，禁用 cp-<run_id> 派生规则），`base_sha`=`seal_coordinates.base_sha`，并带 `propose_branch`=同分支、`propose_branch_sha`=`seal_coordinates.approved_sha`；坐标缺失 → blocked seal_coordinates_missing。
**禁止 close（#31 实证）**：本阶段结束时**不要**调 close——这个共享 run 要活到 evaluate/judge 用完候选，由 cleanup 阶段统一收尾；提前 close = evaluate 必死 "shared run is terminal"。
**共享 run（必带）**：派发带 `"keep_open": true`——候选不推远端（铁律），evaluate/judge 靠同一桥接 run 的保留工作区才看得到它（预演实证：独立 run 收尾即回收，workspace_source_attempt_unavailable）。
**产出交接（必发）**：completed 时 evidence 必须含 `{"type":"candidate_coordinates","repo":"perfectuser21/cecelia","branch":"<候选分支>","head_sha":"<40位>","bridge_run_id":"<本次桥接 run>","source_attempt_id":"<桥接 POST 202 返回的 attempt_id（UUID，形如 c6a2c43b-…）——绝不是信封里的 a1>"}`（repo/source_attempt_id 必带——金丝雀 #21 实证缺 repo 必 workspace_candidate_repo_mismatch）——evaluate/judge 只认这条。
流程：POST attempt-run（role=generator，payload 从信封 task_request 取 sprint_dir/base_repo，**branch/base_sha 严格按上方"坐标"一节取自 seal_coordinates，不取 task_request 里的同名字段**）→ 每 30s GET 轮询至终态 → 按 BRAIN_BRIDGE.md 封闭映射表产 WORKER_RESULT。派发/执行失败一律结构化原样上报（evidence 带 attempt_id），禁止在本机模拟或假装完成；Brain 不可达 → `status=blocked`、`summary="brain_bridge_unreachable: stage generate"`、`retryable=true`。


## 验收（Commander 据此判定）
- 候选分支存在 RED 与 GREEN 两次提交
- 声明的测试文件全部存在
- 本地测试全绿的证据（命令与输出摘要）

## 安全停止
- 合同不可实现（CONTRACT_SELF_CONTRADICTION）
- 越权改动冻结产物
