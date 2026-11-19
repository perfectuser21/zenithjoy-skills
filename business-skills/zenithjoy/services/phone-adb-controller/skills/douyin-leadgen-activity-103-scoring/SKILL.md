---
name: douyin-leadgen-activity-103-scoring
description: 交出按公司原政策持久化的评论评分。用于独立消费已提交评论评分或接手同一评分 Activity；不执行整个工作流。
metadata:
  change_summary: "对齐当前Activity合同、通用Checker与共享截止；不新增执行授权"
  version: 0.18.0
  primary_execution: agent-v1
  primary_hosts:
    - official-child-v1
  execution_transports:
    - raw-model-v1
  activity_ref: douyin_comment_scoring.scoring
  activity_version: 2.9.0
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/douyin-leadgen-activity-103-scoring/references/maintenance-scopes.md

  decision_ref: 8331c673-1113-4a04-a5dd-54ec76a916fe
  method_role: single-activity
  instruction_dependencies: self-contained

---

# 交出按公司原政策持久化的评论评分

仅执行 `douyin_comment_scoring.scoring`，使用业务合同版本 `2.9.0`。方法版本变化不修改Activity身份或公司业务政策。本版按主理人决定 `8331c673-1113-4a04-a5dd-54ec76a916fe` 取消额外模型评分复核；新合同按本决定使用单次评分，不要求额外模型复核。若现有宿主仍硬性要求旧双审，报告实现尚未适配，不伪造字段绕过。离线校验不等于实机验收。

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

输入真实Task/run、公司/租户/line、当前冻结政策、处理数量/截止、已提交评论与关联视频原文、稳定身份、资格/采样来源证明和当前授权评分/提交/读回工具。`source_run`、评论ID清单或sources映射只有调用方明确给出才限批；不从前一个102、环境残留或本地文件名自动继承。

默认独立消费本公司的合法待评分PG队列；默认队列仍要求视频“评论已采”。不操作手机、不取手机锁，不等整轮102结束。102本批无评论不等于103公司队列为空；只按本任务的真实查询范围报告empty。任务显式限批则严格保持，不能为凑样本换历史bench。

输出逐评论ID、原来源、实际等级/理由/原文引用、政策版本、本次评分调用身份、scored/excluded/blocked及实际模型调用、PG独立读回；本活动不创建Lead/outbox或发送。

评分前读取合同要求的视频标题和转写原文，保留各自来源；工具缺失已承诺的转写输入时如实报告缺口，不以标题冒充转写，也不因工具遗漏删除合同要求。

## 操作

1. 核当前公司与line唯一映射、冻结产品/客户/评分政策及数量。六类、strong/weak、A/B/C等都以该公司当前政策为准；不拿旧手册的固定分类、重复文本必spam、其他公司的阈值覆盖它。
2. 通过当前事务/租约领取合法已提交且待评分的评论，保存精确ID→原harvest_batch映射、cursor、blocked IDs与额度。空队列要有真实查询回执，0条记skipped/empty，不称“已评分5条”。
3. 核每行原生身份、公司/来源与视频资格。默认队列要求真实matched及“评论已采”。普通API显式交接可保留视频“待判定”或原102处理租约，但调用方须明确给出 `committed_partial_ids`（1～50条、`source_run=null`）：逐行重验完整verified原生主页/返回评论/同VID配对、exact UID/昵称/正文与哈希/视频URL/原batch、真实102账号绑定，以及102/103冻结公司/租户/line/版本/政策和评分规则一致。仅已提交不构成准入，unknown或来源不符仍blocked；本活动不为其补认证或改102状态。
   正式102配额采样仍是独立窄例外，只允许正式collection主span点名的精确PG IDs，在原102绑定、同source SHA、Activity/Step及终态pass/verified、冻结配额、101来源、逐VID qualification/collection两主span身份及PG公司/租户/政策都一致时接纳。视频保持“待判定”不等于可任意领，TaskRun文字/本地JSON不代替这些回执。
4. 普通API显式交接的 `score_scope`、`score`、`score_recovery`、`score_exclusion_readback`、`score_readback`及 `policy_review`始终传同一 `committed_partial_ids`，`ids`只能取该清单子集，`sources`保留精确ID→原102 batch映射；不得顺带消费默认队列。`policy_review`另保留本103 `claim`，只确定性核对已存单次评分，不新增模型。
   正式采样覆盖核新增+核实历史、逐VID配额和规范PG行摘要；历史行保留原batch，仅未评分行进入本活动。旧matched判断run保持原值，本轮资格身份必须有效。103只验官方跨机收据和PG冻结记录，不声称重算102私有文件。软预算、失败102或来源含糊的行保持待决。精确历史修复仅在维护Task明示时读取本目录[历史接纳例外](references/maintenance-scopes.md)，默认不启用。
5. 调用符合当前公司政策的单次评分工具。A的个人提问/意向信号、B相关讨论、C画像内寒暄都须原文证据与本公司冻结规则对应；是否存在这些等级由政策决定。画像证据使用当前冻结画像的真实ID与业务字段原文，并对应冻结评分规则；画像、字段或引用无法验证时保持unknown。评论引用与视频引用分别来自原文，短引用按完整原文核语境，不能补造提问或把泛问句升档。
6. 每条评论只做一次模型评分：用同一份公司政策、评论和关联视频原文得出等级、理由及引用，随后持久保存。不追加独立政策复核、第二模型投票或评后重审，不要求两份response_id或 `policy_reviews[2]`。记录实际provider/model及本次响应身份；只存真实返回的审计字段，不拼造历史双审结构。
7. 有效评分为“不相关”时，保存relevance=不相关、intent_grade=null及真实理由和原文依据，不为此新增“已排除”状态或Lead/outbox。HTTP/模型/网络错误、输出缺失或引用不能对应原文时保持未决，不用第二次模型复核补结论，不把技术失败当业务排除。历史“已排除”行保留原审计，只按已有维护授权读取或恢复；已存在的有效评分不为补审重评。
8. 调用前核工具的真实调用链：评分后若内部还自动调用模型做policy_audit或其他评分复核，也不满足本次“一次评估”要求。使用已发布且无需额外模型复核的单次评分与提交入口；缺少该入口则报告 `scoring_tool_contract_mismatch`，不能只因工具保存单份policy_audit就认定它只调用一次模型。既有工具强制双审或提交字段不兼容时保留真实缺口，不伪造回执。
9. 每批从业务存储读回评论、视频、政策版本、本次评分/排除及状态，确认保存对象与结果一致；这是读取数据，不再次调用模型判断。排除行还核无评分、无触达outbox。scored、excluded和blocked分别计数，两类成功消费共同占原额度。纯排除批有真实读回可完成；真正空批不能充作评分样本。
10. 恢复先核已提交IDs及原cursor，未知写入只读回，不重发同一评论评分或消费另一批补数。到截止停止新领取，保存已完成、待决集合与原因；不改原102状态，不调用手机或104。

## 成功条件

本次实际评分或正式排除均有同公司政策、一次真实评分及原文依据、精确PG终态和持久化读回；无越权来源/重复消费。空批明确skipped；工具仍强制额外模型复核或不满足采样来源合同为blocked，不能标评分通过。

## 副作用

原评论/视频原文和公司政策送当前批准的单次评分服务，写PG评分、审计、合法排除与本次消费记录。按原工具保留provider/model/响应身份；不外发手机截图/音频、不占手机、不建Lead/outbox、不执行发送。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

执行提案中的 `success` 必须有本Activity合同要求的真实产物证据，仍须独立通用Checker验收；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复能力声明

以下 `agent_recovery` 只描述可选能力，不能被解释为本次已选额度。实际是否允许返工及其次数只读本run冻结的 `runtime.checker_repair`；原授权、动作累计次数、未知不重做和绝对截止仍约束所有回合。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
