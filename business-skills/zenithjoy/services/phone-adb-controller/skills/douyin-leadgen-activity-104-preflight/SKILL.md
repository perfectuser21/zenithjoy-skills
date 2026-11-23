---
name: douyin-leadgen-activity-104-preflight
description: 取得已授权触达上下文。用于触达前核对发送账号、批准政策与资源或接手同一预检 Activity；不执行整个工作流。
metadata:
  version: 1.4.2
  activity_ref: douyin_lead_outreach.preflight
  activity_version: 5.3.2
  validation: awaiting-real-run
  support_files: []
  method_role: single-activity
  instruction_dependencies: self-contained
---

# 取得已授权触达上下文

仅执行 `douyin_lead_outreach.preflight`，业务合同版本 `5.3.2`。本方法自包含，普通任务不以旧Skill、Workflow母说明或Commander会话作为操作前置。

## 合同、执行提案与独立验收

读取本run冻结的完整当前Activity Contract，核对来源、Activity身份、版本与摘要；输入输出、前后条件、DoD及已选公司政策以该合同为准，不从旧specific检查列表另立标准。执行者交付的是执行提案和原始证据，不是验收结论；独立通用Checker读取同一合同并用只读工具核实事实。模型自述、工具verified摘要或退出0不能代替原件，也不能替下一Activity判通过。

预算只引用冻结Activity Contract的 `budget` 与本run原绝对截止：业务受 `run.deadline_ms` 约束，收尾受 `run.cleanup_deadline_ms` 约束，实际可用时间取适用Activity预算和相应绝对截止的更早者。换Activity、恢复或新工具调用不重置剩余时间；不得挪用收尾窗口新增业务。

`agent_recovery` 仅声明方法可选能力，不是本次重试额度。只有本run实际冻结的 `runtime.checker_repair` 明确授权、剩余额度与原截止仍有效时，才按失败原因和证据进行允许的返工；没有该设置不自行增回合。保留原Task/run、动作身份和已成功成果；未知副作用先读回，未知不重做，不能换nonce或generation重放。返工不增加本次批次、评分、录制或发送授权，不重复已成功业务动作。Checker不执行业务写入，也不授予发送权。

## 执行上下文与工具边界

本活动所需的宿主能力以当前合同的 `required_host_tools` 为准，沿用运行器提供的统一工具入口和回执格式。

本文件就是本 Activity 的操作方法；不要求加载 Workflow 母 Skill 或旧业务 Skill。Workflow 决定活动顺序，本方法只完成当前输入指定的活动。

- 输入须明确真实 `task_id`、`run_id/run_tag`、`activity_ref`、公司/租户/业务线、公司配置与政策版本、处理范围、业务及收尾截止、实际工具与授权。已有 Task 只读回，不重复建单；缺身份或范围由调用方补齐，不从示例、最新目录或其他租户借值。
- 正式 Workflow 宿主给出的合同原件、方法/源码摘要、绑定、资源 owner 和工具 schema 都要核对；校验失败停止。普通 API 单 Activity 任务使用本任务明确授予、来源和作用域已核的工具，不伪造 Workflow ACK、actor、broker request 或冻结合同，也不因缺正式绑定而擅自切为手工模式。
- 下文是所需能力和已存在的操作名示例，不是新的工具注册或写入授权。用当前真实 schema/已部署签名确定调用；缺少合法单活动工具就报 `tool_unavailable`，不启动整条 Workflow、原 Activity handler 或任意裸 RPC/SQL顶替。保留原运行权限与公司校验。
- 已绑定 child/失败接手只使用该次交接授予的工具和操作。旧 owner/child、连接或原生操作终态不明就保留隔离；不通过新 run、nonce 或 generation 重置次数。`resume` 仅在原宿主明确授予时按原共享额度执行，不能因为读了本 Skill 新增恢复权。返工必须另有本次冻结的 `runtime.checker_repair`，不能由方法声明推断额度。
- 原生调用采用本次工具已验证的执行超时并受当前合同剩余预算约束。工具返回running/session不是失败或已停止，沿同一session等真实返回，不并发重试或换EID；预算不足不启动新动作，未知终态由原owner收尾。
- 副作用保留同一持久动作身份；回执未知先读回，不换 ID 重交。数据与字段写入走已授权业务接口，凭据只经组织凭据工具/1Password取得，放入工具进程，不进正文、参数回显或日志。到业务截止停止新增业务，保留收尾预算。


## 输入与交付

本预检只交宿主已正式分配并持久化的同一 Run 的 `run_tag/profile/serial`。正式派单与 Run 依据宿主冻结身份及独立 Brain 只读核对，不另创建运行账本；同一 run_tag 读回不是重复创建，不因它已存在而拒绝。核对 Task/run、公司、设备、账号和 owner 的完整绑定，身份冲突则停止，不借其他 Run 或换身份补齐。已持锁时只读回同一身份的既有锁，保留实际 acquire receipt，不重复发起领取或释放副作用；尚未取得资源仍按原授权与原精确协议执行，不以本说明新增权限。

开始条件只核配置、冻结身份与截止：确认本任务的公司/租户、设备与目标账号绑定、工具授权、资源 owner 计划和原绝对截止。登录态和取得锁的回执是执行后产物，不把尚未生成的产物当作开始输入；已有资源则核其真实归属，不接管其他 owner。实际登录、设备状态与本人锁/租约仍须在执行中核实，并以本轮原件交独立通用Checker验收。

- 输入 `Device`：`serial`、`host`及冻结的资源授权/owner 计划；已有 `lock_holder` 时提供真实归属，未取得锁不伪造持锁回执。
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

按当前合同的 `delivery` 交件：业务值写入 `outputs`，把工具实际返回、可独立读回的原件相对路径放入 `handoff`，按本轮或对象标识和证据用途归组。较大的媒体交带原件摘要的回执，由原媒体读回工具复核。旧文中的证据要求由这些实际引用满足。

宿主按冻结的 `delivery.report` 归档本轮适用的原始回执供 Checker 一次读取。交付中保留原路径，不补造未发生分支的原件。

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

执行提案中的 `success` 必须有本Activity合同要求的真实产物证据，仍须独立通用Checker验收；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复能力声明

以下 `agent_recovery` 只描述可选能力，不能被解释为本次已选额度。实际是否允许返工及其次数只读本run冻结的 `runtime.checker_repair`；原授权、动作累计次数、未知不重做和绝对截止仍约束所有回合。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
