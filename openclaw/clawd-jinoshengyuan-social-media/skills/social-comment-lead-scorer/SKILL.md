---
name: social-comment-lead-scorer
description: "Use Luna to score every collected social comment in bounded batches as strong intent, weak intent, peer, irrelevant, or spam, with evidence and confidence. Use as the fourth business stage after comment collection and before deterministic deduplication and delivery."
---


## 交结果之前先落盘（尽力而为，绝不因它阻塞）

输出最后一行 `WORKER_RESULT {json}` 之前，先用**网关侧文件写工具**（不是 `exec`）把**完全相同**的 JSON
写到这个确定路径：

```
/root/clawd-work-commander/state/workflow-runs/<run_id>__<attempt_id>.<stage_id>.<stage_attempt>.worker-result.json
```

这条路径是可写的（0913 实证：preflight 第 3 次正是靠它写成、Commander 读到、阶段才通过）。
偶尔 `file_write` 会失败——那时记一条 warning 就好，见下。

**这份落盘是尽力而为的备份，不是验收条件。**写失败就在 `warnings` 里记一句然后照常返回你真实的
`status` 与 `recommended_next_action`。**任何情况下都不得因为"回执没写成"而把 `status` 改成 `blocked`**——
那会把一次成功的阶段变成失败。它不需要 write-guard、不计入 `business_writes` / `artifact_writes` / 外部交互计数。

## 产出契约（构造 WORKER_RESULT 前逐项自检）

> 本节与 `agentic-workflow-runtime/references/protocol.md` 的「metrics 封闭键集」逐字一致；
> 冲突时以 protocol.md 为准。适用阶段：scoring。

**metrics 必填**（没发生就填 0，禁止自造键名）：通用 4 键 `external_interactions` `business_reads` `business_writes` `artifact_writes`；本阶段另加 `comments_scored` `strong_intent` `weak_intent` `peer` `irrelevant` `spam`。

**真实模式 completed 的最小 evidence**（`evidence` 必须是对象数组，空数组不接受）：
- completed 至少每批次 1 条：`{"type":"scoring_batch","batch":…,"scored":…,"distribution":{…}}`

- 五类分布键**必须全部出现**（哪怕为 0），且五类之和等于 `comments_scored`。
- **先扫全批查重再逐条判**：同一文本被不同账号重复发布（≥2 次）一律判 spam 并在 reason 注明「重复文本」。（深度 eval 实测：62 条里两条一字不差的"评论"来自不同账号，两个模型都各自判了 weak_intent——单条视角看不见跨条刷屏。）

# 社媒评论线索评分

当 `orchestrator=n8n` 时，本 Skill 是一个独立 Agent 节点：不得召唤 Commander、其他 Agent 或下一阶段，只回传相同的执行身份、阶段、幂等键和 `task_request_hash`，由 n8n 验收并推进。`contract_test` 只验证 Skill 与返回合同，不读取业务评论、不回写原始池。

当由 `agentic-workflow-runtime` 调用时，只按 frozen `task_request` 的评分策略执行，结束前返回唯一 `WORKER_RESULT`（`schema_version` 为 2，`status` 只填一个词（`completed` / `blocked` / `failed` 三选一），`recommended_next_action` 只填一个词（`accept` / `retry` / `stop` / `request_approval` 四选一）），逐字回显 Commander 传入的执行身份与 `task_request_hash`，并附每批次的评分分布与证据。哈希缺失或不一致时不得执行。

只读取已完成的 `comment-leads.json`、对应 `comment-batch.json` 和 frozen `task_request`，确认输入 `task_request_hash` 与 Commander 完全一致；缺失或不一致时不得评分。不操作手机，不写最终线索，不对外发送内容。

## 分批评分

- 按采集批次读取，每次最多 100 条评论；数千/数万评论不得一次性放入模型上下文。
- Luna 结合评论原文、视频全文判定、目标人群、搜索关键词和租户意向/排除规则评分。
- 每条都必须产生结论，不只选看起来有价值的评论。

## 分类

| 类型 | 含义 | 合格线索候选 |
| --- | --- | --- |
| `strong_intent` | 明确想学、求链接、询价、报名、询问操作 | 是 |
| `weak_intent` | 对适用性、可靠性、路径有具体兴趣或犹豫 | 是 |
| `peer` | 同行经验、业务推广或招代理，不是需求方 | 否 |
| `irrelevant` | 寒暄、表情、泛夸、娱乐围观或主题无关 | 否 |
| `spam` | 营销引流、机器重复或异常广告 | 否 |
| `review` | 证据不足或语义无法可靠判断 | 否 |

每条输出 `category`、`score_0_100`、`confidence`、`reason`、`audience_match`、`candidate_for_delivery`和原始证据引用。不使用单一关键词命中替代语义判断。

## 输出与回写

每个输入批次生成 `scored-comment-batch.json`，最后合并为 `scored-comments.json`。所有工件和最终唯一 `WORKER_RESULT` 必须带相同 `task_request_hash`。批次结果原位回写租户原始评论池的业务相关性、意向等级、处理状态、AI 理由或排除原因，并回读验证。

写本地工件前申请 `artifact_write`；每批回写原始池前申请 `raw_comment_update`。最终只有所有采集批次均已评分且回读，阶段才能 `completed`。

本 Skill 不做跨视频/跨历史线索去重；确定性去重和最终写入由下一个配送 Skill 完成。
