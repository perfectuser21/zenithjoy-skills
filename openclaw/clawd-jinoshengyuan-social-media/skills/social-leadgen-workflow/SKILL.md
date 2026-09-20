---
name: social-leadgen-workflow
description: "Define the n8n-owned, task-contract-driven social-video lead-generation workflow across five bounded OpenClaw Agent nodes: policy-controlled discovery, full-transcript qualification, round-robin comment collection, Luna lead scoring, and deterministic delivery. Use for recurring or manual social lead collection without embedding tenant IDs or search defaults in Worker Skills."
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
> 冲突时以 protocol.md 为准。适用阶段：（工作流总纲，不直接执行）。

**metrics 必填**（没发生就填 0，禁止自造键名）：通用 4 键 `external_interactions` `business_reads` `business_writes` `artifact_writes`；本阶段另加 各阶段键集见 `agentic-workflow-runtime/references/protocol.md` 的「metrics 封闭键集」，本文不重复定义。

**真实模式 completed 的最小 evidence**（`evidence` 必须是对象数组，空数组不接受）：
- 各阶段最小证据清单见对应阶段 skill 文首的「产出契约」节

- 阶段 skill 与 protocol.md 冲突时，以 protocol.md 为准并停下上报，不得自行取舍。

# 社媒视频获客 Workflow

把一次任务编排为五个可恢复业务阶段，不直接包含公司、账号、设备、表格或平台命令。

这是一个由 n8n 持有唯一流程状态的 Workflow Package。n8n 读取并验证 [workflow-manifest.json](references/workflow-manifest.json)，为每个阶段创建独立 OpenClaw Agent 节点，负责顺序、超时、重试、卡片、Cleanup 和终态。本业务 Agent 只执行一个有界阶段，不得召唤其他 Agent，也不得自行推进 Workflow。`work-commander` 只保留为开放式复杂任务的回退节点，不进入本固定流程主链路。

## 输入合同

开始前由 n8n Intake 读取租户注册表、生成 `tenant_context`，并把用户要求归一化为不可变的 `task_request`。必须包含：

- `tenant_id`、`platform`、`platform_adapter`、`destination_adapter`；
- 当前账号角色和允许动作；
- 目标人群和本次关键词；
- 排序、时间层、时长、范围、位置、视频判定、评论采集、评分和配送策略；
- 目标系统资源标识。

先运行 `node scripts/validate-task-request.mjs <task_request.json>`，再运行 `node scripts/render-task-description.mjs <task_request.json>`。校验或可读描述生成失败时不得创建执行 Attempt。把校验后的 JSON、SHA-256 和可读描述同时写入 Intake 记录及 Workflow 主卡；之后任何阶段只接受相同哈希的合同。

缺少必填值就停止。不得借用默认租户、另一个 Agent、另一台设备或 `main` 的凭据。字段和阶段工件见 [任务合同](references/job-contract.md)。

## 预检与五阶段编排

1. 调用平台适配器做设备、通话、账号和平台锁预检。
2. **视频发现 Agent** 调用 `social-video-discovery`：严格执行 `task_request.search_policy` 的关键词、排序、时间层、时长、范围和位置，返回所有可重开视频链接并去重。
3. **视频判定 Agent** 调用 `social-video-qualifier`：对每个链接调用 `douyin-reference-capture-phone` 取完整 ASR 全文（full 定义：≤5分钟全片、>5分钟前300秒全覆盖，与5分钟封顶一致），由 Luna 校正后只给一次 `qualified/rejected/review` 结论。
4. **评论采集 Agent** 调用 `social-comment-lead-collector`：严格执行 `task_request.comment_policy`；穷尽模式按合同批次公平轮转，Top-N 模式按合同上限停止，每批落原始池并保存游标。
5. **评论评分 Agent** 调用 `social-comment-lead-scorer`：Luna 分批判断强意向、弱意向、同行、无关、广告异常或待复核，原位回写原始池。
6. **配送 Agent** 调用 `social-lead-delivery`：不重新打分，只做确定性视频/评论/人员/跨运行去重，写入合格线索并回读。

每个阶段由 n8n 使用显式 `agent_id` 和 `skill` 调用本租户 Agent 的独立 Session，只读前序工件并输出本阶段结果。n8n 负责状态推进、结构校验、重试和卡片投影；语义判定仍由对应 Agent Skill 完成。终态 Attempt 不可复活；恢复时由 n8n 创建新的 `attempt_id`，只导入已验证的完成阶段。

当执行环境有共享作业目录时，可用 `scripts/workflow-state.mjs` 做业务工件镜像；n8n execution、冻结合同、阶段结果和生命周期事件是跨环境恢复依据：

```text
node scripts/workflow-state.mjs init --job-dir <dir> --job-id <id> --tenant-id <tenant> --platform <platform> --window-start <ISO> --window-end <ISO>
node scripts/workflow-state.mjs show --job-dir <dir>
node scripts/workflow-state.mjs set --job-dir <dir> --stage <stage> --status <status> --note <note>
```

## 合同、搜索与评论窗口

- 用户显式参数优先；租户 `run_policy` 只提供 Intake 默认值，不能覆盖本次 `task_request`。
- 推荐默认是“最多评论、先一周后半年、时长不限、范围不限、位置不限、评论每视频 30 条/轮并穷尽可见窗口”，但只有 Intake 写入后才生效。
- `exhaust_visible_results=true` 时不按视频数量停止，平台实际结果结束或连续无新稳定 ID 才停；为 `false` 时必须有用户给出的明确边界。
- `visible_window_exhaustive` 中批次大小只是轮转颗粒度，不是总采集上限；`top_n` 必须在合同中提供 `per_video_limit`。
- “所有视频”表示平台在该查询和日期窗口内实际展示的全部可见结果；不得声称覆盖平台未展示的内容。

总运行时间和新增线索数默认不设上限。日期窗口、平台穷尽条件、风控和无进展条件决定停止。

## 运行边界

- 默认只读研究和内部写入；禁止点赞、关注、评论、私信、发布或修改账号。
- 设备/平台动作只能由 `platform_adapter` 执行；业务阶段不得直接调用裸设备命令。
- 任何使用前台 App 的阶段都必须取得平台锁。结束、零结果或安全停止后调用适配器清理并验证 App 已退出。
- 验证码、登录挑战、账号或设备不匹配、来电、平台风控、连续截图失败立即安全停止。

## 完成标准

只有五个业务阶段均为 `completed`、各阶段实际参数与 `task_request_hash` 一致、评论满足合同停止条件、原始池和最终线索已回读、日期游标已更新、平台清理已验证，才能汇报完成。汇报冻结的任务描述、各时间层视频、全文合格/不合格、每视频评论轮次与停止状态、评分分布、人员去重、配送和停止原因。
