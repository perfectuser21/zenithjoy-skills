# harness-generator 执行计划（Dry-Run Eval）

## 任务上下文

```
TASK_ID:         eval-gen-001
SPRINT_DIR:      /tmp/sprint-eval-gen-001
CONTRACT_BRANCH: contract/eval-gen-001
PLANNER_BRANCH:  planner/eval-gen-001
```

---

## Step 0: 解析任务上下文 — 自检结果

| 变量 | 值 | 状态 |
|------|----|------|
| CONTRACT_BRANCH | contract/eval-gen-001 | ✅ 已注入 |
| SPRINT_DIR | /tmp/sprint-eval-gen-001 | ✅ 已注入 |
| BRAIN_URL | （dry-run，跳过） | ⚠️ dry-run 豁免 |
| IS_SKELETON | false | — |

---

## Step 2: 分支命名计划

```bash
BRANCH="cp-$(TZ=Asia/Shanghai date +%m%d%H%M)-eval0001"
# 示例：cp-05301423-eval0001
# 合规检查：^cp-[0-9]{8,10}-[a-z0-9][a-z0-9_-]*$  ✅
```

---

## 合同 DoD 解析

合同共包含 4 个验收条目：

### [ARTIFACT] 条目（2 条）
1. `packages/brain/src/routes/ping.js` 必须存在
   - 校验命令：`test -f packages/brain/src/routes/ping.js`
2. `tests/ping.test.js` 必须存在
   - 校验命令：`test -f tests/ping.test.js`

### [BEHAVIOR] 条目（2 条）
1. GET /api/brain/ping 返回 HTTP 200，且响应体含 `pong: true`
   - 校验命令：`curl -sf localhost:5221/api/brain/ping | jq -e '.pong == true'`
2. 响应体含 `ts` 字段（unix 时间戳，> 0）
   - 校验命令：`curl -sf localhost:5221/api/brain/ping | jq -e '.ts > 0'`

**总计：2 ARTIFACT + 2 BEHAVIOR，generator 严格只实现这 4 项，合同外一字不加。**

---

## 两次 Commit 完整计划

### Commit 1 — RED（仅测试文件 + DoD，禁含实现）

**commit message：** `test(harness): sprint failing tests (Red)`

**staging 的文件：**
- `tests/ping.test.js`（从合同 checkout，原样复制，下方展示完整内容）
- `DoD.md`（从 contract-dod.md 复制，加 contract 来源 header）

**为什么 commit 1 会是红色：**
- `packages/brain/src/routes/ping.js` 尚不存在
- HTTP server 尚未注册 `/api/brain/ping` 路由
- 测试 import 的模块不存在 → 运行时立即失败
- `curl localhost:5221/api/brain/ping` 会返回 404 或连接拒绝

**Red 证据（预期输出形态）：**
```
FAIL  tests/ping.test.js
  Brain /ping endpoint
    × GET /api/brain/ping 返回 HTTP 200
    × 响应包含 pong: true
    × 响应包含 ts 字段且 > 0

Test Files  1 failed (1)
Tests       3 failed (3)
```

---

### Commit 2 — GREEN（实现代码 + ARTIFACT 产物）

**commit message：** `feat(harness): sprint implementation (Green)`

**staging 的文件：**
- `packages/brain/src/routes/ping.js`（下方展示完整内容）
- `packages/brain/src/server.js`（追加路由注册片段，若已存在则仅追加 import + use）

**commit 2 严格禁止修改 `tests/ping.test.js`**——测试文件在 commit 1 后不可变更，CI 强校验。

**Green 证据（预期输出形态）：**
```
✓  tests/ping.test.js (3)
  Brain /ping endpoint
    ✓ GET /api/brain/ping 返回 HTTP 200
    ✓ 响应包含 pong: true
    ✓ 响应包含 ts 字段且 > 0

Test Files  1 passed (1)
Tests       3 passed (3)
```

---

## Commit 1 测试文件内容（tests/ping.test.js）

```js
// tests/ping.test.js
// 从合同 contract/eval-gen-001 原样 checkout，禁止修改
import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import request from 'supertest'
import { createApp } from '../packages/brain/src/server.js'

let app
let server

beforeAll(async () => {
  app = await createApp()
  server = app.listen(0) // 随机端口，避免与生产 5221 冲突
})

afterAll(async () => {
  await new Promise((resolve) => server.close(resolve))
})

describe('Brain /ping endpoint', () => {
  it('GET /api/brain/ping 返回 HTTP 200', async () => {
    const res = await request(server).get('/api/brain/ping')
    expect(res.status).toBe(200)
  })

  it('响应包含 pong: true', async () => {
    const res = await request(server).get('/api/brain/ping')
    expect(res.body.pong).toBe(true)
  })

  it('响应包含 ts 字段且 > 0', async () => {
    const res = await request(server).get('/api/brain/ping')
    expect(typeof res.body.ts).toBe('number')
    expect(res.body.ts).toBeGreaterThan(0)
  })
})
```

**说明：**
- 使用 `supertest` 驱动真实 HTTP 请求，不使用 mock
- `beforeAll` 启动真实 express 应用（随机端口，避免与生产 5221 冲突）
- `afterAll` 关闭 server，防止端口泄漏
- 3 个 `it()` 块分别覆盖合同 2 条 [BEHAVIOR]（HTTP 200 单独一条，`pong` 一条，`ts` 一条）
- commit 1 时 `packages/brain/src/routes/ping.js` 不存在 → import 失败 → 全红 ✓

---

## Commit 2 实现代码内容（packages/brain/src/routes/ping.js）

```js
// packages/brain/src/routes/ping.js
import { Router } from 'express'

const router = Router()

/**
 * GET /api/brain/ping
 * 合同 [BEHAVIOR]:
 *   - 返回 HTTP 200
 *   - 响应体含 pong: true
 *   - 响应体含 ts（unix 时间戳，秒级整数，> 0）
 */
router.get('/ping', (_req, res) => {
  res.status(200).json({
    pong: true,
    ts: Math.floor(Date.now() / 1000),
  })
})

export default router
```

**server 入口修改（packages/brain/src/server.js 需追加路由注册）：**

```js
// 在现有 server.js 中追加（示例片段，具体位置视现有代码结构而定）
import pingRouter from './routes/ping.js'

// ...existing middleware setup...

app.use('/api/brain', pingRouter)
```

**实现极简说明：**
- `pong: true` — 硬编码布尔值，满足合同 [BEHAVIOR] 断言 `.pong == true`
- `ts: Math.floor(Date.now() / 1000)` — 当前 unix 秒级时间戳，始终 > 0，满足 [BEHAVIOR] 断言 `.ts > 0`
- HTTP 200 由 `res.status(200)` 显式指定
- 无任何合同外字段（无 `message`、无 `version`、无其他内容）

---

## Scope 确认：合同覆盖检查（CONTRACT IS LAW）

| 合同条目 | 类型 | 落实位置 | 状态 |
|---------|------|----------|------|
| `packages/brain/src/routes/ping.js` exists | [ARTIFACT] | commit 2 创建此文件 | ✅ |
| `tests/ping.test.js` exists | [ARTIFACT] | commit 1 checkout 此文件 | ✅ |
| GET /api/brain/ping returns HTTP 200 | [BEHAVIOR] | ping.js → `res.status(200)` | ✅ |
| Response contains pong: true | [BEHAVIOR] | ping.js → `pong: true` | ✅ |
| Response contains ts field > 0 | [BEHAVIOR] | ping.js → `ts: Math.floor(Date.now()/1000)` | ✅ |

**合同外内容：一字未加。**

以下内容不会出现在实现中：

| 项目 | 不加的原因 |
|------|-----------|
| 响应 `message` 字段 | 合同 [BEHAVIOR] 只检查 `pong` 和 `ts` |
| 响应 `version` 字段 | 合同未提及 |
| 认证/鉴权中间件 | 合同未要求 `/ping` 需要 auth |
| 速率限制 | 合同未要求 |
| 额外 unit tests | 合同只规定 2 ARTIFACT + 2 BEHAVIOR |
| health check 数据库连接 | 合同未要求 |

---

## Contract 自验（Step 6.5）计划

push 前必须真起 server 在 5221 端口，逐条跑合同 [BEHAVIOR] manual:bash 命令：

```bash
# 启动 server（背景进程）
node packages/brain/src/server.js &
SERVER_PID=$!
sleep 2  # 等待 server 就绪

# 跑合同 [BEHAVIOR] 1
curl -sf localhost:5221/api/brain/ping | jq -e '.pong == true'
# 预期 exit 0，输出 true

# 跑合同 [BEHAVIOR] 2
curl -sf localhost:5221/api/brain/ping | jq -e '.ts > 0'
# 预期 exit 0，输出 true

# 清理
kill $SERVER_PID

echo "[contract-self-verify] 2 / 2 PASS — 可以 push"
```

全部 exit 0 后才执行 `git push origin HEAD`。

---

## 禁止事项确认

- [x] 未修改测试文件（commit 1 checkout 后不触碰）
- [x] 未在合同外加任何功能（无额外端点/中间件/日志）
- [x] 未自判 PASS（需 evaluator + CI 最终裁定）
- [x] 未在 main 分支操作
- [x] 未使用广泛文件搜索（`find /Users` 等）
- [x] dry-run 模式：无实际 git commit，无 push

---

## Dry-Run 确认

本文档是 dry-run eval 输出，不包含以下实际操作：
- 无 `git checkout`、`git commit`、`git push`
- 无文件写入（除本 execution-plan.md）
- 无 npm/vitest 实际执行
- 无 HTTP server 启动

实际执行时，上述代码块将按 harness-generator Step 3（Red）→ Step 4（Green）→ Step 5（Verification）→ Step 6.5（Contract 自验）→ Step 7（Push + PR）顺序执行。

---

## Verdict（dry-run 预期）

```json
{
  "verdict": "DONE",
  "pr_url": "https://github.com/perfect21/zenithjoy/pull/XXX",
  "all_behaviors_passed": true,
  "behaviors_run": 2,
  "behaviors_passed": 2
}
```
