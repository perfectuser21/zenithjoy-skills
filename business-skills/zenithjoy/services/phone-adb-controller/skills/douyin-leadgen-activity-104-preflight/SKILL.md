---
name: douyin-leadgen-activity-104-preflight
description: 取得已授权触达上下文。用于触达前核对发送账号、批准政策与资源或接手同一预检 Activity；不执行整个工作流。
metadata:
  version: 1.1.0
  activity_ref: douyin_lead_outreach.preflight
  activity_version: 5.0.1
  validation: awaiting-real-run
  support_files: []
  method_role: single-activity
  instruction_dependencies: self-contained
---

# 取得已授权触达上下文

仅执行 `douyin_lead_outreach.preflight`，业务合同版本 `5.0.1`。本方法自包含，普通任务不以旧Skill、Workflow母说明或Commander会话作为操作前置。

## 执行上下文与工具边界

本文件就是本 Activity 的操作方法；不要求加载 Workflow 母 Skill 或旧业务 Skill。Workflow 决定活动顺序，本方法只完成当前输入指定的活动。

- 输入须明确真实 `task_id`、`run_id/run_tag`、`activity_ref`、公司/租户/业务线、公司配置与政策版本、处理范围、业务及收尾截止、实际工具与授权。已有 Task 只读回，不重复建单；缺身份或范围由调用方补齐，不从示例、最新目录或其他租户借值。
- 正式 Workflow 宿主给出的合同原件、方法/源码摘要、绑定、资源 owner 和工具 schema 都要核对；校验失败停止。普通 API 单 Activity 任务使用本任务明确授予、来源和作用域已核的工具，不伪造 Workflow ACK、actor、broker request 或冻结合同，也不因缺正式绑定而擅自切为手工模式。
- 下文是所需能力和已存在的操作名示例，不是新的工具注册或写入授权。用当前真实 schema/已部署签名确定调用；缺少合法单活动工具就报 `tool_unavailable`，不启动整条 Workflow、原 Activity handler 或任意裸 RPC/SQL顶替。保留原运行权限与公司校验。
- 已绑定 child/失败接手只使用该次交接授予的工具和操作。旧 owner/child、连接或原生操作终态不明就保留隔离；不通过新 run、nonce 或 generation 重置次数。`resume` 仅在原宿主明确授予时按原共享额度执行，不能因为读了本 Skill 新增恢复权。显式额外回合策略仍只接受原合同唯一键 `max_additional_turns=1`；默认无额外回合，raw 回合原冻结上限仍为 1～64，不增加原预算。
- 原生调用采用已验证的执行超时并受当前剩余预算约束；旧controller可能需要300000ms。工具返回running/session不是失败或已停止，沿同一session等真实返回，不并发重试或换EID；预算不足不启动新动作，未知终态由原owner收尾。
- 副作用保留同一持久动作身份；回执未知先读回，不换 ID 重交。数据与字段写入走已授权业务接口，凭据只经组织凭据工具/1Password取得，放入工具进程，不进正文、参数回显或日志。到业务截止停止新增业务，保留收尾预算。


## 输入与交付

- 输入 `Device`：`serial`、`host`、`lock_holder`。
- 输入 `Account`：`platform`、`profile`、`sender_id`、`dm_paused`、`daily_cap`。
- 输出 `Device`：`online`、`call_state`、`lock_holder`。
- 输出 `Account`：`logged_in`。
- 输出 `Run`：`run_tag`、`profile`、`serial`。

公司、task/run、截止、源码及执行权从本次已授权任务上下文读取；正式宿主同时核对原冻结绑定。缺字段保持缺失并报告，不从示例或其他租户补。

## 操作

1. 本Activity独立于102预检。读取本公司已启用104配置、当前发送账号/profile/serial、批准话术、目标范围和当前限额，缺项不能从其他公司补。
2. 正式宿主核对实际部署release和原运行绑定；普通API任务核本任务已授权工具的真实来源与作用域，不补造正式绑定。两者均核发送授权、真实登录账号、设备空闲及双层锁owner；已有本会话授权持续有效，不重复索要。
3. 核对现行暂停、冷却、风险与额度。Skill不绕过暂停或换账号绕风控；已授权迁移暂停也只能走精确hash/owner可回读恢复步骤。
4. 预检只核本轮授权、公司账号、原政策与批准话术，不创建或领取canonical订单；原动作结果未知先读回，不点击发送、不自动清除prepared。

## 成功条件

公司104已启用、发送授权有效、实际账号/profile/serial一致、设备与通话空闲、本人租约和锁及暂停/额度均可读回；只交授权上下文，不领单、不发送。

## 副作用

读取公司政策、账号、设备与订单历史；取得本任务设备锁和中央租约。不领单、不准备发送、不发消息。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

`success` 必须满足本活动下文的可观察成功条件；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复声明

以下仅保留原方法的可选恢复能力声明，不授予本次执行额度；只有原run合同明确且合法选定时生效，仍受上文原owner终态、nonce/generation、共享操作次数和原绝对截止约束。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
