# Sprint PRD — W55 Brain 批量端点

**Task ID**: eval-planner-002-baseline  
**Sprint**: W55  
**Feature**: Brain API POST /api/brain/decisions/bulk  
**日期**: 2026-05-30

---

## 1. 背景与目标

Brain API（`localhost:5221`，Cecelia 系统）提供对 `decisions` 表的操作能力。当前只有 `POST /api/brain/decisions/match`（关键词匹配）和 strategic-decisions CRUD 路由，缺少批量写入能力。

当多个决策需要在一次 session 中批量记录时（如 harness 收尾、sprint 回顾），逐条调用效率低且容易因单条失败打断整批写入。本 sprint 新增 `POST /api/brain/decisions/bulk` 端点，支持一次请求写入最多 10 条 decisions，并返回结构化的成功/失败摘要。

---

## 2. 功能范围

### 2.1 新增端点

**`POST /api/brain/decisions/bulk`**

- 挂载于 Cecelia Brain API 服务（`packages/brain/server.js`，端口 5221）
- 鉴权：与现有 Brain 内部路由一致（无强制 token，dev 环境放行）
- 路由文件：新建 `packages/brain/src/routes/decisions-bulk.js`
- 在 `server.js` 挂载：`app.post('/api/brain/decisions/bulk', express.json(), decisionsBlukHandler)`

### 2.2 请求格式

```json
POST /api/brain/decisions/bulk
Content-Type: application/json

{
  "decisions": [
    {
      "category": "architecture",
      "topic": "选择哪个数据库",
      "decision": "使用 PostgreSQL",
      "reason": "已有团队经验，支持 JSONB",
      "status": "active"
    },
    {
      "category": "api",
      "topic": "认证方案",
      "decision": "使用 Bearer token",
      "reason": "与现有内部 API 保持一致"
    }
  ]
}
```

**字段约束**（单条 decision）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `category` | string | 否 | varchar(50)，如 architecture/api/deploy |
| `topic` | string | 是 | varchar(200)，决策主题，不能为空 |
| `decision` | string | 是 | text，决策内容，不能为空 |
| `reason` | string | 否 | text，决策理由 |
| `status` | string | 否 | 默认 `active`，可选 active/superseded |

**数组约束**：
- `decisions` 字段必须存在且为数组
- 数组长度 1~10，超过 10 返回 400
- 空数组返回 400

### 2.3 响应格式

**成功（全部写入）— HTTP 200**：
```json
{
  "created": 2,
  "failed": 0,
  "errors": []
}
```

**部分成功（部分写入）— HTTP 207**：
```json
{
  "created": 1,
  "failed": 1,
  "errors": ["index 1: topic is required"]
}
```

**全部失败或请求非法 — HTTP 400**：
```json
{
  "created": 0,
  "failed": 0,
  "errors": ["decisions must be an array of 1-10 items"]
}
```

**服务器错误 — HTTP 500**：
```json
{
  "created": 0,
  "failed": 2,
  "errors": ["index 0: DB insert failed: connection refused", "index 1: DB insert failed: connection refused"]
}
```

### 2.4 数据库操作

写入目标表：`decisions`（Brain DB，无 schema 前缀）

```sql
INSERT INTO decisions (category, topic, decision, reason, status, created_at, updated_at)
VALUES ($1, $2, $3, $4, $5, now(), now())
RETURNING id
```

- 每条 decision 独立 INSERT（不使用事务批量插入），允许部分成功
- `status` 默认值 `'active'`
- `id` 为 `uuid DEFAULT gen_random_uuid()`（数据库自动生成）
- 不填 `trigger`/`context`/`actions`/`confidence`（这些字段为 operational 路径专用，本端点是 manual 写入路径）

---

## 3. decisions 表结构参考

来源：Brain DB `packages/brain/migrations/009_fix_decisions_schema.sql`：

```sql
CREATE TABLE IF NOT EXISTS decisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  category varchar(50),
  topic varchar(200),
  decision text,
  reason text,
  status varchar(20) DEFAULT 'active',
  superseded_by uuid,
  created_at timestamp DEFAULT now(),
  updated_at timestamp DEFAULT now(),
  trigger text,
  context jsonb,
  actions jsonb,
  confidence numeric,
  executed_at timestamp,
  notion_synced_at timestamptz,  -- migration 284
  notion_id varchar(100) UNIQUE  -- migration 289
);
```

---

## 4. 实现计划

### commit-1：失败 E2E smoke（TDD 第一刀）

文件：`packages/brain/src/routes/__tests__/decisions-bulk.test.js`

覆盖以下用例：
1. 写入 2 条合法 decisions → `{created: 2, failed: 0, errors: []}`，HTTP 200
2. decisions 超过 10 条 → HTTP 400
3. decisions 为空数组 → HTTP 400
4. decisions 字段缺失 → HTTP 400
5. 单条缺少 topic → HTTP 207，`{created: 0, failed: 1, errors: ["index 0: topic is required"]}`
6. DB 报错时 → HTTP 500，errors 含 DB 错误信息
7. 混合：3 条其中 1 条缺 decision → `{created: 2, failed: 1, ...}`，HTTP 207

### commit-2：实现 + 挂载

1. 新建 `packages/brain/src/routes/decisions-bulk.js`
2. 在 `packages/brain/server.js` 挂载路由
3. 所有 commit-1 测试通过

---

## 5. E2E / Smoke 验收标准

### 5.1 Smoke Test（curl）

文件：`.github/workflows/scripts/smoke/brain-decisions-bulk-smoke.sh`

```bash
#!/bin/bash
set -e
BASE="http://localhost:5221"

# Test 1: 批量写入 2 条
RESP=$(curl -s -X POST "$BASE/api/brain/decisions/bulk" \
  -H "Content-Type: application/json" \
  -d '{"decisions":[{"topic":"选DB","decision":"PostgreSQL"},{"topic":"选框架","decision":"Express"}]}')
echo "Test 1: $RESP"
echo "$RESP" | jq -e '.created == 2 and .failed == 0' > /dev/null

# Test 2: 超 10 条拒绝
RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/brain/decisions/bulk" \
  -H "Content-Type: application/json" \
  -d '{"decisions":[{"topic":"t","decision":"d"},{"topic":"t","decision":"d"},{"topic":"t","decision":"d"},{"topic":"t","decision":"d"},{"topic":"t","decision":"d"},{"topic":"t","decision":"d"},{"topic":"t","decision":"d"},{"topic":"t","decision":"d"},{"topic":"t","decision":"d"},{"topic":"t","decision":"d"},{"topic":"t","decision":"d"}]}')
[ "$RESP" = "400" ] || { echo "Test 2 FAIL: expected 400 got $RESP"; exit 1; }

# Test 3: 写入后能在 decisions 表查到
COUNT=$(psql "$BRAIN_DATABASE_URL" -t -c "SELECT count(*) FROM decisions WHERE topic='选DB' AND decision='PostgreSQL';")
[ "$COUNT" -ge "1" ] || { echo "Test 3 FAIL: record not found in DB"; exit 1; }

echo "All brain-decisions-bulk smoke tests PASSED"
```

### 5.2 单元测试

运行：`cd packages/brain && node --experimental-vm-modules ../../node_modules/.bin/vitest run src/routes/__tests__/decisions-bulk.test.js`

验收条件：7/7 通过，0 失败。

---

## 6. 文件变更清单

| 操作 | 文件路径 |
|------|---------|
| 新建（测试，commit-1） | `packages/brain/src/routes/__tests__/decisions-bulk.test.js` |
| 新建（实现，commit-2） | `packages/brain/src/routes/decisions-bulk.js` |
| 修改（挂载路由，commit-2） | `packages/brain/server.js` |
| 新建（smoke，commit-2） | `.github/workflows/scripts/smoke/brain-decisions-bulk-smoke.sh` |

---

## 7. 不在范围内

- 不支持 upsert（ON CONFLICT），每条独立 INSERT
- 不支持事务性批量（全部成功或全部失败），允许部分成功
- 不支持 `trigger`/`context`/`actions`/`confidence` 字段（operational 路径字段，由 decision engine 自动填）
- 不支持 `notion_id`/`notion_synced_at` 写入（由 Notion 同步任务管理）
- 不支持分页或条数超过 10 的分批自动拆分

---

## 8. 风险与依赖

| 风险 | 处理方式 |
|------|---------|
| Brain DB 不可用 | 各条独立 try/catch，DB 错误计入 `failed` + `errors`，返回 500 |
| `topic` 或 `decision` 为空字符串 | 校验时 trim 后判断，空串视为缺失 |
| decisions 表 `topic` varchar(200) 超长 | 数据库层报错，计入 `errors[index]` |
| 并发写入产生重复 | decisions 无唯一约束（除 notion_id），可重复写入，由调用方控制 |

---

## 9. Golden Path（验收场景）

**用户看到什么（完成条件）**：

调用 `POST /api/brain/decisions/bulk` 传入含 2 条 decision 的数组后：
1. HTTP 响应为 200，body `{created: 2, failed: 0, errors: []}`
2. Brain DB `decisions` 表中能查到这 2 条新记录，`status = 'active'`
3. Smoke test 脚本 exit 0，CI 绿

---

*本 PRD 由 Harness Planner 生成，无 Brain API 上下文时基于代码库分析（`packages/brain/src/decision.js`、`migrations/009_fix_decisions_schema.sql`、`packages/brain/src/routes/decisions.js`）完成。*
