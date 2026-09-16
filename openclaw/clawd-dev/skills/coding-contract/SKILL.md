---
name: coding-contract
description: "Coding harness stage `contract`（合同）worker for the V4 Commander canvas: proposer 起草合同（contract-draft + contract-dod + Test Contract 表），reviewer 对抗审查；本阶段一轮，retry=下一轮. Use only when spawned by work-commander with a WORKFLOW_STAGE_REQUEST envelope."
---

# 合同（stage `contract`）

本 Worker 只执行 coding-harness 工作流的 `contract` 一个有界阶段。目标：proposer 起草合同（contract-draft + contract-dod + Test Contract 表），reviewer 对抗审查；本阶段一轮，retry=下一轮。

## 铁律
- 只处理信封里显式声明的 `stage_id=contract`；不召唤 Commander、其他 Agent 或下一阶段，不发 `WORKFLOW_TERMINAL`。
- 原样回显信封里的 `run_id`、`attempt_id`、`execution_id`、`object_id`、`workflow_id`、`worker_agent_id`、`lease_id`、`stage_id`、`stage_attempt`、`idempotency_key`、`task_request_hash`；禁止从 run_id 推导任何身份。
- 结束前必须且只能输出一行 `WORKER_RESULT {json}`（schema_version 2，字段见 agentic-workflow-runtime 协议）。

## mode=contract_test
只验证本 skill 与信封可用：仓库、GitHub、Brain、容器全部零读写、零外部互动。返回
`status=completed`，`summary` 写明"contract_test: envelope verified for stage contract"，`metrics={"external_interactions":0,"business_writes":0}`，`artifacts=[]`，`evidence=[{"type":"envelope_check","stage_id":"contract","ok":true}]`，`write_fences=[]`，`recommended_next_action=accept`。

## mode=run（真实执行）
真实执行通过 Cecelia Brain fleet 桥接完成（本容器只发 HTTP，不碰仓库、不跑代码）。完整调用配方、凭据加载、终态映射表见 `/root/clawd-dev/BRAIN_BRIDGE.md`；本阶段 role=`proposer`。
**proposer 初稿常备要求**（金丝雀 #17/#27/#28 里 reviewer 反复退回的三样，初稿就带上少挨一轮）：①枚举类断言一律写成**封闭集合**（恰好 N 项、逐项列名、断言不多不少），禁用"包含"式弱断言；②每个正向 oracle 配至少一个**负向 oracle**（不该发生的事有测试证明不发生）；③范围断言用**这个 canonical 模板**（逐字用它，别自己发明——#28/#30 两发都死在自创写法上）：
```ts
it('范围 oracle：全仓 diff 恰好等于交付清单', () => {
  const allowed = ['docs/current/<交付文件>.md'].sort(); // 合同交付清单，逐字列全
  const diff = execSync('git diff --name-only <BASE_SHA>..HEAD', { encoding: 'utf8' })
    .split('\n').filter(Boolean)
    .filter((f) => !f.startsWith('sprints/')) // sprint 工件不计入交付范围
    .sort();
  expect(diff).toEqual(allowed); // 恰好相等：不多一个文件，不少一个文件
});
```
（<BASE_SHA> 用冻结基线 base_sha 字面量写死）（"只改这个文件"要断言 diff 文件清单恰好等于清单，不是只看目标文件存在）。
**本阶段是两步（一格一轮）**：①role=proposer 起草合同产物【V4 死规矩（r51/r52 连环案卷）：**禁止在合同任何位置引用或承诺 task-plan.json**——那是旧 kernel 产物，V4 不产不封；范围白名单/scope oracle 只准列本轮真实提交到 propose 分支的文件，多列一个 seal 必 409 contract_references_missing_artifact。】（**起草协议——r46/r48 两次全 run 报废的教训**：①任何「恰好 N」断言的 N 必须现场推导：先在草稿里完整列出这 N 项的清单，逐项数出 N，再写断言——禁止先写 N 再补清单；②起草完成后必须做一轮自检：把全部断言两两配对推演一遍，任何一对可能互斥（数量类 vs 存在类尤其）就地修正；③自检结论写进 contract-draft 的「断言自洽声明」小节：列出断言总数与推演结论）；②proposer completed 后必须再发一次 role=`reviewer` 的桥接派发做对抗审查（payload 相同，title 注明 review），只有 reviewer 结果的 verdict 为 APPROVED 才算本阶段可交；reviewer 结果为 PROPOSED/CHANGES_REQUESTED → 把意见带回重跑 proposer（预算内），否则回 blocked。两个 attempt 的 id 都进 evidence，reviewer 的裁定原文进 summary。
**reviewer 封闭判据（金丝雀 #28/#30/#35 案卷：判分无封闭清单=每轮发明新要求=谈判永不收敛）**：reviewer 派发的 description 必须显式注入这份考卷，且声明"**八项全过必须 APPROVED，禁止以清单外理由退回**"：
① contract-draft/contract-dod/Test Contract 三件存在且引用冻结 hash；② Test Contract 每行 it() 可解析且对应测试文件存在；③ 枚举断言为封闭集合（恰好 N 项）；④ 每个正向 oracle 有对应负向 oracle；⑤ 范围 oracle 使用 canonical git-diff 模板且 BASE_SHA 为冻结基线字面量；⑥ 交付清单与 thin_prd 范围一致不超纲；⑦ 断言均可机械执行（测试可跑，无"人工确认"类字眼）。⑧ 断言集自洽：任意两条断言不得互斥（数量类「恰好 N」与存在类「必须含 X」要合并推演——r46 案卷：恰好 4 个 H2 与第 5 个 H2 并存，generator 无法合法产出 GREEN，全 run 报废）。
清单外的改进意见只准写进 warnings（不阻塞 APPROVED）。
**seal 交接坐标（APPROVED 时必发）**：evidence 里必须追加一条机器可读条目 `{"type":"seal_coordinates","bridge_run_id":"<共享桥接 run_id>","sprint_dir":"<sprint_dir>","branch":"<合同所在 propose 分支>","approved_sha":"<reviewer APPROVED 认可的 40 位合同头 sha>","base_sha":"<冻结基线>"}`——seal 阶段只认这条，缺了 seal 必 blocked（金丝雀 #14 实证）。
**run_id 共享（必做）**：proposer 派发带 `"keep_open": true`，记下返回 `run_id`；reviewer（及重跑的 proposer）都带同一 `run_id`——否则 reviewer 在独立 workspace 看不到 proposer 的 contract_artifacts（金丝雀 #6b 实证必 REVISION）。阶段结束（无论成败）POST `/api/brain/harness/attempt-run/close` 收尾该 run_id。
**reviewer 续接（必带，Brain ≥1.273.158）**：reviewer 派发的 payload 必须带 `propose_branch` + `propose_branch_sha`——从 proposer 结果 `result.artifacts` 中 `type=git_artifact` 项的 `branch`/`head_sha` 原样取。不带则 reviewer 的 workspace 从 main 新建，看不到合同产物（金丝雀 #6b/#7 实证必 REVISION）。proposer 派发**必带** `planner_prd_artifact`（STAGE_REQUEST 上下文里 plan 阶段转交的对象原样传，含 verification_status:"verified"）——不带则 proposer 工作区从 main 开工、分支上没有 sprint-prd.md，seal 必死 FROZEN_CONTRACT_ARTIFACTS_MISSING（金丝雀 #24 实证）；上下文缺该对象 → blocked planner_prd_artifact_missing。
流程：POST attempt-run（role=proposer，payload 从信封 task_request 取 sprint_dir/base_repo/base_sha/branch）→ 每 30s GET 轮询至终态 → 按 BRAIN_BRIDGE.md 封闭映射表产 WORKER_RESULT。派发/执行失败一律结构化原样上报（evidence 带 attempt_id），禁止在本机模拟或假装完成；Brain 不可达 → `status=blocked`、`summary="brain_bridge_unreachable: stage contract"`、`retryable=true`。


## 验收（Commander 据此判定）
- contract-draft/contract-dod 工件存在
- Test Contract 表每行声明的测试文件路径与 it() 名可解析
- reviewer verdict=APPROVED 且 blockers 为空

## 安全停止
- 合同自相矛盾且两轮未收敛
- 范围超出 thin_prd
