---
name: douyin-leadgen-activity-102-dedup
description: 交出本轮可处理的视频集合。用于核验101来源、筛选与认领视频或接手同一判重 Activity；不执行整个工作流。
metadata:
  change_summary: "按现有判重合同交付作者原生身份和视频租约读回原件"
  version: 0.8.1
  primary_execution: agent-v1
  primary_hosts:
    - official-child-v1
  execution_transports:
    - raw-model-v1
  activity_ref: douyin_video_processing.dedup
  activity_version: 3.3.1
  validation: awaiting-real-run
  support_files: []

  method_role: single-activity
  instruction_dependencies: self-contained

---

# 交出本轮可处理的视频集合

仅执行 `douyin_video_processing.dedup`，使用业务合同版本 `3.3.1`。方法版本变化不修改Activity身份或公司业务政策。本版为说明重写，离线校验不等于实机验收。

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

输入公司/政策、明确视频范围与101来源回执、真实VID/链接、页面评论指标及 ordinary/deep/auto 策略、领取数量/截止和队列工具。输出逐VID的 received/eligible/claimed/skipped、排除原因、真实 owner/租约期限、原来源及后续资格输入。

## 操作

1. 按本轮明确输入定位101实际回执与持久记录，核run、VID、规范链接、公司/租户/line和来源证据。不是“最新目录”就可信，不按标题/作者昵称判重。跨批输入只有逐VID原来源、原子认领与当前合同明确支持时接受。
2. 独立读取队列和原状态，排除合法完成、同公司同政策已确认不合格、人工隔离或别人的有效租约。技术错误造成的未知不是内容拒绝；发现历史错误状态时保留证据，通过当前已授权修复接口处置，不直接改状态。
3. 按真实页面评论总量选普通（≤500）或深采（>500）；unknown须由当前授权原生复核或交回未决，不能用PG已采数量/默认0替代。确认无评论单列，不录音消耗采集预算。
4. 先按下节核实待判重候选的作者身份。通过当前事务仅领取已证实为非自家作者且符合其余条件的精确授权VID。回复丢失先读 owner/VID/租约，不再次竞争领取；原子领取0条保留实际筛选原因，不转领隔离旁VID。运行期间按原协议维护本人租约，不能抢其他owner或重置未知尝试。
5. 输出每条真实筛选与领取结果、来源和恢复入口；禁止在本活动录音、判视频资格、采评论或评分。

## 作者原生身份与自家号过滤

- 先读本轮冻结的101逐VID来源原件。已有可独立核实且能绑定精确VID的原生作者抖音号时直接使用。作者昵称、标题、头像、登录账号或评论者主页均不能作为该视频作者的抖音号。
- 原件不足且当前设备上下文、工具、授权和业务预算仍有效时，只对仍可处理的精确授权VID补读。用现有签名 `open-video VID EID` 打开原视频，核对原生详情与此VID绑定。若现有原件没有独立VID绑定，按当前工具签名取得 `current-video-link` 的真实原生详情取链原件并核实其VID，不能只用 `open-video` 输出回显的输入值。用 `ui-evidence EID` 读当前原生树定位该视频详情中的作者入口，用 `tap-evidence X Y EID [WAIT_MS]` 留存点击路径，随后读取作者主页的原生XML和可用的截图。EID使用本run前缀，沿工具回执保留关联。核验页面从该视频的作者入口进入，读取页面明确标注的“抖音号”。通过当前工具公开的只读文件获取能力（本宿主已有 `fetch-native`）按原名保留原件并引用可读路径。VID绑定、作者入口、主页账号字段或原件可读性不明时，记录未决并保留现场交接。
- 与本run冻结的同公司、同租户、抖音平台、已启用且已核验的 `douyin_id` 精确比对，保留配置版本、账号身份类型、比较结果与原件引用。主页短链或 `sec_uid` 可作为导航关联证据。只有已核实同一身份命名空间或有可信映射时，才可用于账号相等性比较。确认自家作者时按原政策排除。身份或配置不可核实时，本VID记 `unknown`，不能认领、进入可处理集合或资格阶段，也不能当成合法空集合的证据。
- 交付逐VID的101来源引用、原生详情与作者导航回执、作者主页原件及路径和可用摘要、冻结公司政策版本及筛选结果。Checker自行读取原件及本run冻结政策。

## 视频租约原件

- 保留 `claim_videos` 真实动作回执与前后读回，记录精确VID、line、`process_status`、当前批次、原 `judgment_config.run_id`（适用时）、最后认领或续期时间。回复未知时按动作身份和原记录读回，不重领。
- Checker通过既有只读 `pg.rows` 的 `videos` 关系取得同line、精确VID的原始行及数据库 `connection.snapshot_at`，对照认领回执与本run原始状态。当前冻结队列规则中，普通重领仅在处理中行的 `updated_at` 严格早于数据库时间减15分钟时开放。本run owner为 `处理中:<run_tag>` 且批次匹配时，结合数据库原始快照时间复算 `updated_at + 15分钟` 并核验适用的所有权。若后续冻结实现返回明确到期时间，按实际冻结实现取证。缺时间、所有权不一致或读回时已失效均如实交待。特殊交接仍遵循其冻结CAS规则。
- 若真实提案协议提供 `evidence` 和 `outputs.Video`，引用实际原件并按合同交付已核集合。`raw-model-v1` 保留宿主可独立读回的原件和回执，完成后按原 `finish` schema 停止，不向 `finish` 增加字段。命令退出0、单独的 `harvest_batch`、模型摘要或当前墙钟不能代替租约读回。

## 来源证明与认领分支

先区分101来源证明与认领接口分支：`producer_key`、`input_provenance` 或逐VID的 `upstream` 只证明已批准的101来源，不等于本次 `claim_videos` 请求带有受信 `producer_descriptor`。

当前宿主明示 ordinary 且未提供 `producer_descriptor` 时，按真实 schema 先 `inspect_videos`，完成逐VID筛选后才以 `op:"claim_videos"`、`video_ids:已核为可认领的本轮精确授权VID数组`、`limit:本轮冻结上限`、`config_required:true`、`source_run:null` 调用已授权业务接口；run/line沿宿主固定身份。没有已核可认领VID时，不发起空认领。已有 `matched` 且处于 `待判定` 的视频，或当前 `harvest_batch` 不同于101来源批次，不能仅据此判定不可认领；由原接口在事务中校验公司政策、精确VID和可领取状态并原子认领，不在Agent侧改状态或抢其他owner。以实际领取与读回为准，认领不等于本轮资格已通过。

只有本任务真实冻结、校验并向认领接口提供受信 `producer_descriptor` 时，才走producer交接例外：保留其中精确公司、完整政策、verified启用账号/设备、pending/待判定、原101 batch的CAS和单条上限；该分支不接受已matched、人工、批次漂移或过期处理中，不借普通TTL重领。不能自行构造descriptor、借用101 run改普通 `source_run`，或因例外拒绝切换分支。两条路径均保留原VID/公司/租约范围；领取0条不换领、不创建快照，未知回复先读原owner与租约。

## 成功条件

候选集合和各排除原因可独立读回；每个 claimed VID 的公司、真实来源及唯一有效owner一致。真正无可处理输入记 empty/skipped，不报“已处理N条”或给资格阶段制造候选。

## 副作用

业务读回与事务视频租约领取或续期分别留痕。本Activity明确授权且现有设备锁、精确VID和业务截止均符合要求时，可使用既有设备上下文补读原生指标或作者身份。原生导航只为取证，不录音、采评论、评分、关注、点赞或发送。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

执行提案中的 `success` 必须有本Activity合同要求的真实产物证据，仍须独立通用Checker验收；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复能力声明

以下 `agent_recovery` 只描述可选能力，不能被解释为本次已选额度。实际是否允许返工及其次数只读本run冻结的 `runtime.checker_repair`；原授权、动作累计次数、未知不重做和绝对截止仍约束所有回合。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
