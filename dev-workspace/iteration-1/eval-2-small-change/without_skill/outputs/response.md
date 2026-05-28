# 回应：给 journey_features 表加 priority 字段

## 调研结论

`journey_features` 表位于 **Cecelia Brain DB**（`packages/brain/`），不在 ZenithJoy 仓库。

当前表结构（来自 migration `282_dev_management_tables.sql`）：

```sql
CREATE TABLE IF NOT EXISTS journey_features (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  notion_id        VARCHAR(100) UNIQUE,
  journey_id       UUID         REFERENCES journeys(id) ON DELETE SET NULL,
  step_id          UUID         REFERENCES journey_steps(id) ON DELETE SET NULL,
  name             VARCHAR(200) NOT NULL,
  thickness        VARCHAR(20)  NOT NULL DEFAULT 'thin'
                   CHECK (thickness IN ('thin','medium','thick','mature')),
  status           VARCHAR(20)  NOT NULL DEFAULT 'planned'
                   CHECK (status IN ('planned','building','done','deprecated')),
  area_id          UUID         REFERENCES areas(id) ON DELETE SET NULL,
  unit_test_path   VARCHAR(500),
  version          VARCHAR(50),
  notion_synced_at TIMESTAMPTZ,
  created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

`priority` 字段目前不存在（`issues` 表有 P0/P1/P2/P3，但 `journey_features` 没有）。

---

## 需要改动的 3 个地方

### 1. 新建 migration `284_journey_features_priority.sql`

路径：`/Users/administrator/perfect21/cecelia/packages/brain/migrations/284_journey_features_priority.sql`

```sql
-- Migration 284: journey_features 加 priority 字段
-- 支持 P0/P1/P2，默认 P1

ALTER TABLE journey_features
  ADD COLUMN IF NOT EXISTS priority VARCHAR(5) NOT NULL DEFAULT 'P1'
    CHECK (priority IN ('P0', 'P1', 'P2'));

CREATE INDEX IF NOT EXISTS idx_journey_features_priority ON journey_features (priority);

COMMENT ON COLUMN journey_features.priority IS 'P0=必须本 sprint 完成 / P1=默认优先级 / P2=可推迟';
```

**设计决策：**
- 值域选 `P0/P1/P2`（3 级），不采用 `issues` 表的 4 级（P0-P3），因为 feature 粒度不需要 P3
- 默认 `P1` 符合用户要求，且与已有惯例一致（中等优先级为默认）
- `NOT NULL DEFAULT 'P1'` — 历史存量数据自动得到 P1，无需手工补全

### 2. 更新路由 `packages/brain/src/routes/journeys.js`

**POST `/api/brain/journey_features`** — 接收并写入 `priority`：

```js
// 在常量区加
const VALID_FEATURE_PRIORITY = ['P0', 'P1', 'P2'];

// POST handler 解构加 priority
const { name, journey_id, thickness, status, area, unit_test_path, version, priority } = req.body;

// 校验
if (priority && !VALID_FEATURE_PRIORITY.includes(priority)) {
  return res.status(400).json({ error: `priority must be one of: ${VALID_FEATURE_PRIORITY.join(',')}` });
}

// INSERT 语句加列
`INSERT INTO journey_features
   (name, journey_id, thickness, status, area_id, unit_test_path, version, priority, notion_synced_at)
 VALUES ($1,$2,$3,$4,$5,$6,$7,$8,NULL)
 RETURNING *`
// 参数加 priority || 'P1'
```

**PATCH `/api/brain/journey_features/:id`** — 支持更新 `priority`：

```js
const { thickness, status, unit_test_path, version, priority } = req.body;

if (priority && !VALID_FEATURE_PRIORITY.includes(priority)) {
  return res.status(400).json({ error: `priority must be one of: ${VALID_FEATURE_PRIORITY.join(',')}` });
}

// sets/vals 逻辑里加
if (priority) { sets.push(`priority=$${idx++}`); vals.push(priority); }
```

**GET `/api/brain/journey_features`** — 支持按 priority 过滤（可选）：

```js
const { journey_id, area, status, priority, limit = 100 } = req.query;
if (priority) { params.push(priority); clauses.push(`priority=$${params.length}`); }
```

### 3. 补测试 `journeys.test.js`

```js
describe('POST /api/brain/journey_features — priority', () => {
  it('priority 非法值返回 400', async () => {
    // 不 mock query，直接测校验逻辑
    const res = await request(app)
      .post('/api/brain/journey_features')
      .send({ name: 'Feature X', priority: 'P9' });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/priority/);
  });

  it('priority 合法值写入成功', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [{ id: 'f1', name: 'Feature X', priority: 'P0' }] });
    const res = await request(app)
      .post('/api/brain/journey_features')
      .send({ name: 'Feature X', priority: 'P0' });
    expect(res.status).toBe(201);
    expect(res.body.priority).toBe('P0');
  });

  it('不传 priority 时默认 P1', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [{ id: 'f2', name: 'Feature Y', priority: 'P1' }] });
    const res = await request(app)
      .post('/api/brain/journey_features')
      .send({ name: 'Feature Y' });
    expect(res.status).toBe(201);
    // 检查 SQL 参数里用了 'P1' 默认值
    const callArgs = mockQuery.mock.calls[0][1];
    expect(callArgs).toContain('P1');
  });
});
```

---

## 执行步骤

由于 Cecelia repo 的 branch-protect hook 要求在 `cp-*` 分支上操作，需要先创建工作分支：

```bash
# 在 cecelia repo 创建分支
git -C /path/to/cecelia checkout -b cp-20260526-journey-features-priority

# 然后按顺序：
# 1. 写 migration 284（已创建：284_journey_features_priority.sql）
# 2. 更新 journeys.js 路由（POST + PATCH + GET）
# 3. 补测试，先跑 failing test 确认 TDD commit-1
# 4. 实现路由变更，让测试通过
# 5. 推 PR
```

migration 文件已创建在：
`/Users/administrator/perfect21/cecelia/packages/brain/migrations/284_journey_features_priority.sql`

路由和测试文件因 branch-protect hook 阻止在 main 直接修改，需在 cp-* 分支执行。

---

## 风险说明

- 存量数据：`DEFAULT 'P1'` + `NOT NULL` 的 `ALTER TABLE ... ADD COLUMN` 在 PostgreSQL 12+ 是原子快速操作（元数据变更，不全表重写），线上安全。
- Notion 同步：`notion_synced_at` 不需要置 NULL（priority 不映射 Notion 字段，本地字段）。若后续要同步到 Notion，需在 `notion-push-sync.js` 补 mapping。
