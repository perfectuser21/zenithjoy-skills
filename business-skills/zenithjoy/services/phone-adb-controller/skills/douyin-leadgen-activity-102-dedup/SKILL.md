---
name: douyin-leadgen-activity-102-dedup
description: 交出本轮可处理的视频集合。用于核验101来源、筛选与认领视频或接手同一判重 Activity；不执行整个工作流。
metadata:
  change_summary: "0.7.0: 在Activity内整合有效业务步骤，去除母Skill和旧Skill执行依赖，保留原合同与授权边界"
  version: 0.7.0
  primary_execution: agent-v1
  primary_hosts:
    - official-child-v1
  execution_transports:
    - raw-model-v1
  activity_ref: douyin_video_processing.dedup
  activity_version: 3.2.1
  validation: awaiting-real-run
  support_files: []

  method_role: single-activity
  instruction_dependencies: self-contained

---

# 交出本轮可处理的视频集合

仅执行 `douyin_video_processing.dedup`，保留业务合同版本 `3.2.1`。方法版本变化不修改Activity身份或公司业务政策。本版为说明重写，离线校验不等于实机验收。

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

输入公司/政策、明确视频范围与101来源回执、真实VID/链接、页面评论指标及 ordinary/deep/auto 策略、领取数量/截止和队列工具。输出逐VID的 received/eligible/claimed/skipped、排除原因、真实 owner/租约期限、原来源及后续资格输入。

## 操作

1. 按本轮明确输入定位101实际回执与持久记录，核run、VID、规范链接、公司/租户/line和来源证据。不是“最新目录”就可信，不按标题/作者昵称判重。跨批输入只有逐VID原来源、原子认领与当前合同明确支持时接受。
2. 独立读取队列和原状态，排除合法完成、同公司同政策已确认不合格、人工隔离或别人的有效租约。技术错误造成的未知不是内容拒绝；发现历史错误状态时保留证据，通过当前已授权修复接口处置，不直接改状态。
3. 按真实页面评论总量选普通（≤500）或深采（>500）；unknown须由当前授权原生复核或交回未决，不能用PG已采数量/默认0替代。确认无评论单列，不录音消耗采集预算。
4. 通过当前事务领取精确授权VID，不扩大公司或批次范围。回复丢失先读 owner/VID/租约，不再次竞争领取；原子领取0条是实际空集合，不转领隔离旁VID。运行期间按原协议维护本人租约，不能抢其他owner或重置未知尝试。
5. 输出每条真实筛选与领取结果、来源和恢复入口；禁止在本活动录音、判视频资格、采评论或评分。

## 明示producer交接

默认沿当前同源规则。只有本任务真实冻结并校验了producer交接例外，才按其中精确公司、完整政策、verified启用账号/设备、pending/待判定、原101 batch的CAS和单条上限执行；已matched、人工、批次漂移或过期处理中不借普通TTL重领。领取0条不换领，不扩大到其他producer或临时创建快照。旧运行没有该例外就不启用。

## 成功条件

候选集合和各排除原因可独立读回；每个 claimed VID 的公司、真实来源及唯一有效owner一致。真正无可处理输入记 empty/skipped，不报“已处理N条”或给资格阶段制造候选。

## 副作用

业务读回和事务视频租约领取/续期会改变本轮队列owner；保留原来源和领取回执。默认不操作手机；只有本Activity明确授予的原生指标补读才可使用既有设备上下文，不借此录音、采评论或评分。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

`success` 必须满足本活动下文的可观察成功条件；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复声明

以下仅保留原方法的可选恢复能力声明，不授予本次执行额度；只有原run合同明确且合法选定时生效，仍受上文原owner终态、nonce/generation、共享操作次数和原绝对截止约束。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
