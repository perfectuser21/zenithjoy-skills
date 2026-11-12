---
name: douyin-leadgen-103
description: Workflow 103的活动组织与交接目录；实际执行由各Activity自己的Skill完成，不作为单Activity操作方法。
metadata:
  change_summary: "0.18.0: 每条评论评估一次保存，评分和线索标记均取消双审门槛"
  version: 0.18.0
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/douyin-leadgen-103/references/activity-methods.json

  document_role: workflow-index

---

# Workflow 103 · 评论评分与线索标记

`douyin_comment_scoring` 是 Workflow；下表各 Activity 的 Skill 才是具体操作方法。独立消费本公司已提交待评/已评队列，不占手机；只有任务显式来源约束才限批。

## 活动组织

`scoring → mark_leads`

| Activity | 唯一操作Skill | 方法版本 |
|---|---|---|
| `scoring` | [douyin-leadgen-activity-103-scoring](../douyin-leadgen-activity-103-scoring/SKILL.md) | `0.16.0` |
| `mark_leads` | [douyin-leadgen-activity-103-mark-leads](../douyin-leadgen-activity-103-mark-leads/SKILL.md) | `0.16.0` |

机器引用真身为[Activity方法清单](references/activity-methods.json)，版本必须与上述方法文件一致。101/102共用同一份preflight与cleanup，不复制。

## 输入与交接

- 由调用者提供真实Task/run、公司/租户/line、冻结公司配置与原政策、处理范围/数量/截止及各Activity获授权工具和资源。Workflow负责组织与交接，不替Activity猜账号、扩大范围或自创工具权限。
- 每个Activity只读本次明确输入和自己的方法，不回读本目录作操作前提，不再加载旧业务Skill。后继Activity消费前驱真实持久回执；未知或失败不能用文字补pass。cleanup仍按原责任处理，不能把业务失败洗成完成。
- 实际评分/排除、原文证据与公司政策版本、Lead及outbox/外部读回。真正空队列记skipped，不宣称评分成功。
- 103的队列独立于某次102是否产出；不要从102环境自动继承SOURCE_RUN。任务明确限定批次时照守，未限定则查公司合法队列。资格、采集、评分、标记、配送分别报告；104发送仍需独立授权。

## 实现与状态

Skill与Code是Activity的实现方式，Workflow本身不是一个替代全部Activity的大Skill。正式宿主照原冻结合同/绑定授权，普通API任务照本次明确工具授权，二者不能伪装或互相降级。旧managed工具说明保留为历史兼容资料，不是新的执行前置。

本次仅更新方法说明与引用；未发布新控制器、ASR或评分实现。方法自包含/离线评审与真实实机、工具能力验收分别记录；缺单次评分工具或正式采样回执时如实报告，不宣称整版通过。

## 历史宿主兼容声明

以下仅保留冻结解析字段；不授予执行权限、不增加本次预算。实际恢复仍由对应Activity合同约束。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```

主理人决定 `8331c673-1113-4a04-a5dd-54ec76a916fe`：每条评论按公司规则评估一次即保存，不增加模型复核；线索标记消费已有评分，不重新判分。历史宿主的双审硬门尚未适配时如实报告，不伪造双审记录。
