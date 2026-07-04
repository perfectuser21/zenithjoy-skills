---
id: harness-controller-skill
description: |
  Harness Controller — PR-level 单 session 编排者（SDD 模式，替代 LangGraph 图的编排位置）。
  一个 claude session 从头跑完一条 sprint：planner → GAN(proposer×reviewer) → generator(TDD) → evaluator → judge → merge → report。
  移植 Superpowers 6.0 subagent-driven-development 零件：进度台账 / 文件接力 / 四态出口协议 / 单评审双裁决 / compaction 恢复。
  点火方：Brain harness dispatch（无头）或人工前台（同一份 skill 两种触发，行为一致）。
  /dev 仍是唯一需求入口：本 skill 消费 /dev 路径C 的交接契约（PrepPRD + 铁律清单 + NFR），不做需求对抗。
version: 1.1.1
created: 2026-07-04
changelog:
  - 1.1.1: Step 4 补 evaluator unverifiable[] 兜底职责（T5 配套：controller 逐条核对无法验证项后才放行，对齐 SDD 6.0 Cannot-verify 裁决）
  - 1.1.0: N4 三跑实证修订——①merge 前禁退出(run-3 恢复session早退实证)②台账每步硬性 bash③report 回写 initiative_runs phase(治巡逻误报 Stuck)④CI 门禁三件套前置进 generator 验收(三跑均在 CI 才踩)
  - 1.0.0: 首版——SDD 模式移植（主理人 2026-07-04 拍板：单 session skill 接力，不自造 orchestrator，Brain 核心不动）
---

> **语言规则: 所有输出简体中文。**
> **角色**: 车间主任（编排/派活/验收），不亲自写代码。每个阶段派 fresh subagent（Task tool），自己只保留协调所需的最小上下文。

# /harness-controller — PR-level 单 session 接力编排

## 硬约束（凌驾于一切阶段逻辑）

1. **CONTRACT IS LAW**：合同批准后，任何阶段不得改合同/合同测试来迁就实现
2. **judge 是 merge 唯一权威**：CI 绿只是必要条件；evaluator PASS + judge PASS 才允许 merge（`should-auto-merge.sh` CI 双保险兜底，但你不得依赖它兜底）
3. **绝不让同一 subagent 无变化重试**：BLOCKED 必须改变某样东西（补上下文/换模型/拆任务/上报）
4. **台账先行**：每个阶段完成立刻 append 台账，永远信台账+git/PR 外部真相，不信自己记忆
5. **零人为交互**（无头模式）：任何不确定 → 派 Research subagent 查（代码/decisions/learnings）代答；仅 review_required 的人工门除外
6. **完成判据 = PR MERGED + report done，两者齐才许结束 session**：修完 CI、推完 commit 都不算完——`gh pr view` 显示 MERGED 之前，你没有任何理由输出完成结论或停止工作（N4 run-3 实证：恢复 session 修完 CI 自判完成早退，害整条 run 多一次点火）

## Step 0: 上下文装载 + 台账检查（每次进入/恢复都先做）

```bash
# 0.1 任务上下文（Brain dispatch 注入 env；前台手跑则从参数拿）
: "${HARNESS_TASK_ID:?}" "${SPRINT_DIR:?}"
BRAIN=${BRAIN_URL:-http://localhost:5221}
TASK=$(curl -s "$BRAIN/api/brain/tasks/$HARNESS_TASK_ID")
# payload 里应有：prep_prd_body（/dev 交接）、journey_id、review_required、target_environment、base_repo

# 0.2 台账（compaction/崩溃恢复的锚，SDD 6.0 模式）
LEDGER=".harness/progress.md"
mkdir -p .harness && printf '*\n' > .harness/.gitignore
cat "$LEDGER" 2>/dev/null || echo "(新 sprint，无台账)"
```

**恢复规则**：台账里标 `done` 的阶段直接跳过；从第一个无记录阶段续跑。台账记录格式（每阶段一行，append-only）：

```
planner: done (sprint-prd.md@<commit7>, invariants=N, fr=N)
gan: done (contract-draft.md@<branch> r<N>, verdict=APPROVED, 铁律覆盖=N/N)
generator: done (pr=#<num>, red=<sha7>, green=<sha7>)
evaluator: done (verdict=PASS, sha=<pr_head7>)
judge: done (verdict=PASS, sha=<pr_head7>)
merge: done (pr=#<num> MERGED)
report: done
```

**外部真相优先**：台账说 generator done 但 `gh pr view` 说 PR 不存在 → 信 gh，重跑该阶段并在台账 append 更正行（不删旧行）。

**台账写入是硬性动作，不是可选项**（N4 三跑均未写台账，恢复全靠翻 git——本版修正）。每阶段完成必须执行：

```bash
echo "<阶段>: done (<关键证据>)" >> .harness/progress.md
```

## Step 1: Planner（写 PRD）

派 fresh subagent（Task tool，模型=标准档）：

```
prompt: 调用 Skill(harness-planner)。上下文：
  TASK_ID=<id> SPRINT_DIR=<dir> BRAIN_URL=<url>
  PrepPRD 全文见 task payload.prep_prd_body（你自己 curl 取）。
  产出 <SPRINT_DIR>/sprint-prd.md 并 commit。
  报告格式：status(DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED) + 产物路径 + invariant/累积FR 加载数
```

- harness-planner v8.12+ 自带整条 line 的 invariant 三源 + 累积 FR 加载——**验收时检查 sprint-prd.md 含「## Invariant 约束」「## 累积 FR」两段**，缺了 = planner 报告不实，打回重跑
- 四态处置：见「四态协议」节
- 完成 → 台账 append → Step 2

## Step 2: GAN（合同对抗，proposer × reviewer 循环）

循环（无硬轮数上限——刻意设计，禁加 MAX_ROUNDS；守护 = 预算/streak，见下）：

1. 派 **proposer** fresh subagent：`调用 Skill(harness-contract-proposer)`，输入 = sprint-prd.md 路径 + 上轮 reviewer feedback 文件路径（首轮无）。产出 contract-draft.md + contract-dod.md + tests/ 推到 propose 分支
2. 派 **reviewer** fresh subagent：`调用 Skill(harness-contract-reviewer)`，输入 = PRD + 合同路径。产出 rubric 打分 + verdict
3. **controller 只认结构化 verdict**：APPROVED → 出环；REVISION → feedback 落文件、回 1
4. **铁律覆盖硬检查（controller 自查，不信 reviewer 自觉）**：PrepPRD 交接的每条铁律，在 contract-dod.md 里 grep 到对应断言才算过；缺 → 作为 feedback 打回 proposer（这是"0→1 积累必须加载"的机械保证）

守护（照抄旧图语义）：proposer 连续 2 轮没 push 产物 / reviewer 连续 3 轮无 verdict / 成本超预算 → 终局 FAIL 上报

完成 → 台账 append（含轮次、铁律覆盖 N/N）→ Step 3

## Step 3: Generator（TDD 实现，SDD×TDD 的接点）

派 fresh subagent（模型=标准档）：

```
prompt: 调用 Skill(harness-generator)。CONTRACT_BRANCH=<branch> SPRINT_DIR=<dir>。
  铁律：commit 1 = 合同测试原样 checkout(Red)，commit 2+ = 实现(Green)；
  测试文件 commit 1 后绝对不可改（CI 强校验）；push 前自跑合同 [BEHAVIOR] 全过。
  报告：四态 + pr_url + Red/Green commit SHA
```

- generator 内部 TDD 纪律由 harness-generator skill 承载（不变）；controller 验收三件事：**PR 真实存在**（gh pr view）、**commit 顺序含 (Red)/(Green)**、**CI 在跑**
- **CI 门禁三件套 push 前自查**（N4 三跑全在 CI 才踩这些门，各浪费一轮修复——左移到此）：①contract-draft.md 含 Test Contract 表且 [BEHAVIOR] 覆盖文本与测试 it() 名称子串匹配 ②feat 改动带 packages/brain/scripts/smoke/<feature>-smoke.sh（CI 兼容纯检查）③DoD 条目全勾 [x]。任一缺失 → 让 generator 补完再 push
- CI 失败 → 派 fix subagent（同 skill Mode 2，带失败日志），fix 轮次计入台账，上限 20
- 完成（CI 全绿）→ 台账 append → Step 4

## Step 4: Evaluator（真跑验收）

先跑**确定性双门**（不烧 LLM）：
- ARTIFACT 门：合同 [ARTIFACT] Test 命令逐条 bash 真跑，失败 → 直接判 FAIL 回 generator fix
- Contract Gate 反作弊（弱 oracle/mock 环境/exit-0 兜底红线）：命中 → `contract_invalid` 终局（责任在 GAN，不进 fix loop）

双门过 → 派 evaluator fresh subagent：`调用 Skill(harness-evaluator)`（target_environment 路由由 evaluator skill 自带）。
- **verdict 锚定 PR head SHA 记入台账**；PR 后续有新 commit → 旧 verdict 作废必须重评
- FIXED 按 PASS 归一（前科语义）；FAIL → 带 feedback 回 Step 3 fix
- **evaluator 报 unverifiable[] 非空时（T5 第三态）**：controller 必须逐条兜底——用自己掌握的跨阶段上下文核对（查合同原意/看 PR diff/必要时派 Research subagent 实测）；确认是真缺口 → 按 FAIL 处理回 Step 3；确认可放行 → 记台账后继续。**禁止不核对就当 PASS 放行**

## Step 5: Judge（独立裁判，硬门禁）

- 只对 evaluator PASS 复核：`node scripts/harness-judge-cli.mjs --task-id <id> --sprint-dir <dir> --pr <url>`（thin wrapper，N3 提供；DeepSeek + Golden Path 逐步覆盖校验，逻辑=harness-judge.js 原样）
- judge FAIL → 带 feedback 回 Step 3（打回重写）；judge PASS → 台账 append（锚 sha）→ Step 6
- **禁止**：跳过 judge / 替 judge 降级 / 在 judge 前 merge

## Step 6: Review 门（仅 review_required=true）+ Merge

- review_required → 起预览环境 + Bark 通知主理人（附 approve 命令），阻塞等 task_events 批准事件
- merge（唯一权威路径）：evaluator PASS + judge PASS（+ 人工批准如需）→ `gh pr merge --squash --delete-branch`
  - BEHIND → `gh pr update-branch` ≤3 次；**update 改变 head sha → evaluator/judge verdict 以新 sha 重锚**（轻量 rebase 不重评，台账记 re-anchor 行）
  - CONFLICTING → 终局 FAIL 上报
- 完成 → 台账 append → Step 7

## Step 7: Report（收尾六步）

调用 Skill(harness-report)（Phase A/B 不变：回写 Brain task 状态 → Dashboard → Notion → 飞书 → 本地备份 → Sprint 状态同步）。

**追加硬性动作——回写 initiative_runs 终态**（否则 Brain 巡逻把 run 误判为 Stuck at Planner 并派干预任务，N4 实证）：

```bash
curl -s -X PATCH "$BRAIN/api/brain/orchestrator/relay-runs/${HARNESS_INITIATIVE_ID}" \
  -H "Content-Type: application/json" \
  -d '{"phase":"done"}'   # 终局失败改 {"phase":"failed","failure_reason":"<一句话>"}
```

台账 append `report: done`，确认 PR 状态 = MERGED（硬约束 6），输出最终摘要，session 结束。

## 四态协议（所有 subagent 统一出口，处置表）

| 状态 | controller 动作 |
|---|---|
| DONE | 验收产物（外部真相核对）→ 台账 → 下一阶段 |
| DONE_WITH_CONCERNS | 读 concerns：正确性/scope 问题先解决再走；观察类记台账继续 |
| NEEDS_CONTEXT | 补齐缺失上下文（自己查或派 Research subagent 查），**同模型重派** |
| BLOCKED | 分诊：缺上下文→补料重派 / 需更强推理→**升级模型重派** / 任务太大→拆分 / 计划本身错→终局上报。绝不无变化重试 |

## CI 配套硬规矩（controller 的检查责任）

1. 合同测试 merge 后**永久留在 repo** 跑 regression——merge 前确认测试文件在 PR diff 里且路径在 CI 收集范围
2. tdd-commit-order / 测试文件 commit-1 后不可改——CI 强校验，controller 不得用任何方式绕过
3. feat PR 必须带 smoke 脚本（CI lint 强制）
4. **禁 `gh pr merge --admin`**，禁绕 CI

## 文件接力纪律（SDD 6.0）

- 阶段间传**文件路径**，不往 subagent prompt 里粘贴大产物（合同/PRD/diff）
- review 用的 diff 以"派发前记录的 BASE"生成，**绝不用 HEAD~1**（多 commit 会静默截断）
- controller 自己不读全量 diff/合同——保持协调上下文恒定小，长跑不 compaction；万一 compaction，Step 0 台账恢复
