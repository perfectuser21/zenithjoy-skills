---
name: write-tests
description: |
  Walking Skeleton 做完后补测试。每次功能跑通后调用。
  补三种测试：Unit+Integration（apps/api/tests/）、E2E（apps/dashboard/e2e/）、Smoke（packages/brain/scripts/smoke/）。
  触发词：补测试、写测试、test、walking skeleton 做完了、功能跑通了、补 E2E、补 unit test
version: 1.0.0
---

# Write Tests — Walking Skeleton 完成后补测试

## 核心规则

每次 Walking Skeleton 做完，补 **3 个文件**：

| 文件 | 类型 | 放哪里 |
|------|------|--------|
| `<feature>.test.ts` | Unit + Integration | `apps/api/tests/` |
| `<feature>.spec.ts` | E2E（含 Golden Path） | `apps/dashboard/e2e/` |
| `<feature>-smoke.sh` | Smoke | `packages/brain/scripts/smoke/` |

---

## 第一步：确认 Golden Path

问用户：**这个功能最核心的一条路是什么？**

Golden Path = 用户最常走的那条路，走通了功能就算活着。
例：内容采集 → 贴链接 → 采集完成 → 拿到文案

E2E 文件的第一个 case 就是 Golden Path。

---

## 第二步：写 Unit + Integration（`apps/api/tests/<feature>.test.ts`）

### 模板结构

```typescript
import request from 'supertest';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import app from '../src/app';
import pool from '../src/db/connection';

vi.mock('../src/db/connection', () => ({
  default: { query: vi.fn(), end: vi.fn() },
}));

const mockQuery = pool.query as ReturnType<typeof vi.fn>;

describe('<Feature> — Unit Tests', () => {
  it('函数名：输入 → 期望输出', () => {
    // 测纯函数，不需要 mockQuery
  });
});

describe('<Feature> — Integration Tests', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('POST /api/<route> 正常场景 → 201', async () => {
    mockQuery.mockResolvedValueOnce({ rows: [/* mock DB 返回 */] });
    const res = await request(app).post('/api/<route>').send({ ... });
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({ ... });
  });

  it('POST /api/<route> 错误场景 → 400', async () => {
    const res = await request(app).post('/api/<route>').send({});
    expect(res.status).toBe(400);
  });
});
```

### 必须覆盖的 case 类型

- 正常输入 → 正确状态码 + 返回值
- 缺少必填字段 → 400
- 数据不存在 → 404
- 核心业务逻辑（如重复提交、状态流转、callback 写入）
- 关键纯函数的输入输出

---

## 第三步：写 E2E（`apps/dashboard/e2e/<feature>.spec.ts`）

### 模板结构

```typescript
import { test, expect } from '@playwright/test';

const BASE = process.env.E2E_BASE_URL || 'http://localhost:5173';

// Golden Path — 必须第一个，最核心流程
test('golden path: <核心功能描述>', async ({ page }) => {
  // stub API
  await page.route('**/api/<route>', async route => {
    await route.fulfill({ json: { /* 假数据 */ } });
  });

  await page.goto(`${BASE}/<path>`);
  // 用户操作
  await page.fill('textarea', '测试内容');
  await page.click('button:has-text("提交")');
  // 验证结果
  await expect(page.locator('text=等待中')).toBeVisible();
});

// Error Path
test('error path: 失效链接显示友好提示', async ({ page }) => { ... });

// 边界情况
test('重复提交不报错，重新采集', async ({ page }) => { ... });
```

### 注意事项

- API 全部用 `page.route()` stub，不依赖真实服务
- 在 GitHub Actions windows-latest runner 上跑（ZenithJoy 项目规则）
- 第一个 case 必须是 Golden Path
- 用 `VITE_SKIP_AUTH=true` 跳过登录

---

## 第四步：写 Smoke（`packages/brain/scripts/smoke/<feature>-smoke.sh`）

### 模板结构

```bash
#!/bin/bash
set -euo pipefail

API="${API_URL:-http://localhost:5200}"
DB_CMD="docker exec zenithjoy-postgres psql -U cecelia -d cecelia -c"

echo "=== <Feature> Smoke Test ==="

# 1. 提交真实请求
echo "Step 1: 提交请求..."
RESULT=$(curl -sf -X POST "$API/api/<route>" \
  -H "Content-Type: application/json" \
  -d '{"<key>": "<value>"}')
ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Created ID: $ID"

# 2. 等待处理
echo "Step 2: 等待处理..."
sleep 15

# 3. 验证 DB 结果
echo "Step 3: 验证 DB..."
STATUS=$($DB_CMD "SELECT status FROM zenithjoy.<table> WHERE id='$ID';" | grep -v "^-\|^(" | tr -d ' ')
[ "$STATUS" = "done" ] || { echo "FAIL: status=$STATUS"; exit 1; }

echo "✅ Smoke test passed"
```

### 注意事项

- 用真实 curl，不 mock
- 等待时间根据功能估算（采集类至少 15-30s）
- 部署后手动触发，不是每次 PR 都跑

---

## 完成标志

- [ ] `apps/api/tests/<feature>.test.ts` 存在，覆盖 unit + integration
- [ ] `apps/dashboard/e2e/<feature>.spec.ts` 存在，第一个 case 是 golden path
- [ ] `packages/brain/scripts/smoke/<feature>-smoke.sh` 存在
- [ ] CI 跑绿（api tests + E2E）
