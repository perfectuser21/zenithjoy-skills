---
name: wf-douyin_video_processing
version: 0.9.0
changelog:
  - "0.9.0: 同步共享预检与清场的正式预算合同及方法依赖，原总额与授权不变"
  - "0.8.0: 同步official-child-v1精确内部宿主兼容；原授权和验收边界不变"
  - "0.7.0: 同步正常执行无工具回合方法；保留旧child恢复"
  - "0.4.0: 同步活动合同的承诺、来源去向与可判定读回；样本仍待业务核准"
  - "0.3.4: 同步102规范块格式兼容版本，方法合同与授权范围不变"
  - "0.3.3: 配套固定a83/beb单pending来源交接及事务领取方法，默认同源与v1不变"
  - "0.3.1: 配套collection0.2.1的显式零评论证据合同，沿冻结方法验收"
description: "抖音视频处理 wf_run 陪跑说明：显式加载本次冻结业务Skill，保持原合同与安全交接边界。"
---

# 抖音视频处理陪跑

此薄 wrapper 对应 `product-map/contracts/douyin_video_processing.yaml` 的 `commander_skill`；业务真身只有 `services/phone-adb-controller/skills/douyin-leadgen-102/SKILL.md`，不在此复制动作。

当前 `wf_run` 须由 Agent 显式加载本 wrapper 和业务 Skill，自动调用未接好。此字段入冻结合同不表示 runner 已调用 Skill，也不把本流程改成通用 Commander 的 `codex_agent` 或 commander-v2 执行协议。

先从本run已验证的冻结部署清单读取工作流业务Skill `runtime/skills/douyin-leadgen-102/SKILL.md` 及其 `references/activity-methods.json`、`runtime-calls.json`、`reuse-map.json`，核对本run源码和每文件SHA。再从 `run-definition.json` 对应Activity的 `implementations` 选择确切 `kind: skill`、name/version/source/digest，并按真实 `execution_path` 读取独立Activity Skill及其支持文件。Workflow清单必须与各Activity冻结绑定完全一致；不能再把整流程业务Skill路径当成每个Activity方法。最新部署副本或本机Codex链接不能代替本run冻结字节，缺绑定或原件即阻断。

执行前确认 workflow_key 为 `douyin_video_processing`，实际公司、line、profile、serial、run_id、attempt、source_run（适用时）、执行权、截止时间及锁/租约均与冻结事实一致。保持原 Activity Commander、定义ACK、原件及PG独立读回；不改现场代码、不换账号、不扩大预算或输入范围。

`mode=workflow` 仅在当前业务 Skill 的正式完整CLI满足本轮范围时执行该流程；`mode=activity` 只处理指定冻结 Activity。仅接受原run已生成的leadgen-activity-v1请求及其私有broker工具；无法安全移交当前执行权或工具缺失时保留原失败及恢复条件并报告 BLOCKED，不能重跑整流程冒单步接手、使用 `leadgen-activity.sh` 冒 resume、直调裸queue/RPC函数、并发接管活动run或回退旧流程。旧Skill参考仅加载 reuse-map 明确适用动作，不把 reference_only 当可执行fallback。

只处理102资格与评论采集。来源必须是本次冻结并合法验证的101 source_run；保持实际VID、音频、评论者身份、正文和返回面板守卫。首轮5评论与后续分档按授权及业务Skill支持情况执行，未实施分档不能冒称自动支持。

交接须保留本轮 qualification 主 span 的逐 VID 身份、旧判断 run 与 collection 主 span 的精确评论 ID；旧 PG 判断 run 不重写。交接只报告实际运行、逐活动/Step核验、清理及业务读回；代码退出0、合同可加载或 planned登记均不等于业务PASS。未知外部副作用先取合法读回，不能补造证据或重放动作。

本版显式v2 producer交接只按业务Skill已冻结范围处理a83／beb的唯一pending VID `7689863996204591985`，加载dedup／qualification `0.2.2`。完整原两VID来源、固定哈希与consumer自身真实来源保持，事务领取最多1条／采集最多5评论及480秒；领取0条不换领，旁VID人工状态不恢复。不把它当通用跨版、新搜索或发送许可，原v1／缺省同源与原2秒、未知拒绝边界不变；新组合的实机验收仍未完成。

## 方法升级

本流程依赖的Activity方法版本由业务Skill的 `references/activity-methods.json` 精确登记。方法变化要同步本陪跑Skill版本与合同 `commander_skill.version`；Commander只使用本run冻结组合。代码内部兼容评估、Skill实机验收和自动handoff能力分别记证据，不从文件存在推定已能接手。

本版依赖 `douyin-leadgen-102@0.9.0` 及 `douyin-leadgen-activity-102-qualification@0.6.0`。仅把明确通知暂态交给该方法有界被动复读；同run/Activity/owner、最多两次只读证和一次原slot resume及原独立verify不变。未知或活跃录制不借陪跑清场，未有实际交接证据仍不宣称Skill救场成功。


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
