---
name: douyin-leadgen-activity-102-preflight
description: 取得采集设备与账号执行上下文。用于采集预检、确认手机账号或接手同一预检 Activity；不执行整个工作流。
metadata:
  change_summary: "0.8.0: 在Activity内整合有效业务步骤，去除母Skill和旧Skill执行依赖，保留原合同与授权边界"
  version: 0.8.0
  primary_execution: agent-v1
  primary_hosts:
    - official-child-v1
  execution_transports:
    - raw-model-v1
  activity_ref: douyin_video_processing.preflight
  activity_version: 2.3.0
  validation: awaiting-real-run
  support_files: []

  method_role: single-activity
  instruction_dependencies: self-contained

---

# 取得采集设备与账号执行上下文

仅执行 `douyin_video_processing.preflight`，保留业务合同版本 `2.3.0`。方法版本变化不修改Activity身份或公司业务政策。本版为说明重写，离线校验不等于实机验收。当前合同Activity预算上限600秒，执行取本次Activity与Workflow截止的更早值，并保留原owner归还、停止和验收窗口；不能延长旧run。

## 执行上下文与工具边界

本文件就是本 Activity 的操作方法；不要求加载 Workflow 母 Skill 或旧业务 Skill。Workflow 决定活动顺序，本方法只完成当前输入指定的活动。

- 输入须明确真实 `task_id`、`run_id/run_tag`、`activity_ref`、公司/租户/业务线、公司配置与政策版本、处理范围、业务及收尾截止、实际工具与授权。已有 Task 只读回，不重复建单；缺身份或范围由调用方补齐，不从示例、最新目录或其他租户借值。
- 正式 Workflow 宿主给出的合同原件、方法/源码摘要、绑定、资源 owner 和工具 schema 都要核对；校验失败停止。普通 API 单 Activity 任务使用本任务明确授予、来源和作用域已核的工具，不伪造 Workflow ACK、actor、broker request 或冻结合同，也不因缺正式绑定而擅自切为手工模式。
- 下文是所需能力和已存在的操作名示例，不是新的工具注册或写入授权。用当前真实 schema/已部署签名确定调用；缺少合法单活动工具就报 `tool_unavailable`，不启动整条 Workflow、原 Activity handler 或任意裸 RPC/SQL顶替。保留原运行权限与公司校验。
- `execution_transport=raw-model-v1` 时不运行 shell、SSH、插件或子会话，只输出宿主 schema 的一个意图：`inspect`、`phone`、`business` 或 `finish`；`phone` 使用 `command,args`，`business` 使用 `operation,input`。不夹带最终 status/result。`finish` 只停止提意图，业务结果由宿主工具记录与独立读回确定。
- 已绑定 child/失败接手只使用该次交接授予的工具和操作。旧 owner/child、连接或原生操作终态不明就保留隔离；不通过新 run、nonce 或 generation 重置次数。`resume` 仅在原宿主明确授予时按原共享额度执行，不能因为读了本 Skill 新增恢复权。显式额外回合策略仍只接受原合同唯一键 `max_additional_turns=1`；默认无额外回合，raw 回合原冻结上限仍为 1～64，不增加原预算。
- 原生调用采用已验证的执行超时并受当前剩余预算约束；旧controller可能需要300000ms。工具返回running/session不是失败或已停止，沿同一session等真实返回，不并发重试或换EID；预算不足不启动新动作，未知终态由原owner收尾。
- 副作用保留同一持久动作身份；回执未知先读回，不换 ID 重交。数据与字段写入走已授权业务接口，凭据只经组织凭据工具/1Password取得，放入工具进程，不进正文、参数回显或日志。到业务截止停止新增业务，保留收尾预算。

## 输入与交付

输入调用者指定的设备类型（实体/云）、`host/profile/serial`、平台、目标原生账号、已启用公司配置及唯一 verified/enabled 账号绑定；还要有设备租约、本地锁和清理责任的实际工具与 owner 信息。101、102共享本方法，不为101复制一份预检。

交付 `Device.online/call_state/lock_holder`、`Account.logged_in/actual_id`、`Run.run_tag/profile/serial`，以及公司绑定、原生账号证据、锁读回、后续工具范围和唯一清理责任人。每个 true 都须有本轮原件。

## 操作

1. 读回本 Task、公司配置、设备注册和工具来源。公司、租户、line、profile、serial与目标账号须精确对应；按配置的明确启用/授权字段判断，不靠名字或昵称猜。注册表的在线状态不代替实际设备检查。
2. 通过实际只读设备通道检查目标 serial、前台与通话状态。已有 controller 的 `preflight`、`status`、`window` 是能力示例；命令、参数及副作用先核当前 schema。不能把会先探测 ADB 的 `help` 当成纯文本查询；不启动/重启共享ADB、手机、网络或代理。
3. 核中央 serial 租约和本地锁。如果宿主已持有，只读回原 owner，不重复取得或释放；若本任务明确授权直接取得，走现有精确领取协议并读回。被其他 owner 占用、未注册、离线或通话不 idle 时停止。Task记账回写与设备租约分别核验，不能用 queued 或 CLI退出替代真实资源归属。
4. 持有效授权打开抖音。用本轮新鲜前台、截图、控件树及原生账号读取确认实际抖音号；例如实际工具提供 `open-app`、`account-current EID` 时按其签名调用。账号、公司或设备不符、登录挑战、PIN/验证码、风控时停止，不自行切号或换云/实体设备。
5. 确定后续资源由谁持有、谁收尾。输出真实中央 owner/lease version、本地 owner、资源截止及清理责任；后续 Activity沿用，不把 Task UUID、manual owner、工具 nonce混为同一身份。

## 成功条件

设备实际在线、通话空闲、公司绑定唯一有效、实际原生账号匹配、本人资源授权读回成立、后续操作与清理责任明确。这里只交预检上下文，不搜索、不领视频、不录音、不采评论、不改设备台账镜像状态。

## 副作用

实际副作用限于获授权的设备/账号页面导航、运行取证工件，以及本次明确由本活动领取的设备租约/本地锁。不开搜索、不改账号、不发布；如定位工具需视觉外发，只有当前任务已批准的既有服务可接收必要画面，不新增接收方。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

`success` 必须满足本活动下文的可观察成功条件；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复声明

以下仅保留原方法的可选恢复能力声明，不授予本次执行额度；只有原run合同明确且合法选定时生效，仍受上文原owner终态、nonce/generation、共享操作次数和原绝对截止约束。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
