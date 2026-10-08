---
name: skill-retire
description: |
  退役：找出连续 30 天没跑、或已被新流程取代的流程，出退役建议清单；主理人确认后逐条执行——skill 移归档目录（只移不删）、树上标 deprecated、仍有别的流程在用的仓库共用物件保留。技能工厂循环的第⑥步「退役」，决策 9b3b027b。
  触发：任务里写「阶段：退役」「使用 skill：skill-retire」、清理不用的流程、退役 skill。
  不适用：流程坏了要修（走回流：某个 activity 坏了回探索，整条走法变了回试跑）；删除任何数据。
---

> **语言规则：所有输出简体中文。**

# 退役 skill-retire

退役是**整理**，不是删除。全程只移不删，每一步可撤回。

Brain 地址：`BRAIN=${BRAIN_URL:-http://100.79.41.61:5221}`。

## 两段式：先出清单，确认后再执行

### 第一段：出建议清单（只读）

找候选，满足任一条：

| 条件 | 怎么查 |
|---|---|
| 连续 30 天没跑 | 该流程最近一次运行（执行单 / 运行记录）距今 ≥ 30 天 |
| 被新流程取代 | 树上同一能力下已有新流程覆盖同一结果，且主理人或决策写明取代关系 |

每个候选写清：

| 字段 | 写什么 |
|---|---|
| 流程 / 能力 | 树上坐标 |
| 退役理由 | 30 天未跑（最近一次运行日期）/ 被谁取代（依据） |
| 要归档的 skill | 每个步骤 skill、整流程 skill、`wf-<能力>` 的路径 |
| 仓库共用物件 | 它用到的每个仓库物件，查还有没有别的流程在用（`activity_uses`）；还有人用的标「保留」 |
| 影响 | 有没有定时任务、Commander 调度单、别的流程引用它；有就列出，并写「先停调度再退役」 |

交付清单后**停下**，等主理人逐条确认（零等待铁律不适用：退役属删改类，按红线先出清单）。

### 第二段：逐条执行（主理人确认过的那几条）

1. 技能库开 `cp-*` 分支，把要归档的 skill 目录移到 `_archive/<日期>-<流程名>/`（`git mv`，只移不删），从各工位 `skills.manifest` 去掉；提 PR，不直接改 main。
2. Commander 侧的 `wf-<能力>` 同样移归档，提 PR 到 zenithjoy-workspace；调度单、白名单的改动交有头会话。
3. 树上标 deprecated：经 Brain 现成接口改状态；没有可用接口就写进交付物 `handover`，交有头会话处理，不直接写数据库。
4. 仓库物件：只有清单里标「无人再用」的才改为不活跃；「保留」的一概不动。
5. 每一条执行后读回核对（PR 链接、manifest 已去掉、树上状态），写进交付物。

## 交付物（每段最后只输出这一个 JSON）

```json
{
  "stage": "retire",
  "phase": "list | execute",
  "candidates": [
    {"flow": "", "capability_key": "", "reason": "idle_30d | superseded", "evidence": "最近运行日期 / 取代依据",
     "skills_to_archive": [], "warehouse_items": [{"key": "", "other_users": [], "action": "keep | deactivate"}],
     "dependents": ["定时任务 / 调度单 / 引用方"], "confirmed": false}
  ],
  "executed": [{"flow": "", "skills_pr": "", "commander_pr": "", "tree_status": "deprecated | handed_over", "readback_ok": true}],
  "handover": [],
  "open_questions": []
}
```

## 红线

- 只移不删：skill 进归档目录，数据不删，树上只改状态。
- 没有主理人逐条确认，不进第二段。
- 还有别的流程在用的仓库物件一律保留。
- 有定时任务或调度单还在指向它的，先停调度，再退役。
