---
name: douyin-leadgen-activity-104-preflight
description: 取得已授权触达上下文。用于触达前核对发送账号、批准政策与资源或接手同一预检 Activity；不执行整个工作流。
metadata:
  version: 0.2.0
  activity_ref: douyin_lead_outreach.preflight
  activity_version: 4.1.0
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/leadgen-activity-execution.md
---

# 取得已授权触达上下文

仅执行 `douyin_lead_outreach.preflight`。业务合同版本为 `4.1.0`；方法版本独立记录，不因生成代码而更换Activity身份。

先读取[共同执行与升级约束](../leadgen-activity-execution.md)，再读本轮冻结的[所属工作流Skill](../douyin-leadgen-104/SKILL.md)中与本活动有关的配置、复用来源和授权。输入输出、验收探针以[正式Activity合同](../../../../product-map/contracts/douyin_lead_outreach.yaml)的 `preflight` 为准；本文件不覆盖该合同或公司政策。

## 输入输出

- 输入 `Device`：`serial`、`host`、`lock_holder`。
- 输入 `Account`：`platform`、`profile`、`sender_id`、`dm_paused`、`daily_cap`。
- 输入 `Lead`：`douyin_id`、`profile_url`、`intent_grade`、`repeat_hits`、`status`。
- 输入 `RecipientQualification`：`line_key`、`comment_id`、`status`、`company_id`、`company_version`、`native_profile_sha256`、`reason`、`tenant_id`、`policy_id`。
- 输出 `Device`：`online`、`call_state`、`lock_holder`。
- 输出 `Account`：`logged_in`。
- 输出 `Run`：`run_tag`、`profile`、`serial`。
- 输出 `OutreachOrder`：`sender_id`。

公司、task/run、截止、源码及执行权从本次正式绑定读取。缺字段保持缺失并报告，不从示例或其他租户补。

## 方法

1. 本Activity独立于102预检。读取本公司已启用104配置、当前发送账号/profile/serial、批准话术、目标范围和当前限额，缺项不能从其他公司补。
2. 核对实际部署release、运行绑定、发送授权、真实登录账号、设备空闲及双层锁owner；已有本会话授权持续有效，不重复索要。
3. 核对现行暂停、冷却、风险与额度。Skill不绕过暂停或换账号绕风控；已授权迁移暂停也只能走精确hash/owner可回读恢复步骤。
4. 检查canonical合格订单、prepared/已发送/未知历史和独占执行权。原动作结果未知先读回；预检不点击发送、不自动清除prepared。

## 代码配套与验收

配套代码取正式合同 `implementation_bindings` 的全部 `kind=code` 项，并按本轮冻结源码校验；由 `leadgen-activity-methods.lock.json` 固定本Skill和代码集合。代码文件存在不代表可由Agent直接调用，公共入口以[当前调用映射](../douyin-leadgen-104/references/runtime-calls.json)为准。

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
