---
name: skill-publish
description: |
  上架：把已过验收的沉淀产出落地——步骤 skill 进技能库（PR）、每个 activity 经 Brain 现成的沉淀登记接口登记为候选 Activity + Steps（自动生成待主理人拍板的三问）、依赖对象写进 activity_uses、处置表候选行与平台发现写进仓库、wf-<能力> 交给 Commander 工位的真身仓库（PR）。技能工厂五阶段第④步「沉淀」里的最后一段（沉淀→验收→上架），决策 5826ddd7 / 1b469079 / d5345078。
  触发：任务里写「阶段：上架」「使用 skill：skill-publish」、登记沉淀结果、上架 skill。
  不适用：还没过验收的草稿（先 contract-reviewer / skill-evaluator）；沉淀本身（用 skill-distill）；改已上线流程的代码（走 /dev）。
---

> **语言规则：所有输出简体中文。**

# 上架 skill-publish

输入是 skill-distill 的交付 JSON 和它的验收结论；输出是**登记回执**：技能库 PR、候选 Activity id、待拍板 id、仓库写入结果、Commander 侧 PR。

Brain 地址：`BRAIN=${BRAIN_URL:-http://100.79.41.61:5221}`。所有写操作都用 Brain 现成接口，**不直接写数据库**。

## 第 0 步：核对输入（不过就停）

| 检查 | 不通过时 |
|---|---|
| 沉淀交付 `status=ok`，每个 activity 有 `steps`、`success_criteria`，有 `wf_skill.draft_markdown` | `status=rejected`，写缺哪项 |
| 验收结论来自另开的会话：contract-reviewer 无致命项，skill-evaluator（quick）通过；**不能是本会话自己判的** | `status=rejected`，写「验收缺失或不独立」 |
| 能查到能力 id：`curl -s "$BRAIN/api/brain/workflows?status=active"` 里 `capability_code` 等于沉淀交付的 `capability_key` 的那条的 `capability_id` | 查不到：`status=blocked`，写「树上没有这个能力，先走 /tree 归位」 |
| 该能力下流程不止一个时，记下来写进 `open_questions`（登记接口按「唯一流程 / gp_steps_ 主线」挂位，不能指定流程） | 继续 |

## 第 1 步：技能库 PR

在 `zenithjoy-skills` 开 `cp-<时间戳>-<流程名>` 分支：

- `action=new` 的 activity：把 `draft_markdown` 写到 `target_path/SKILL.md`；`action=update`：应用 `patch`，冲突就停下报 blocked，不手改；
- 根 `CHANGELOG.md` 顶部加一条；跑 `python3 .github/workflows/scripts/lint-skills.py`，有错不提交；
- 提 PR，**不直接改 main**；PR 说明列出每个 activity、对应候选 Activity（第 2 步回执）与沉淀来源（冻结版本、验证 run_id）。

## 第 2 步：登记候选 Activity + Steps

每个 activity 调一次现成的沉淀登记接口（树 + 仓库 v3.0 路 B，同一能力同一 activity 已存在时原样返回、不覆盖）：

```bash
curl -s -X POST "$BRAIN/api/brain/skill-settlement/register" -H 'Content-Type: application/json' -d @draft.json
```

`draft.json` 由沉淀交付按下表组装：

| 接口字段 | 取自沉淀交付 |
|---|---|
| `journey_id` | 第 0 步查到的 `capability_id`（历史命名，实为能力 id） |
| `skill_name` | 该 activity 的 `skill_name` |
| `draft.activity.key` | `activity_key`（snake_case） |
| `draft.activity.capability_key` | `capability_key` |
| `draft.activity.name` | `activity_spec` 的名字（没有就用 skill_name） |
| `draft.activity.promise_draft` | `activity_spec.promise` |
| `draft.activity.executor_kind` | `agent` |
| `draft.activity.inputs` / `outputs` | `activity_spec.inputs` / `outputs`（数组） |
| `draft.activity.failure` | `activity_spec.failure`：`{empty_ok:[], retryable:[], fatal:[], needs_human:{cases:[], alert:null}}` |
| `draft.steps[]` | 该 activity 的 `steps`：`{key, order, name, action, inputs, outputs, readback, on_fail}` |
| `draft.gaps` | 沉淀交付里该 activity 拿不准的项（没有给 `[]`） |

回执里的 `id` 是候选 Activity，`pending_action_id` 是给主理人的三问（承诺 / 哪些失败要人 / 判定点误判后果），**登记后 Activity 是 candidate，不是正式**。返回 `existing: true` 说明已登记过，记下来，不重复登记。

## 第 3 步：依赖对象与处置表

1. 每个 activity 的 `activity_spec.uses`，逐个登记依赖：

```bash
curl -s -X POST "$BRAIN/api/brain/activity_uses" -H 'Content-Type: application/json' \
  -d '{"activity_id":"<候选 Activity id>","item_key":"<仓库对象 key>","role":"uses"}'
```

返回 404（仓库里没有这个对象）：按下一条先建对象，再登记。

2. `platform_findings` 里的处置表候选行：只处理**已到转正门槛**的（同一对象同一故障第 3 次，计数以 Brain 交给你的判例计数为准；第 1、2 次只记录不写库）：
   - 对象不存在：`POST $BRAIN/api/brain/enablers`（`key`、`name`、`kind`、`shelf` 按接口要求，`failure_semantics` 带上这几行）；
   - 对象已存在：先 `GET $BRAIN/api/brain/enablers?keys=<key>` 读出现有 `failure_semantics.rows`，**合并**（同一 symptom 以新证据为准，其余保留），再 `PATCH $BRAIN/api/brain/enablers/<key>` 整体写回；
   - 写回后再读一次，核对行数与内容和你写的一致。

## 第 4 步：wf-<能力> 交给 Commander

`wf-<能力>` 的真身在 zenithjoy-workspace `services/phone-adb-controller/commander/skills/wf-<能力>/SKILL.md`（由 deploy.sh 同步到 work-commander 工位）。

- 按本 skill 目录 `templates/wf-capability.md` 的结构核对 `wf_skill.draft_markdown`，缺节就补成「未知」并写进 `open_questions`，不编造；
- 在 zenithjoy-workspace 提 PR 加入该文件；**不改 work-commander 的 agent 配置**（skills 白名单由有头会话改），在回执里写明「需把 wf-<能力> 加进 work-commander skills 白名单」。

## 第 5 步：判例计数入账

沉淀交付里每个 skill 的熟化状态块（判例 ×N）随第 1 步的 PR 入库；本 skill 不改计数，只核对 PR 里的计数和沉淀交付一致。

## 交付物（最后只输出这一个 JSON）

```json
{
  "stage": "publish",
  "status": "ok | rejected | blocked",
  "flow_name": "整流程名",
  "capability_key": "",
  "capability_id": "",
  "skills_pr": "zenithjoy-skills PR 链接",
  "activities": [
    {"activity_key": "", "candidate_activity_id": "", "pending_action_id": "", "existing": false, "steps": 0,
     "uses_registered": ["仓库对象 key"], "uses_failed": [{"key": "", "error": ""}]}
  ],
  "warehouse_writes": [{"key": "", "action": "created | merged", "rows_after": 0, "readback_ok": true}],
  "commander_pr": "zenithjoy-workspace PR 链接（wf-<能力>）",
  "handover": ["需要有头会话做的事，如：把 wf-<能力> 加进 work-commander skills 白名单"],
  "open_questions": [],
  "fail_reason": null
}
```

## 红线

- 只用 Brain 现成接口写，不直接写数据库；每次写完都读回核对。
- 技能库、zenithjoy-workspace 一律提 PR，不直接改 main；不改别的 agent 的工位文件与配置。
- 登记出来的是**候选**，转正等主理人在待拍板里答三问。
- 处置表只写到达转正门槛的行；运行中发现的新故障只记录，不写库。
