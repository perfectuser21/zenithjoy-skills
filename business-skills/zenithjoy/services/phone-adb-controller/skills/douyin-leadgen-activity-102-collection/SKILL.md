---
name: douyin-leadgen-activity-102-collection
description: 交出持久化且身份可验证的评论。用于从合格视频采集评论并读回或接手同一评论采集 Activity；不执行整个工作流。
metadata:
  change_summary: "对齐当前Activity合同、通用Checker与共享截止；不新增执行授权"
  version: 0.10.1
  primary_execution: agent-v1
  primary_hosts:
    - official-child-v1
  execution_transports:
    - raw-model-v1
  activity_ref: douyin_video_processing.collection
  activity_version: 2.8.1
  validation: awaiting-real-run
  support_files: []

  method_role: single-activity
  instruction_dependencies: self-contained

---

# 交出持久化且身份可验证的评论

仅执行 `douyin_video_processing.collection`，使用业务合同版本 `2.8.1`。方法版本变化不修改Activity身份或公司业务政策。本版补充普通API显式交接与凭证补齐方法；离线校验不等于实机验收。

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

输入已领且有效matched的VID/链接、公司/政策、当前原生账号与租约、qualification回执、`comment_limit`/策略/范围/预算、原历史评论核验工具和提交/读回工具。采样数量来自当前任务；5条是已有实测任务的授权值，不是所有任务默认上限。

开工前只核本轮已独立验收的资格交付、有效租约、冻结身份和配额。评论正文、原生 UID、主页链接、返回评论页原件、历史命中和真实已提交数由采集执行后交付，再由独立 Checker 核对。

输出完整评论的原文、原显示时间/地区、昵称、稳定 `douyin_id`、主页/视频链接、真实评论ID或明确近似去重键、line、batch、原生关联证据、`recipient_evidence`、PG ID与读回；另列新增、history_verified、duplicates、coverage及最后成功批次。未知身份原件单独留存，不能冒完整可消费行。

## 操作

1. 重核本轮VID的有效资格、公司/政策、原生账号和当前租约；失败/unknown资格不采。已证0评论使用当前正式零评论分支及同VID证据；无数字不当0。旧matched缓存须本轮原生身份核实与同公司/政策，并保留旧判断run。
2. 用已确认VID/deeplink直接回详情（工具可提供 `open-video VID EID`），不重新搜索猜同标题。核前台与当前视频，再用新鲜控件定位评论入口；`open-comments EID` 是已有能力示例，参数以当前schema为准。验评论列表出现、输入框未聚焦、键盘未弹出。
3. 按任务配额和范围逐屏读小批，不把全评论塞给模型。保存完整正文、原始时间/地区、评论列表锚点与当前VID。相关搜索块、广告UI与回复计数不当独立完整评论；未展开回复不能报全量。
4. 以当前工具返回的评论头像坐标和昵称编码原样进入该人的主页，核显示名、原生抖音号/稳定身份、主页链接及账号类型，再返回同一评论上下文。已有 `commenter-identity X Y B64 EID` 等操作须先核实际签名；不要把昵称当坐标、自己改工具给出的base64或用相似账号补ID。只接受当前PG/schema要求的原生身份字段，不拿昵称哈希代平台ID。
5. 一条核验失败不丢弃其他已核条目。组织号、号不可见、身份冲突分别保留原件及 `non_lead_org/identity_partial/identity_unverified` 等当前工具允许状态；是否可入库、排除或交付由当前冻结合同决定。缺稳定身份的对象不得标可触达；旧手册“连同正文都写原始池”不覆盖当前完整字段门禁。
6. 优先真实评论ID去重；无平台ID用已发布的VID+稳定评论人+完整正文等组合键并说明近似局限。同一人在不同视频的真实评论保留来源，不按人或相同正文一律删掉。历史消费先读PG/URL原生证明，只有同实际VID、完整身份与正文独立核实者计 `history_verified`；不靠标题关联旧评论。
7. 用当前事务提交每批原生证明及公司绑定，随后独立读回精确PG ID、UID、正文、URL、公司/来源。未知提交先核原动作，失败批不计提交，不换batch重发。保持原公司冻结账号与设备绑定；评论自报company/profile不能授予权限。
   普通API任务若已通过 `collect_partial` 保存同一行但 `recipient_evidence` 尚未verified，先取得完整真实原生主页、返回评论与同VID配对及原102冻结账号绑定，再使用获授权的 `certify_collected_comment` 补证据：输入原102 `run`、line、VID/规范视频URL、`comment_id`及原评论字段和新完整 `recipientEvidence`。仅原102本人持有matched视频租约、该行仍待分拣且未评分、原UID/昵称/正文/主页/视频来源逐项相等时可认证；接口只升级原非verified凭证，不能覆盖已有verified证据或改其他字段。随后用同run/VID/comment_id调用 `certify_collected_comment_readback`，以真实verified读回交接；unknown、冲突或工具缺失仍保留未决，不手写SQL改状态。
8. 新增、核实历史、重复和实际覆盖分别累计。配额达标标sampled/quota_reached，不宣称页面评论总量或已采尽。正式102配额抽样保留视频“待判定”等当前合同语义；不能为了103放行手改成“评论已采”。只有明确页尾、时间边界及相应范围才标该范围exhausted；连续几屏没新增只记stalled，不把屏号/累计数当稳定游标。
9. 普通API显式交接只交调用方指定的 `committed_partial_ids`（1～50个精确PG ID）及原ID→102 batch映射，`source_run=null`；每行须有完整verified原件、matched视频和与103一致的冻结公司/租户/line/版本/政策及评分规则。保持视频原状态，不能因已提交或补认证就宣称默认103队列会消费。
   正式采样交接仍交出逐VID精确PG ID集合、规范行摘要、停止原因和新增/历史计数，绑定本run/binding/source SHA；独立比对qualification与collection两个主span的同VID身份收据、冻结公司/租户/政策及旧判断run。回执缺失/歧义、超过原3MB限额或工具只会把5条样本写成已采尽时，保留已确认成果并报工具/交接缺口，不能宣称可供103。
10. 截止保存已提交集合、最后成功批与恢复入口，输出partial时也保住成果。不执行103评分、不建Lead/outbox；设备与视频租约交明确的cleanup责任人收尾。

## 成功条件

当前采样/范围目标满足，完整身份和本轮资格/来源逐条可核，实际PG行与本次所选交接模式的读回一致。未达配额或缺身份/交接为partial/blocked；真实0评论按正式替代证据单列，不冒采到0条就达成5条配额。

## 副作用

会导航评论区与原生评论人主页，写本次取证/批次工件、经授权的评论行/历史消费和采样回执。只收集证据，不执行意向评分；不点赞、关注、回复、私信或发布。缺失的原显示时间/地区保留unknown，不能推测填值；字段合同不接受缺失时留未决原件，不报完整行。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

执行提案中的 `success` 必须有本Activity合同要求的真实产物证据，仍须独立通用Checker验收；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复能力声明

以下 `agent_recovery` 只描述可选能力，不能被解释为本次已选额度。实际是否允许返工及其次数只读本run冻结的 `runtime.checker_repair`；原授权、动作累计次数、未知不重做和绝对截止仍约束所有回合。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
