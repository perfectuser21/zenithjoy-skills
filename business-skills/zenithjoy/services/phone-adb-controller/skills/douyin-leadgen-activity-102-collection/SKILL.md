---
name: douyin-leadgen-activity-102-collection
description: 交出持久化且身份可验证的评论。用于从合格视频采集评论并读回或接手同一评论采集 Activity；不执行整个工作流。
metadata:
  version: 0.2.0
  activity_ref: douyin_video_processing.collection
  activity_version: 2.5.0
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/leadgen-activity-execution.md
---

# 交出持久化且身份可验证的评论

仅执行 `douyin_video_processing.collection`。业务合同版本为 `2.5.0`；方法版本独立记录，不因生成代码而更换Activity身份。

先读取[共同执行与升级约束](../leadgen-activity-execution.md)，再读本轮冻结的[所属工作流Skill](../douyin-leadgen-102/SKILL.md)中与本活动有关的配置、复用来源和授权。输入输出、验收探针以[正式Activity合同](../../../../product-map/contracts/douyin_video_processing.yaml)的 `collection` 为准；本文件不覆盖该合同或公司政策。

## 输入输出

- 输入 `CommentSampleRequest`：`run_tag`、`source_run`、`profile`、`serial`、`line`、`comment_limit`、`collection_budget_s`。
- 输入 `Video`：`line_key`、`video_id`、`video_url`、`judgment_status`。
- 输入 `Device`：`serial`、`lock_holder`。
- 输入 `Account`：`sender_id`、`nickname`。
- 输入 `Run`：`run_tag`。
- 输入 `HistoricalComment`：`id`、`line_key`、`run_tag`、`source_run`、`video_id`、`video_url`、`schema_version`、`status`、`douyin_id`、`body`、`history_sha256`、`coverage`。
- 输出 `Comment`：`line_key`、`dedup_key`、`nickname`、`douyin_id`、`profile_url`、`body`、`video_id`、`harvest_batch`、`recipient_evidence`。
- 输出 `Video`：`process_status`。

公司、task/run、截止、源码及执行权从本次正式绑定读取。缺字段保持缺失并报告，不从示例或其他租户补。

## 方法

1. 只处理本轮已领且资格合格的视频；核对本任务冻结的comment_limit、策略和截止；配额取当前任务授权值，接手不能扩大。本次验收授权每合格视频5条，不把这个样本数写成所有任务的固定上限。
2. 逐屏读取评论，保留正文、原显示时间地区、评论人稳定身份、主页/视频链接和原生关联证据；相关搜索词、仅昵称或缺身份的测速结果不当完整评论。
3. 优先真实评论ID幂等；没有ID按原正式组合键去重并说明局限。每小批走原事务提交，之后独立读回完整UID、正文、URL、公司与来源。
4. 原生头像/主页核验失败保持未决，不用相似账号或模型猜测补身份。别名URL只有同真实VID且正式读回接口验证时才可复用。
5. 分别累计新增、历史核实、重复、实际覆盖；提交失败不计成功。达到本任务comment_limit是采样达标，不代表评论已采尽；保留部分成果和最后成功批次。

## 代码配套与验收

配套代码取正式合同 `implementation_bindings` 的全部 `kind=code` 项，并按本轮冻结源码校验；由 `leadgen-activity-methods.lock.json` 固定本Skill和代码集合。代码文件存在不代表可由Agent直接调用，公共入口以[当前调用映射](../douyin-leadgen-102/references/runtime-calls.json)为准。

按正式合同的后置探针、原始证据及持久化读回验收；区分Code结果、Skill接手结果和清理结果。单Activity接手入口为原run的 `activity-skill-tool.mjs <broker-request.json> inspect|phone|resume`；只能使用本次持久handoff给出的冻结路径，不能自己建request、换run或直接启动Workflow。源码接线与Skill实机接手验收分别记证据，当前方法仍 awaiting-real-run。

## 本方法的真实接手入口

Code失败、分类与有限安全重试后，由原run的handoff broker持有同一Activity闭包、身份、资源和截止。真实work-commander父会话经官方sessions_spawn派本Skill子会话；先核原request/nonce及自己的绑定。只调用本次给出的工具路径：`inspect`读取实际进度；`phone`经stdin JSON `{command,args}`仅读证或受控归位；必要时 `resume`仅继续当前slot的成熟Code一次。不得构造新Workflow、改源码/策略/账号/暂停或另取/释放锁。

`send_dm`失败一律readback_only，不能resume或点击发送；没有确定发送证据保持unknown。Skill交付不直接写成功，原进程按原verify/Step/PG读回独立裁判。子会话终态未知保留资源，不能清场干扰未知执行者。没有正式已绑定子会话或source/method/预算不符即blocked。

## 本轮冻结账号来源

MMV102首个设备动作前把选定profile/serial冻结到本run的company_config_runs.task_inputs.device_binding，再核当前原生抖音号；实号通过后生成本run私有company-binding工件。原生评论证明、解析和PG提交必须消费同一绑定，PG按原102冻结行重验公司/租户/平台与唯一verified enabled账号；不将原件自报字段当授权，不为缺失历史来源新建快照。旧M4无此新工件的路径保持原守卫。

评论区StepDoD只接受抖音原生 `ety`、`e19` 或 `eyi` EditText 与原生精确评论数量header配对；资源、class和package须同时成立。该面板证据不替代逐VID的新鲜nonce与identity sidecar，也不替代评论身份和持久化读回。


## 同run有界Agent恢复合同

以下仅是原冻结Activity合同的显式opt-in形状，不是模型或方法自行授予的执行额度：

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```

从本run对应的 `version.payload.contract.agent_recovery` 核此对象：仅允许唯一键 `max_additional_turns`、值为整数1；字段缺省保持原一次性接手，非法值或多余键阻断。一次额外Agent turn不是新Workflow attempt，不增加业务次数或预算。

Code失败或Code实际产出未过原verify时，首次Skill接手仍走原入口；首次Skill/Agent已确认失败或其实际产出未过原verify时，由唯一work-commander在同一次recover与原broker存活期内决定是否用这一次额外turn。先取得原owner和原child精确官方终态及停止证明，并确认broker无在途操作、原资源授权有效且尚在原Activity执行截止；父CLI或子终态未知、外部写入（含发布/发送）结果未知均不重派、不清pending、不刷新TTL。模型自述、CLI退出0或预览页不能替代这些证明。

保留同run/task/binding/source/Activity、原业务nonce、原handler闭包与已成功VID。每turn只增加不可覆盖的transport generation及官方child绑定，引用原业务nonce；先撤销旧child工具权，再精确授权当前generation，旧child迟到调用/回执不得执行或覆盖新证据。不得删除原launch/binding/closed记录，不能换nonce或重建broker重置额度。

原broker的resume总计最多一次，原生读证总计最多两次，失败调用也消费相应额度。resume前Agent失败且余量合法才可继续使用尚未消耗的resume；resume已预留或业务已执行后，后继turn仅inspect/readback/verify，禁止再resume、受控归位或其他业务动作。资格恢复沿原成功VID集合及每VID次数，不重领、不重录成功项。send_dm始终readback_only；collection partial、能力/权限/来源阻断仍按原规则停止。所有turn共享原截止，不挪用cleanup预算执行业务。

原进程独立verify及真实持久读回通过后才继续后续Activity；无结果不能靠新child文本补成功。额外turn耗尽、剩余预算不足或仍核验失败即准确failed/partial/unknown并保原证，不承诺每种障碍都能救回。本版仍awaiting-real-run，配套源码、发布与实机验收分别留证。
