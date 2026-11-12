---
name: douyin-leadgen-101
description: Workflow 101的活动组织与交接目录；实际执行由各Activity自己的Skill完成，不作为单Activity操作方法。
metadata:
  change_summary: "0.10.0: 仅保留Workflow编排目录，Activity方法各自完整，退役旧手册执行引用"
  version: 0.10.0
  validation: awaiting-real-run
  support_files:
    - services/phone-adb-controller/skills/douyin-leadgen-101/references/activity-methods.json

  document_role: workflow-index

---

# Workflow 101 · 视频发现

`douyin_video_discovery` 是 Workflow；下表各 Activity 的 Skill 才是具体操作方法。按公司关键词与真实筛选发现视频；输入数量是上限，不能保证搜到。

## 活动组织

`preflight → collect_videos → cleanup`

| Activity | 唯一操作Skill | 方法版本 |
|---|---|---|
| `preflight` | [douyin-leadgen-activity-102-preflight](../douyin-leadgen-activity-102-preflight/SKILL.md) | `0.8.0` |
| `collect_videos` | [douyin-leadgen-activity-101-collect-videos](../douyin-leadgen-activity-101-collect-videos/SKILL.md) | `0.8.0` |
| `cleanup` | [douyin-leadgen-activity-102-cleanup](../douyin-leadgen-activity-102-cleanup/SKILL.md) | `0.8.0` |

机器引用真身为[Activity方法清单](references/activity-methods.json)，版本必须与上述方法文件一致。101/102共用同一份preflight与cleanup，不复制。

## 输入与交接

- 由调用者提供真实Task/run、公司/租户/line、冻结公司配置与原政策、处理范围/数量/截止及各Activity获授权工具和资源。Workflow负责组织与交接，不替Activity猜账号、扩大范围或自创工具权限。
- 每个Activity只读本次明确输入和自己的方法，不回读本目录作操作前提，不再加载旧业务Skill。后继Activity消费前驱真实持久回执；未知或失败不能用文字补pass。cleanup仍按原责任处理，不能把业务失败洗成完成。
- 视频身份、筛选、同视频指标与来源持久读回。101不做公司业务资格判断、录音或评论采集。
- 103的队列独立于某次102是否产出；不要从102环境自动继承SOURCE_RUN。任务明确限定批次时照守，未限定则查公司合法队列。资格、采集、评分、标记、配送分别报告；104发送仍需独立授权。

## 实现与状态

Skill与Code是Activity的实现方式，Workflow本身不是一个替代全部Activity的大Skill。正式宿主照原冻结合同/绑定授权，普通API任务照本次明确工具授权，二者不能伪装或互相降级。旧managed工具说明保留为历史兼容资料，不是新的执行前置。

本次仅更新方法说明与引用；未发布新控制器、ASR或评分实现。方法自包含/离线评审与真实实机、工具能力验收分别记录；缺专用指标、双审或正式采样回执时如实报告，不宣称整版通过。

## 历史宿主兼容声明

以下仅保留冻结解析字段；不授予执行权限、不增加本次预算。实际恢复仍由对应Activity合同约束。

<!-- agent-recovery-policy -->
```json
{"agent_recovery":{"max_additional_turns":1}}
```
