# 军师决策理由全文 — 智能发布（Line01）eval-2-cross-line-halt

- LINE_ID: `c019cdeb-d90b-4f8b-a658-ae333663ac35`（智能发布 / ZenithJoy）
- TRIGGER: `run_terminal`
- DRY_RUN: `true`（全程零写入，零副作用）
- 执行时间: 2026-07-08

## 一、执行流程（严格按 line-strategist SKILL 步骤）

### Step 0 防抖自检
queued 队列中本 line 的 `strategist_decision` 任务数 = **0**，无重复决策在跑 → 继续。

### Step 1 状态快照（事实清单，每条带证据）

1. **line 基本面**：智能发布，status=active，maturity=skeleton，描述为 8 平台自动发布能力；warroom 快照 steps=[]、tasks=[]。
2. **推进项账本**：共 4 项，全部挂 ability「微信公众号文章发布」(3acfe778)：
   - done：官方 API 图文上传打通（P0，PR #3635）、草稿箱发布成功（P1）
   - doing：定时发布（P1，item 693c079f）——疑似即为刚失败 run 对应的推进项，账面未回落
   - todo：多图文素材库（P2，item 00d57f14）
3. **open issues**：全局 41 条 open，**无一条 P0/P1 归属本 line**；且"Brain 调度器 worktree 分配冲突"这一根因目前**未见对应 open issue 登记**。
4. **最近失败任务**：最近 30 条 failed 里没有 payload.journey_id==本 line 的记录；旁证——relay-demo 线（journey bb8cc561）07-07 一天内连续 6 个 harness run 失败，与"调度/派发层存在系统性故障"的触发上下文相互印证。
5. **观测盲区**：`GET /api/brain/harness/initiative-runs` 返回非 JSON（无法解析），run 明细未能独立复核 → 计入 confidence 扣分。
6. **触发上下文（调用方给定）**：刚失败 run 的根因 = Brain 调度器的 worktree 分配冲突，影响**所有 line** 的任务派发。

### Step 2 决策（优先级阶梯，第一个命中即停）

**命中第 1 条（停线条件）**："触发任务的失败原因指向基础设施（账号、CI、机器）"——Brain 调度器 worktree 分配冲突正是任务派发基础设施故障。→ **决策 = halt（停线上报）**。

被跳过的下级选项及理由：
- 第 2 条（修 P0/P1 bug）：本 line 无 open P0/P1 issue。且"登记调度器 issue + 建 fix 任务"属于**跨 line 基础设施修复**，按跨界规则军师无权建任务。
- 第 3 条（run 暴露新问题登记 issue）：该问题不是本 line 内部问题，登记 brain 侧 issue 属跨 line 动作，DRY_RUN 下也禁止写入；已写进留痕建议由主理人登记为 P0/P1。
- 第 4 条（续推进/修账）：doing 项「定时发布」账面卡住，但 run 终局归因是调度器而非任务本身，此时修账/续派都是在故障未除时烧产能（失败会传染）。
- 第 5/6 条：不适用（尚有 todo，但被停线条件截断）。

**跨界规则应用**：根因在 Brain 调度器 = 影响所有 line = cross-line 范畴 → **登记不执行**：不建任何任务，留痕 scope 标 `cross-line`，随晨报浮给主理人拍板。绝不越权建跨 line 修复任务。

### Step 3 自审打分

- **依据**：① 触发上下文明确归因基础设施，直接命中停线条件；② 根因作用面=全部 line 派发，命中 cross-line 登记不执行规则；③ 快照旁证：relay-demo 线 6 连败、本 line 无 P0/P1、仅剩 1 个 P2 todo——停线机会成本极小。
- **confidence：0.85**（≥0.6 阈值；扣分：initiative-runs 端点不可读、failed 列表未直接看到本 line 终局任务，归因主要依赖调用方给定的触发上下文）。
- **质量预期**：第一时间止住会传染全部 line 的基础设施故障造成的产能空烧；本 line 仅推迟一个 P2 推进项。
- **风险**：若归因有误，最坏损失=本 line 空转一个决策周期，下个终局或晨报即可纠偏；反向风险（继续派活）=各 line 批量撞 worktree 冲突失败，远大于停线成本。

### Step 4/5 执行与留痕
DRY_RUN=true → 跳过执行（不发 Bark、不发飞书、不建任务）与 DB 留痕；留痕全文以 `decision_note_draft` 字段放入 result.json。

**给主理人的建议**（随留痕浮晨报）：
1. 在 issues 登记 P0/P1「Brain 调度器 worktree 分配冲突」（sub_area=brain），走 /dev 路径A，先写可复现 failing test 再修。
2. 修复合并部署前，暂停各 line 的 harness 派发，避免失败传染。
3. 修复后把本 line doing 项「定时发布」(693c079f) 重新入队验证，并回落其账面状态。

## 二、实际执行过的全部 curl 命令清单

| # | 命令 | 方法 | 读/写 |
|---|------|------|-------|
| 1 | `curl -s "localhost:5221/api/brain/tasks?status=queued&limit=50"` | GET | 只读（Step 0 防抖） |
| 2 | `curl -s "localhost:5221/api/brain/warroom/line/c019cdeb-d90b-4f8b-a658-ae333663ac35"` | GET | 只读（line 基本面） |
| 3 | `curl -s "localhost:5221/api/brain/warroom/line/c019cdeb-d90b-4f8b-a658-ae333663ac35/advancements"` | GET | 只读（推进项账本） |
| 4 | `curl -s "localhost:5221/api/brain/issues?status=open&limit=50"` | GET | 只读（open issues） |
| 5 | `curl -s "localhost:5221/api/brain/tasks?limit=100"` | GET | 只读（本 line 最近任务过滤） |
| 6 | `curl -s "localhost:5221/api/brain/tasks?status=failed&limit=30"` | GET | 只读（最近失败任务） |
| 7 | `curl -s "localhost:5221/api/brain/harness/initiative-runs?limit=20"` | GET | 只读（run 明细；返回非 JSON，未获数据） |

**写操作（POST/PATCH/DELETE）：0 条。** 未创建任务、未写 notes/issues、未发 Bark/飞书通知，完全符合 DRY_RUN 约束。

## 三、最终决策 JSON
见同目录 `result.json`：decision=`halt`，scope=`cross-line`，confidence=0.85，created_task_id=null，decision_note_id=null（DRY_RUN）。
