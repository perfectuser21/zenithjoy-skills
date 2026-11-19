---
name: wf-douyin_lead_outreach
version: 0.9.0
description: "抖音线索触达 wf_run 陪跑说明：显式加载本次冻结业务Skill，保持原合同与安全交接边界。"
---

# 抖音线索触达陪跑

此薄 wrapper 对应 `product-map/contracts/douyin_lead_outreach.yaml` 的 `commander_skill`；业务真身只有 `services/phone-adb-controller/skills/douyin-leadgen-104/SKILL.md`，不在此复制动作。

使用本run实际冻结的执行入口、方法及工具；本wrapper只组织和交接，不赋予另开旧CLI、重派执行者或改变协议的权限。

`send_dm` 只按当前Activity合同核真实发送结果；没有原生发送证据保持失败或未知，不以旧specific探针名字或执行者自述替代证据。

先从本run已验证的冻结部署清单读取工作流业务Skill `runtime/skills/douyin-leadgen-104/SKILL.md` 及其 `references/activity-methods.json`，核对本run源码和每文件SHA。再从 `run-definition.json` 对应Activity的 `implementations` 选择确切 `kind: skill`、name/version/source/digest，并按真实 `execution_path` 读取独立Activity Skill及其支持文件。Workflow清单必须与各Activity冻结绑定完全一致；不能再把整流程业务Skill路径当成每个Activity方法。最新部署副本或本机Codex链接不能代替本run冻结字节，缺绑定或原件即阻断。

执行前确认 workflow_key 为 `douyin_lead_outreach`，实际公司、line、profile、serial、run_id、attempt、source_run（适用时）、执行权、截止时间及锁/租约均与冻结事实一致。保持原 Activity Commander、定义ACK、原件及PG独立读回；不改现场代码、不换账号、不扩大预算或输入范围。

本次只组织冻结Workflow及其明确Activity；执行者使用当前提供的独立Activity Skill和获授权工具，不要求先制造Code失败或调用旧handler。接手不能重跑整流程、伪造旧broker请求、并发接管活run或绕过源/身份/资源权限；失败与未知保留原件。

只处理104 canonical ready队列的已批准触达与写回。保持原prepared、一次发送、全池去重、账号及原生目标身份、批准正文、风险和ratecaps；暂停未解除不发送。已发送或结果未知先按原状态机读回，不重复POST、不释放prepared重发，不用裸private-message-send或旧outreach-tick代替正式入口。

普通 `company_queue` 入口按公司资格队列领取；单条授权验收须显式 `LEADGEN_OUTREACH_MODE=exact` 并提供私有 `LEADGEN_OUTREACH_SCOPE_FILE`，冻结飞书记录、comment及来源。精确输入缺失或不符不得退回普通队列。

交接只报告实际运行、逐活动/Step核验、清理及业务读回；代码退出0、合同可加载或 planned登记均不等于业务PASS。未知外部副作用先取合法读回，不能补造证据或重放动作。

陪跑者只根据真实事件提供指导或停止建议，不代替执行者操作、不批准发送、不改状态。执行权限、截止、停止事实由原运行机制管理；验收交给独立通用Checker，指导或abort请求本身不是已停止证明。

## 方法升级

本流程依赖的Activity方法版本由业务Skill的 `references/activity-methods.json` 精确登记。方法变化要同步本陪跑Skill版本与合同 `commander_skill.version`；Commander只使用本run冻结组合。代码内部兼容评估、Skill实机验收和自动handoff能力分别记证据，不从文件存在推定已能接手。

## 合同、执行提案与独立验收

读取本run冻结的完整当前Activity Contract，核对来源、Activity身份、版本与摘要；输入输出、前后条件、DoD及已选公司政策以该合同为准，不从旧specific检查列表另立标准。执行者交付的是执行提案和原始证据，不是验收结论；独立通用Checker读取同一合同并用只读工具核实事实。模型自述、工具verified摘要或退出0不能代替原件，也不能替下一Activity判通过。

预算只引用冻结Activity Contract的 `budget` 与本run原绝对截止：业务受 `run.deadline_ms` 约束，收尾受 `run.cleanup_deadline_ms` 约束，实际可用时间取适用Activity预算和相应绝对截止的更早者。换Activity、恢复或新工具调用不重置剩余时间；不得挪用收尾窗口新增业务。

`agent_recovery` 仅声明方法可选能力，不是本次重试额度。只有本run实际冻结的 `runtime.checker_repair` 明确授权、剩余额度与原截止仍有效时，才按失败原因和证据进行允许的返工；没有该设置不自行增回合。保留原Task/run、动作身份和已成功成果；未知副作用先读回，未知不重做，不能换nonce或generation重放。返工不增加本次批次、评分、录制或发送授权，不重复已成功业务动作。Checker不执行业务写入，也不授予发送权。

## 宿主恢复能力声明

以下 `agent_recovery` 只描述可选能力，不能被解释为本次已选额度。实际是否允许返工及其次数只读本run冻结的 `runtime.checker_repair`；原授权、动作累计次数、未知不重做和绝对截止仍约束所有回合。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
