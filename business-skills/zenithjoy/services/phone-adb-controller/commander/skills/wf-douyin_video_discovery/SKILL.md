---
name: wf-douyin_video_discovery
version: 0.6.1
description: "抖音视频发现 wf_run 陪跑说明：显式加载本次冻结业务Skill，保持原合同与安全交接边界。"
---

# 抖音视频发现陪跑

此薄 wrapper 对应 `product-map/contracts/douyin_video_discovery.yaml` 的 `commander_skill`；业务真身只有 `services/phone-adb-controller/skills/douyin-leadgen-101/SKILL.md`，不在此复制动作。

当前 `wf_run` 须由 Agent 显式加载本 wrapper 和业务 Skill，自动调用未接好。此字段入冻结合同不表示 runner 已调用 Skill，也不把本流程改成通用 Commander 的 `codex_agent` 或 commander-v2 执行协议。

先从本run已验证的冻结部署清单读取工作流业务Skill `runtime/skills/douyin-leadgen-101/SKILL.md` 及其 `references/activity-methods.json`、`runtime-calls.json`、`reuse-map.json`，核对本run源码和每文件SHA。再从 `run-definition.json` 对应Activity的 `implementations` 选择确切 `kind: skill`、name/version/source/digest，并按真实 `execution_path` 读取独立Activity Skill及其支持文件。Workflow清单必须与各Activity冻结绑定完全一致；不能再把整流程业务Skill路径当成每个Activity方法。最新部署副本或本机Codex链接不能代替本run冻结字节，缺绑定或原件即阻断。

执行前确认 workflow_key 为 `douyin_video_discovery`，实际公司、line、profile、serial、run_id、attempt、source_run（适用时）、执行权、截止时间及锁/租约均与冻结事实一致。保持原 Activity Commander、定义ACK、原件及PG独立读回；不改现场代码、不换账号、不扩大预算或输入范围。

`mode=workflow` 仅在当前业务 Skill 的正式完整CLI满足本轮范围时执行该流程；`mode=activity` 只处理指定冻结 Activity。仅接受原run已生成的leadgen-activity-v1请求及其私有broker工具；无法安全移交当前执行权或工具缺失时保留原失败及恢复条件并报告 BLOCKED，不能重跑整流程冒单步接手、使用 `leadgen-activity.sh` 冒 resume、直调裸queue/RPC函数、并发接管活动run或回退旧流程。旧Skill参考仅加载 reuse-map 明确适用动作，不把 reference_only 当可执行fallback。

只处理101视频发现。本流程共享的设备预检与收尾引用 douyin_video_processing.preflight / cleanup；遇到这两个 Activity，显式加载冻结的 douyin-leadgen-102，只执行其预检或收尾范围，不启动102资格判断或评论采集。collect_videos 5.1.1保留正式输出 `Video.discovery_metrics`（运行结果 `Video.metrics`）及 `discovery_metrics_verified == 1`：同视频原件重算、独立PG完整观测与公司绑定读回均通过；发现链接或旧观测存在不能冒充指标已持久化。unknown不填0，旧观测拒绝不能计成功。本版方法配套仍awaiting-real-run，候选源码修复不代表运行宿主已发布或本版实机验收通过。

交接只报告实际运行、逐活动/Step核验、清理及业务读回；代码退出0、合同可加载或 planned登记均不等于业务PASS。未知外部副作用先取合法读回，不能补造证据或重放动作。

判读数量时读取本次冻结的 `discovery_input`：schema 1 严格限首屏卡片数，超额零候选动作；schema 2 显式 `max_attempts` 才允许首屏较多时处理前 N 槽位。实际显示、尝试、唯一保存和新增数分别读回；重复/失败/缺身份消耗尝试，不为凑数量建议新 run 或翻屏。schema 2 无失败/缺口且 `attempt_limit_reached` 仅本次采样完成，`all_results_scanned=false` 不能说搜尽；执行未知仍阻断，不以新方法洗旧 strict 失败。完整输入约束取业务 Skill 的本次版本。

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
