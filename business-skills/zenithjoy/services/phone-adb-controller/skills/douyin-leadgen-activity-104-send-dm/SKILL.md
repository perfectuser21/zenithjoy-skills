---
name: douyin-leadgen-activity-104-send-dm
description: 交出一次可核验的批准私信发送结果。用于执行已授权单次私信或接手同一触达 Activity；不执行整个工作流。
metadata:
  version: 1.4.1
  activity_ref: douyin_lead_outreach.send_dm
  activity_version: 6.1.1
  validation: awaiting-real-run
  support_files: []
  method_role: single-activity
  instruction_dependencies: self-contained
---

# 交出一次可核验的批准私信发送结果

仅执行 `douyin_lead_outreach.send_dm`，业务合同版本 `6.1.1`。本方法自包含，普通任务不以旧Skill、Workflow母说明或Commander会话作为操作前置。

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

- 输入 `Lead`：`douyin_id`、`profile_url`、`intent_grade`、`repeat_hits`、`status`。
- 输入 `Account`：`profile`、`sender_id`、`dm_paused`、`daily_cap`。
- 输入 `Device`：`serial`、`lock_holder`。
- 输入 `OutreachOrder`：原canonical合格未发送订单、批准话术快照及原资格证据。有界测试另输入 `OutreachScope`：本run冻结的唯一飞书 record_id、原comment_id、公司及来源身份。
- 输入 `RecipientQualification`：原订单关联的公司资格、103 评分存档与原生身份快照。
- 更新 `OutreachOrder`：`lead_record_id`、`douyin_id`、`sender_id`、`script_id`、`message`、`result`。

公司、task/run、截止、源码及执行权从本次已授权任务上下文读取；正式宿主同时核对原冻结绑定。缺字段保持缺失并报告，不从示例或其他租户补。

## 操作

1. 只使用本公司原canonical订单及批准正文。普通 `company_queue` 模式按该公司的现行资格与排序领取最多一单；`LEADGEN_OUTREACH_MODE=exact` 有界测试模式必须从 `LEADGEN_OUTREACH_SCOPE_FILE` 私有文件冻结唯一飞书 record_id 与 comment_id、公司及来源身份，交叉核对原出站映射和订单；仅领取完全匹配的订单，不领取旁单。精确范围缺失、未知、重复或未匹配则拒发，不能以 `limit=1` 或全公司排序首单代替精确范围。核对稳定目标UID/主页、发送账号、模板与准确内容；已知范围内订单确实无合格候选才记empty。
   领取前使用受控宿主读回原订单关联的 103 评分。历史 provider 记录须有其原始响应标识，新 Agent 记录须核对宿主绑定的 scoring 身份、评分输入及答案摘要。两种记录都要匹配同一条原评论和该公司的当前冻结政策。来源或摘要缺失、不符或未知时保持 blocked，保留原单。评分通过后仍要分别核对本次发送授权、发送账号、暂停和额度。
2. 沿订单原生主页链接进入并核对真实目标。深链降为搜索或返回相似账号时重新核对稳定身份，不能按昵称相似发送。
3. 发送前必须由正式状态机确认同一持久动作prepared及独占执行权；保存同一目标、账号、内容哈希和发送前会话证据。没有受控单Activity接口时保持blocked，不用裸controller替代业务prepare。
4. 执行一次真实发送，核对同一会话、准确正文、新气泡增量、前台与风险原件。已存在气泡不算新发，不重复点击。
5. 超时、崩溃、平台限制或写回缺失时先查原动作和原会话。已发只交写回；结果未知保留prepared，不再发送。只证明发出，不推断送达或已读。

6. 工具必须接受同一持久动作身份并在已确认prepare后执行。只使用任务给出的已部署工具签名；工具若只支持旧run救场、没有新任务的安全发送入口，明确报tool_unavailable，不自行构造broker请求或裸发送绕过prepare。

## 成功条件

原订单、公司与来源、批准正文、当前发送账号和原生目标身份一致；prepare明确确认后最多执行一次发送。依据同一会话的新气泡增量及原件区分sent/restricted/rate_limited/unknown；只有满足当前合同成功条件才可提出success，受限不推定已发，unknown不能报发送成功。发出不等于送达或已读。

## 副作用

按原状态机领取原订单、记录prepared及尝试额度；只向本任务已授权的原生目标发送批准正文一次，并保存原始证据。模型/工具回执未知不重复发送。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

执行提案中的 `success` 必须有本Activity合同要求的真实产物证据，仍须独立通用Checker验收；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复能力声明

以下 `agent_recovery` 只描述可选能力，不能被解释为本次已选额度。实际是否允许返工及其次数只读本run冻结的 `runtime.checker_repair`；原授权、动作累计次数、未知不重做和绝对截止仍约束所有回合。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
