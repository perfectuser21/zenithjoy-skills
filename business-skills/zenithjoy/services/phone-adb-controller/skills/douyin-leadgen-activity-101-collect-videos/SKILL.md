---
name: douyin-leadgen-activity-101-collect-videos
description: 按关键词交出筛选后的视频链接。用于采集关键词搜索结果或接手同一视频发现 Activity；不执行整个工作流。
metadata:
  change_summary: "Agent 逐步点击分享、复制、读回并核对同一视频"
  version: 0.13.4
  primary_execution: agent-v1
  primary_hosts:
    - official-child-v1
  execution_transports:
    - raw-model-v1
  activity_ref: douyin_video_discovery.collect_videos
  activity_version: 5.6.3
  validation: awaiting-real-run
  support_files: []

  method_role: single-activity
  instruction_dependencies: self-contained

---

# 按关键词交出筛选后的视频链接

仅执行 `douyin_video_discovery.collect_videos`，使用业务合同版本 `5.6.3`。方法版本变化不修改Activity身份或公司业务政策。本版为说明重写，离线校验不等于实机验收。

## 合同、执行提案与独立验收

读取本run冻结的完整当前Activity Contract，核对来源、Activity身份、版本与摘要；输入输出、前后条件、DoD及已选公司政策以该合同为准，不从旧specific检查列表另立标准。执行者交付的是执行提案和原始证据，不是验收结论；独立通用Checker读取同一合同并用只读工具核实事实。模型自述、工具verified摘要或退出0不能代替原件，也不能替下一Activity判通过。

预算只引用冻结Activity Contract的 `budget` 与本run原绝对截止：业务受 `run.deadline_ms` 约束，收尾受 `run.cleanup_deadline_ms` 约束，实际可用时间取适用Activity预算和相应绝对截止的更早者。换Activity、恢复或新工具调用不重置剩余时间；不得挪用收尾窗口新增业务。

`agent_recovery` 仅声明方法可选能力，不是本次重试额度。只有本run实际冻结的 `runtime.checker_repair` 明确授权、剩余额度与原截止仍有效时，才按失败原因和证据进行允许的返工；没有该设置不自行增回合。保留原Task/run、动作身份和已成功成果；未知副作用先读回，未知不重做，不能换nonce或generation重放。返工不增加本次批次、评分、录制或发送授权，不重复已成功业务动作。Checker不执行业务写入，也不授予发送权。

## 执行上下文与工具边界

本活动所需的宿主能力以当前合同的 `required_host_tools` 为准，沿用运行器提供的统一工具入口和回执格式。

本文件就是本 Activity 的操作方法；不要求加载 Workflow 母 Skill 或旧业务 Skill。Workflow 决定活动顺序，本方法只完成当前输入指定的活动。

- 输入须明确真实 `task_id`、`run_id/run_tag`、`activity_ref`、公司/租户/业务线、公司配置与政策版本、处理范围、业务及收尾截止、实际工具与授权。已有 Task 只读回，不重复建单；缺身份或范围由调用方补齐，不从示例、最新目录或其他租户借值。
- 正式 Workflow 宿主给出的合同原件、方法/源码摘要、绑定、资源 owner 和工具 schema 都要核对；校验失败停止。普通 API 单 Activity 任务使用本任务明确授予、来源和作用域已核的工具，不伪造 Workflow ACK、actor、broker request 或冻结合同，也不因缺正式绑定而擅自切为手工模式。
- 下文是所需能力和已存在的操作名示例，不是新的工具注册或写入授权。用当前真实 schema/已部署签名确定调用；缺少合法单活动工具就报 `tool_unavailable`，不启动整条 Workflow、原 Activity handler 或任意裸 RPC/SQL顶替。保留原运行权限与公司校验。
- `execution_transport=raw-model-v1` 时不运行 shell、SSH、插件或子会话，只输出宿主 schema 的一个意图：`inspect`、`phone`、`business` 或 `finish`；`phone` 使用 `command,args`，`business` 使用 `operation,input`。不夹带最终 status/result。`finish` 只停止提意图，业务结果由独立通用Checker依据当前合同和宿主原始证据核验。
- 已绑定 child/失败接手只使用该次交接授予的工具和操作。旧 owner/child、连接或原生操作终态不明就保留隔离；不通过新 run、nonce 或 generation 重置次数。`resume` 仅在原宿主明确授予时按原共享额度执行，不能因为读了本 Skill 新增恢复权。返工必须另有本次冻结的 `runtime.checker_repair`，不能由方法声明推断额度。
- 原生调用采用本次工具已验证的执行超时并受当前合同剩余预算约束。工具返回running/session不是失败或已停止，沿同一session等真实返回，不并发重试或换EID；预算不足不启动新动作，未知终态由原owner收尾。
- 副作用保留同一持久动作身份；回执未知先读回，不换 ID 重交。数据与字段写入走已授权业务接口，凭据只经组织凭据工具/1Password取得，放入工具进程，不进正文、参数回显或日志。到业务截止停止新增业务，保留收尾预算。

## 输入与交付

输入已通过的设备/账号上下文、公司与 line、关键词及其任务/公司启用配置来源、排序/时间/地区/时长/范围筛选、唯一成功视频上限、尝试/屏数上限和截止。数量缺失先从当前任务或运营配置取，仍缺则由调用方补齐；不把某次1条冒烟当默认产能。

输出逐视频真实 `line_key/video_id/video_url/title/author/keyword/comment_count/harvest_batch` 与 `discovery_metrics`：同视频原始点赞/页面评论显示值、解析值或 null、分档、观测时间、身份与证据摘要。业务字段 `comment_count` 保留102“已采评论数量”语义，不存页面评论总数。另报实际成功唯一VID数、尝试数、重复观测、停止原因和 `all_results_scanned`。

## 逐VID交付与证据索引

按冻结的 `delivery.report.files` 交各证据角色对应的真实原件，搜索材料归 `run`，逐视频材料归实际 VID。

如果冻结契约声明了 `delivery`，在最终提案原有 `outputs` 和 `evidence` 之外，按其 schema 提交 `handoff`。共享原件放在 `handoff.run`，逐视频原件以 `outputs.Video` 中的真实 `video_id` 为键。每个值是本轮工具返回的可读相对文件路径。宿主统一归档，执行者只提交实际原件的路径。

- 新冻结交付 schema 支持 `handoff.run.video_page_screenshot` 和 `handoff.run.cards_screenshot` 时，成对提交本轮点击后所见的视频页签截图和应用筛选后的原首屏截图。引用从当前工具实际回执取得，用 `fetch-native` 取回原件，同时交前台和动作回执。两张图须能辨认搜索词、视频已选中以及原首屏卡片或明确空态。
- 恢复到只接受 `video_page_xml` 和 `cards_xml` 的既有冻结版本时，继续按其 schema 交付真实 XML；原件缺失如实报告。分享页和逐 VID 指标的 XML 仍从本轮原始存档取回。
- `filters_receipt` 填实际筛选回执。 `selected_page` 和 `results_page` 填实际筛选选中项和应用后的结果页截图。
- 逐视频填 `share_xml`、`link_receipt`、`write_receipt` 和 `readback_receipt`，四个文件须对应同一 VID。真实空结果交 `handoff.run` 的空卡片与筛选原件，逐视频组留空。缺原件如实记录，禁止用截图摘要、猜测路径或另一轮的原件代替。

完成前按本次冻结输出 schema 逐VID交付 `Video`，不能仅报两条总数或指标片段。持久字段 `line_key/video_id/video_url/title/keyword/comment_count/harvest_batch` 与完整 `discovery_metrics` 的业务字段取同VID实际PG读回；保留指标对象中的原始显示值、解析值或 null、分档、观测时间、run/profile/来源、公司绑定及原件摘要，不将对象缩成点赞和评论两个数字。`comment_count` 是102已采评论数量，不能将页面 `comment_total` 填入，也不能因旧工具没返回而补默认0。`author` 使用本VID原生卡片与取链绑定证据，不把PG没有的字段冒称持久列。

正式 final 执行提案的 `outputs.Video` 每行对象自身必须包含 `line_key/video_id/video_url/title/author/keyword/comment_count/harvest_batch/discovery_metrics`，字段名保持合同原名，链接使用 `video_url`。每行以同VID的实际 `handoff` 读回构成，补入原生证据支持的 `author`；不能只交 `{video_id,author}`，再把其他字段放进证据文件让下游代为拼装。证据索引用于核实字段，不替代这些结构化交付字段。

`discovery_metrics` 沿用原件的层级、键名和值，逐项交出已有业务字段：`version/run/run_id/profile/source_commit/line_key/video_id/video_url/observed_at/evidence_id`，`likes` 和 `comment_total` 各自的 `raw/value`，`comment_tier`，`company_binding` 的 `company_id/tenant_id/line_key/run_id/version`，以及 `digest`、`evidence.kind`、`evidence.sha256`。缺失或原值为 null 如实保留，不换键、不填默认值，也不重新计算一个摘要去替代原 `digest`。

唯一允许省略的是最终提案中的 `discovery_metrics.evidence.xml` 原始大文本，不是省略指标或身份字段。原XML仍须在同VID真实工具回执、持久PG原件中完整可独立读取；在 `proposal.evidence` 按当前schema逐VID引用本run实际可读的 `native/<实际文件名>.xml` 和相应原工具回执，保留原件SHA并核对一致。引用取真实返回位置，不把示例路径或EID猜成文件名。不要求将整段XML重复塞入模型最终回答，但所有原始证据的核对义务不变。

不自行在 `receipts/` 写摘要或另造交付文件，也不把证据文件代替 `outputs.Video` 的完整行。`metrics_evidence_id` 取自本轮该 VID 的真实详情 XML 回执，按冻结入口规定去掉 `-share.xml` 后缀；仅当参数错拼且工具明确返回 ENOENT 时，根据原回执纠正拼写，在同一原件上修正只读调用，不重做手机取链或 discover。除冻结规则明确的后缀外，原件文件名逐字沿用。若原ID正确仍不可读，保留真实缺口，不编造原件或换动作身份。

逐VID分别引用原 `discover` 写入回执与后续只读回执：`inserted` 区分本次新增和已存在，`judgment_status`（原工具可能返回 `status`）记录实际资格状态；二者是不同维度，matched不是“本次新增”。只读回执固定的 `inserted:false` 不证明原写入是否新增，必须查该VID原写入结果；原结果未知则保留未知，不重放 discover 以重造回执。新增、已存在、重复观测与未决计数须能由逐VID结果回算。

未启用可选字段的 `discover_readback` 返回状态、转写有无、指标一致摘要及digest；`inspect_videos` 的基础返回不包含完整交付字段。只读扩展 `discover_readback` 的 `include_handoff:true`，返回 `handoff={line_key,video_id,video_url,title,keyword,comment_count,harvest_batch,discovery_metrics}` 原持久值；`inspect_videos` 的 `include_discovery_protection:true` 用于同VID discover前与读回后保存过程状态、历史批次、评论计数和转写摘要。只在本run冻结工具明确支持该参数时调用，并核对实际返回；不支持则报告缺口，不自行假定接口可用。只有摘要时保留完整原生观察和原回执，逐项说明缺哪个持久字段/前后原件，结果保持partial/unknown，不用模型补造PG值或把旧verified当完整原件。旧run缺少写前读回不能事后回填。

交付可读证据索引，逐项给真实工具动作名、EID/VID及原件位置；工具返回SHA时保留实际SHA，没有则不编造。索引应能定位本次关键词搜索、视频页签、筛选面板/选中项/结果页、各原槽位卡片、取链与解析、同详情metrics、discover原写入、独立PG读回及可用的写前/写后保护原件。说明哪个VID和哪个输出字段由哪个回执支持，不只写“搜索完成/筛选正确/PG通过”；路径或file-id必须是当前只读工具实际能访问的原件，摘要被截断须取得原件，无法读取则明确证据缺口。

`Run` 同时交真实停止原因和实际扫描范围：冻结模式/关键词/筛选、尝试与唯一VID数、已看屏数和卡片槽位、未检查范围及停止回执。达到首屏候选/尝试/成功上限分别如实说明，不把停止原因写成搜尽；次数、耗时、截止和异常来自原回执，不估算缺失值。只有合同允许且有同范围页尾原件才能声明 `all_results_scanned=true`；首屏有界采样一律 false。沿原预算与原动作结束，不为补字段、换停止理由或满足数量追加未授权扫描/重跑；空集、部分完成、工具失败和未知分别记录。

## 操作

1. 每批手机动作前核当前资源 owner、目标设备与账号上下文。若原生请求仍在途，等待真实返回，不并起第二条操作。controller支持命令和owner参数的范围要逐项核；不为绕过不支持的owner参数而去掉权限检查。
2. 按真实工具签名执行 `open-search ENCODED_KEYWORD`。冻结契约支持截图交付时，先用 `foreground` 和 `snapshot-evidence EID` 结合当前图确认前台是抖音、搜索词正确。若「视频」已选中就直接继续，否则从当前截图定位「视频」，调用一次 `tap-evidence X Y EID`，检查同一次点击的回执和新截图。从新图确认关键词正确、「视频」已选中且结果已加载；即使控件树不可用，只要这三点清楚就继续。图上仅显示加载或页签不明确时，只观察当前页，不根据控件树缺失推断还在综合页，也不重复点击。截图交付路径不调用 `search-video-tab`。仅恢复至要求 XML 的旧冻结契约时，遵循该版本的页签操作与取证。
3. 在结果页直接调用现有筛选操作，不先手点一次再让复合动作点第二次。已部署形式示例：`search-time-layer TIME EID SORT DURATION SCOPE LOCATION`；六项均来自本次输入。保存面板、选中项、结果三份原件，核各实际选项；参数合法不等于原生UI已支持。
4. 截图交付路径用 `snapshot-evidence EID` 读取应用筛选后的原首屏。确认关键词和已选视频页签，按屏幕阅读顺序记录原始槽位、可见标题、时长和当前坐标。相关搜索词、广告入口、占位和无法确认的卡片不作为视频候选，保留它们的原槽位，不补位或重新编号。每次点击前用新鲜截图确认仍是同一原槽位，再调用 `tap-evidence X Y EID`。视口或卡片身份不确定时停止该候选，不按旧坐标盲点。截图交付路径不调用会自行切换页签的 `search-video-cards`；仅恢复至要求 XML 的旧冻结契约时使用它。标题只用于定位，视频身份仍取真实链接。
5. 每个原槽位只执行一条受控取链路径。在已打开的视频详情，按最新截图确认同一候选及前台。Agent 自己用 `tap-evidence` 点分享，观察分享面板后再点明确标注的「分享链接」。只点功能区按钮，保留「链接已复制」的原始画面。
   - 通过 `open-search %20` 打开未提交的空搜索输入框。先看输入框和键盘，只在确认是本轮复制的抖音短链建议项时点击；也可用输入框原生粘贴项。读回聚焦搜索框 XML 中的完整短链。这个输入框只用于读回，不发起搜索，也不点分享对象。
   - 用已部署可访问的公开 HTTPS 读取能力解析短链，保留原短链和最终规范 URL；仅接收明确的抖音视频 ID，图文单独排除。用 `open-video VIDEO_ID EID` 按解析的 ID 重新打开，核对画面、作者及标题和原视频一致。在短链解析并确认重新打开的是同一视频后，使用 `ui-evidence <run>-candidate1-link-t1-share`（将 candidate1 换为实际原槽位） 留存指标原件，指标入口的实际证据 ID 是对应原件 basename 去掉 `-share.xml`。读回、解析、重新打开各留本轮回执。用本次实际粘贴读回的输入框原生 XML 作为链接原件，使用原轮动作回执证明点击、复制成功和重新打开。无真实新复制或不能核对同一视频时如实报失败。
   - 连接波动时，先确认上一操作已结束且未产生待决结果。以当前设备、账号、页面和同一原候选的证据重新确定位置，在合同原额度和原截止内做明确可恢复的步骤。连接还未就绪只观察，无法确认同一视频或动作结果未知时，保留证据并停止此候选。
6. 离开详情前，将同次详情XML/截图与本次解析VID对应。点赞数、页面评论总量保留原文与时间；解析万/亿等单位。缺数字、带+、不精确或越界显示记 `value=null` 并说明原因，不填0；评论分档为 `zero/1_100/101_500/over_500/unknown`。真实0评论可以留发现观察，但不得伪装为有评论的待采输入；持久化工具不能区分观察与待采状态时保留原件并报接口缺口。
7. 经公司/来源校验的正式写入能力提交，再按同一VID/链接独立读回公司、来源和本轮观测。按当前合同核对同视频指标原件、解析和PG完整持久读回；仅旧 discover ACK、数据库默认0或旧观测不足以通过。新字段未发布时保存带VID的持久指标工件及 `metrics_persistence_missing`，结果为partial/failed，不宣称专用指标已入库。
8. 同VID重复观测幂等，只有本次同等或更新观测按接口规则接受；保持原资格、transcript、102进度、comment_count、已采视频原batch。新增/重复/历史分别计数；旧行不能冒本轮新增。
9. 取链返回note或临时搜索框后，用已有归位能力返回相同关键词与筛选，重新核页面，不把临时搜索框当新的任务。按授权继续当前屏/翻屏；达到数量、尝试或截止分别记 `limit_reached/attempt_limit_reached/deadline`，重复屏或加载停滞记 `stalled`。只有明确且范围匹配的页尾原件才能记 `exhausted`。

## 有界首屏输入

保留当前正式 `Run.discovery_input`：schema1 的 `max_candidates` 限首屏卡片数，超额零候选动作；schema2 的 `max_attempts` 限实际尝试，只试前N个原槽位。两模式互斥、唯一关键词、单首屏，不翻屏、不恢复视口、不用重入重置额度。重复、缺身份、失败均耗尝试；失败或未知按原安全规则停止，不为凑N补槽。`target_count` 是独立成功唯一VID上限。schema2已知无失败且达到尝试N时，可完成有界采样，但必须 `all_results_scanned=false`，不能声称新增N条或搜尽。

真实 `no_cards` 只在同一搜索范围内明确的原生空结果证据符合当前合同的empty条件时交付empty，并停止依赖视频产物的后续业务，不凑造视频。

## 成功条件

本轮真实视频身份、原生筛选、指标与来源均有原件，实际持久行和专用指标独立读回通过，计数/停止原因可回算。只交发现结果；不录音、不判断视频业务资格、不采评论、不调用103，也不释放共享设备资源。

## 副作用

实际副作用包括搜索/筛选/详情导航、工具取链带来的剪贴板变化、截图/XML工件，以及经授权的视频/指标持久化。关键词、卡片/链接可交本次批准的解析/定位工具；不发送评论、点赞、关注、私信或作品，不调ASR/评分。

## 结果与验收

交付本次 Activity 的实际 `task_id/run_id/activity_ref`、`status`、`stop_reason`、输入对象身份、逐项结果、实际新增/历史/重复/未决计数、持久读回和证据位置、工具/模型实际调用与未知项、资源交接及副作用。工具或模型回执缺失写 unknown，不填 0；明确未调用才填 0。

执行提案中的 `success` 必须有本Activity合同要求的真实产物证据，仍须独立通用Checker验收；已提交部分成果但未达目标记 `partial`；缺授权、来源或工具记 `blocked`；实际调用失败记 `failed`；真实无输入记 `skipped/empty`。业务上的真实拒绝、无语音、捕获失败、空队列分别记录。Agent文字、脚本退出0、收尾成功都不能替代业务验收，不能据此替下一个 Activity 报成功。

## 宿主恢复能力声明

以下 `agent_recovery` 只描述可选能力，不能被解释为本次已选额度。实际是否允许返工及其次数只读本run冻结的 `runtime.checker_repair`；原授权、动作累计次数、未知不重做和绝对截止仍约束所有回合。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
