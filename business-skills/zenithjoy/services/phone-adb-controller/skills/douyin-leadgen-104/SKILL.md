---
name: douyin-leadgen-104
description: Workflow 104的活动组织与交接目录；实际执行由各Activity自己的Skill完成，不作为单Activity操作方法。
metadata:
  change_summary: "0.9.3: 说明104对原订单两种评分存档的读回"
  version: 0.9.3
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/douyin-leadgen-104/references/activity-methods.json

  document_role: workflow-index

---

# Workflow 104 · 线索触达与写回

`douyin_lead_outreach` 是 Workflow，独立消费本公司资格合格、外部配送已确认且未发送的原订单队列；沿订单读取已提交的103评分来源，无需启动或等待整批103。发送仍以本次任务已有明确授权为前提。

## 合同、执行提案与独立验收

读取本run冻结的完整当前Activity Contract，核对来源、Activity身份、版本与摘要；输入输出、前后条件、DoD及已选公司政策以该合同为准，不从旧specific检查列表另立标准。执行者交付的是执行提案和原始证据，不是验收结论；独立通用Checker读取同一合同并用只读工具核实事实。模型自述、工具verified摘要或退出0不能代替原件，也不能替下一Activity判通过。

预算只引用冻结Activity Contract的 `budget` 与本run原绝对截止：业务受 `run.deadline_ms` 约束，收尾受 `run.cleanup_deadline_ms` 约束，实际可用时间取适用Activity预算和相应绝对截止的更早者。换Activity、恢复或新工具调用不重置剩余时间；不得挪用收尾窗口新增业务。

`agent_recovery` 仅声明方法可选能力，不是本次重试额度。只有本run实际冻结的 `runtime.checker_repair` 明确授权、剩余额度与原截止仍有效时，才按失败原因和证据进行允许的返工；没有该设置不自行增回合。保留原Task/run、动作身份和已成功成果；未知副作用先读回，未知不重做，不能换nonce或generation重放。返工不增加本次批次、评分、录制或发送授权，不重复已成功业务动作。Checker不执行业务写入，也不授予发送权。

## 活动组织

`preflight → send_dm → write_back → cleanup`

| Activity | 唯一操作Skill | 方法版本 |
|---|---|---|
| `preflight` | [douyin-leadgen-activity-104-preflight](../douyin-leadgen-activity-104-preflight/SKILL.md) | `1.4.0` |
| `send_dm` | [douyin-leadgen-activity-104-send-dm](../douyin-leadgen-activity-104-send-dm/SKILL.md) | `1.4.1` |
| `write_back` | [douyin-leadgen-activity-104-write-back](../douyin-leadgen-activity-104-write-back/SKILL.md) | `1.2.0` |
| `cleanup` | [douyin-leadgen-activity-104-cleanup](../douyin-leadgen-activity-104-cleanup/SKILL.md) | `0.7.0` |

机器引用真身为[Activity方法清单](references/activity-methods.json)。每个Activity使用自己的完整方法；只消费前驱持久结果，不要求回读本目录或旧手册。

## 输入与交接

- 调用者提供真实Task/run、公司/租户/line、公司政策与批准话术、实际发送账号/profile/serial、目标范围、数量、截止及各Activity已授权工具。沿用会话已有授权，不自行扩大目标、内容或次数。
- 104异步消费合格订单，按原订单核验历史 provider 或受权 Agent 的评分存档。本次触达另核正文、权限与额度。来源、资格、配送、发送分别记账；空队列记skipped，未决不记成功。
- send_dm保持原canonical claim→prepared→一次发送协议；同一目标、账号和批准正文绑定同一持久动作。未知结果只读回，不换run/ID重复发送；已发未写回只补write_back。
- 每个Activity交出原订单身份、真实结果、证据与持久读回。cleanup保留prepared/已发/unknown保护，不能把归位完成当发送完成。

## 实现与状态

Workflow Skill只组织活动。实际执行使用各Activity方法和本次明确授予的已部署工具；没有安全领单/prepare/发送/写回接口时报告具体缺口，不凭手册构造工具或绕防重复状态机。

正式冻结宿主使用其原合同、绑定、工具和资源权限；普通API任务使用当前任务明确的工具。旧宿主兼容资料不作为新任务执行依赖。本次整理方法与分发，不表示已安装后台调度或完成实体手机发送验收。

## 宿主恢复能力声明

以下 `agent_recovery` 只描述可选能力，不能被解释为本次已选额度。实际是否允许返工及其次数只读本run冻结的 `runtime.checker_repair`；原授权、动作累计次数、未知不重做和绝对截止仍约束所有回合。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
