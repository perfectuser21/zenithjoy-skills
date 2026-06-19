# Dev Skill v20.1.0 执行记录 — Bug 路径 A

---

## Phase 1：意图识别

**输入**："有个 bug：harness pipeline 跑到 evaluator 阶段，如果 E2E 脚本超时退出（exit code 124），系统没有标记任务失败，而是继续等待并最终卡在 running 状态，需要人工干预。"

**判断**：路径 A（Bug）
- 关键词命中："有个 bug"、"卡在 running 状态"、"需要人工干预"
- 现象明确：已知功能出问题，不是新功能需求

---

## Phase 2：上下文查询（路径 A — 3 个 curl）

### curl 1：journeys

Brain API 可用，返回 19 条 Journey。与本 bug 直接相关的：

```
id: bb8cc561-9703-41f7-af48-e455abc0766b
name: Cecelia Harness Pipeline
description: 从 PRD 触发到 PR 合并的 LLM agent 编排自驱执行链路
journey_type: dev_pipeline
maturity: skeleton
status: active
e2e_test_path: packages/brain/scripts/smoke/harness-pipeline-1node-smoke.sh
```

### curl 2：issues

返回 20 条 Issue，与 evaluator/超时/卡死相关的：

- `d43dff7b`：harness 子图 interrupt-waiting 静默卡死 watchdog 不捞（execution_attempts=0 10h 无活动）——**直接相关**
- `33a4ac9a`：GAN 回调 claim 卡死致图永久停滞（at-most-once 暗面）——**相关（callback 不回导致 interrupt 等待）**
- `6a89c10c`：evaluateContractNode interrupt 重执行导致孤儿 evaluator 容器——**直接相关（evaluator 容器侧）**
- `5b4f18d0`：Harness run 把合并门阻塞误记成 Final E2E FAIL——**参考**
- `320399d8`：harness 图执行生命周期缺口：startup re-queue 不查终态 + 在飞执行不感知任务被标 failed——**相关**

### curl 3：decisions/match

关键词 "evaluator E2E timeout exit code 124 running stuck task failure" — 返回空（`{"matched":[],"missing":[]}`），无历史决策记录。

---

## Bug PrepPRD

```markdown
# Bug PrepPRD：evaluator E2E 脚本超时（exit 124）未触发任务失败，任务卡 running

## 症状

harness pipeline 进入 evaluator 阶段后，E2E 验证脚本执行时超时（被 `timeout N bash` 命令杀死，shell 返回 exit code 124）。此时系统没有将任务标记为失败，而是继续保持 `running` 状态，直至需要人工介入（手动 PATCH 为 failed 或重启 Brain）。

具体表现：
1. `initiative_runs` 表中该 run 的 phase 停在 `evaluate` 或 `running`，无进展
2. `tasks` 表中对应 task status 维持 `in_progress`，未变为 `failed`
3. 无 `evaluate_verdict`（既不是 PASS 也不是 FAIL），图的 `interrupt()` 永远在等 callback
4. watchdog / patrol 未捞起此类"有容器但 callback 永不来"的僵死状态

## 根因假设

### 假设 A（主要）：容器级超时 vs E2E 子脚本超时 的混淆

SKILL.md（harness-evaluator）在 Step B-2 中用 `timeout N bash /tmp/e2e-verify.sh` 跑 E2E 脚本。当 E2E **子脚本**被 `timeout` 杀死时，外层 Claude agent 进程仍存活，能正常写 `.brain-result.json` 并 POST callback，路径正确。

但当超时发生在**容器级别**（Docker 外部 kill / WORKER_TIMEOUT_MS 超过 / `docker stop` SIGTERM → SIGKILL），`entrypoint.sh` 的 callback `curl` POST 来不及执行，Brain 的 `interrupt()` 永远收不到回调。`harness-initiative.graph.js` 的 liveness watchdog（`CALLBACK_TIMEOUT_MS` + `CALLBACK_HARD_CEILING_MS`）存在但只检测 generator 路径（`_waitForSubGraphCompletion`）；`evaluateContractNode` 在 `harness-task.graph.js` 中走的是独立 `interrupt()` 等待路径，其无限等待没有被同一套 liveness 逻辑覆盖。

**结论**：evaluator interrupt() 缺少独立的 callback 超时兜底机制，容器被 kill 后无人 resume → 永久卡 running。

### 假设 B（次要）：SKILL.md 的 exit 124 处理路径在某些 target_environment 分支下未触达

SKILL.md v1.15 已在 Step B-2 末尾加了统一超时判定：
```bash
if [[ "$EXIT_CODE" -eq 124 ]]; then
  cat > "$WORKSPACE/.brain-result.json" ...
  exit 0
fi
```

但这是 SKILL.md 中的**伪码/指令文本**，实际由 Claude agent 解读并执行。若 E2E 脚本超时时 Claude agent 本身也被 OOM / SIGKILL 打断（即假设 A 的情况），则该兜底代码段根本没机会执行，`.brain-result.json` 未写入，callback 未 POST。

此外，`linux_server` / `windows_cloud` 分支在触发 GHA workflow 后进入 `for i in $(seq 1 20); do sleep 30; done` 轮询（最长 10 分钟），这段等待期内若容器本身被杀，同样无 callback。

### 假设 C（次要）：liveness 超时仅覆盖 generator 节点，未覆盖 evaluate_contract 节点

在 `harness-initiative.graph.js` 中，`_waitForSubGraphCompletion` 有 `CALLBACK_TIMEOUT_MS` (100 min) soft timeout + `CALLBACK_HARD_CEILING_MS` hard ceiling，专门为 **generator** 节点回调设计。

`harness-task.graph.js` 的 `evaluateContractNode` 同样通过 `interrupt()` 等待 callback，但：
1. 它挂在 **task-level** 子图（`harness-task.graph.js`），调用方是 `runSubTaskNode`
2. `runSubTaskNode` 的超时/liveness 逻辑是否覆盖 evaluate 阶段，需要确认
3. 实证（Issue `d43dff7b`）：interrupt-waiting 僵死状态 10h 无活动，watchdog 未捞起

## 关联上下文

- 相关 Journey：`Cecelia Harness Pipeline`（bb8cc561，dev_pipeline，maturity=skeleton）
- 相关 Issue：
  - `d43dff7b`：harness 子图 interrupt-waiting 静默卡死 watchdog 不捞（P1，In progress）
  - `6a89c10c`：evaluateContractNode interrupt 重执行导致孤儿 evaluator 容器（P1，In progress）
  - `33a4ac9a`：GAN 回调 claim 卡死致图永久停滞（P1，In progress）
  - `320399d8`：harness 图执行生命周期缺口：startup re-queue 不查终态（P2，In progress）
- 相关历史决策：无（decisions/match 返回空）

## 修法

**文件 1：`packages/brain/src/workflows/harness-task.graph.js`**

在 `evaluateContractNode` 的 `interrupt()` 等待路径中，补充 callback 超时兜底：
- 在 `runSubTaskNode`（或 `_waitForSubGraphCompletion` 的 evaluate 分支）中，检测 evaluate 容器的 liveness
- 若 `spawnedAt` 超过 `CALLBACK_TIMEOUT_MS` 且容器已死（`checkLiveness` 返回 death reason）→ 主动 resume 子图，注入 `{ status: 'failed', error: 'evaluate_callback_timeout: container_died' }`
- 对应路由：`evaluate_verdict: 'FAIL'`，`evaluate_error: 'evaluator container timed out without callback'`

**文件 2：`packages/brain/src/harness-watchdog.js` 或 `harness-initiative-patrol.js`**

扩展 watchdog 覆盖范围：
- 当前 watchdog 主要检测 `generator` 容器的 callback 超时
- 新增：检测 `evaluate` 阶段的容器（`harness-evaluate-*`），若容器已死但 task 仍 `in_progress` 且 `evaluate_verdict` 为 null，主动标记任务失败

**文件 3：`packages/workflows/skills/harness-evaluator/SKILL.md`**（zenithjoy-skills 侧）

SKILL.md 已有 exit 124 兜底，但需强化：
- `windows_cloud` / `linux_server` 的轮询等待期（30s × 20 次）内，加 `SECONDS` 检测，超过外部 WORKER_TIMEOUT 阈值（如 80min）提前 break 并写 timeout FAIL
- 确保 `.brain-result.json` 写入在 `exit 0` 前有显式 fsync（防止被 SIGKILL 截断）

## Regression Test 计划

**Failing Test（commit-1）**：

文件：`packages/brain/src/__tests__/harness-evaluate-timeout-recovery.test.js`

```javascript
// 模拟场景：evaluateContractNode 的 interrupt() 等待期间，容器死亡（exit 124 / SIGKILL）
// Brain 没有收到 callback
// 预期：Brain 应在 CALLBACK_TIMEOUT_MS 后检测到容器已死，主动将 evaluate_verdict 置为 FAIL
// 不应让 task 永久停留在 running/in_progress 状态

describe('evaluateContractNode — callback timeout recovery', () => {
  it('container exits with code 124 (timeout), no callback received → evaluate_verdict = FAIL', async () => {
    // Arrange: spawn evaluator 容器，模拟容器死亡（checkLiveness 返回 death reason）
    // 不发送任何 callback
    // Assert: 超过 CALLBACK_TIMEOUT_MS 后，task status 变为 failed
    // Assert: evaluate_verdict = 'FAIL'
    // Assert: evaluate_error 包含 'timeout' 或 'container_died'
    // 关键断言：task 不应停留在 running 超过 CALLBACK_TIMEOUT_MS + 10s margin
  });

  it('E2E sub-script times out (exit 124) but container stays alive → callback sent with verdict=FAIL', async () => {
    // 场景 B：子脚本超时但容器存活
    // 预期：evaluator skill 写 brain-result.json，callback 正常 POST，evaluate_verdict = FAIL
    // 不进入 fix loop（evaluate_error 明确说明是 timeout，非 implementation failure）
  });
});
```

## 验收标准

- [ ] failing test 先 commit（commit-1），CI L1 run 可见失败
- [ ] 修复：evaluateContractNode 加 callback 超时兜底，容器死亡时主动推进到 FAIL 而非永久等待
- [ ] test 变绿（commit-2）
- [ ] 手动验证：用 `docker kill` 强杀一个正在跑的 evaluate 容器，确认 task 在 ~CALLBACK_TIMEOUT_MS 内自动标记 failed（不需要人工干预）
- [ ] CI 全绿
```

---

## 执行状态

**路径识别**：路径 A（Bug）✅

**上下文查询**（3 个 curl）：
- curl 1 `/api/brain/journeys`：返回 19 条，定位到 `Cecelia Harness Pipeline`（bb8cc561）✅
- curl 2 `/api/brain/issues?limit=20`：返回 20 条，找到 4 条直接相关 Issue ✅
- curl 3 `/api/brain/decisions/match`：返回空（无历史决策）✅

**PrepPRD 状态**：已生成，包含以下内容：
- 3 条根因假设（主要 + 2 次要）
- 关联 Issue：4 条（d43dff7b / 6a89c10c / 33a4ac9a / 320399d8）
- 修法：3 个文件（harness-task.graph.js / harness-watchdog.js / harness-evaluator SKILL.md）
- Regression Test 计划：2 个测试场景
- 验收标准：5 条（含手动验证）

**下一步（真实执行时）**：
1. 写 decision（`category: "bug-fix"`）到 Brain strategic-decisions
2. 调用 `Skill({"skill":"superpowers:systematic-debugging"})`
3. → engine-worktree → fix PR → engine-ship → engine-pr-watchdog
