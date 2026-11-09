---
name: douyin-leadgen-activity-101-collect-videos
description: 按关键词交出筛选后的视频链接。用于采集关键词搜索结果或接手同一视频发现 Activity；不执行整个工作流。
changelog:
  - "0.7.0: 显式兼容冻结official-child-v1内部正式宿主，保留旧运行与恢复边界"
  - "0.6.0: 新增显式无工具回合身份与父Code执行；保留旧child与恢复约束"
metadata:
  version: 0.7.0
  primary_execution: agent-v1
  primary_hosts:
    - official-child-v1
  execution_transports:
    - raw-model-v1
  activity_ref: douyin_video_discovery.collect_videos
  activity_version: 5.1.1
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/leadgen-activity-execution.md
    - services/phone-adb-controller/skills/leadgen-official-child-host.md
---

# 按关键词交出筛选后的视频链接

仅执行 `douyin_video_discovery.collect_videos`。业务合同版本为 `5.1.1`（breaking）；新增同视频指标输出与持久化读回通过条件，不能沿用4.1.0的成功回执。方法版本独立记录，Activity身份保持不变。

先读取[共同执行与升级约束](../leadgen-activity-execution.md)，再读本轮冻结的[所属工作流Skill](../douyin-leadgen-101/SKILL.md)中与本活动有关的配置、复用来源和授权。输入输出、验收探针以[正式Activity合同](../../../../product-map/contracts/douyin_video_discovery.yaml)的 `collect_videos` 为准；本文件不覆盖该合同或公司政策。

## 从第一步执行本 Activity

本版支持 Runner 正式选择的 `mode=execute`，以及原有失败后接手模式；共同执行约束中关于 Code 失败、原 handler 和 resume 的条款只用于失败接手，不用于 `execute`。只执行本次指定的一个 Activity，不自行启动、切换或重启 Workflow。

`execute` 的旧入口仍须核本 run 冻结 `execution_mode=agent`、中央不可变 `actor=runtime:phone-adb-controller:agent-v1` 及原 runtime snapshot、来源、方法和资源绑定。只有本方法新版本显式冻结的 `primary_host=official-child-v1` 可采用[内部正式宿主兼容合同](../leadgen-official-child-host.md)，由父进程核实其精确 `common-runner/internal` 绑定；不能按 actor 文本自行选择。actor 不是权限或成功证明；Agent 不创建绑定、不改 actor、不调用内部 RPC 或裸队列。缺合法工具或任一准入证据即报告具体阻断。

仓库 YAML 链接仅定位业务合同来源，不要求执行目录具有该仓库。执行时读取本次 `request.method.contract` 中由 Runner 与中央固定 Activity 版本核验过的 `payload`、`sha256` 和版本身份；缺该原件即报告缺失，不从最新仓库、链接不存在或自拟内容补合同。

1. 原官方 child 方式：先核官方 child 绑定与本次私有 request 的 run、task、Activity、来源、方法和截止，调用 `inspect` 读取输入、当前原件、允许操作及 Commander 指导。 `execution_transport=raw-model-v1` 时按下节核官方回合绑定，并由父 Code 代调 inspect；不伪造 child。
2. 只用本 request 给出的 `phone` 和 `business` 工具逐步执行。`phone` 输入为 `{command,args}`，`business` 输入为 `{operation,input}`；操作及字段以服务端本 Activity 当前实际暴露的 schema 为准，不猜操作名或自己扩白名单。锁和资源由 Runner 代码管理，Agent 不能更换 owner、公司、账号、设备、来源、额度或截止。
3. 按下文业务方法，从新鲜原生证据选择每一步，调用细粒度操作并保存/读回结果。禁止 `resume`、调用原 Activity handler、整段 `collect-comments` 或用整工作流脚本代替本 Activity。资格与评分沿原公司政策及实际授权的判断工具，不自己改阈值或补造证据。
4. 副作用调用保留原持久操作身份。回执丢失、写入或原生动作结果未知时只读回同一操作，不重新提交、不换 operation ID 重做。确认 0 评论不得入待采队列；无结果、部分成果和真实空结果分别交付。
5. 进度、问题或错误通过 `inspect` 的结构化事件报告。下一回合读取并处理 `commander_guidance`；收到 `commander_abort` 停止本 child。 无工具回合按下节提交 inspect 意图，由 Code 停止本回合及父循环。Commander 不批准外部动作，不改业务顺序、规则或状态。
6. 交付本次工具产生的持久结果及证据位置。Agent 的完成文字不是结果，Runner 根据服务端回执、原件、PG 及原独立 verify 判定；无法验证时明确未完成。执行终态未知保留隔离，不能为下一 Activity 清场。

`execute` 不适用于 104；本版正常执行与故障接手均仍需分别留实机证据，状态保持 `awaiting-real-run`。

## 父 Code 管理的无工具回合

仅本方法新版本的正常 `mode=execute` 可使用冻结的 `execution_transport=raw-model-v1`。字段缺省继续原官方 child 方式；旧 run、旧方法、失败接手和 104 不切换。该声明必须与本次固定源码、中央 Activity 方法版本、Task、run、binding、资源及原绝对截止共同核验；Agent 文字或环境临时改值不能选择通道。

此方式由 Runner 的 Code 调用官方 `agent`，固定 `modelRun=true`、`deliver=false`，服务端禁用 Agent 的 shell、子会话、插件及其他工具。Agent 不领 spawn 权、不创建绑定、不用 CLI、SSH、裸 RPC 或队列。身份改核本回合由 Code 独占保存的官方 run/session/request 身份及其 Task/run/slot/source/nonce 绑定；不得把 raw run 伪装成 `sessions_spawn` child，也不套用旧 child 双停回执。父 Code 仍须完成原中央授权、固定 Skill 与合同核验。

父循环每轮传入真实 `inspect`、上次工具回执和未消费的 Commander 指导。自动 inspect 是 Code-owner 的只读上下文读取，仍核本轮授权、身份、epoch 与截止，不消耗模型单意图授权，也不执行 phone/business；Agent 显式 inspect 与其他操作仍经原 broker 的一次性回合授权。只回复一个 JSON 意图，不加 Markdown 或额外字段：`{"type":"inspect","question":"需要澄清的问题"}`（也可仅用 progress 或 error 字段）、`{"type":"phone","command":"当前schema允许的操作","args":[]}`、`{"type":"business","operation":"当前schema允许的操作","input":{}}` 或 `{"type":"finish"}`。inspect 的 question/progress/error 至多一项，也允许无事件。Agent 不能选择模型、身份、资源或额度；phone/business 仍由同一个原私有 broker 核白名单和实际权限后执行。不要自己调用这些工具。

`finish` 只是停止提出操作，不包含 status/result，不证明 Activity 完成。实际业务结果只能来自 broker 的服务端记录、原件、PG 与独立 verify。Code 在前一回合官方终态和连接关闭确认后才执行工具；每回合与操作独占记账，截止、epoch、业务操作身份和 max_turns 计数不重置。`request.max_turns` 必须来自本次正式冻结，为 1..64 的整数；缺失或非法时不启动，无默认加额。该正常回合上限不增加合同允许的恢复次数。回执或副作用未知只读回原身份，不重发同一回合或操作。

收到 Commander abort 或原截止即停止新增回合及工具调用，由 Code 精确中止本回合并核官方终态、本次连接和所有本人工具资源的实际收尾。一个 model 回合结束不等于父循环、工具或 Activity 已停止；缺任一停止证据则保持 needs_review 与原隔离，不释放未知资源。该方式不扩大 Commander 权限，不改独立 Judge、业务政策、零评论规则、恢复次数或原冻结预算；尚未实际验收仍为 awaiting-real-run。

## 输入输出

- 输入 `Keyword`：`line_key`、`word`。
- 输入 `Device`：`serial`、`lock_holder`。
- 输入 `Run`：`run_tag`。
- 输入 `SearchRequest`：`keywords`、`sort`、`time_layer`、`location`、`target_count`、`max_duration_s`。
- 输出 `Video`：`line_key`、`video_id`、`video_url`、`title`、`keyword`、`comment_count`、`harvest_batch`、`author`、`discovery_metrics`。正式输出 `Video.discovery_metrics` 映射运行结果的 `Video.metrics`，保存本次真实观测，含同视频点赞数、页面评论总数、分档及身份和原始证据；原 `comment_count` 保留102已采评论数量语义，不能拿它存页面评论总数。
- 输出 `Run`：`status`、`stop_reason`、`all_results_scanned`。

可选 `Run.discovery_input` 使用本次冻结的显式模式，不能从成功数量推导尝试额度：schema 1 的 `max_candidates` 限首屏卡片数，超额零候选动作；schema 2 的 `max_attempts` 限实际尝试，首屏卡片较多时只尝试前 N 个原槽位，真实显示数仍照记。两模式互斥、唯一关键词、单首屏，不翻屏、不露出/恢复视口，不用同 run 重入重置额度。重复、缺身份、失败均耗尝试；失败/执行未知仍按原安全合同停止，不为凑 N 重试或补后续槽位。`target_count` 仍是独立的成功唯一视频上限。

schema 2 达到 N 且无失败或已知缺口时，本次有界尝试采样可完成，输出 `attempt_limit_reached` 与 `all_results_scanned=false`，实际持久化数量独立读回；不能声称新增 N 条或搜尽。预算不足、存在失败/缺口或真实未知，按实际 partial/failed/unknown 交付；旧 schema 1 超额/达到上限的原语义不改。

公司、task/run、截止、源码及执行权从本次正式绑定读取。缺字段保持缺失并报告，不从示例或其他租户补。

## 方法

1. 从本任务或该公司已启用配置取关键词、排序、时间与地区条件、数量和截止；记录真实来源。新鲜树确认关键词、视频页签及筛选生效。
2. 逐屏识别真实视频卡片，跳过相关搜索词块、广告和加载占位。点开前刷新树，按当前节点定位，不沿用旧屏坐标。
3. 逐个打开视频、取分享链接并解析真实 video_id，核对当前详情与返回链接身份。复制失败不复用上一条链接，标题相同不直接认定为重复。
4. 在离开该视频详情前，把取链同次详情XML与本次解析的真实video_id绑定。保留原始显示值、观测时间、证据ID、完整XML及其摘要；按万、亿等显示单位解析点赞数和页面评论总数。缺失、带+等无法精确解析或越界显示保持unknown（value=null并记原因），不能填0；评论总数分档为zero、1_100、101_500、over_500、unknown。
5. 经当前公司正式接口保存视频及专用 `discovery_metrics`，不直调裸队列或SQL。观测绑定原冻结run tag、实际run_id/attempt、profile、line、source_commit、VID及规范链接；公司/租户绑定由原接口从公司冻结记录独立读取，不能接受视频自报归属。逐VID重算原件并通过原 `discover_readback` 独立读回完整观测和公司绑定；`discovery_metrics_verified == 1` 是必需后置条件，只有写入ACK或旧观测存在不能通过。
   同真实VID重复发现仅幂等接受相同观测，或更新更晚的observed_at；旧观测不能计成功。保持102状态、判定、transcript、comment_count、已采进度、历史来源及已采视频原batch。重复观测单列，101不按业务资格筛掉视频。接口未发布、字段缺失或读回不符，保留原件及 `metrics_persistence_missing`/实际失败原因，按原核验报告failed/partial，不能把旧版本成功当5.0.0通过。
6. 回搜索现场继续剩余卡片，再滑动等待加载。数量、截止、停滞分别记停止原因；“暂无更多，查看所有内容”若未验证后半句含义，不宣称搜尽全部AI视频。

## 代码配套与验收

配套代码取正式合同 `implementation_bindings` 的全部 `kind=code` 项，并按本轮冻结源码校验；由 `leadgen-activity-methods.lock.json` 固定本Skill和代码集合。代码文件存在不代表可由Agent直接调用，公共入口以[当前调用映射](../douyin-leadgen-101/references/runtime-calls.json)为准。

按正式合同的后置探针、原始证据及持久化读回验收；区分Code结果、Skill接手结果和清理结果。单Activity接手入口为原run的 `activity-skill-tool.mjs <broker-request.json> inspect|phone|resume`；只能使用本次持久handoff给出的冻结路径，不能自己建request、换run或直接启动Workflow。源码接线与Skill实机接手验收分别记证据，当前方法仍 awaiting-real-run。

## 本方法的真实接手入口

Code失败、分类与有限安全重试后，由原run的handoff broker持有同一Activity闭包、身份、资源和截止。真实work-commander父会话经官方sessions_spawn派本Skill子会话；先核原request/nonce及自己的绑定。只调用本次给出的工具路径：`inspect`读取实际进度；`phone`经stdin JSON `{command,args}`仅读证或受控归位；必要时 `resume`仅继续当前slot的成熟Code一次。不得构造新Workflow、改源码/策略/账号/暂停或另取/释放锁。

`send_dm`失败一律readback_only，不能resume或点击发送；没有确定发送证据保持unknown。Skill交付不直接写成功，原进程按原verify/Step/PG读回独立裁判。子会话终态未知保留资源，不能清场干扰未知执行者。没有正式已绑定子会话或source/method/预算不符即blocked。


## 同run有界Agent恢复合同

以下仅是原冻结Activity合同的显式opt-in形状，不是模型或方法自行授予的执行额度：

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```

从本run对应的 `version.payload.contract.agent_recovery` 核此对象：仅允许唯一键 `max_additional_turns`、值为整数1；字段缺省保持原一次性接手，非法值或多余键阻断。一次额外Agent turn不是新Workflow attempt，不增加业务次数或预算。 `send_dm`不启用额外Agent turn，仍按原单次 `readback_only`；opt-in是恢复上限，不扩大该限制。

Code失败或Code实际产出未过原verify时，首次Skill接手仍走原入口；首次Skill/Agent已确认失败或其实际产出未过原verify时，由唯一work-commander在同一次recover与原broker存活期内决定是否用这一次额外turn。先取得原owner和原child精确官方终态及停止证明，并确认broker无在途操作、原资源授权有效且尚在原Activity执行截止；父CLI或子终态未知、外部写入（含发布/发送）结果未知均不重派、不清pending、不刷新TTL。模型自述、CLI退出0或预览页不能替代这些证明。

保留同run/task/binding/source/Activity、原业务nonce、原handler闭包与已成功VID。每turn只增加不可覆盖的transport generation及官方child绑定，引用原业务nonce；先撤销旧child工具权，再精确授权当前generation，旧child迟到调用/回执不得执行或覆盖新证据。不得删除原launch/binding/closed记录，不能换nonce或重建broker重置额度。

原broker的resume总计最多一次，原生读证总计最多两次，失败调用也消费相应额度。resume前Agent失败且余量合法才可继续使用尚未消耗的resume；resume已预留或业务已执行后，后继turn仅inspect/readback/verify，禁止再resume、受控归位或其他业务动作。资格恢复沿原成功VID集合及每VID次数，不重领、不重录成功项。send_dm始终readback_only；collection partial、能力/权限/来源阻断仍按原规则停止。所有turn共享原截止，不挪用cleanup预算执行业务。

原进程独立verify及真实持久读回通过后才继续后续Activity；无结果不能靠新child文本补成功。额外turn耗尽、剩余预算不足或仍核验失败即准确failed/partial/unknown并保原证，不承诺每种障碍都能救回。本版仍awaiting-real-run，配套源码、发布与实机验收分别留证。
