---
name: douyin-leadgen-activity-103-scoring
description: 交出按公司原政策持久化的评论评分。用于独立消费已提交评论评分或接手同一评分 Activity；不执行整个工作流。
metadata:
  version: 0.10.0
  activity_ref: douyin_comment_scoring.scoring
  activity_version: 2.7.0
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/leadgen-activity-execution.md
---

# 交出按公司原政策持久化的评论评分

仅执行 `douyin_comment_scoring.scoring`。业务合同版本为 `2.7.0`；方法版本独立记录，不因生成代码而更换Activity身份。

先读取[共同执行与升级约束](../leadgen-activity-execution.md)，再读本轮冻结的[所属工作流Skill](../douyin-leadgen-103/SKILL.md)中与本活动有关的配置、复用来源和授权。输入输出、验收探针以[正式Activity合同](../../../../product-map/contracts/douyin_comment_scoring.yaml)的 `scoring` 为准；本文件不覆盖该合同或公司政策。

## 输入输出

- 输入 `Comment`：`dedup_key`、`body`、`nickname`、`douyin_id`、`profile_url`、`process_status`。
- 输入 `Video`：`title`、`transcript`。
- 输出 `Comment`：评分通过时交出 `relevance`、`intent_grade` 及双审证据；两审一致缺证据时交出独立 `process_status=已排除`、安全原因及双审摘要，评分字段为空。

公司、task/run、截止、源码及执行权从本次正式绑定读取。缺字段保持缺失并报告，不从示例或其他租户补。

## 方法

1. 在MMV执行，不取手机租约、不操作ADB，也不等待整批102结束。任务限定来源批次时严格保留该范围；无有效评论就empty，不拿历史bench凑验收。
2. 通过原队列事务领取本公司的已提交待评分评论。通常要求同来源批次、视频状态“评论已采”、资格 matched。正式102配额抽样是窄例外：视频保持“待判定”表示未全量采尽；只有 Brain 原102绑定、同SHA来源、全部Activity/Step与终态 pass/verified、冻结采样上限、原101来源、公司政策和PG整批评论原生身份逐条核实后，103才可领取 collection 主 span 点名的精确ID。逐视频覆盖=配额，新增及历史计数相加、规范PG行摘要与Brain回执一致；历史行保留旧harvest_batch，未评分者才进入103。多视频、跨机同样核，缺回执或歧义拒绝。金诺已验收102d跨SHA历史批次只按 Issue `3004abdb-d5b8-448c-b35c-58203ef84e1d` 的固定run、绑定、VID和五条原件受控兼容，不扩大到其他旧批。软预算、失败102或任意“待判定”视频不能凭状态进入。原102g失败run、VID `7699489394579915663` 的三条固定UUID仍仅凭用户决定、旧执行停止、原生身份、v14冻结政策、无旧outbox及精确 `db_audit` 回执接纳，且只绑定单一103 run。所有路径不改原102结论或视频状态；产品、客户与等级规则仍来自本公司。
3. 复用正式judge-comment与持久化评分入口；当前金诺保留原2.0.0政策。A须有评论原文中的个人提问或冻结意向信号，并以视频标题原文片段核同主题。若冻结A标准含“求资料”或“明确求助”，合格视频标题明确涉及流程，评论明确请求给出流程，则按原政策的求助证据审查；泛问句或不索取流程不凭此升级。模型引用必须分别是评论、视频的原文片段；引用短片段时以完整原文作窄判据，不能要求引用片段重复整个请求。B可为相关讨论而无行动意向，C可为画像内寒暄，但B/C均须有评论原文引用与冻结画像片段相连；不相关需独立模型复核一致。调用模型的真实provider/model/回执与失败按原件记录。
4. 同一评论的政策Commander最多调用两次。两份不同 response_id 且均符合原等级与原文证据，才在同一PG事务提交评分与 `judgment_config.policy_reviews[2]`。两份独立复核都确认缺 `personal_intent_evidence_missing` 或 `audience_or_topic_evidence_missing`，且原因和候选等级一致时，同一事务把评论置为 `已排除`，清空旧评分，保存安全原因与两份复核身份及哈希。首审视频引用重试也占两次额度；Jev、评分Commander、政策Commander原调用上限不增加。旧单审半提交评论仍须按固定ID、原run、公司冻结政策、维护Task和无配送意图受控重评；满足双审缺证据条件时清空旧A并排除。模型/HTTP/网络故障、身份复用、额度耗尽或两审分歧保持待分拣与原安全原因，不能猜分或把它们当作业务排除。
5. 评分与排除分别计数、共同占本轮预算。评分行由独立读回器重新读取PG原评论、视频、冻结公司政策和双审证据；排除行独立读回终态、来源、无评分、双审缺证据摘要及无触达outbox。纯排除批次须有真实排除读回才可完成；真正空批不得伪称产出。两类读回均不发第三次政策模型调用；任何绑定或证据不符保持unknown。
6. 本活动只交评分或排除结果，不建线索、outbox，也不发送私信；评分成功仍须由后续标记活动独立验收。

## 单条误排除恢复

仅对维护Task明确指定的金诺102l评论 `f5e16a6d-9183-4606-b840-9698bd710eed` 使用现有103受控恢复入口；不开放批量或任意CID恢复。核对原102批次、公司与租户、v14冻结政策、原103 run已完成且进程已停止、原评论和视频原文哈希、两份旧A候选证据及旧排除原因，并独立确认无Lead和outbox。恢复事务保留旧评分判断与双审审计，只将此行回到待分拣；新run固定相同公司政策并独立读回恢复回执、原审计和无配送，再只重评此CID。重复、来源不符、授权失效或外部副作用不明均停止；恢复不增模型两次上限，也不触发104。

失败回执只输出固定安全证据分类与政策模型实际调用数；JSON、身份、原文引用、冻结规则或排除原因校验失败各保留独立分类，不输出模型原始响应或把故障当成业务排除。

## 代码配套与验收

配套代码取正式合同 `implementation_bindings` 的全部 `kind=code` 项，并按本轮冻结源码校验；由 `leadgen-activity-methods.lock.json` 固定本Skill和代码集合。代码文件存在不代表可由Agent直接调用，公共入口以[当前调用映射](../douyin-leadgen-103/references/runtime-calls.json)为准。

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
