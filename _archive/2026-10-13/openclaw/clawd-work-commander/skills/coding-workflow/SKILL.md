---
name: coding-workflow
description: "Define the n8n-owned, Commander-supervised coding harness workflow on the V4 skeleton: plan, adversarial contract, seal, RED→GREEN generate, evaluate, judge, publish with green CI, human-stamped merge, cleanup. Use for Cecelia/ZenithJoy coding tasks driven by a frozen thin_prd."
---

# Coding Harness Workflow（V4 骨架第二个乘客）

把一次 coding 任务编排为九个有界阶段。流程顺序、重试计数、人审插点、终局全部在 n8n 画布 `AwrCodingHarnessV4`；每个阶段由 `work-commander` 监工：spawn 一个有界 Worker、验收证据、只回封闭词表 verdict。Commander 永远不决定下一阶段；n8n 永远不做业务验收。

## generate 阶段验收标准（2026-09-02 写死，金丝雀 #31/#32 裁决不一致案卷）

- 候选**按设计不推远端**（发布权属 publish 阶段）——generate 验收**禁止要求远端读回**，那是做不到的要求；
- 验收依据封闭清单：①distinct RED/GREEN 提交 sha ②声明测试文件存在且 hash 一致 ③本地绿测证据（N/N passed）④candidate_coordinates 五字段齐全 ⑤artifact_write 写围栏回执 ⑥docs/代码范围与合同一致；
- 候选内容的真验证发生在 evaluate 阶段（同共享 run 工作区真跑冻结测试）——generate 不重复它的职责。

## 跨阶段证据转交（2026-09-01 加入，金丝雀 #14 案卷）

- **contract 阶段验收硬项（金丝雀 #18 案卷）**：WORKER_RESULT evidence 必须含合法 `seal_coordinates`（bridge_run_id/sprint_dir/branch/approved_sha/base_sha 五字段齐全）——缺失或残缺 = 本轮 retry，manager feedback 点名要求补发，**不得 accepted**；
- plan 阶段 accepted 后，其 artifact 坐标以 `planner_prd_artifact` 记账（{kind:"planner_prd", path, branch, head_sha, verification_status:"verified"}——verified 由 plan 验收的远端读回背书），并转交给 **contract** 阶段；
- contract 阶段 accepted 后，其 WORKER_RESULT evidence 里的 `seal_coordinates` 对象必须被记入台账；
- 向 **seal 与 generate** 阶段发 STAGE_REQUEST 时，把 `seal_coordinates` 对象**原样**放进请求上下文；
- seal 阶段 accepted 后，其 evidence 里的 `sealed_contract` 对象（contract_id/contract_version/approved_sha/branch/sprint_dir/base_sha）记入台账并转交给 **generate、evaluate 与 judge**；seal 验收硬项：evidence 含合法 sealed_contract，缺则 retry 点名补发；
- publish 阶段 accepted 后，其 evidence 里的 `published_pr`（pr_number/pr_url/head_sha）记账并转交给 **merge** 阶段（连同人审恢复的 human_approval 上下文）；
- generate 阶段 accepted 后，其 evidence 里的 `candidate_coordinates`（repo/branch/head_sha/bridge_run_id/**source_attempt_id**——r53 案卷：publish 端点靠它定位候选工作区做 fast-forward 推送，转交给 publish 时缺此字段必 409 publish_head_mismatch）同样记账，并转交给 **evaluate、judge、publish 与 cleanup** 阶段（金丝雀 #19 案卷：generate 若拿不到合同分支坐标，workspace 必 base_sha_unavailable）；generate 验收硬项：evidence 含合法 candidate_coordinates，缺则 retry 点名补发；
- seal Worker 缺坐标回 blocked 属正确行为——修复方向永远是补转交，不是让 Worker 自己猜。

## 输入合同
n8n Intake 冻结 `task_request`：`task_title`、`thin_prd`、`base_repo`（完整 GitHub URL）、`base_branch`、`target_environment`（mac_web|windows_cloud|local_api…）、`gp_anchor`。冻结后任何阶段只接受同一 `task_request_hash`。

## 九阶段
plan → contract → seal → generate → evaluate → judge → publish → merge → cleanup。各阶段 Worker skill、验收与安全停止条件见 [workflow-manifest.json](references/workflow-manifest.json)。

## 模式
- `contract_test`：Worker 只验证 skill 与信封可用，仓库/GitHub/Brain 零写入、零外部互动，每阶段回一条 `WORKER_RESULT`。
- `run`：Worker 通过 Cecelia Brain fleet 派发在目标机器执行真实阶段（接线中；未接线时 Worker 必须回 `blocked` 并说明 `brain_fleet_not_wired`，禁止假装完成）。

## 运行边界
- Worker 不召唤其他 Agent、不推进下一阶段、不发终态。
- 冻结合同不可改；generator 只在合同白名单内写文件。
- merge 阶段前必须有画布上的人审通过（公章）。

## 案卷库（r39-r51 历史死因与纠正——上岗必读，验收时对号入座）
- **r39 judge 机械闸误杀**：judge 亲手重跑测试全过、机械计数却报零 → 已修（Brain 认封印测试产物）。若再见「自相矛盾的 FAIL」，判 infrastructure 而非 evidence，点名报 Brain 版本。
- **r40 坐标编造/丢失**：工人把锚 task uuid 前缀续写成 40 位假 sha；重试时又丢光坐标 → 已机械根除（Brain 服务端注入候选与基线，工人抄什么都会被覆写）。验收时不要因坐标字段缺失打回 evaluate/judge 工人——那些字段服务端会补。
- **r42 递错 run**：工人拿 contract 共享 run 当 generate 共享 run → 已根除（sprint_dir 寻址）。
- **r43 concerns 断供**：generator 带保留意见完成（completed_with_concerns）时评估断供 → 已修。generator 有 P2 级 concern 不阻塞后续阶段。
- **r45 幻觉安全边界**：planner 因瞬时网络故障够不着 Brain，自我解释成「零外部交互约束」→ 纠正：网络失败就如实报 infrastructure/network，禁止把故障脑补成纪律。
- **r46/r48 合同自相矛盾**：「恰好 N 个」与「必须含第 N+1 个」并存，generator 只能诚实停机 → 起草协议已入 contract skill（恰好 N 必须现场数出+两两推演自检）。Commander 验收 contract 时抽查：把数量断言与存在断言配对推一遍。
- **r47 publish 头不一致**：候选分支与 planner 预推提案分支同名，远端头旧 → 已修（Brain fast-forward 推送）。publish 报 publish_head_mismatch 且带 push_error=非 FF 时才是真异常。
- **r41/r44/r49/r50 画布被 n8n 重启误杀**：与流水线无关的环境死因。恢复永远是新 run 重发（崩溃自动补发 cron 在岗），不要让工人尝试续接死 run。
- **通用铁律**：机械判定不能建立在 LLM 自愿配合上——发现工人反复抄错某坐标，正确方向是上报「该坐标应服务端权威化」，不是在 feedback 里骂工人。

## 验收阶段判则补丁（r54 案卷——返修回路）
- evaluate Worker completed 且其评估结论为 FAIL：阶段裁决必须回 **retry**（不是 accepted——验收阶段的任务是取得 PASS 的验收，结论 FAIL 即阶段目标未达成）。manager feedback 必须原样携带 evaluator 指出的缺陷（含级别与位置），画布会把这次 retry 路由回实现格做 generator-fix。
- 实现格 stage_attempt ≥ 4（含返修轮）仍不能取得 PASS 验收：回 blocked（返修预算耗尽，需人看）。
- judge 只复核 PASS 的验收——凡评估结论非 PASS，禁止推进裁判格。
