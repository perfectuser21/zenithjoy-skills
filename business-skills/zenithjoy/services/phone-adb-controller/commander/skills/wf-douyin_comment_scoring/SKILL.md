---
name: wf-douyin_comment_scoring
version: 0.16.0
changelog:
  - "0.15.0: 同步official-child-v1精确内部宿主兼容；原授权和验收边界不变"
  - "0.14.0: 同步正常执行无工具回合方法；保留旧child恢复"
description: "抖音评论评分 wf_run 陪跑说明：显式加载本次冻结业务Skill，保持原合同与安全交接边界。"
---

# 抖音评论评分陪跑

此薄 wrapper 对应 `product-map/contracts/douyin_comment_scoring.yaml` 的 `commander_skill`；业务真身只有 `services/phone-adb-controller/skills/douyin-leadgen-103/SKILL.md`，不在此复制动作。

当前 `wf_run` 须由 Agent 显式加载本 wrapper 和业务 Skill，自动调用未接好。此字段入冻结合同不表示 runner 已调用 Skill，也不把本流程改成通用 Commander 的 `codex_agent` 或 commander-v2 执行协议。

先从本run已验证的冻结部署清单读取工作流业务Skill `runtime/skills/douyin-leadgen-103/SKILL.md` 及其 `references/activity-methods.json`、`runtime-calls.json`、`reuse-map.json`，核对本run源码和每文件SHA。再从 `run-definition.json` 对应Activity的 `implementations` 选择确切 `kind: skill`、name/version/source/digest，并按真实 `execution_path` 读取独立Activity Skill及其支持文件。Workflow清单必须与各Activity冻结绑定完全一致；不能再把整流程业务Skill路径当成每个Activity方法。最新部署副本或本机Codex链接不能代替本run冻结字节，缺绑定或原件即阻断。

执行前确认 workflow_key 为 `douyin_comment_scoring`，实际公司、line、profile、serial、run_id、attempt、source_run（适用时）、执行权、截止时间及锁/租约均与冻结事实一致。正式102配额抽样只在Brain原绑定、pass/verified、冻结上限与公司、Brain qualification/collection 两主 span 同绑定同 SHA 逐 VID 原生身份，以及 collection 点名的精确评论ID和PG规范行摘要核实后接纳；未全采视频仍保“待判定”，软预算与失败102仍隔离。金诺102d跨SHA仅限固定历史桥；金诺102g失败来源仍须用户决定、原生终止证明与PG审计回执，且只绑定单一103 run。保持原 Activity Commander、定义ACK、原件及PG独立读回；不改现场代码、不换账号、不扩大预算或输入范围。

`mode=workflow` 仅在当前业务 Skill 的正式完整CLI满足本轮范围时执行该流程；`mode=activity` 只处理指定冻结 Activity。仅接受原run已生成的leadgen-activity-v1请求及其私有broker工具；无法安全移交当前执行权或工具缺失时保留原失败及恢复条件并报告 BLOCKED，不能重跑整流程冒单步接手、使用 `leadgen-activity.sh` 冒 resume、直调裸queue/RPC函数、并发接管活动run或回退旧流程。旧Skill参考仅加载 reuse-map 明确适用动作，不把 reference_only 当可执行fallback。

只处理103原政策评分与标记，独立消费已提交PG评论；使用冻结公司原评分政策。MMV/none不占手机锁或手机中央租约。mark资格每人最多15秒且RPC180秒，首批5、建议每批不超过10，不能以语法允许50冒充本轮可完成50。

评分须在同一事务中取得两份有效且响应身份不同的政策证据后才持久化；两次独立复核一致缺个人意向或受众/话题证据时，评论另记为 `已排除`，清空旧评分并留安全原因与双审摘要。评分和排除分别从PG独立读回；mark_leads只消费真评分，已排除评论不得建Lead、outbox或104订单，纯排除批次可空消费。模型/HTTP/网络故障、双审分歧及身份复用仍待分拣重试。旧单份证据保持unknown，不凭旧评分直接建线索，也不补第三次政策模型调用。

交接只报告实际运行、逐活动/Step核验、清理及业务读回；代码退出0、合同可加载或 planned登记均不等于业务PASS。未知外部副作用先取合法读回，不能补造证据或重放动作。

## 方法升级

本流程依赖的Activity方法版本由业务Skill的 `references/activity-methods.json` 精确登记。方法变化要同步本陪跑Skill版本与合同 `commander_skill.version`；Commander只使用本run冻结组合。代码内部兼容评估、Skill实机验收和自动handoff能力分别记证据，不从文件存在推定已能接手。


## 同run有界Agent恢复合同

以下仅是原冻结Activity合同的显式opt-in形状，不是模型或方法自行授予的执行额度：

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```

从本run对应的 `version.payload.contract.agent_recovery` 核此对象：仅允许唯一键 `max_additional_turns`、值为整数1；字段缺省保持原一次性接手，非法值或多余键阻断。一次额外Agent turn不是新Workflow attempt，不增加业务次数或预算。 `send_dm`不启用额外Agent turn，仍按原单次 `readback_only`；opt-in是恢复上限，不扩大该限制。

仅对本run已冻结opt-in的Activity执行该方法恢复政策：同一次recover、同broker/原业务nonce内最多额外一个Agent turn，原owner与child官方停止双证和原权限/截止仍是前置。原resume一次、native读证两次累计不重置；resume已用后仅inspect/readback/verify。generation精确授权并撤销旧child；unknown、send_dm只读、collection partial及能力/权限阻断守卫不变。最终仅原独立verify决定继续，不能把额外turn当新业务attempt、发送额度或清场许可。当前配套及实机能力以实际发布/验收为准。

## Agent 从第一步执行的观察职责

当原固定 request.mode 为 execute 时，Agent 从首步执行当前 Activity，不要求先制造 Code 失败，也不要求它 resume 原 handler。仅根据真实事件提供 answer、steer 或 abort；明确指出相关规则或完成标准。执行模式、受控操作、截止及结果验收仍由 Runner 管。不得替 Agent 执行、批准发送或改状态；源/权限/未知停止证明缺口不能用指导越过。Skill 与代码接手的实机结果分别记录。

正常执行采用新方法明确冻结的 `execution_transport=raw-model-v1` 时，只观察父 Code 转发的事件与证据并给纠偏；不自行调用 child/spawn/CLI。父 Code 管理官方无工具回合身份、原 broker 执行和完整终态。旧 child 及失败恢复合同不变，不能将两种收据混用；本版仍待实机验收。
