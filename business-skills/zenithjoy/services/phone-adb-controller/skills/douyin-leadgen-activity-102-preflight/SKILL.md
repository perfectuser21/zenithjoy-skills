---
name: douyin-leadgen-activity-102-preflight
description: 取得采集设备与账号执行上下文。用于采集预检、确认手机账号或接手同一预检 Activity；不执行整个工作流。
metadata:
  change_summary: "对齐当前Activity合同、通用Checker与共享截止；不新增执行授权"
  version: 0.11.1
  primary_execution: agent-v1
  primary_hosts:
    - official-child-v1
  execution_transports:
    - raw-model-v1
  activity_ref: douyin_video_processing.preflight
  activity_version: 2.6.1
  validation: awaiting-real-run
  support_files: []

  method_role: single-activity
  instruction_dependencies: self-contained

---

# 取得采集设备与账号执行上下文

仅执行 `douyin_video_processing.preflight`，使用业务合同版本 `2.6.1`。方法版本变化不修改Activity身份或公司业务政策。本版为说明重写，离线校验不等于实机验收。

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

本预检只交宿主已正式分配并持久化的同一 Run 的 `run_tag/profile/serial`。正式派单与 Run 依据宿主冻结身份及独立 Brain 只读核对，不另创建运行账本；同一 run_tag 读回不是重复创建，不因它已存在而拒绝。核对 Task/run、公司、设备、账号和 owner 的完整绑定，身份冲突则停止，不借其他 Run 或换身份补齐。已持锁时只读回同一身份的既有锁，保留实际 acquire receipt，不重复发起领取或释放副作用；尚未取得资源仍按原授权与原精确协议执行，不以本说明新增权限。

开始条件只核配置、冻结身份与截止：确认本任务的公司/租户、设备与目标账号绑定、工具授权、资源 owner 计划和原绝对截止。登录态和取得锁的回执是执行后产物，不把尚未生成的产物当作开始输入；已有资源则核其真实归属，不接管其他 owner。实际登录、设备状态与本人锁/租约仍须在执行中核实，并以本轮原件交独立通用Checker验收。

输入调用者指定的设备类型（实体/云）、`host/profile/serial`、平台、目标原生账号、已启用公司配置及唯一 verified/enabled 账号绑定；还要有设备租约、本地锁和清理责任的实际工具与 owner 信息。101、102共享本方法，不为101复制一份预检。

交付 `Device.online/call_state/lock_holder`、`Account.logged_in/actual_id`、`Run.run_tag/profile/serial`，以及公司绑定、原生账号证据、锁读回、后续工具范围和唯一清理责任人。每个 true 都须有本轮原件。

## 操作

1. 读回本 Task、公司配置、设备注册和工具来源。公司、租户、line、profile、serial与目标账号须精确对应；按配置的明确启用/授权字段判断，不靠名字或昵称猜。注册表的在线状态不代替实际设备检查。
2. 通过实际只读设备通道检查目标 serial、前台与通话状态。已有 controller 的 `preflight`、`status`、`window` 是能力示例；命令、参数及副作用先核当前 schema。不能把会先探测 ADB 的 `help` 当成纯文本查询；不启动/重启共享ADB、手机、网络或代理。
3. 核中央 serial 租约和本地锁。如果宿主已持有，只读回原 owner，不重复取得或释放；若本任务明确授权直接取得，走现有精确领取协议并读回。被其他 owner 占用、未注册、离线或通话不 idle 时停止。Task记账回写与设备租约分别核验，不能用 queued 或 CLI退出替代真实资源归属。保留宿主返回的本地与中央取得回执，交出工具回执路径、owner、中央租约版本和独立状态读回。手机网关返回的原始路径仅作来源线索，不把它拼接成运行目录下的附件。
4. 持有效授权打开抖音。用本轮新鲜前台、截图、控件树及原生账号读取确认实际抖音号；例如实际工具提供 `open-app`、`account-current EID` 时按其签名调用。账号、公司或设备不符、登录挑战、PIN/验证码、风控时停止，不自行切号或换云/实体设备。
5. 确定后续资源由谁持有、谁收尾。输出真实中央 owner/lease version、本地 owner、资源截止及清理责任；后续 Activity沿用，不把 Task UUID、manual owner、工具 nonce混为同一身份。

## 成功条件

设备实际在线、通话空闲、公司绑定唯一有效、实际原生账号匹配、本人资源授权读回成立、后续操作与清理责任明确。这里只交预检上下文，不搜索、不领视频、不录音、不采评论、不改设备台账镜像状态。

## 副作用

实际副作用限于获授权的设备/账号页面导航、运行取证工件，以及本次明确由本活动领取的设备租约/本地锁。不开搜索、不改账号、不发布；如定位工具需视觉外发，只有当前任务已批准的既有服务可接收必要画面，不新增接收方。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

执行提案中的 `success` 必须有本Activity合同要求的真实产物证据，仍须独立通用Checker验收；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复能力声明

以下 `agent_recovery` 只描述可选能力，不能被解释为本次已选额度。实际是否允许返工及其次数只读本run冻结的 `runtime.checker_repair`；原授权、动作累计次数、未知不重做和绝对截止仍约束所有回合。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
