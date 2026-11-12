---
name: douyin-leadgen-activity-103-mark-leads
description: 交出原生身份核实的线索与配送状态。用于按评分保留线索、独立资格核对并配送或接手同一标记 Activity；不执行整个工作流。
metadata:
  change_summary: "0.16.0: 按主理人决定评估一次即保存，取消额外模型复核及下游双审门槛"
  version: 0.16.0
  primary_execution: agent-v1
  primary_hosts:
    - official-child-v1
  execution_transports:
    - raw-model-v1
  activity_ref: douyin_comment_scoring.mark_leads
  activity_version: 3.9.0
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/douyin-leadgen-activity-103-mark-leads/references/maintenance-scopes.md

  decision_ref: 8331c673-1113-4a04-a5dd-54ec76a916fe
  method_role: single-activity
  instruction_dependencies: self-contained

---

# 交出原生身份核实的线索与配送状态

仅执行 `douyin_comment_scoring.mark_leads`，使用业务合同版本 `3.9.0`。方法版本变化不修改Activity身份或公司业务政策。本版按主理人决定 `8331c673-1113-4a04-a5dd-54ec76a916fe` 取消额外模型评分复核；新合同按本决定使用单次评分，不要求额外模型复核。若现有宿主仍硬性要求旧双审，报告实现尚未适配，不伪造字段绕过。离线校验不等于实机验收。

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

输入本公司已评分、待分拣的精确评论与原来源、原评分run/冻结政策/评分结果与原文依据、原生身份与视频资格证明、授权线索/outbox/桥接工具、处理量和截止。本活动可独立消费已有评分，不要求必须由同一个103 run刚刚评分；每行原评分身份须可回验，任务显式限批时照守范围。

输出comment→lead关联、created/repeats、等级和证据，`RecipientQualification`的passed/excluded/unknown、公司版本/原生主页摘要/理由，以及outbox动作身份、payload/fields摘要、真实feishu_record_id和confirmed/held/unknown。PG创建不等于外部配送确认。

## 操作

1. 仅领取 `待分拣`、已有真实单次评分和原文依据的真实评论；`已排除`行即使旧A分残留也不得建Lead/outbox/104订单。读取原评论、原视频、公司政策版本、原评分结果及引用，核对公司与来源身份；不要求双审字段，不再次调用模型评估评分。
2. 原视频通常须“评论已采”；正式采样保留“待判定”的窄例外，仍逐VID核102绑定/source SHA、quota精确IDs、qualification与collection两主span、PG冻结公司/租户/政策和旧判断run。不能因普通TaskRun写了completed、采样文件存在或旧matched就开放；软预算、失败或隔离来源不放行。历史例外只在明确维护Task中按本目录[历史接纳范围](references/maintenance-scopes.md)核，不自行扩大。
3. 按原规则确定该行是否保留线索及重复出现次数。直接使用原评分等级、理由与证据，按公司规则确定保留和配送范围；不重新判断个人意向或升降等级。原评分缺失、来源身份或公司绑定不符时保持unknown，不调用模型补评。
4. 独立核评论人的原生主页/稳定抖音身份与公司受众条件；昵称、搜索相似人、摘要或模型猜测不代替原件。真实接收人资格工具给passed/excluded/unknown，unknown/未确认者不能标ready或推成已交付。
5. 复用原事务和line级串行去重：Lead upsert、原评论关联、durable outbox一致提交，再推进评论状态。技术失败回滚或保留未决，不手写数据库改状态，不以“最新评分覆盖身份冲突”。
6. 外部配送只走该公司原桥接/outbox权限。先持久动作身份/attempted，再由现有桥接单次创建；未知按原marker、UID和完整字段GET读回，不另跑push-leads或换ID重复POST，不覆盖受保护/已发送历史行。外部记录与scope不符停在held/unknown。
7. 分别读回PG Lead、评论终态、资格结论、outbox payload/fields摘要及外部recordID/字段。没有完整字段的真实外部读回不能报confirmed；0合格或纯排除可以是真实合法结果，不能为了验收制造线索。
8. 仅同公司版本、资格passed且配送confirmed的订单具备原104输入条件；这不构成执行104的授权。本活动不操作手机、不发私信、不推进整个获客链的游标，不把所有评分行当可触达行。

## 成功条件

本次消费范围、原评分/政策版本与原生身份核对、PG事务及外部状态均可独立读回。明确区分created/repeated/recipient-excluded/held/unknown。真正空输入记skipped；外部unknown保留原动作，不能以PG已有Lead宣称配送成功。

## 副作用

可能调用当前批准的受众资格模型，事务写PG Lead、评论关联、重复计数及outbox，并由已授权的原桥接写该公司飞书记录。逐项保留实际动作身份和确认状态；不向用户发消息、不执行104、不写无授权外部系统。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

`success` 必须满足本活动下文的可观察成功条件；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复声明

以下仅保留原方法的可选恢复能力声明，不授予本次执行额度；只有原run合同明确且合法选定时生效，仍受上文原owner终态、nonce/generation、共享操作次数和原绝对截止约束。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
