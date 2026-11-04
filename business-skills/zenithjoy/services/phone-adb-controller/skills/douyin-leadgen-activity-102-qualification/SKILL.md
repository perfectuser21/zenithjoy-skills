---
name: douyin-leadgen-activity-102-qualification
description: 交出有证据的视频资格结论。用于核对目标视频、录音转写并按公司政策判断资格或接手同一 Activity；不执行整个工作流。
metadata:
  version: 0.4.0
  primary_execution: agent-v1
  activity_ref: douyin_video_processing.qualification
  activity_version: 3.4.2
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/leadgen-activity-execution.md
---

# 交出有证据的视频资格结论

仅执行 `douyin_video_processing.qualification`。业务合同版本为 `3.4.2`；方法版本独立记录，不因生成代码而更换Activity身份。

先读取[共同执行与升级约束](../leadgen-activity-execution.md)，再读本轮冻结的[所属工作流Skill](../douyin-leadgen-102/SKILL.md)中与本活动有关的配置、复用来源和授权。输入输出、验收探针以[正式Activity合同](../../../../product-map/contracts/douyin_video_processing.yaml)的 `qualification` 为准；本文件不覆盖该合同或公司政策。

## 从第一步执行本 Activity

本版支持 Runner 正式选择的 `mode=execute`，以及原有失败后接手模式；共同执行约束中关于 Code 失败、原 handler 和 resume 的条款只用于失败接手，不用于 `execute`。只执行本次指定的一个 Activity，不自行启动、切换或重启 Workflow。

`execute` 必须由本 run 的冻结 `execution_mode=agent`、中央不可变 `actor=runtime:phone-adb-controller:agent-v1` 声明及原 runtime snapshot、来源、方法和资源绑定共同准入。actor 是运行声明，不是权限或执行成功证明；Agent 不创建绑定、不改 actor、不调用内部 RPC 或裸队列。缺合法工具或准入即报告具体阻断。

1. 先核官方 child 绑定与本次私有 request 的 run、task、Activity、来源、方法和截止，调用 `inspect` 读取输入、当前原件、允许操作及 Commander 指导。
2. 只用本 request 给出的 `phone` 和 `business` 工具逐步执行。`phone` 输入为 `{command,args}`，`business` 输入为 `{operation,input}`；操作及字段以服务端本 Activity 当前实际暴露的 schema 为准，不猜操作名或自己扩白名单。锁和资源由 Runner 代码管理，Agent 不能更换 owner、公司、账号、设备、来源、额度或截止。
3. 按下文业务方法，从新鲜原生证据选择每一步，调用细粒度操作并保存/读回结果。禁止 `resume`、调用原 Activity handler、整段 `collect-comments` 或用整工作流脚本代替本 Activity。资格与评分沿原公司政策及实际授权的判断工具，不自己改阈值或补造证据。
4. 副作用调用保留原持久操作身份。回执丢失、写入或原生动作结果未知时只读回同一操作，不重新提交、不换 operation ID 重做。确认 0 评论不得入待采队列；无结果、部分成果和真实空结果分别交付。
5. 进度、问题或错误通过 `inspect` 的结构化事件报告。下一回合读取并处理 `commander_guidance`；收到 `commander_abort` 停止本 child。Commander 不批准外部动作，不改业务顺序、规则或状态。
6. 交付本次工具产生的持久结果及证据位置。Agent 的完成文字不是结果，Runner 根据服务端回执、原件、PG 及原独立 verify 判定；无法验证时明确未完成。执行终态未知保留隔离，不能为下一 Activity 清场。

`execute` 不适用于 104；本版正常执行与故障接手均仍需分别留实机证据，状态保持 `awaiting-real-run`。

## 输入输出

- 输入 `Video`：`line_key`、`video_id`、`video_url`、`title`、`comment_count`、`judgment_status`。
- 输入 `Device`：`serial`、`lock_holder`。
- 输出 `Video`：`judgment_status`、`judgment_reason`、`transcript`。

公司、task/run、截止、源码及执行权从本次正式绑定读取。缺字段保持缺失并报告，不从示例或其他租户补。

## 方法

1. 用真实视频ID进入详情，核对当前页面确为本轮目标；前台、包UID和播放器归属均留原证。 MMV显式开启设备执行的qualification，在原预检已核公司与账号后，先续期并精确核当前run锁，确认本profile不存在活跃或无法确定的受管录音，再经同owner关闭抖音并直接打开本VID；随后重新取真实分享链接核本VID。该开页边界不猜SDK，不改变M4、identity或collection路径，也不把多音轨改判成可录。
2. 先实读Android SDK原件；SDK≥33仅选同版3.3.4日志刷新补丁固定客户端与对应server，保留原playback音源、audio-dup、require-audio、Matroska与原编解码选择；不得使用SDK31包或旧brew录制绕过就绪门禁。两类SDK都须成对验client/server固定SHA、同owner有界无覆盖server准备，首末保存同一runtime原件名与SHA，停止后fresh SDK须与启动原件一致。SDK31仅在本run显式设备owner核验、已验收补丁客户端与server精确SHA校验及有界无覆盖jar准备成功后，使用独立output音源、no-video、raw PCM与WAV；这是已核的显式策略，不是失败后自动回退。SDK32、未知SDK、未安装runtime或校验不符保持unsupported/pending。SDK31必须保存私有runtime原件与SHA，起止client/server/原件名及SHA一致，停止后实解码唯一pcm_s16le音轨且无视频轨，必须decoder退出0、真实样本数/采样率/解码秒数达到本次请求80%、私有解码原件SHA及退出后原生恢复原件供queue/Workflow独立核验；首末原生音轨归属、无其他started媒体和退出恢复仍须成立。模式、SDK、required、实际音轨数量及SDK原件名/SHA必须进入本轮proof，起止两端一致，并由qualification独立核验。复用已部署录制与音轨核验方法，分别核对实际媒体音量、native播放/静音状态、真实录像及音轨。设置回显不能代替实际读回；轨道started但标记muted不能直接放行。
3. 播放控件仅从本次完整新树定位：本包、唯一“播放视频，按钮”或“暂停视频，按钮”、enabled/clickable及合法屏幕bounds；不依赖混淆resource-id，也不凭文案决定播放阶段，动作前后都须原生音轨核验。仅当本包UID/详情前台、唯一started音轨且静音原因只有streamVolume/portVolume、没有受管活录制时，按键紧前必须fresh核同包唯一stream/port候选；若已started则不按键；除下述明确通知暂态仅允许被动复读外，未知或外来轨道立即拒绝。允许一次已核正数音量→邻近非零档→原档刷新；UP已提交但读回未知/不符时只允许绝对恢复明确非零原档并读回，仍保失败，不起录；每次读回必须成立，恢复后fresh唯一started且muted none才启动录制。未知/外UID/共享UID/解析失败/多音轨不能借恢复放行。录制停止后另存退出后原生恢复证据，持续失败保pending，不重启或kill未知进程。
4. SDK/模式未知、require-audio缺失、音轨不符或捕获静音属于捕获/合同能力缺口，不以UI点击、音量循环或Skill重试放行。倍速设置、录制启动或停止失败时保留最早stderr、exit code、阶段和已有证据。proof中media_volume=null只表示未记录，不能据此推断音量0，或把native音轨首错改写成音量失败。
5. 核对真实采集媒体时长、实际播放速度、提取音频和转写证据，只有达到当前正式合同才调用原公司资格政策。缺真实音频/转写记unknown，不伪造合格。playback_dup被App opt-out、缺音轨或录音静音只证明捕获未知，保持pending，不能借此把原视频内容判rejected；不使用标题或旧ASR兜底。
6. 缓存结论仅在同视频原生身份、同公司和政策版本均相符时复用。若本轮核验旧 matched 结论，原 PG judgment_config.run_id 保持旧批次；本轮资格主 Activity span 发布同一 run/binding/SHA、精确 VID、cached/fresh、旧判断 run 和本轮原生身份核验哈希。该哈希是 102 对私有原件的正式验收收据，103 跨机只核两份官方 span 与 PG 冻结记录，不声称重算本机私有文件。资格 Activity/Step 任一 fail/partial 都不能供采样准入。逐 VID 交付 matched/rejected/unknown 和证据；仅合格视频交给评论采集。

## 显式v2领取边界

本run显式冻结并核验的v2 producer交接沿所属工作流的唯一pending白名单执行：实际领取在同一事务内重验原producer与当前consumer公司／完整政策／已verified启用账号及设备绑定，并以 `pending`、`待判定`、原101 `harvest_batch` 精确CAS，最多1条；已matched、人工、批次漂移或过期处理中不得按普通15分钟规则重领，领取0条不换领、不恢复隔离旁VID。保持原资格步骤、采集1至5条及480秒冻结预算，UI评论总量unknown要原生复核，不能用旧PG默认0或标题判零。默认队列、原v1和原生2秒／UNKNOWN安全边界不变；本v2仍待实机验收。

本固定M4旧快照缺省字段只按所属工作流的已发布精确兼容分支处理，不补旧PG绑定；本run冻结profile／serial和领取前对本run原生预检实际读出抖音号 `44997267357` 的比对仍须通过；不新增第二次account-current读取，显式错误拒、MMV严格绑定不变。

## 明确通知暂态与失败后的原生读证

只有原生完整证据能唯一确定：本包唯一 started AudioTrack、外 UID 的 started MediaPlayer 明确标为 `USAGE_NOTIFICATION`、duck 列表唯一精确匹配本包 UID/piid，且 faded/muted/banned 与未知轨道均为空，才归为明确通知暂态。该次仍是 `unknown`，不是可录或资格通过。每次原生读证先无覆盖保留首次全部原件，再最多四次每次500毫秒被动等待并取新原件；每次调用的2秒只限显式等待；最多两次broker读证的显式等待合计不超过4秒，仍不得越过原run总截止。不点击、不调音量、不重启。仅 fresh 证据重新满足原有唯一未静音本包音轨要求时才能继续；到限仍未知、共享UID、同UID通知、duck不符、外来媒体或解析不完整均保留原失败，不扩大录音或资格准入。

在原run已绑定的 `qualification`、`repair` 接手中，先 `inspect` 核对原request/nonce、冻结绑定和本次 `phone_capabilities`；inspect不提供fresh前台与受管录制判据，不能从缺字段推断通过。只有该次broker实际提供能力时，才能通过 `phone` 提交 `{"command":"native-audio-evidence","args":[]}`，最多两次。该原生入口由原owner在执行紧前强制核当前run锁、目标详情前台及无活跃或不明受管录制，任一核验失败保持blocked，不由子会话补造通过字段。证据名与路径由父进程生成；子会话不提供EID、VID、owner或文件路径。入口仅读证及上述有界等待，不停止或kill任何录制。若存在或无法排除活跃录制则blocked；录音退出取证失败由原Code先停自己的录制并确认PID退出，再报告最早错误，Skill不代清未知执行者。

新证据稳定后只能在剩余截止内 `resume` 原失败slot的成熟Code一次，再由原独立verify及业务持久化读回裁判。无法恢复保持blocked/partial并报告具体原因；读证成功不代替真实录音、转写、资格或评论落库，本方法仍待实机接手验收。

## 代码配套与验收

配套代码取正式合同 `implementation_bindings` 的全部 `kind=code` 项，并按本轮冻结源码校验；由 `leadgen-activity-methods.lock.json` 固定本Skill和代码集合。代码文件存在不代表可由Agent直接调用，公共入口以[当前调用映射](../douyin-leadgen-102/references/runtime-calls.json)为准。

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
