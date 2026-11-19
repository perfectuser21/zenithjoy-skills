---
name: douyin-leadgen-activity-104-cleanup
description: 归位触达现场并保留未决发送。用于触达收尾、失败后保护订单或接手同一收尾 Activity；不执行整个工作流。
metadata:
  version: 0.6.0
  activity_ref: douyin_lead_outreach.cleanup
  activity_version: 3.4.0
  validation: awaiting-real-run
  support_files: []
  method_role: single-activity
  instruction_dependencies: self-contained
---

# 归位触达现场并保留未决发送

仅执行 `douyin_lead_outreach.cleanup`，业务合同版本 `3.4.0`。本方法自包含，普通任务不以旧Skill、Workflow母说明或Commander会话作为操作前置。

## 合同、执行提案与独立验收

读取本run冻结的完整当前Activity Contract，核对来源、Activity身份、版本与摘要；输入输出、前后条件、DoD及已选公司政策以该合同为准，不从旧specific检查列表另立标准。执行者交付的是执行提案和原始证据，不是验收结论；独立通用Checker读取同一合同并用只读工具核实事实。模型自述、工具verified摘要或退出0不能代替原件，也不能替下一Activity判通过。

预算只引用冻结Activity Contract的 `budget` 与本run原绝对截止：业务受 `run.deadline_ms` 约束，收尾受 `run.cleanup_deadline_ms` 约束，实际可用时间取适用Activity预算和相应绝对截止的更早者。换Activity、恢复或新工具调用不重置剩余时间；不得挪用收尾窗口新增业务。

`agent_recovery` 仅声明方法可选能力，不是本次重试额度。只有本run实际冻结的 `runtime.checker_repair` 明确授权、剩余额度与原截止仍有效时，才按失败原因和证据进行允许的返工；没有该设置不自行增回合。保留原Task/run、动作身份和已成功成果；未知副作用先读回，未知不重做，不能换nonce或generation重放。返工不增加本次批次、评分、录制或发送授权，不重复已成功业务动作。Checker不执行业务写入，也不授予发送权。

## 执行上下文与工具边界

本文件就是本 Activity 的操作方法；不要求加载 Workflow 母 Skill 或旧业务 Skill。Workflow 决定活动顺序，本方法只完成当前输入指定的活动。

- 输入须明确真实 `task_id`、`run_id/run_tag`、`activity_ref`、公司/租户/业务线、公司配置与政策版本、处理范围、业务及收尾截止、实际工具与授权。已有 Task 只读回，不重复建单；缺身份或范围由调用方补齐，不从示例、最新目录或其他租户借值。
- 正式 Workflow 宿主给出的合同原件、方法/源码摘要、绑定、资源 owner 和工具 schema 都要核对；校验失败停止。普通 API 单 Activity 任务使用本任务明确授予、来源和作用域已核的工具，不伪造 Workflow ACK、actor、broker request 或冻结合同，也不因缺正式绑定而擅自切为手工模式。
- 下文是所需能力和已存在的操作名示例，不是新的工具注册或写入授权。用当前真实 schema/已部署签名确定调用；缺少合法单活动工具就报 `tool_unavailable`，不启动整条 Workflow、原 Activity handler 或任意裸 RPC/SQL顶替。保留原运行权限与公司校验。
- 已绑定 child/失败接手只使用该次交接授予的工具和操作。旧 owner/child、连接或原生操作终态不明就保留隔离；不通过新 run、nonce 或 generation 重置次数。`resume` 仅在原宿主明确授予时按原共享额度执行，不能因为读了本 Skill 新增恢复权。返工必须另有本次冻结的 `runtime.checker_repair`，不能由方法声明推断额度。
- 原生调用采用本次工具已验证的执行超时并受当前合同剩余预算约束。工具返回running/session不是失败或已停止，沿同一session等真实返回，不并发重试或换EID；预算不足不启动新动作，未知终态由原owner收尾。
- 副作用保留同一持久动作身份；回执未知先读回，不换 ID 重交。数据与字段写入走已授权业务接口，凭据只经组织凭据工具/1Password取得，放入工具进程，不进正文、参数回显或日志。到业务截止停止新增业务，保留收尾预算。


## 输入与交付

收尾开始只需本run冻结身份、原截止和可读取的执行/资源事实入口；不能以尚未生成的锁回执阻止开始收尾核对。若尚未开工，且通过运行账本、动作记录及资源当前读回独立证明本run没有动作、在途请求、锁或租约，则交付无本run资源的证据，不操作手机、不关闭应用、不领取或释放资源，也不触碰其他 owner。缺回执不等于没有动作；不能证明上述事实或存在未知时，未知保留，不重放、不强清。以下停止、归位和释放步骤仅适用于已确认的本人资源。

- 输入 `Device`：冻结 `serial`及资源读回入口；`lock_holder`按实际存在情况读取，不要求未开工run先有持锁回执。
- 输入 `Run`：`run_tag`。
- 输出 `Device`：`lock_holder`。
- 输出 `Run`：`status`。

公司、task/run、截止、源码及执行权从本次已授权任务上下文读取；正式宿主同时核对原冻结绑定。缺字段保持缺失并报告，不从示例或其他租户补。

## 操作

1. 本Activity独立于102收尾。先核对订单claimed/prepared/sent/unknown及原发送回执；收尾不再次发消息。
2. 仅通过原状态机释放本run尚未prepared、归属和状态明确且可安全回队列的claim；先核当前工具真实签名和原件；当前冻结宿主提供时，使用 `commander_host_tools.invoke` 的 `kind="outreach"`、唯一 `action_name` 与 `args=[JSON.stringify({op:"release"})]`，身份来自冻结context，不自填原单ID。接口缺失不伪造释放；结果未证先读原订单/PG事实，不补发。prepared、已发或结果未知保持原保护，不按TTL或退出码回成待发送。
3. 关闭应用、回安全桌面，精确释放本人设备锁与中央租约，并独立读回；不清除其他owner资源、不恢复/移除不属于自己的暂停标志。
4. 输出真实订单保留情况、设备清理和锁读回。清理完成不能替代发送/写回验收，未决必须进入最终报告。

## 成功条件

未开工且已独立证明无本run动作、在途请求、锁或租约时，以该无资源证明交付收尾结果，不要求产生手机归位或释放回执；其余分支按实际本人资源核验如下条件。

只清理本任务现场，未prepared的本人claim按原状态机释放，prepared/已发/unknown保护保留；设备和租约归位读回，业务未决独立列出。

## 副作用

可能关闭本次应用、回安全桌面、释放本人安全可释放的claim/设备锁/中央租约；不解除未决发送保护，不碰其他owner。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

执行提案中的 `success` 必须有本Activity合同要求的真实产物证据，仍须独立通用Checker验收；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复能力声明

以下 `agent_recovery` 只描述可选能力，不能被解释为本次已选额度。实际是否允许返工及其次数只读本run冻结的 `runtime.checker_repair`；原授权、动作累计次数、未知不重做和绝对截止仍约束所有回合。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
