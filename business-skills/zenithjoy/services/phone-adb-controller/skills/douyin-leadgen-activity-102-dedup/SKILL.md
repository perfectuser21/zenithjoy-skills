---
name: douyin-leadgen-activity-102-dedup
description: 交出本轮可处理的视频集合。用于核验101来源、筛选与认领视频或接手同一判重 Activity；不执行整个工作流。
metadata:
  version: 0.4.1
  primary_execution: agent-v1
  activity_ref: douyin_video_processing.dedup
  activity_version: 3.2.1
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/leadgen-activity-execution.md
---

# 交出本轮可处理的视频集合

仅执行 `douyin_video_processing.dedup`。业务合同版本为 `3.2.1`；方法版本独立记录，不因生成代码而更换Activity身份。

先读取[共同执行与升级约束](../leadgen-activity-execution.md)，再读本轮冻结的[所属工作流Skill](../douyin-leadgen-102/SKILL.md)中与本活动有关的配置、复用来源和授权。输入输出、验收探针以[正式Activity合同](../../../../product-map/contracts/douyin_video_processing.yaml)的 `dedup` 为准；本文件不覆盖该合同或公司政策。

## 从第一步执行本 Activity

本版支持 Runner 正式选择的 `mode=execute`，以及原有失败后接手模式；共同执行约束中关于 Code 失败、原 handler 和 resume 的条款只用于失败接手，不用于 `execute`。只执行本次指定的一个 Activity，不自行启动、切换或重启 Workflow。

`execute` 必须由本 run 的冻结 `execution_mode=agent`、中央不可变 `actor=runtime:phone-adb-controller:agent-v1` 声明及原 runtime snapshot、来源、方法和资源绑定共同准入。actor 是运行声明，不是权限或执行成功证明；Agent 不创建绑定、不改 actor、不调用内部 RPC 或裸队列。缺合法工具或准入即报告具体阻断。

仓库 YAML 链接仅定位业务合同来源，不要求执行目录具有该仓库。执行时读取本次 `request.method.contract` 中由 Runner 与中央固定 Activity 版本核验过的 `payload`、`sha256` 和版本身份；缺该原件即报告缺失，不从最新仓库、链接不存在或自拟内容补合同。

1. 先核官方 child 绑定与本次私有 request 的 run、task、Activity、来源、方法和截止，调用 `inspect` 读取输入、当前原件、允许操作及 Commander 指导。
2. 只用本 request 给出的 `phone` 和 `business` 工具逐步执行。`phone` 输入为 `{command,args}`，`business` 输入为 `{operation,input}`；操作及字段以服务端本 Activity 当前实际暴露的 schema 为准，不猜操作名或自己扩白名单。锁和资源由 Runner 代码管理，Agent 不能更换 owner、公司、账号、设备、来源、额度或截止。
3. 按下文业务方法，从新鲜原生证据选择每一步，调用细粒度操作并保存/读回结果。禁止 `resume`、调用原 Activity handler、整段 `collect-comments` 或用整工作流脚本代替本 Activity。资格与评分沿原公司政策及实际授权的判断工具，不自己改阈值或补造证据。
4. 副作用调用保留原持久操作身份。回执丢失、写入或原生动作结果未知时只读回同一操作，不重新提交、不换 operation ID 重做。确认 0 评论不得入待采队列；无结果、部分成果和真实空结果分别交付。
5. 进度、问题或错误通过 `inspect` 的结构化事件报告。下一回合读取并处理 `commander_guidance`；收到 `commander_abort` 停止本 child。Commander 不批准外部动作，不改业务顺序、规则或状态。
6. 交付本次工具产生的持久结果及证据位置。Agent 的完成文字不是结果，Runner 根据服务端回执、原件、PG 及原独立 verify 判定；无法验证时明确未完成。执行终态未知保留隔离，不能为下一 Activity 清场。

`execute` 不适用于 104；本版正常执行与故障接手均仍需分别留实机证据，状态保持 `awaiting-real-run`。

## 输入输出

- 输入 `Video`：`video_id`、`author`、`comment_count`、`keyword`。
- 输出 `Video`：`video_id`、`author`、`comment_count`、`keyword`。

公司、task/run、截止、源码及执行权从本次正式绑定读取。缺字段保持缺失并报告，不从示例或其他租户补。

## 方法

1. 验证真实101来源运行、已冻结定义、对应VID与公司归属，不能拿最新目录名或未绑定旧批次替代来源。
2. 读取原正式队列，排除合法完成、确认不合格及被其他有效租约持有的视频。按真实video_id判断，不用标题或昵称当唯一身份。
3. 通过现有原子领取协议持有本轮视频集合；丢失回复先读回领取归属，不重复创建竞争领取。
4. 分别输出received、eligible、已完成跳过及其他排除原因，保留逐VID和租约证据；不在判重阶段录音或评分。

## 显式v2固定来源范围

仅在所属工作流已按正式入口冻结并通过validator核验的 `producer_descriptor.schema_version=2` 时，接受其固定a83／beb原来源：完整两VID定义与进度原字节、snapshot／progress固定哈希及所有冻结文件闭包均须通过；不能裁剪为目标一条或重写旧来源。范围只含 `7689863996204591985`，其他公司、批次、profile／serial或VID均拒绝。缺省同来源和原v1保持；该描述符不是通用跨版、隔离恢复或设备授权。

交出来源与排除证据后，实际领取仍由qualification所调用的正式队列事务执行；事务必须重验当前仍 `pending`／`待判定` 且 `harvest_batch` 为原101、公司完整冻结政策和账号绑定一致，最多1条。不以先前读回替代领取紧前CAS，不借普通队列15分钟重领，领取0条不换领。保留旁VID `7700112581541257551` 的人工状态。UI评论总量未知保持unknown，不用旧PG默认0代替原生总量。

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
