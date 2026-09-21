---
name: social-lead-outreach
description: "Claim, assign, and privately contact already-delivered social leads using only tenant-approved scripts and distribution accounts, with exact sender/target readback, idempotent write fences, sent-bubble evidence, and lead/claim reconciliation. Use only as the outreach stage after delivery in the V4 Commander canvas."
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

## 调用手机控制器的超时（必读，没有例外）

对 `douyin-phone-adb` 的**每一次** exec 调用都显式设置 `timeout: 300000`（毫秒）。
不要按命令名挑、不要凭"这条看起来很快"估一个值：任何命令都可能要读 UI 树，
而读树内置重试最坏约 180 秒；连 `lock-release` 这种瞬时命令也会因链路排队而超过十几秒。

0912 实证：worker 自行给 `current-video-link` 估了 70000ms、给 `lock-release` 估了 15000ms，
两条都在正确执行的半途被掐断，报成 `gateway timeout`。
整轮 discovery 的第 4 次（也是最后一次）尝试就断送在这里——
筛选已应用、四张相关卡片已识别、详情页已打开，只差取链接这一步。


## 产出契约（构造 WORKER_RESULT 前逐项自检）

> 本节与 `agentic-workflow-runtime/references/protocol.md` 的「metrics 封闭键集」逐字一致；
> 冲突时以 protocol.md 为准。适用阶段：outreach。

**metrics 必填**（没发生就填 0，禁止自造键名）：通用 4 键 `external_interactions` `business_reads` `business_writes` `artifact_writes`；本阶段另加 `contacts_made` `claims_acquired`。

**真实模式 completed 的最小 evidence**（`evidence` 必须是对象数组，空数组不接受）：
- completed 至少每次触达 1 条：`{"type":"outreach","lead":…,"channel":…,"result":…}`

- 触达是不可弥补的对外动作：claim 未取得前一次触达都不许发生，`contacts_made` 必须 ≤ `claims_acquired`。

# 社媒线索触达

本 Skill 只执行 V4 画布声明的 `stage_id=outreach`。不得召唤 Commander、其他 Agent 或下一阶段；不得改写话术；不得点赞、关注、评论、发布或打电话。最终只返回一条 `WORKER_RESULT` JSON。

## 合同测试与关闭态

- `mode=contract_test`：只验证 Skill、冻结合同和必需字段可加载，手机动作、业务读取、业务写入、claim 和外部互动必须全部为 0，然后返回 `completed`。
- `task_request.outreach_policy.enabled=false`：不读取候选、不操作手机、不创建 claim，返回 `completed`，指标全部为 0。
- 其他模式必须同时满足：`delivery_policy.external_outreach=true`、`outreach_policy.enabled=true`、channel 为 `douyin_private_message`、claim_mode 为 `claim_then_send`，并有非空 `approval_id`、`approved_by`、`approved_at` 与 1–20 的 `max_per_run`。任一不符立即 `blocked`。

## 输入与前置验收

1. 逐字符回显 Commander 传入的 run、attempt、execution、object、workflow、worker、lease、stage、stage_attempt、idempotency 和 `task_request_hash`；禁止推导或缩写。
2. 读取本 run 已验收的 delivery 工件，哈希必须等于冻结合同，且只选择 `delivered_leads` 中未触达、发送状态明确为“未发送”、有稳定 `douyin_id` 的记录。只有昵称而无稳定抖音号时不得搜索或发送。
3. 读取当前租户自己的话术库、账号池和 outreach claim 表。禁止借用另一租户、`main` 或历史运行的数据。
4. 话术必须同时满足“启用状态=启用、资质核验=已通过、可发送状态=启用”，正文逐字符使用，不得润色、补充、截断或拼接。
5. 分发账号必须为当前租户、状态正常、角色允许分发、每日上限未耗尽。搜索号不得发送。

## 分配

- 按租户表内权重执行最大余数和相邻批次余数轮换；同一 `execution_id + lead_record_id` 做稳定随机，已分配线索不得重分。
- 多个分发号按剩余容量平衡轮换，话术版本、客服和分发号是三个独立维度。
- 先获得 `final_lead_write` 围栏并写回实验批次、话术 ID/版本、客服、实际分发号、分配序号和审批 ID，随后立即回读。

## Claim 门禁

每条外部消息之前必须先获得 `outreach_claim_write` 围栏，在租户 claim 表按以下唯一键查重并创建 claim：

`tenant_id + douyin_private_message + target_douyin_id`

claim 至少保存 `claim_key`、lead record ID、run/execution、话术 ID、发送账号、状态、claimed_at、approval_id 和 fence receipt。创建后必须回读完全一致，才允许操作手机。

- 已有 `sent`、`unknown` 或其他 run 持有的 claim：不得发送。
- 同一 execution 的 `claimed` 可在未触发发送动作前幂等恢复。
- 点击发送后若不能读回结果，claim 必须记为 `unknown`，绝不自动重发。

## 手机发送

所有动作只通过租户登记的 `platform_adapter` 控制器执行：

1. `account-current <evidence_id>` 读回当前昵称和抖音号。
2. 如不是已分配分发号，调用 `account-switch <sender_douyin_id> <evidence_id>`；必须读回精确目标账号。验证码、登录确认、账号安全设置、实名、支付或风控页立即 `blocked`，不得点“跳过”绕过。
3. 再次确认通话状态 idle、平台锁仍属于本 run。
4. 将已批准话术正文按 UTF-8 标准 base64 编码，只调用一次：

   `private-message-send <sender_douyin_id> <target_douyin_id> <message_b64> <evidence_id>`

   该语义命令必须完成目标抖音号读回、输入框逐字回读、发送前证据、一次发送动作、已发送气泡逐字回读和原输入法恢复。Worker 禁止拆成裸 `tap` 或自行输入。
5. 命令返回 `send_status=sent` 才计入已发送；其他结果按未知发送处理，不重试该对象。

## 发送后对账

- `sent`：先获得 `final_lead_write` 与 `outreach_account_update` 围栏，再把 claim、最终线索发送状态/时间/话术/账号和账号今日已触达数写回并逐项回读。
- `unknown`：只写 claim 与最终线索为“发送结果待人工复核”，不得把账号计数或线索标成成功。
- 每个写入回执必须与当前 Commander event 和 fence token 一致。
- 写入（必须用 OpenClaw 文件写工具，严禁 exec 在节点上写——节点无此路径，见 discovery 同款 0912 实证）`/Users/administrator/openclaw-root/workspaces-root/clawd-work-commander/artifacts/outreach/<execution-safe>_outreach.json` 前获得 `artifact_write`，工件保存所有 claim、分配、发送证据、回写回读与哈希。

## 输出

正式启用触达时，只有至少 1 条消息完成 `claim → 精确账号 → 精确目标 → 精确正文 → sent bubble → 三方回写读回` 才可 `completed`。没有可触达候选、缺稳定抖音号、没有合格话术/账号或全被 claim 去重时返回 `blocked`；可证明的发送前瞬时故障可 `failed` 且 `retryable=true`。发送动作之后的未知结果必须 `blocked`、`retryable=false`。

```json
{
  "type": "WORKER_RESULT",
  "schema_version": 2,
  "run_id": "required",
  "attempt_id": "required",
  "execution_id": "required",
  "task_request_hash": "required SHA-256",
  "stage_id": "outreach",
  "stage_attempt": 1,
  "tenant_id": "required",
  "worker_agent_id": "required",
  "status": "completed",
  "summary": "required",
  "metrics": {
    "external_interactions": 0,
    "business_reads": 0,
    "business_writes": 0,
    "artifact_writes": 0,
    "contacts_made": 0,
    "claims_acquired": 0
  },
  "artifacts": [],
  "evidence": [{"type": "outreach", "lead": "<稳定标识>", "channel": "douyin_private_message", "result": "sent"}],
  "write_fences": [],
  "warnings": [],
  "retryable": false,
  "recommended_next_action": "accept"
}
```
