---
name: douyin-leadgen-activity-102-cleanup
description: 归位采集现场并释放本人资源。用于采集流程收尾、失败后清理或接手同一收尾 Activity；不执行整个工作流。
metadata:
  change_summary: "0.8.0: 在Activity内整合有效业务步骤，去除母Skill和旧Skill执行依赖，保留原合同与授权边界"
  version: 0.8.0
  primary_execution: agent-v1
  primary_hosts:
    - official-child-v1
  execution_transports:
    - raw-model-v1
  activity_ref: douyin_video_processing.cleanup
  activity_version: 2.3.0
  validation: awaiting-real-run
  support_files: []

  method_role: single-activity
  instruction_dependencies: self-contained

---

# 归位采集现场并释放本人资源

仅执行 `douyin_video_processing.cleanup`，保留业务合同版本 `2.3.0`。方法版本变化不修改Activity身份或公司业务政策。本版为说明重写，离线校验不等于实机验收。当前合同Activity预算上限300秒，执行取本次Activity与Workflow截止的更早值；不挪用清理窗口新增业务。

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

101、102共用本 Activity。输入本run最后已确认状态、成果/异常、实际资源清单及owner、在途原生请求/录制PID、本人视频租约、清理责任分工与截止。输出逐项停止/归位/释放/读回结果、未决资源、最终真实业务状态和恢复条件。

## 操作

1. 先保存真实已提交集合、PG/动作读回及失败原件，保留最早错误。此活动不重跑搜索、录音、资格、采集或评分，不用收尾窗口开新业务。
2. 确认所有本次原生请求和写入的真实终态。只通过当前授权的本人PID/动作身份停止本任务录制或采集，并确认退出；未知、外owner或归属不明的不kill、不清锁。CLI退出或Agent finish不代表原生进程已结束。
3. 已确认执行权、无未知在途操作时，通过现有 `close-app`、`return-safe-desktop` 等能力关闭本次应用、回默认HOME；以窗口包和新鲜截图核桌面，不硬编码某手机launcher，不点用户私人相册素材。
4. 按实际清理责任释放本人视频租约、本地锁、中央serial租约，逐项使用原协议的精确owner和必要的fresh lease_version/CAS并独立读回；不删除锁目录、按TTL推断free、把Task UUID当manual owner或释放另一任务的锁。
5. 如果宿主明确保留最终释放权，只交本人资源原件、已停止/归位证明与剩余owner给宿主；不能自己和宿主双重释放，也不能在尚未读回时写“锁已释放”。设备台账在线/心跳由镜像维护，收尾不手改。
6. owner变化、结果未知、释放失败或超时都按实际保留隔离和恢复条件，不为了下一个Activity硬清。最终报告同时列业务结果与cleanup结果；cleanup成功不把业务failed/partial升级completed。

## 成功条件

所有应由本活动处置的本人进程、应用、租约均有真实终态/读回；明确交宿主的资源另标 `handed_to_owner`，直到宿主free证据才算全资源释放。未决项不隐去、不报全清。

## 副作用

会停止本人的已确认进程、关闭本次应用、回HOME及精确释放本人租约/锁，保存终态工件。不能操作其他owner进程、重启共享服务、清除未知动作或改业务资格/评分。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

`success` 必须满足本活动下文的可观察成功条件；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复声明

以下仅保留原方法的可选恢复能力声明，不授予本次执行额度；只有原run合同明确且合法选定时生效，仍受上文原owner终态、nonce/generation、共享操作次数和原绝对截止约束。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
