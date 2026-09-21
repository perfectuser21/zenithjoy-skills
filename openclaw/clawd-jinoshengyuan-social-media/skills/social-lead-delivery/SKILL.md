---
name: social-lead-delivery
description: "Deterministically deduplicate scored social lead candidates across comments, videos, runs, and the tenant destination; write only qualified leads, verify readback, and update cursors. Use as the fifth business stage after social-comment-lead-scorer; do not rescore comments or contact users."
---


## 交结果之前先落盘（尽力而为，绝不因它阻塞）

输出最后一行 `WORKER_RESULT {json}` 之前，先用**网关侧文件写工具**（不是 `exec`）把**完全相同**的 JSON
写到这个确定路径：

```
/Users/administrator/openclaw-root/workspaces-root/clawd-work-commander/state/workflow-runs/<run_id>__<attempt_id>.<stage_id>.<stage_attempt>.worker-result.json
```

这条路径是可写的（0913 实证：preflight 第 3 次正是靠它写成、Commander 读到、阶段才通过）。
偶尔 `file_write` 会失败——那时记一条 warning 就好，见下。

**这份落盘是尽力而为的备份，不是验收条件。**写失败就在 `warnings` 里记一句然后照常返回你真实的
`status` 与 `recommended_next_action`。**任何情况下都不得因为"回执没写成"而把 `status` 改成 `blocked`**——
那会把一次成功的阶段变成失败。它不需要 write-guard、不计入 `business_writes` / `artifact_writes` / 外部交互计数。

## 产出契约（构造 WORKER_RESULT 前逐项自检）

> 本节与 `agentic-workflow-runtime/references/protocol.md` 的「metrics 封闭键集」逐字一致；
> 冲突时以 protocol.md 为准。适用阶段：delivery。

**metrics 必填**（没发生就填 0，禁止自造键名）：通用 4 键 `external_interactions` `business_reads` `business_writes` `artifact_writes`；本阶段另加 `leads_written` `duplicates_skipped` `readback_verified` `cursor_updates`。

**真实模式 completed 的最小 evidence**（`evidence` 必须是对象数组，空数组不接受）：
- completed 至少 2 条：`{"type":"delivery_write",…}`（写入明细）+ `{"type":"readback",…}`（回读验证）

- 每一笔写入必须在 `write_fences` 附 guard receipt；`readback_verified` 为 0 时禁止报 completed。

# 社媒线索去重与配送

当 `orchestrator=n8n` 时，本 Skill 是一个独立 Agent 节点：不得召唤 Commander、其他 Agent 或下一阶段，只回传相同的执行身份、阶段、幂等键和 `task_request_hash`，由 n8n 验收并推进。`contract_test` 只验证 Skill 与返回合同，最终线索、原始池和游标写入必须全部为零。

当由 `agentic-workflow-runtime` 调用时，只按 frozen `task_request` 的配送策略执行，结束前返回唯一 `WORKER_RESULT`（`schema_version` 为 2，`status` 只填一个词（`completed` / `blocked` / `failed` 三选一），`recommended_next_action` 只填一个词（`accept` / `retry` / `stop` / `request_approval` 四选一）），逐字回显 Commander 传入的执行身份与 `task_request_hash`，并附去重命中数、实际写入数、回读结果与游标更新的证据及其 guard receipt。哈希缺失或不一致时不得执行。

只读取已完成的 `scored-comments.json` 和 frozen `task_request`，确认输入 `task_request_hash` 与 Commander 完全一致；缺失或不一致时不得配送。本阶段不调用 Luna 重新评分，不操作手机，不评论、私信或触达用户。

当 `stage_attempt > 1` 时，必须读取任务内 Manager 基于上一轮耐久裁决提供的 `manager_feedback`，只修复该清单且不得改变 frozen `task_request`。最终结果返回同源 `manager_feedback_ack`，包含逐项 `resolved`、`unresolved` 和新鲜证据；仍有未解决项时不得声称 completed。

## 去重的准确含义

去重不是删除不同人的相似评论，而是防止同一对象重复创建：

1. **视频去重**：同一平台视频 ID/解析链接只保留一个视频对象。
2. **原始评论去重**：同一评论 ID 只写一次；重复扫到时合并证据。
3. **线索人员去重**：优先使用现场读回的稳定 `douyin_id`，其次用平台用户 ID/规范化主页链接。同一人在多条视频下的多条评论合并到一条线索，但保留所有评论原文和来源；只有昵称而无稳定标识时不得标为可触达。
4. **跨运行去重**：一次性读取租户最终线索表已有稳定标识，已存在对象做幂等更新，不重复新建。

仅凭昵称相同不做高置信去重；标记低置信并保留为待复核。**去重优先级**：稳定标识（`douyin_id`）> 规范化主页链接 > 仅昵称（标记不可触达，不参与去重合并）；同一对象多个标识冲突时以最新一次评分结果为准。

## 配送

- 只处理 `candidate_for_delivery=true` 且类型属于 `task_request.scoring_policy.deliver_categories` 的评分结果。
- 把同一人的目标人群、关键词、视频、评论、分数、判断理由和全部来源写入租户最终线索表。
- 同步写入现场读回的 `douyin_id` 与 `outreach_eligible`；只有稳定抖音号、未触达且通过评分的记录才可为 `outreach_eligible=true`。
- 批量写入后回读目标记录 ID 和关键字段；只有回读成功才计为配送成功。
- 将对应原始评论记录更新为“进入最终线索”并写入关联；排除评论保留在原始池及其理由。
- 只有发现、全文判定、穷尽采集、评分和配送都成功时，才推进关键词时间游标。
- 正式获客模式最终 `delivered_leads=0` 时不得声称 completed，也不得伪造或放宽评分；应返回非重试的业务未达标结果。`commander_supervision` 模式下由 Commander 记录为 `blocked`，要求用新的 frozen task_request 启动新 run；**n8n 直连模式下(无 Commander)按 `status=completed_with_concerns` 处理，不依赖 Commander 转译**。`contract_test` 的零写入不受此规则影响。

这里的“配送”仅指写入公司内部最终线索表。话术分配、评论、私信或电话触达是下游独立 Workflow，未经批准不得执行。

## Runtime 写入栅栏与输出

每批变更前分别申请：

- `artifact_write`：写 `delivery.json`；
- `final_lead_write`：新增或幂等更新最终线索；
- `raw_comment_update`：写入原始到最终的关联；
- `keyword_cursor_write`：全链验收后推进日期游标。

输出 `delivery.json`，包含 `task_request_hash`、合格候选、去重合并、新增/更新目标记录 ID、原始关联、回读状态、游标和错误；最终唯一 `WORKER_RESULT` 也必须回传相同哈希。
