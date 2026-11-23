---
name: wf-douyin_comment_scoring
version: 0.20.2
changelog:
  - "0.15.0: 同步official-child-v1精确内部宿主兼容；原授权和验收边界不变"
  - "0.14.0: 同步正常执行无工具回合方法；保留旧child恢复"
description: "抖音评论评分 wf_run 陪跑说明：显式加载本次冻结业务Skill，保持原合同与安全交接边界。"
---

# 抖音评论评分陪跑

本wrapper仅说明正式 `wf_run` 的冻结宿主兼容；普通API独立Activity直接使用各Activity方法，不加载本wrapper。

此薄 wrapper 对应 `product-map/contracts/douyin_comment_scoring.yaml` 的 `commander_skill`；业务真身只有 `services/phone-adb-controller/skills/douyin-leadgen-103/SKILL.md`，不在此复制动作。

使用本run实际冻结的执行入口、方法及工具；本wrapper只组织和交接，不赋予另开旧CLI、重派执行者或改变协议的权限。

先从本run已验证的冻结部署清单读取工作流业务Skill `runtime/skills/douyin-leadgen-103/SKILL.md` 及其 `references/activity-methods.json`，核对本run源码和每文件SHA。再从 `run-definition.json` 对应Activity的 `implementations` 选择确切 `kind: skill`、name/version/source/digest，并按真实 `execution_path` 读取独立Activity Skill及其支持文件。Workflow清单必须与各Activity冻结绑定完全一致；不能再把整流程业务Skill路径当成每个Activity方法。最新部署副本或本机Codex链接不能代替本run冻结字节，缺绑定或原件即阻断。

执行前确认 workflow_key 为 `douyin_comment_scoring`，实际公司、line、profile、serial、run_id、attempt、source_run（适用时）、执行权、截止时间及锁/租约均与冻结事实一致。以下整run来源约束仅用于formal正式102配额抽样：只在Brain原绑定、pass/verified、冻结上限与公司、Brain qualification/collection 两主 span 同绑定同 SHA 逐 VID 原生身份，以及 collection 点名的精确评论ID和PG规范行摘要核实后接纳；未全采视频仍保“待判定”，软预算与失败102仍隔离。金诺102d跨SHA仅限固定历史桥；金诺102g失败来源仍须用户决定、原生终止证明与PG审计回执，且只绑定单一103 run。ordinary `committed_partial_ids` 则按本次冻结合同与103方法分支，精确消费已提交且原生身份、视频资格和公司政策均已核实的评论，不要求整个102成功；不遍历旁单或借formal历史例外放行。保持原 Activity Commander、定义ACK、原件及PG独立读回；不改现场代码、不换账号、不扩大预算或输入范围。

本次只组织冻结Workflow及其明确Activity；执行者使用当前提供的独立Activity Skill和获授权工具，不要求先制造Code失败或调用旧handler。接手不能重跑整流程、伪造旧broker请求、并发接管活run或绕过源/身份/资源权限；失败与未知保留原件。

只处理103原政策评分与标记，独立消费已提交PG评论；使用冻结公司原评分政策。MMV/none不占手机锁或手机中央租约。处理范围和批量只取本次冻结输入与合同，不能以接口最大容量冒充本轮授权或剩余预算。

本版沿用主理人决定 `8331c673-1113-4a04-a5dd-54ec76a916fe`：每条评论按冻结公司规则评估一次并持久化实际模型响应身份、理由与原文证据；`policy_review`及mark_leads仅确定性核验已存评分与原生身份，不追加模型复核。不相关保存真实不相关结论及空等级，不制造Lead/outbox；历史已排除行保留审计。模型/HTTP/网络故障、画像或引用不能验证时保持未决，不把技术失败当业务排除。已有有效评分先读回复用，不为补审重评；若旧冻结宿主仍要求双审，报告实现/合同不兼容，不拼造第二份响应或放宽旧绑定。

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
