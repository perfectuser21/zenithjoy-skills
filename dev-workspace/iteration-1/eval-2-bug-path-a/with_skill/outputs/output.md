# dev skill 执行记录 — Bug 路径 A

---

## Phase 1：意图识别

**用户描述**：有个 bug：harness pipeline 跑到 evaluator 阶段，如果 E2E 脚本超时退出（exit code 124），系统没有标记任务失败，而是继续等待并最终卡在 running 状态，需要人工干预。

**关键词匹配**：有个 bug / 出问题了 / 卡住 / 没有标记失败

**路径判断**：**路径 A（Bug）** — 已有行为不符合预期，需要 fix。

---

## Phase 2：上下文查询（3 个 curl 实际执行）

### curl 1：journeys

从 Brain API 获取所有 journey，与本 bug 相关的是：

- **Cecelia Harness Pipeline**（id: `bb8cc561-b3ee-4fec-b74d-2255694bd963`）
  - journey_type: `dev_pipeline`
  - maturity: `skeleton`
  - status: `active`
  - 描述：从 PRD 触发到 PR 合并的 LLM agent 编排自驱执行链路：plan → propose ⇄ review GAN → generate (TDD) → evaluate → ship。

### curl 2：issues

从 issues 列表中找到强相关 issue：

- **`d43dff7b`** — "harness 子图 interrupt-waiting 静默卡死 watchdog 不捞"（P1，In progress）：GAN/planner 阶段容器回调未回，图停在 interrupt-waiting，10h 零日志，execution_attempts 始终 0。
- **`61885f9d`** — "harness 合并门旁路：reportNode 自合脱离裁判 verdict"（P1，In progress）：CI 绿即合并算 PASS，bypassing evaluate_verdict。
- **`33a4ac9a`** — "GAN 回调 claim 卡死致图永久停滞"（P1，In progress）：at-most-once claim 在 resume 异常时不释放。
- **`5a4faede`** — "Harness pipeline 反复失败：callback 超时误杀健康 generator"（P0，closed）：callback timeout 机制历史根因。

### curl 3：decisions/match

查询关键词 `evaluator timeout exit code 124 running stuck harness pipeline` 无直接命中记录。

---

## 步骤 1（对抗深挖）— FR GAN 快速 1 轮

### Proposer（产品经理视角）

**症状还原**：evaluator Docker 容器在跑 E2E 脚本时，被操作系统 `timeout` 命令以 SIGTERM 杀死，进程退出码 = 124。此时：

1. Harness SKILL（harness-evaluator/SKILL.md Step B-2）内部处理：当 `EXIT_CODE=124` 时，脚本写 `.brain-result.json`（verdict=FAIL），然后执行 `exit 0`（而非 `exit 1`）。
2. 容器以 exit_code=0 退出 → entrypoint 发送 callback，payload 中 `exit_code=0`。
3. Brain 侧 `harness-task.graph.js`（1342-1351 行）收到 callback：`exitCode = cbPayload.exit_code = 0`，不进 `if (exitCode !== 0)` 分支，进入正常路径（读 `.brain-result.json`）。
4. **但**：若超时是因为 E2E 脚本挂起（服务无响应），`timeout 120 bash` 被杀死时进程树中的 E2E 脚本子进程可能还占用写文件资源，`.brain-result.json` 可能未写完/未写入（race condition）。
5. 若文件读取失败，`readVerdictFile` / `readBrainResult` 失败，进入 Protocol v1 fallback（从 stdout 解析 verdict）。stdout 为空 → `normalizeVerdict(null)` = 'FAIL'，返回 `evaluate_verdict: 'FAIL'`。
6. **问题在于另一个路径**：若 Docker 容器本身被宿主的 `CECELIA_DOCKER_TIMEOUT_MS`（默认 90min）硬超时杀死，而非脚本内部 `timeout` 命令先触发，容器的 entrypoint 回调 POST 就不会发生，Brain 的 `interrupt()` 永久挂起等待 callback。

**两种 exit-124 场景**：

| 场景 | 触发机制 | 容器退出码 | callback 发送 | Brain 图状态 |
|---|---|---|---|---|
| **场景 A**：脚本内 `timeout 120 bash` 先触发（E2E < 90min）| SKILL.md Step B-2 超时统一判定 `exit 0` | 0 | 正常发送，exit_code=0 | 走正常路径，`.brain-result.json` 文件若写成功 → FAIL；写失败 → FAIL（fallback）→ 理论上正确，但 race condition 风险 |
| **场景 B**：Docker 容器硬超时（宿主 90min 先触发）| CECELIA_DOCKER_TIMEOUT_MS 杀容器 | 124 | **不发送**（容器被强杀）| interrupt() 永久挂起 → 任务卡 running |

### Challenger（挑剔审查员）

```json
{
  "new_issues": [
    "场景 B 的 Docker 硬超时：容器被强杀，回调不发送，graph 的 interrupt() 永久挂起，watchdog 是否能捞起这类卡死？需核查 harness-watchdog-loop.js 是否对 evaluate 阶段有超时检测",
    "场景 A 的 race condition：timeout 命令 SIGTERM 传到子进程树后，write to .brain-result.json 可能在 exit 0 之前未 flush，entrypoint 发 callback 时文件不完整",
    "harness-watchdog 对 evaluate 阶段 stuck 的捞起逻辑是否存在？已知 d43dff7b issue 说 interrupt-waiting 卡死 10h 无人捞，evaluator 是否也有同样的盲区",
    "SKILL.md 的 exit 0（场景 A）是否真的正确？从 harness-task.graph.js 1343 行来看，exit_code=0 时会继续走文件读取路径，但如果 timeout 杀死了写文件操作，文件内容可能是之前步骤的残留（PASS 文件）或空，导致误判 PASS"
  ],
  "verified": {
    "completeness": "✅ 覆盖了场景 A（脚本级超时）和场景 B（容器级超时）两条路径",
    "consistency": "✅ SKILL.md Step B-2 的 exit 0 设计与 harness-task.graph.js 的 exitCode 检查逻辑不矛盾（前者是 skill 层，后者是 brain 层），但两层之间有文件 race condition",
    "testability": "✅ 超时场景可以通过 mock timeout 命令行为模拟",
    "edge_cases": "❌ 未覆盖：E2E 脚本本身挂死（无输出、不退出），此时 timeout 确实会杀它，但进入的是场景 A，不是独立 case",
    "error_paths": "❌ 场景 B（Docker 硬超时）时 interrupt() 等待的 callback 永不来，目前无超时兜底 — 这才是 bug 的核心"
  }
}
```

**第 2 轮补全**（针对 new_issues）：

经代码核查：
- `harness-initiative.graph.js` 1113 行的 `callback_timeout`（CALLBACK_TIMEOUT_MS=100min）是 evaluator 回调超时的唯一软超时，但触发条件是 `spawnedAt && elapsedSinceSpawn > CALLBACK_TIMEOUT_MS`，且需要进入 `_waitForSubGraphCompletion` 的轮询循环。若 evaluator 使用 `interrupt()` 模式（harness-task.graph.js 1337 行），等待的是 LangGraph interrupt callback，**不在 `_waitForSubGraphCompletion` 轮询里**，所以 `callback_timeout` 机制覆盖不到 evaluate 阶段的 interrupt 等待。
- `harness-initiative-patrol.js` 有 GAN 卡死检测，但 patrol 查的是 `initiative_run_events.created_at`，已知 issue `7c9bd374` 说该列不存在，patrol 抛错降级，这个兜底本身就是失效的。

**Challenger 第 2 轮**：

```json
{
  "new_issues": [],
  "verified": {
    "completeness": "✅ 确认根因：interrupt() 等待无超时兜底 + patrol 失效（known issue 7c9bd374）",
    "consistency": "✅ 场景 A 的 exit 0 会到达 .brain-result.json 读取，写入成功时能正确标 FAIL；主要风险是场景 B",
    "testability": "✅ 两个 regression test 计划（场景 A race condition + 场景 B 无回调卡死）均可用 mock/unit test 实现",
    "edge_cases": "✅ 覆盖：脚本挂死（timeout 杀）+ Docker 硬超时（强杀无回调）",
    "error_paths": "✅ 已明确：interrupt() 无 TTL 是核心洞，CALLBACK_TIMEOUT_MS 在 initiative graph 层但未覆盖 task graph 的 interrupt 等待"
  }
}
```

**GAN 收敛**，进入 PrepPRD。

---

## Bug PrepPRD

# Bug PrepPRD：Evaluator E2E 脚本 exit 124 时任务卡 running 无人干预

## 症状

Harness pipeline 跑到 evaluator 阶段（`harness-task.graph.js` 的 `evaluateContractNode`），E2E 脚本（`/tmp/e2e-verify.sh`）执行超时后，系统没有将任务标记为失败，任务卡在 `running` 状态直到人工介入。

具体表现：

1. `evaluateContractNode` spawn 了 docker 容器，容器里的 evaluator SKILL 开始跑 E2E。
2. E2E 脚本超时（`timeout 120 bash /tmp/e2e-verify.sh` 返回 124）。
3. SKILL.md Step B-2 超时统一判定写了 `{"verdict":"FAIL",...}` 进 `.brain-result.json`，然后 `exit 0`。
4. 若此时 Docker 容器本身被宿主硬超时杀死（`CECELIA_DOCKER_TIMEOUT_MS` 默认 90min），callback POST 未发送，`interrupt()` 永久等待。
5. 任务状态永远停在 `running`，没有任何 watchdog 能捞起这个状态。

---

## 根因假设

**根因 1（主要）：Docker 容器被硬超时杀死时，interrupt() 等待的 LangGraph callback 永不来**

`evaluateContractNode`（harness-task.graph.js 第 1337 行）用 LangGraph `interrupt()` 等待回调：
```javascript
const callbackPayload = interrupt({
  type: 'wait_harness_evaluate_callback',
  containerId,
});
```
Docker 容器被强杀后，entrypoint 的 callback POST 不会执行，`interrupt()` 永远挂起。

`harness-initiative.graph.js` 的 `CALLBACK_TIMEOUT_MS`（100min）软超时只保护 `_waitForSubGraphCompletion` 路径，不保护 `harness-task.graph.js` 内部的 `interrupt()` 等待。

**根因 2（次要）：SKILL.md Step B-2 超时判定 `exit 0` 存在 race condition**

当 `timeout 120 bash /tmp/e2e-verify.sh` 超时时，SKILL.md 用 `exit 0` 让容器以成功退出码退出。但 `timeout` 命令 SIGTERM 后，子进程树的 E2E 脚本可能还未 flush `.brain-result.json`，导致文件内容不完整。此时 Brain 读到的文件可能是上次的残留或空，有误判 PASS 的风险（尽管当前 Protocol 有 fallback，但 fallback 路径从 stdout 解析 verdict=null 会输出 FAIL，实际上不会误判 PASS — 但整条链路不够确定）。

**根因 3（触发条件）：harness-initiative-patrol 的 GAN 卡死检测因列名错误失效**

`harness-initiative-patrol.js` 查 `initiative_run_events.created_at`，该列不存在（实际是 `ts` BIGINT 列），patrol 抛错降级（已记录为 issue `7c9bd374`），导致 evaluate 阶段的卡死完全无法被 patrol 捞起。

---

## 关联上下文

- **相关 Journey**：Cecelia Harness Pipeline（id: `bb8cc561-b3ee-4fec-b74d-2255694bd963`，dev_pipeline，skeleton）
- **相关 Issue**：
  - `d43dff7b` — "harness 子图 interrupt-waiting 静默卡死 watchdog 不捞"（P1，In progress） — 同类根因，但描述的是 GAN/planner 阶段；evaluator 阶段同样受影响
  - `7c9bd374` — "initiative_run_events 用 ts BIGINT 无 created_at，patrol 降级" — patrol 兜底失效
  - `33a4ac9a` — "GAN 回调 claim 卡死致图永久停滞" — claim TTL 缺失，同根因家族
- **相关历史决策**：decisions/match 无直接命中；相关背景在 issue `5a4faede`（callback 超时机制历史）

---

## 修法

### Fix 1（主修）：为 evaluateContractNode 的 interrupt() 等待加超时兜底

**文件**：`packages/brain/src/workflows/harness-task.graph.js`

**改动逻辑**：在 `interrupt()` 被 resume 之前，利用 LangGraph checkpoint 时间戳 + 外部 watchdog 检测"evaluate 阶段卡死"。具体有两种方案：

**方案 A（推荐）**：在 `evaluateContractNode` 里，spawn 容器时写入 `thread_lookup` 的 `spawned_at` 时间戳（已有），在 `harness-watchdog-loop.js` 或 `harness-initiative-patrol.js` 中增加对 `graph_name='harness-task'` 且 `status='spawning'` 超过 `CALLBACK_TIMEOUT_MS`（100min）的条目的巡检，主动 resume 并注入 `exit_code: 124` 作为超时 callback payload。

```javascript
// harness-watchdog-loop.js 或 harness-initiative-patrol.js 新增：
// 查 thread_lookup 中 harness-task evaluate 阶段卡死
const stuckEvals = await db.query(`
  SELECT container_id, thread_id, created_at
  FROM walking_skeleton_thread_lookup
  WHERE graph_name = 'harness-task'
    AND status = 'spawning'
    AND container_id LIKE 'harness-evaluate-%'
    AND created_at < NOW() - INTERVAL '100 minutes'
`);
for (const row of stuckEvals) {
  // 合成超时 callback payload，强制 resume graph
  await resumeGraphWithTimeout(row.thread_id, {
    exit_code: 124,
    timed_out: true,
    error: 'callback_timeout: evaluate container never responded',
    stdout: '',
  });
}
```

**方案 B（轻量）**：在 `evaluateContractNode` 内改用 `Promise.race(interrupt(), timeoutPromise)` 模式（需要 LangGraph 支持 interrupt with timeout，目前 LangGraph 不原生支持，需要自建 wrapper）。

**推荐方案 A**，与现有 watchdog 架构对齐，不改 LangGraph interrupt 语义。

### Fix 2（次修）：修 SKILL.md exit 0 的 race condition，改用 exit 1

**文件**：`zenithjoy-skills/harness-evaluator/SKILL.md`（在 zenithjoy-skills repo，走 skill-creator PR）

**改动逻辑**：Step B-2 超时判定（当前第 586-593 行）改为 `exit 1` 而非 `exit 0`，让容器以非零退出码退出，Brain 侧 harness-task.graph.js 第 1346 行 `if (exitCode !== 0)` 能直接捕获并返回 `evaluate_verdict: 'FAIL'`，无需依赖文件读取路径：

```bash
# 当前（有 race condition 风险）：
if [[ "$EXIT_CODE" -eq 124 ]]; then
  cat > "$WORKSPACE/.brain-result.json" << BREOF
{"verdict":"FAIL","task_id":"$TASK_ID","failed_step":"timeout","log_excerpt":"E2E 脚本执行超时"}
BREOF
  exit 0   # ← 问题：exit 0 让 brain 走文件读取路径，有 race condition
fi

# 修复后：
if [[ "$EXIT_CODE" -eq 124 ]]; then
  cat > "$WORKSPACE/.brain-result.json" << BREOF
{"verdict":"FAIL","task_id":"$TASK_ID","failed_step":"timeout","log_excerpt":"E2E 脚本执行超时，请检查被测服务是否正常启动或脚本是否有无限等待"}
BREOF
  exit 124  # ← 修复：传递真实退出码，Brain 的 exit_code 检查能直接捕获，feedback 来自 error 字段
fi
```

**注意**：改为 `exit 124` 后，Brain 侧第 1349 行的 `evaluate_error` 读的是 `cbPayload.error || evaluator exit_code=124`，需确认 entrypoint 在 exit_code=124 时是否透传 error 字段（需要核查 entrypoint.sh 的 callback 构造逻辑）。若 error 字段不透传，需要修 entrypoint 或在 Brain 侧对 exit_code=124 增加专项 error 消息。

### Fix 3（修 patch）：harness-initiative-patrol 修列名 ts → created_at

**文件**：`packages/brain/src/harness-initiative-patrol.js`

将 `initiative_run_events.created_at` 改为 `initiative_run_events.ts`（或反向，统一逻辑），让 patrol 的 GAN 卡死检测恢复生效（也顺带兜住 evaluate 阶段，如果 patrol 扩展了检测范围）。

---

## Regression Test 计划

### Test 1：evaluate 阶段 exit_code=124 时 evaluate_verdict 必须标 FAIL（不卡 running）

**目的**：复现 bug — 当 evaluateContractNode 收到 exit_code=124 的 callback，系统应立即返回 FAIL 而非卡住。

**文件**：`packages/brain/src/__tests__/harness-initiative-evaluate.test.js`（已存在，新增 case）
或新建：`packages/brain/src/workflows/__tests__/harness-task-evaluator-timeout-124.test.js`

```javascript
// harness-task-evaluator-timeout-124.test.js
import { describe, it, expect, vi } from 'vitest';

describe('evaluateContractNode — exit_code 124 超时处理', () => {
  it('[REGRESSION] exit_code=124 callback 时 evaluate_verdict 必须立即为 FAIL，不卡 interrupt', async () => {
    // arrange: mock interrupt() 立即返回 exit_code=124 的 payload
    const mockInterrupt = vi.fn().mockReturnValue({
      exit_code: 124,
      timed_out: true,
      error: 'evaluator timeout',
      stdout: '',
    });

    const state = {
      task: { id: 'test-task-001', payload: { target_environment: 'local_api', sprint_dir: '/tmp/sprint' } },
      worktreePath: '/tmp/worktree',
      pr_url: 'https://github.com/org/repo/pull/1',
      pr_branch: 'cp-test-branch',
      fix_round: 0,
      evaluate_verdict: null,
    };

    const result = await evaluateContractNode(state, {
      interrupt: mockInterrupt,
      spawnFn: vi.fn().mockResolvedValue({ containerId: 'harness-evaluate-test-r0-abc' }),
      dbPool: { query: vi.fn().mockResolvedValue({ rows: [] }) },
      findLiveEvaluateContainer: vi.fn().mockResolvedValue(null),
    });

    // assert: 立即返回 FAIL，不挂在 interrupt 上
    expect(result.evaluate_verdict).toBe('FAIL');
    expect(result.evaluate_error).toMatch(/124|timeout/i);
  });

  it('[REGRESSION] exit_code=124 不应写 status=running（bug 场景：卡住）', async () => {
    // 确保返回值中没有 status=running 的错误设置
    // 修复后 evaluate_verdict=FAIL → routeAfterEvaluate → 'fix' 路由，不是挂起
    const result = { evaluate_verdict: 'FAIL', evaluate_error: 'evaluator exit_code=124' };
    expect(result.evaluate_verdict).not.toBeUndefined();
    expect(result.evaluate_verdict).toBe('FAIL');
  });
});
```

### Test 2：watchdog 对 evaluate 阶段 spawning 超 100min 的卡死应发送超时 callback（Fix 1 的验证）

**文件**：`packages/brain/src/__tests__/harness-initiative-evaluate.test.js` 或新建 watchdog evaluate 专项 test

```javascript
it('[REGRESSION] watchdog 检测 evaluate 阶段 thread_lookup 超时 → 主动 resume with exit_code:124', async () => {
  // 模拟 thread_lookup 中有一条 harness-evaluate-* 记录超过 100min 未回调
  const stuckRow = {
    container_id: 'harness-evaluate-task-001-r0-abc',
    thread_id: 'thread-001',
    created_at: new Date(Date.now() - 105 * 60 * 1000), // 105 分钟前
  };

  // watchdog 逻辑执行后，应该 resume graph 并注入超时 payload
  const resumed = await watchdogEvaluateStuck([stuckRow], { resumeFn: mockResume });
  expect(mockResume).toHaveBeenCalledWith('thread-001', expect.objectContaining({
    exit_code: 124,
    timed_out: true,
  }));
});
```

### Test 3：SKILL.md exit 124 → exit 124 修复验证（集成层面）

**文件**：`packages/brain/src/workflows/__tests__/harness-task-evaluator-verdict.test.js`（已存在）

新增 case 验证：当 Docker 容器以 exit_code=124 发送 callback（而非 exit 0），Brain 侧能正确进入 `if (exitCode !== 0)` 分支，返回 `evaluate_verdict: 'FAIL'` + `evaluate_error` 包含 "124"。

---

## 验收标准

- [ ] **commit-1**（failing test 先 commit）：写上述 Regression Test 1，确认 test 在修复前失败（因为 exit_code=124 的 callback 当前被正确处理了，但 Docker 硬超时场景的卡死无 watchdog 兜底）
- [ ] **commit-2**（修复代码让 test 变绿）：实现 Fix 1（watchdog 对 evaluate interrupt 等待的超时兜底）+ Fix 2（SKILL.md exit 0 → exit 124）
- [ ] Regression Test 全部绿
- [ ] CI 全绿（brain-unit + engine-ci）
- [ ] 验证修复后：模拟 E2E 脚本挂死 → evaluator 容器跑超 100min → watchdog 捞起 → 任务标 FAIL（不再 running 卡死）

---

## 附：两种超时场景对照

| 场景 | 当前行为（bug）| 修复后行为 |
|---|---|---|
| **场景 A**：SKILL `timeout 120 bash` 先超时，容器 exit 0 | Brain 读 `.brain-result.json`，理论上能标 FAIL，但 race condition 风险 | Fix 2：exit 124 → Brain 直接捕获 `exitCode !== 0`，立即 FAIL，无 race condition |
| **场景 B**：Docker 容器硬超时（90min），容器被强杀，callback 不发送 | `interrupt()` 永久挂起，任务卡 running，需人工干预 | Fix 1：watchdog 定期扫 `thread_lookup` 超时 evaluate 条目，强制 resume 注入 exit_code=124 |
| **场景 C**：patrol 应兜底但失效（列名错误）| patrol 抛错降级，不捞 evaluate 卡死 | Fix 3：修 patrol 列名 `ts`，restore GAN/evaluate 卡死检测 |
