---
name: douyin-leadgen-104
description: Workflow 104的活动组织与交接目录；实际执行由各Activity自己的Skill完成，不作为单Activity操作方法。
metadata:
  change_summary: "0.8.0: Workflow薄目录与四个自包含Activity，移除旧Skill relay"
  version: 0.8.0
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/douyin-leadgen-104/references/activity-methods.json

  document_role: workflow-index

---

# Workflow 104 · 线索触达与写回

`douyin_lead_outreach` 是 Workflow，独立消费本公司资格合格、外部配送已确认且未发送的原订单队列；不要求103运行号，不等待整批103。发送仍以本次任务已有明确授权为前提。

## 活动组织

`preflight → send_dm → write_back → cleanup`

| Activity | 唯一操作Skill | 方法版本 |
|---|---|---|
| `preflight` | [douyin-leadgen-activity-104-preflight](../douyin-leadgen-activity-104-preflight/SKILL.md) | `1.1.0` |
| `send_dm` | [douyin-leadgen-activity-104-send-dm](../douyin-leadgen-activity-104-send-dm/SKILL.md) | `1.3.0` |
| `write_back` | [douyin-leadgen-activity-104-write-back](../douyin-leadgen-activity-104-write-back/SKILL.md) | `1.1.0` |
| `cleanup` | [douyin-leadgen-activity-104-cleanup](../douyin-leadgen-activity-104-cleanup/SKILL.md) | `0.4.0` |

机器引用真身为[Activity方法清单](references/activity-methods.json)。每个Activity使用自己的完整方法；只消费前驱持久结果，不要求回读本目录或旧手册。

## 输入与交接

- 调用者提供真实Task/run、公司/租户/line、公司政策与批准话术、实际发送账号/profile/serial、目标范围、数量、截止及各Activity已授权工具。沿用会话已有授权，不自行扩大目标、内容或次数。
- 104异步消费合格订单，不由103标记成功自动推定发送授权。来源、资格、配送、发送分别记账；空队列记skipped，未决不记成功。
- send_dm保持原canonical claim→prepared→一次发送协议；同一目标、账号和批准正文绑定同一持久动作。未知结果只读回，不换run/ID重复发送；已发未写回只补write_back。
- 每个Activity交出原订单身份、真实结果、证据与持久读回。cleanup保留prepared/已发/unknown保护，不能把归位完成当发送完成。

## 实现与状态

Workflow Skill只组织活动。实际执行使用各Activity方法和本次明确授予的已部署工具；没有安全领单/prepare/发送/写回接口时报告具体缺口，不凭手册构造工具或绕防重复状态机。

正式冻结宿主使用其原合同、绑定、工具和资源权限；普通API任务使用当前任务明确的工具。旧宿主兼容资料不作为新任务执行依赖。本次整理方法与分发，不表示已安装后台调度或完成实体手机发送验收。

## 历史宿主兼容声明

以下仅保留原冻结解析字段，不增加本次恢复回合或发送次数。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
