---
name: douyin-leadgen-activity-102-cleanup
description: 归位采集现场并释放本人资源。用于采集流程收尾、失败后清理或接手同一收尾 Activity；不执行整个工作流。
metadata:
  change_summary: "对齐当前Activity合同、通用Checker与共享截止；不新增执行授权"
  version: 0.11.0
  primary_execution: agent-v1
  primary_hosts:
    - official-child-v1
  execution_transports:
    - raw-model-v1
  activity_ref: douyin_video_processing.cleanup
  activity_version: 2.6.0
  validation: awaiting-real-run
  support_files: []

  method_role: single-activity
  instruction_dependencies: self-contained

---

# 归位采集现场并释放本人资源

仅执行 `douyin_video_processing.cleanup`，使用业务合同版本 `2.6.0`。方法版本变化不修改Activity身份或公司业务政策。本版为说明重写，离线校验不等于实机验收。

## 合同、执行提案与独立验收

读取本run冻结的完整当前Activity Contract，核对来源、Activity身份、版本与摘要；输入输出、前后条件、DoD及已选公司政策以该合同为准，不从旧specific检查列表另立标准。执行者交付的是执行提案和原始证据，不是验收结论；独立通用Checker读取同一合同并用只读工具核实事实。模型自述、工具verified摘要或退出0不能代替原件，也不能替下一Activity判通过。

预算只引用冻结Activity Contract的 `budget` 与本run原绝对截止：业务受 `run.deadline_ms` 约束，收尾受 `run.cleanup_deadline_ms` 约束，实际可用时间取适用Activity预算和相应绝对截止的更早者。换Activity、恢复或新工具调用不重置剩余时间；不得挪用收尾窗口新增业务。

`agent_recovery` 仅声明方法可选能力，不是本次重试额度。只有本run实际冻结的 `runtime.checker_repair` 明确授权、剩余额度与原截止仍有效时，才按失败原因和证据进行允许的返工；没有该设置不自行增回合。保留原Task/run、动作身份和已成功成果；未知副作用先读回，未知不重做，不能换nonce或generation重放。返工不增加本次批次、评分、录制或发送授权，不重复已成功业务动作。Checker不执行业务写入，也不授予发送权。

## 执行上下文与工具边界

本文件就是本 Activity 的操作方法；不要求加载 Workflow 母 Skill 或旧业务 Skill。Workflow 决定活动顺序，本方法只完成当前输入指定的活动。

- 输入须明确真实 `task_id`、`run_id/run_tag`、`activity_ref`、公司/租户/业务线、公司配置与政策版本、处理范围、业务及收尾截止、实际工具与授权。已有 Task 只读回，不重复建单；缺身份或范围由调用方补齐，不从示例、最新目录或其他租户借值。
- 正式 Workflow 宿主给出的合同原件、方法/源码摘要、绑定、资源 owner 和工具 schema 都要核对；校验失败停止。普通 API 单 Activity 任务使用本任务明确授予、来源和作用域已核的工具，不伪造 Workflow ACK、actor、broker request 或冻结合同，也不因缺正式绑定而擅自切为手工模式。
- 下文是所需能力和已存在的操作名示例，不是新的工具注册或写入授权。用当前真实 schema/已部署签名确定调用；缺少合法单活动工具就报 `tool_unavailable`，不启动整条 Workflow、原 Activity handler 或任意裸 RPC/SQL顶替。保留原运行权限与公司校验。
- `execution_transport=raw-model-v1` 时不运行 shell、SSH、插件或子会话，只输出宿主 schema 的一个意图：`inspect`、`phone`、`business` 或 `finish`；`phone` 使用 `command,args`，`business` 使用 `operation,input`。不夹带最终 status/result。`finish` 只停止提意图，业务结果由独立通用Checker依据当前合同和宿主原始证据核验。
- 已绑定 child/失败接手只使用该次交接授予的工具和操作。旧 owner/child、连接或原生操作终态不明就保留隔离；不通过新 run、nonce 或 generation 重置次数。`resume` 仅在原宿主明确授予时按原共享额度执行，不能因为读了本 Skill 新增恢复权。返工必须另有本次冻结的 `runtime.checker_repair`，不能由方法声明推断额度。
- 原生调用采用本次工具已验证的执行超时并受当前合同剩余预算约束。工具返回running/session不是失败或已停止，沿同一session等真实返回，不并发重试或换EID；预算不足不启动新动作，未知终态由原owner收尾。
- 副作用保留同一持久动作身份；回执未知先读回，不换 ID 重交。数据与字段写入走已授权业务接口，凭据只经组织凭据工具/1Password取得，放入工具进程，不进正文、参数回显或日志。到业务截止停止新增业务，保留收尾预算。

## 输入与交付

本 Activity 只交本轮收尾阶段状态，以及本run动作、锁和业务租约的可核验证据；`Run.status` 在此表示收尾阶段的交付状态，不是整条 Workflow 已结束。Workflow 真正终态只能在收尾通过后由宿主生成，不要求先读到尚未生成的 Workflow 终态才允许通过本 Activity。已无本轮动作时须引用可核验账本和锁/租约原件，不能只凭自述；未知仍保留本人资源、未决状态及原发送依据，不强清、不重放。

收尾开始只需本run冻结身份、原截止和可读取的执行/资源事实入口；不能以尚未生成的锁回执阻止开始收尾核对。若尚未开工，且通过运行账本、动作记录及资源当前读回独立证明本run没有动作、在途请求、锁或租约，则交付无本run资源的证据，不操作手机、不关闭应用、不领取或释放资源，也不触碰其他 owner。缺回执不等于没有动作；不能证明上述事实或存在未知时，未知保留，不重放、不强清。以下停止、归位和释放步骤仅适用于已确认的本人资源。

101、102共用本 Activity。输入本run最后已确认状态、成果/异常、实际资源清单及owner、在途原生请求/录制PID、本人视频租约、清理责任分工与截止。输出逐项停止/归位/释放/读回结果、未决资源、当前已知业务结果和恢复条件。

## 操作

1. 先保存真实已提交集合、PG/动作读回及失败原件，保留最早错误。此活动不重跑搜索、录音、资格、采集或评分，不用收尾窗口开新业务。
2. 确认所有本次原生请求和写入的真实终态。只通过当前授权的本人PID/动作身份停止本任务录制或采集，并确认退出；未知、外owner或归属不明的不kill、不清锁。CLI退出或Agent finish不代表原生进程已结束。
3. 已确认执行权、无未知在途操作时，通过现有 `close-app`、`return-safe-desktop` 等能力关闭本次应用、回默认HOME；以窗口包和新鲜截图核桌面，不硬编码某手机launcher，不点用户私人相册素材。
4. 按实际清理责任释放本人视频租约、本地锁、中央serial租约，逐项使用原协议的精确owner和必要的fresh lease_version/CAS并独立读回；不删除锁目录、按TTL推断free、把Task UUID当manual owner或释放另一任务的锁。
5. 如果宿主明确保留最终释放权，只交本人资源原件、已停止/归位证明与剩余owner给宿主；不能自己和宿主双重释放，也不能在尚未读回时写“锁已释放”。设备台账在线/心跳由镜像维护，收尾不手改。
6. owner变化、结果未知、释放失败或超时都按实际保留隔离和恢复条件，不为了下一个Activity硬清。最终报告同时列业务结果与cleanup结果；cleanup成功不把业务failed/partial升级completed。

## 成功条件

未开工且已独立证明无本run动作、在途请求、锁或租约时，以该无资源证明交付收尾结果，不要求产生手机归位或释放回执；其余分支按实际本人资源核验如下条件。

所有应由本活动处置的本人进程、应用、租约均有真实终态/读回；明确交宿主的资源另标 `handed_to_owner`，直到宿主free证据才算全资源释放。未决项不隐去、不报全清。

## 副作用

会停止本人的已确认进程、关闭本次应用、回HOME及精确释放本人租约/锁，保存终态工件。不能操作其他owner进程、重启共享服务、清除未知动作或改业务资格/评分。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

执行提案中的 `success` 必须有本Activity合同要求的真实产物证据，仍须独立通用Checker验收；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复能力声明

以下 `agent_recovery` 只描述可选能力，不能被解释为本次已选额度。实际是否允许返工及其次数只读本run冻结的 `runtime.checker_repair`；原授权、动作累计次数、未知不重做和绝对截止仍约束所有回合。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
