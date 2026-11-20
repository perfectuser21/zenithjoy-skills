---
name: douyin-leadgen-102
description: Workflow 102的活动组织与交接目录；实际执行由各Activity自己的Skill完成，不作为单Activity操作方法。
metadata:
  change_summary: "区分默认队列、显式已提交评论交接与正式采样，保留完整身份及单次评分边界"
  version: 0.13.12
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/douyin-leadgen-102/references/activity-methods.json

  document_role: workflow-index

---

# Workflow 102 · 视频处理与评论采集

`douyin_video_processing` 是 Workflow；下表各 Activity 的 Skill 才是具体操作方法。消费可验证101来源，原子领取、按原政策判资格，合格才采评论。

## 合同、执行提案与独立验收

读取本run冻结的完整当前Activity Contract，核对来源、Activity身份、版本与摘要；输入输出、前后条件、DoD及已选公司政策以该合同为准，不从旧specific检查列表另立标准。执行者交付的是执行提案和原始证据，不是验收结论；独立通用Checker读取同一合同并用只读工具核实事实。模型自述、工具verified摘要或退出0不能代替原件，也不能替下一Activity判通过。

预算只引用冻结Activity Contract的 `budget` 与本run原绝对截止：业务受 `run.deadline_ms` 约束，收尾受 `run.cleanup_deadline_ms` 约束，实际可用时间取适用Activity预算和相应绝对截止的更早者。换Activity、恢复或新工具调用不重置剩余时间；不得挪用收尾窗口新增业务。

`agent_recovery` 仅声明方法可选能力，不是本次重试额度。只有本run实际冻结的 `runtime.checker_repair` 明确授权、剩余额度与原截止仍有效时，才按失败原因和证据进行允许的返工；没有该设置不自行增回合。保留原Task/run、动作身份和已成功成果；未知副作用先读回，未知不重做，不能换nonce或generation重放。返工不增加本次批次、评分、录制或发送授权，不重复已成功业务动作。Checker不执行业务写入，也不授予发送权。

## 活动组织

`preflight → dedup → qualification → collection → cleanup`

| Activity | 唯一操作Skill | 方法版本 |
|---|---|---|
| `preflight` | [douyin-leadgen-activity-102-preflight](../douyin-leadgen-activity-102-preflight/SKILL.md) | `0.11.1` |
| `dedup` | [douyin-leadgen-activity-102-dedup](../douyin-leadgen-activity-102-dedup/SKILL.md) | `0.8.4` |
| `qualification` | [douyin-leadgen-activity-102-qualification](../douyin-leadgen-activity-102-qualification/SKILL.md) | `0.8.3` |
| `collection` | [douyin-leadgen-activity-102-collection](../douyin-leadgen-activity-102-collection/SKILL.md) | `0.10.1` |
| `cleanup` | [douyin-leadgen-activity-102-cleanup](../douyin-leadgen-activity-102-cleanup/SKILL.md) | `0.11.2` |

机器引用真身为[Activity方法清单](references/activity-methods.json)，版本必须与上述方法文件一致。101/102共用同一份preflight与cleanup，不复制。

## 输入与交接

- 由调用者提供真实Task/run、公司/租户/line、冻结公司配置与原政策、处理范围/数量/截止及各Activity获授权工具和资源。Workflow负责组织与交接，不替Activity猜账号、扩大范围或自创工具权限。
- 每个Activity只读本次明确输入和自己的方法，不回读本目录作操作前提，不再加载旧业务Skill。后继Activity消费前驱真实持久回执；未知或失败不能用文字补pass。cleanup仍按原责任处理，不能把业务失败洗成完成。
- 逐VID真实资格、完整原生评论身份、PG新增/历史/重复与正式采样交接。采样达标不等于全量采尽。
- 103普通队列不绑定某次102；正式采样必须明确来源并核交接，不得意外继承或自行补造SOURCE_RUN。资格、采集、评分、标记、配送分别报告；104发送仍需独立授权。

## 工作流之间的异步交接

101持久化视频，102消费已验证视频并采评论；103独立消费本公司合格的已提交评论，104独立消费配送已确认的合格订单。各Workflow内部按Activity顺序执行，Workflow之间通过持久队列解耦，不强制同一run或等整批上游完成。

普通103默认队列仍要求评论所属视频已核资格且状态为“评论已采”。`collect_partial`只表示部分评论已提交，不证明身份完整或视频已采尽，也不会自动进入默认评分队列。

普通API活动可由调用者显式交接 `committed_partial_ids` 精确评论ID清单（1～50条，`source_run=null`）：仅接纳原生身份与视频配对证据完整verified、同102来源批次、账号绑定和102/103冻结公司/租户/line/版本/政策及评分规则一致的已提交评论。视频保留“待判定”或原102处理租约；unknown凭证不能评分，具体补证据和操作分别见collection、scoring、mark_leads各自方法。此模式不扩大默认队列。

正式102采样仍须明确指定其102 `source_run`，并核对该run合格的reconciliation、完整spans及qualification/collection精确交接；普通API显式交接不能替代这些正式凭证。未完成或失败来源不能靠改状态放行，任务显式限批时保留原来源范围。

“可独立消费”说明队列关系，不代表已有常驻消费者或自动唤醒；每次由已配置的调度或本次任务实际启动，启动方式与运行证据分别核实。同一手机的101/102/104仍遵守设备锁，103评分和标记不占手机。

## 实现与状态

Skill与Code是Activity的实现方式，Workflow本身不是一个替代全部Activity的大Skill。正式宿主照原冻结合同/绑定授权，普通API任务照本次明确工具授权，二者不能伪装或互相降级。旧managed工具说明保留为历史兼容资料，不是新的执行前置。

本文件说明Workflow组织；具体实现和发布状态按该次Task及固定源码核实。方法自包含/离线评审与真实实机、工具能力验收分别记录；缺专用指标或正式采样回执时如实报告，不宣称整版通过。

## 宿主恢复能力声明

以下 `agent_recovery` 只描述可选能力，不能被解释为本次已选额度。实际是否允许返工及其次数只读本run冻结的 `runtime.checker_repair`；原授权、动作累计次数、未知不重做和绝对截止仍约束所有回合。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
