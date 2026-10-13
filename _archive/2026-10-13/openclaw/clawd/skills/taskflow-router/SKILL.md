---
name: "taskflow-router"
description: "统一消息分类、任务落表、进度卡片、审批按钮与任务闭环"
---

# Unified task flow

Run first for every inbound user message. One Skill owns classification, tracking, cards, approvals, and task lifecycle.

## Classify
Choose exactly one:
- TASK: concrete action, deliverable, research output, system/file change, monitoring, scheduling, or reusable workflow/Skill change.
- QUESTION: knowledge, explanation, capability, or status with no new action.
- CHAT: greeting, acknowledgement, opinion, or casual discussion.
- FOLLOW_UP: correction, approval, rejection, pause, or additional information for an existing task.
- AMBIGUOUS: intent cannot be determined safely.

`记任务：` and `/task` always mean TASK.

## Route
- QUESTION or CHAT: answer normally. Do not write Bitable or send a task card.
- AMBIGUOUS: ask one short clarification. Create nothing until confirmed.
- FOLLOW_UP: update and continue the existing task. Never create a duplicate.
- TASK: create one Bitable record, send one progress card, then execute.

## Task resources
- app_token: Z1oobsDYbaUpcFsTjwWcx8Bmnge
- table_id: tblC4iLYFTFZ4sL0
- Core fields: 任务名称、状态、负责人 (Person )、结果、完成时间、指定机器、指定模型。
- Tracking fields: 任务ID、进度、当前步骤、开始时间、预计完成时间、最后更新时间、阻塞原因、卡片消息ID。
- Approval fields: 审批状态、待批准操作、审批人、审批时间。

## Start a TASK
1. Create the row immediately; generate `TF-YYYYMMDD-短标识`.
2. Set status 进行中, real progress, current step, timestamps, owner, machine/model when specified.
3. Send one Feishu task card and store messageId.
4. Break work into weighted milestones. Default: analysis20%, execution50%, verification20%, delivery10%.
5. Update the same row and card at milestones; tasks over5 minutes update every2–3 minutes when state changes.

## Approval gate
Use when an action needs user authorization, including applying Skill proposals, destructive operations, external/public sends, privilege changes, spending, or scope expansion.

1. Pause before the action. Do not perform it.
2. Set status 待处理; write 当前步骤=等待批准, 审批状态=等待批准, 待批准操作=an exact scoped action, and 阻塞原因.
3. Send a Feishu warning card with:
   - exact action and target
   - impact/risk
   - one-shot buttons “同意放行” and “拒绝”
   - fallback text command
4. Button commands must include task ID and exact decision, for example `批准任务 TF-...：应用提案 <id>` and `拒绝任务 TF-...：应用提案 <id>`.
5. Treat a matching card click or equivalent typed message from the task owner as explicit authorization only for that stated action.
6. On approve: write 审批状态=已批准, 审批人, 审批时间; update card; resume.
7. On reject: write 审批状态=已拒绝, approver/time; update card; skip the action and finish or replan.
8. Ignore mismatched, expired, duplicate, wrong-user, or wrong-task callbacks. Never broaden approval.

## Progress card
Display name, taskID, status, percentage, current step, estimate, last update, blocker, and approval state. Keep one main task card. Approval prompts may be a dedicated interactive card linked to the same task. Update existing cards rather than spamming.

## Finish
- Success: progress100, status已完成, result, completion time, green card.
- Failure: preserve real progress, write error and recovery, red card.
- Waiting: progress unchanged, warning card and blocker.

## OPC card callback

If an inbound message starts with `OPC_CALLBACK `, read the JSON object and invoke `opc-card-callback-router` before normal TASK/QUESTION classification. The action is scoped to the supplied `workflow_run_id`, `object_id`, and `step_run_id`; never create a new task merely because a card button was clicked. Use the Card Registry to find the source message and update the existing card whenever possible. Duplicate or unknown callbacks must be acknowledged with the current state and must not create duplicate cards.
