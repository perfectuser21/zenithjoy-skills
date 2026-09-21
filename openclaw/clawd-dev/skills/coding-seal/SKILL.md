---
name: coding-seal
description: "Coding harness stage `seal`（封印）worker for the V4 Commander canvas: 机械封印已批准合同：冻结四件套 + Test Contract 可解析校验 + 产物 hash. Use only when spawned by work-commander with a WORKFLOW_STAGE_REQUEST envelope."
---

# 封印（stage `seal`）

本 Worker 只执行 coding-harness 工作流的 `seal` 一个有界阶段。目标：机械封印已批准合同：冻结四件套 + Test Contract 可解析校验 + 产物 hash。

## 铁律
- 只处理信封里显式声明的 `stage_id=seal`；不召唤 Commander、其他 Agent 或下一阶段，不发 `WORKFLOW_TERMINAL`。
- 原样回显信封里的 `run_id`、`attempt_id`、`execution_id`、`object_id`、`workflow_id`、`worker_agent_id`、`tenant_id`、`lease_id`、`stage_id`、`stage_attempt`、`idempotency_key`、`task_request_hash`、`commander_event_id`（与 emit-worker-result.mjs 的 ECHO_FIELDS 一致）；禁止从 run_id 推导任何身份。
- 结束前必须且只能输出一行 `WORKER_RESULT {json}`（schema_version 2，字段见 agentic-workflow-runtime 协议）。

## mode=contract_test
只验证本 skill 与信封可用：仓库、GitHub、Brain、容器全部零读写、零外部互动。返回
`status=completed`，`summary` 写明"contract_test: envelope verified for stage seal"，`metrics={"external_interactions":0,"business_writes":0,"business_reads":0,"artifact_writes":0}`，`artifacts=[]`，`evidence=[{"type":"envelope_check","stage_id":"seal","ok":true}]`，`write_fences=[]`，`recommended_next_action=accept`。

## mode=run（真实执行）
本阶段调 Brain 的机械封印端点（Brain ≥1.273.159），不派发执行容器、不改任何文件：

```bash
. /Users/administrator/openclaw-root/workspaces-root/clawd-dev/.brain-bridge.env
curl -s -m 120 -X POST "$BRAIN_BRIDGE_URL/api/brain/harness/attempt-run/contract-seal" \
  -H "Authorization: Bearer $BRAIN_INTERNAL_TOKEN" -H "Content-Type: application/json" \
  -d '{"run_id":"<contract 阶段共享的桥接 run_id>","sprint_dir":"<同 contract 阶段>","branch":"<reviewer APPROVED 那版合同所在分支>","approved_sha":"<该分支被批准时的 40 位头 sha>"}'
```

- 坐标来源：STAGE_REQUEST 上下文里 contract 阶段转交的 `seal_coordinates` 对象（bridge_run_id/sprint_dir/branch/approved_sha）——Commander 按 coding-workflow 合同必须转交；缺失或字段不全 → `blocked`、`summary="seal_coordinates_missing: stage seal"`，禁止自己猜或翻日志拼凑。
- **WORKER_RESULT metrics 键集（金丝雀 #15 实证，协议校验硬要求）**：metrics 必须恰好为 `{"external_interactions": <本阶段 HTTP 调用数>, "business_writes": <封印成功=1 否则 0>, "business_reads": 0, "artifact_writes": 0}`——不得多键不得少键；HTTP 状态码等细节放 evidence 条目 `{"type":"seal_endpoint","http_status":...,"run_id":...}`，禁止塞进 metrics。
- 200 {ok:true} → status=completed。**evidence 必须含 sealed_contract 坐标（generate 只认这条）**：`{"type":"sealed_contract","contract_id":"<响应 sealed.id>","contract_version":<响应 sealed.version>,"approved_sha":"<本次封印用的 approved_sha>","branch":"<合同分支>","sprint_dir":"<sprint_dir>","base_sha":"<冻结基线>"}`。
- 409 contract_seal_rejected → 机械校验不过（Test Contract 不可解析 / 产物缺失 / 防篡改守卫），status=blocked，detail 原样进 summary，recommended_next_action=stop（Commander 决定是否打回 proposer）。
- 网络不通 → blocked brain_bridge_unreachable: stage seal，retryable=true。
- 200 {ok:false} → status=blocked，detail 原样上报，不得当作 completed。


- **approval_provenance 一律不传**（金丝雀 #17 实证：DB 约束只认 NULL 或 direct 快审对象；V4 对抗审查路径=NULL）。

## 验收（Commander 据此判定）
- frozen contract manifest 存在且 hash 记录
- Test Contract 表全部行可解析到冻结产物或仓库既有路径

## 安全停止
- TEST_CONTRACT_UNRESOLVABLE（回合同阶段重写）
