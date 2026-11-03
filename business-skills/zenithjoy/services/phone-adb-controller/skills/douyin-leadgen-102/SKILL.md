---
name: douyin-leadgen-102
description: 执行抖音获客102视频处理：验证101来源、领取待处理视频、判断资格并按评论量采集持久化。用于普通、深采或自动策略及代码异常接手；不修改评分标准或执行私信。
changelog:
  - "0.3.4: 将冻结来源规范块内的v2小标题改为普通段落，兼容严格发布验收解析，交接语义不变"
  - "0.3.3: 声明显式v2单条待判定视频的有限producer交接，保留默认同源与v1"
  - "0.3.1: 绑定collection0.2.1的显式已证零评论合同，正数与未知要求不变"
metadata:
  version: 0.5.2
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/douyin-leadgen-102/references/reuse-map.json
    - services/phone-adb-controller/skills/douyin-leadgen-102/references/runtime-calls.json
    - services/phone-adb-controller/skills/douyin-leadgen-102/references/activity-methods.json
---

# 102 · 视频处理与评论采集

首版可加载 Skill，本版实机验收待执行；不把文档、局部测速或旧版成功当成本版生产通过。

## 冻结来源绑定

MMV102首个设备动作前把选定profile/serial冻结到本run的company_config_runs.task_inputs.device_binding，再核当前原生抖音号；实号通过后生成本run私有company-binding工件。原生评论证明、解析和PG提交必须消费同一绑定，PG按原102冻结行重验公司/租户/平台与唯一verified enabled账号；不将原件自报字段当授权，不为缺失历史来源新建快照。旧M4无此新工件的路径保持原守卫。

显式v2单条待判定producer交接：

缺省仍要求101与本run同部署来源；既有v1只接受其原有固定范围。只有本次已发布实现支持、任务明确选择且通过 `LEADGEN_PRODUCER_DESCRIPTOR_FILE` 冻结的 `schema_version: 2` 描述符，才可消费原 `beb37370c047a13013aa0cc997a0fecc09534dde` 的 `cicdbeb_101_attempt2_20261027_a2dcb023`。此例外仅限 `legacy`／`ANGYVB4402004137`／`jinuo`、原公司与租户及v14政策、唯一VID `7689863996204591985`；不是通用跨版本许可，也不授予恢复隔离、设备或发送权限。

描述符须为本用户所有的绝对路径普通文件、权限0600、单硬链接且非符号链接，字段与固定值须通过已发布validator。保留完整原101冻结定义及含两条视频的进度原字节，按固定snapshot／progress哈希和全部原文件闭包核验；不能裁成一条、改原source、补造快照或把新consumer来源冒成旧producer。新consumer仍使用自身真实已验证manifest与冻结身份。

本固定M4旧快照的 `platform` 或PG `task_inputs.device_binding` 缺省，只能按本次已发布validator的精确兼容分支接受，不能补写旧字段或自造通过值；显式错误仍拒绝。每次仍须核本run冻结的profile／serial、原公司已验证启用账号，并在领取前比对本run原生预检实际读出的抖音号 `44997267357`；此比对不新增第二次account-current读取。MMV原严格绑定守卫不变。

新run必须冻结原来源与采样输入：最多领取1条、每条1至5条评论、采集预算480秒，其他截止及原生2秒守卫不变。PG在领取同一事务内重验原producer与当前consumer的公司冻结资料、完整政策内容、已验证启用的实际账号及绑定；仅 `pending`／`待判定` 且 `harvest_batch` 仍为原101批次的唯一VID可原子领取。状态或批次漂移、已matched／人工隔离／过期处理中均拒绝，不能使用普通队列的15分钟重领规则；领取0条不换领、不新搜索。旁VID `7700112581541257551` 的人工状态保持。

评论总量沿原101证据及打开后真实读回：`unknown` 不当零，旧PG `comment_count` 的默认0不代替原生总量。仍须原录音／资格、评论身份与PG提交读回及清理验收；零评论或文档／代码通过不表示正向102→103已通过。本v2实机状态仍为 awaiting-real-run。

## Activity 方法配套

本工作流的方法依赖真身见[Activity方法清单](references/activity-methods.json)。执行指定Activity时，按本轮冻结 `activities[].implementations` 的真实name/version/source/digest及execution_path加载对应独立Skill；不能把本工作流Skill当作每个Activity的同一份方法。

- `douyin_video_processing.preflight` → `douyin-leadgen-activity-102-preflight@0.3.1`。
- `douyin_video_processing.dedup` → `douyin-leadgen-activity-102-dedup@0.3.1`。
- `douyin_video_processing.qualification` → `douyin-leadgen-activity-102-qualification@0.3.2`。
- `douyin_video_processing.collection` → `douyin-leadgen-activity-102-collection@0.4.2`。
- `douyin_video_processing.cleanup` → `douyin-leadgen-activity-102-cleanup@0.3.1`。

Activity方法、支持文件或合同改变时，更新对应方法版本、所有消费者清单、本工作流Skill与Commander Skill版本；纯代码内部兼容优化用明确兼容评估绑定前后代码集合。先跑 `npm run leadgen:methods:check`，再做相应独立验收。方法配套完成不表示单Activity执行权交接已经接通。

## 复用已有Skill

按 [复用来源与校验值](references/reuse-map.json) 加载 `social-video-qualifier`、`social-comment-lead-collector` 和 `douyin-phone-runtime` 的适用操作。复用视频深链、录音/ASR工件核验、评论区读取、原生评论人身份和部分成果保存；不重新发明这些动作。

旧Skill不能直接作为本版完整入口：保留当前公司的原资格政策及正式录音覆盖验收，不因旧文档的“已设置3倍速”回显就推断实际播放速度；无数字不当0；连续无新增不当真实页尾；累计计数/屏号不当稳定游标；5条采样和深采分别记。旧n8n写入围栏、原始池和阶段身份只在实际调用器提供兼容协议时采用，否则使用当前正式队列/事务/原生证据接口，不能自行伪造fence。

先按 reuse-map 的 `sha256` 核对旧 `SKILL.md` 字节后读取。`path` 只表示当前MMV已核安装位置，不保证其他宿主存在；缺失或不同只能从记录的固定 `repo` / `revision` / `source_path` 读取同字节参考，仍不可读则阻断对应接手。参考说明不等于已部署可执行工具，实际执行仍核本次正式冻结包。

## 调用范围与当前接口

阅读 [当前正式调用映射](references/runtime-calls.json)。`mode=workflow` 执行本流程全部合同；只有现有整段代码满足本轮目标时才使用其中完整入口，不把旧Code成功计成新版新增要求已完成。`mode=activity` 只执行任务指定、已冻结的 Activity；缺合法单步入口、写入授权或执行权交接时报告具体缺口，不用 `leadgen-activity.sh` 冒充单步入口，也不绕过冻结绑定直调裸队列。来源已变更须重新固定与验证，不能沿用旧元数据。

101引用的共享preflight/cleanup只执行对应设备动作，不进入102业务；以本次冻结Workflow的实际共享Activity引用核对范围。预检/收尾只有同任务受托执行权才可操作，不能顺手搜索或领取视频。

## 输入与交付

输入真实任务/运行身份、公司配置版本、host/profile/serial/目标账号、可验证的101来源、策略 ordinary/deep/auto、视频范围、采样或尽量采集目标、完整字段要求、总截止与独立保存/收尾预算。采样条数由任务提供；原授权首轮每合格视频5条仍有效，不能静默扩大成深采。没有正式确认的夜间时窗不自行设置定时器。

输出逐视频资格、判定依据、评论原件及身份来源、实际新增/历史复用/重复数、持久化读回、采集范围、停止原因与清理结果。页面评论总量与已采条数分开；未展开回复不能宣称全量。

## 执行

1. 登记/认领任务，核对公司启用状态、产品/目标客户和原视频资格政策。固定 Skill、已部署代码、配置及输入来源；版本/输入不明先报缺口，不重标旧运行来源。
2. 手机操作使用 `android-publish` 的设备协议，取得中央与本地锁；核对 profile、serial、实际账号和空闲通话状态。103 不在本机等待它占锁执行。
3. 从授权范围选择待处理视频，验证真实101 run、视频ID、公司、业务线、来源证据及PG行。优先复用正式队列领取与租约，排除已合法完成、已确认不合格或被有效租约持有的行。同一来源可按原有已发布入口处理；跨批处理须有逐视频来源和持久原子认领支持。缺这些支持时报告具体队列缺口，不能直接删掉原 intake/source 守卫或用“最新目录”代替来源。
4. 普通策略领真实评论数不超过500的视频；深采领超过500的视频；自动策略在范围内补读未知指标并选预算。unknown 不当零。分档由101提供，打开后复核；预检不承担业务分档。没有延长授权不突破原总预算。
5. 用实际视频ID打开并核对当前视频。SDK≥33维持playback_dup；SDK31仅可用本run明确owner、固定已验客户端/server及原件哈希的output PCM/WAV策略，SDK32或证据不全保持pending。复用已部署录音/播放核验、转写和原资格判断。没有真实录音或转写证据记 unknown，不伪判合格；缓存判断仅在同公司政策版本与真实身份一致时复用。只有资格合格的视频进入评论采集。
6. 先区分已证零评论、正数与未知；仅冻结合同显式允许且同run逐VID原UI/identity/hash齐全时交付零评论，不点击空评论入口、不计采样达标，未知拒绝。正数按原要求打开评论区，逐屏读取并小批提交。保留正式字段合同要求的正文、时间、地区、评论人稳定身份、主页/视频链接及原生关联证据；只采昵称正文的测速脚本不能冒充完整102。优先真实评论ID去重；缺ID时用视频、稳定评论人、完整正文等组合，说明近似去重局限。
7. 每批提交后读回实际行，分别累计 inserted、history_verified、duplicates、coverage；失败批不计入已提交。优先复用既有事务、评论历史核验和采样读回，不另写一套评分或业务计数。显式采样的每视频精确 PG ID 集与规范行摘要须进入本轮 collection 主 span；本轮资格主 span 另留同绑定、同 SHA、逐 VID 原生身份和旧判断 run 收据，供跨机103双回执比对。旧 matched 视频只在同冻结公司/租户/版本/政策与本轮身份核验通过后使用，PG 旧判断 run 不重写；历史评论保原批次。
8. 达到任务采样配额可结束本次采样，标 sampled/quota_reached，不标整条视频采尽。50或500是实现上限/分档边界，命中不等于到底。尽量采集目标下，仅在明确页尾、范围说明和提交读回齐全时标本范围完成；否则 partial，保存累计数和最后成功批次。
9. 业务截止后不再领新视频，留出提交与清理预算。持久记录来源、视频身份、已提交集合、停止原因和恢复入口；关闭App、释放自己的租约和设备锁并读回。

## 原实现的数据外发与调用记录

实际录制音频送阿里云DashScope的Qwen ASR；视频标题、转写和冻结公司资格政策送OpenRouter的Jev及原疑难兜底模型；评论及原生账号证据写原PG，活动证据送原Commander。正常定位使用原生树，实际视觉兜底才外发截图及定位描述。服务/模型以本次冻结代码与已批准配置为准，不在救场中新增外发接收方。密钥不进提示词、正文或回执。逐类保存真实provider/model/response_id、实际调用次数、失败和unknown；以RPC、ASR、视觉及bridge原回执统计，不能用脚本动作数代替模型次数，也不能把缺失回执计为零。

## Commander 与中断恢复

代码为采集主体，Agent/Commander 接收摘要与异常，不把所有评论堆入上下文。代码失败后由 Commander 核对旧执行者、锁及外部结果，再把同一 Activity 交给本 Skill；同一任务目标、身份和截止不变，不现场改代码。

资格判断的通知暂态恢复按冻结 `douyin-leadgen-activity-102-qualification@0.3.2` 执行：仅明确通知duck允许保留原证后的有界被动复读，未知不直接放行；原run broker只读证最多两次，稳定后同slot仅resume一次，再做原独立核验。其他未知、活跃录制、权限或冻结来源不符均保持blocked，不把本恢复策略用于评分或触达。

现场仍在：重读当前树并核对视频后续采，不复用旧坐标。现场丢失：重开目标、重扫并按已提交记录去重；累计计数不是可靠位置游标。缺安全执行权交接、结果未知或锁冲突时保留 blocked，不并起第二采集器。失败运行的采样不能兑现配额。

## 验收

核对每条采集的来源/资格/原生身份、PG新增与历史消费读回、采样范围、完成或partial语义、截止与清理。独立核验使用相同业务合同；Code失败与Skill救场分开记录。本版正常模式与跨批深采分别验证，不用一个5条样本代表所有档位。

来源：[今日101/102方案](https://app.notion.com/p/3f9c40c2ba6381dea615c39380c78e66)、[Skill/Code配套规则](https://app.notion.com/p/3f5c40c2ba6381acbad0d31ee3215f92)。

## 单Activity受控接手

当前源码提供 `leadgen-activity-v1`：仅在原冻结run内Code失败与有限安全重试之后，由真实work-commander父会话派官方Skill child，使用原run私有broker逐Activity接手。`activity-skill-tool.mjs` 不是新任务启动器；inspect/受限phone/一次当前slot resume均受同源方法、绑定、资源和截止约束。子会话终态未知保锁，发送未知只读回。最后仍由原独立verify与持久读回决定成功，不以Agent自述或CLI exit0替代验收。当前源码存在不等于实机接手已验收，具体状态查看当前任务事件与发布观测。

MMV手机执行按[当前调用映射](references/runtime-calls.json)显式设置 `LEADGEN_MMV_DEVICE_RUNTIME=1`，核本机唯一启用的profile/serial和既有ADB端口。随后仍须原公司冻结资料、verified账号/设备绑定及手机当前账号全部通过；公司draft、缺登记或桥未就绪即停，不借金诺或其他租户配置兜底。该设备入口不扩大本轮输入、预算或发送授权。

SDK≥33的playback_dup使用独立固定3.3.4日志刷新运行时；SDK31的output PCM使用独立固定5.0.1运行时。两者按实际SDK唯一选定并分别核验client/server和首末原件，不升级或回退Homebrew。安装路径和运行包不互换，缺包即保持失败。


## 同run有界Agent恢复合同

以下仅是原冻结Activity合同的显式opt-in形状，不是模型或方法自行授予的执行额度：

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```

从本run对应的 `version.payload.contract.agent_recovery` 核此对象：仅允许唯一键 `max_additional_turns`、值为整数1；字段缺省保持原一次性接手，非法值或多余键阻断。一次额外Agent turn不是新Workflow attempt，不增加业务次数或预算。 `send_dm`不启用额外Agent turn，仍按原单次 `readback_only`；opt-in是恢复上限，不扩大该限制。

仅对本run已冻结opt-in的Activity执行该方法恢复政策：同一次recover、同broker/原业务nonce内最多额外一个Agent turn，原owner与child官方停止双证和原权限/截止仍是前置。原resume一次、native读证两次累计不重置；resume已用后仅inspect/readback/verify。generation精确授权并撤销旧child；unknown、send_dm只读、collection partial及能力/权限阻断守卫不变。最终仅原独立verify决定继续，不能把额外turn当新业务attempt、发送额度或清场许可。当前配套及实机能力以实际发布/验收为准。
