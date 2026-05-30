# Sprint PRD — Brain API POST /api/brain/decisions/bulk

## OKR 对齐

- **对应 KR**：KR-INFRA（Brain API 基础设施完善）
- **当前进度**：N/A（dry-run eval，跳过 Brain API 上下文采集）
- **本次推进预期**：新增批量写入能力，减少调用方多次 POST 开销

## 背景

当前 Brain API 只有单条 `POST /api/brain/decisions` 端点。批量场景（如 harness pipeline 一次写多条决策）需循环调用，效率低且容易出现部分成功状态难追踪。本 sprint 加 bulk 端点，一次请求最多写 10 条，返回明确的 created/failed/errors 三元组，调用方可自行决策重试策略。

## Golden Path（核心场景）

调用方从 [POST /api/brain/decisions/bulk，body 含 decisions 数组] → 经过 [Brain API 逐条写入 decisions 表，收集成功/失败] → 到达 [返回 {created, failed, errors}，DB 中可查到已插入记录]

具体：
1. 调用方发送 `POST /api/brain/decisions/bulk`，body 为 `{"decisions": [{...}, {...}]}`，数组长度 1–10
2. Brain API 逐条写入 decisions 表；单条写入失败不中断其余条
3. 返回 HTTP 200，body 为 `{"created": <n>, "failed": <m>, "errors": ["<err1>", ...]}`，errors 长度等于 failed

## Response Schema

### Endpoint: POST /api/brain/decisions/bulk

**Request Body**:
```json
{
  "decisions": [
    {
      "title": "string, 必填",
      "description": "string, 可选",
      "context": "string, 可选"
    }
  ]
}
```
- `decisions` (array, 必填): 长度 1–10；超过 10 条返 HTTP 400
- 数组元素字段与现有单条 decisions 端点字段保持一致（[ASSUMPTION: 现有 decisions 表至少有 title 字段为必填]）

**Success (HTTP 200)**:
```json
{"created": 3, "failed": 1, "errors": ["duplicate key value violates unique constraint"]}
```
- `created` (number, 必填): 成功写入条数
- `failed` (number, 必填): 写入失败条数；全部成功时为 `0`
- `errors` (array of string, 必填): 长度等于 `failed`；全部成功时为 `[]`
- **禁用字段名**: `success_count`/`error_count`/`results`/`data`/`inserted`/`message`
- **Schema 完整性**: response 顶层 keys 必须完全等于 `["created", "failed", "errors"]`，不允许多余字段

**Error (HTTP 400) — 超出 10 条限制**:
```json
{"error": "decisions array exceeds maximum of 10 items"}
```
- 必有 `error` key，禁用 `message`/`msg`/`reason`

**Error (HTTP 400) — 请求体格式错误**:
```json
{"error": "decisions must be a non-empty array"}
```

**Error (HTTP 500) — 全部写入失败**:
- 仍返回 HTTP 200，body 为 `{"created": 0, "failed": <n>, "errors": [...]}`（部分/全部失败不改变 HTTP 状态码）
- [ASSUMPTION: 全部失败也返回 200 + errors 数组，由调用方判断是否需重试]

## 边界情况

- 空数组 `decisions: []` → HTTP 400，`{"error": "decisions must be a non-empty array"}`
- 超过 10 条 → HTTP 400，`{"error": "decisions array exceeds maximum of 10 items"}`
- 数组中部分条目缺少必填字段 → 该条计入 failed，errors 写入字段校验错误信息，其余条继续写入
- 全部条目成功 → `{"created": N, "failed": 0, "errors": []}`
- 全部条目失败 → `{"created": 0, "failed": N, "errors": ["...", ...]}`

## 范围限定

**在范围内**：
- 新增 `POST /api/brain/decisions/bulk` 路由
- 单条写入失败不阻塞其余条（partial success 语义）
- 返回 `{created, failed, errors}` 三元组

**不在范围内**：
- 修改现有 `POST /api/brain/decisions`（单条端点不变）
- 事务性批量写入（全部成功才提交 / 任一失败全部回滚）
- 超过 10 条的分页/分批能力
- Bulk 更新或删除

## 假设

- [ASSUMPTION: 现有 decisions 表已有 id/created_at/updated_at 等基础字段，本 sprint 不加新列]
- [ASSUMPTION: Brain API 使用 Node.js + express 或类似框架，路由风格与现有一致]
- [ASSUMPTION: 全部写入失败时仍返回 HTTP 200，errors 数组完整描述失败原因]

## 预期受影响文件

- `packages/brain/src/routes/decisions.js`（或同等路由文件）: 新增 `/bulk` 路由
- `packages/brain/src/routes/index.js`（如需注册新路由）: 注册 bulk 路由
- `packages/brain/src/__tests__/decisions-bulk.test.js`（或同等测试文件）: 新增单元测试

## E2E 验收

```bash
#!/bin/bash
set -e
BASE_URL="http://localhost:5221"

# Step 1: 正常批量写入（3 条）
RESP=$(curl -sf -X POST "$BASE_URL/api/brain/decisions/bulk" \
  -H "Content-Type: application/json" \
  -d '{"decisions":[{"title":"bulk-test-1"},{"title":"bulk-test-2"},{"title":"bulk-test-3"}]}')
echo "$RESP" | jq -e '.created == 3 and .failed == 0 and (.errors | length) == 0'
echo "✅ 正常批量写入 3 条通过"

# Step 2: 超 10 条限制返 400
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/brain/decisions/bulk" \
  -H "Content-Type: application/json" \
  -d '{"decisions":[{"title":"x"},{"title":"x"},{"title":"x"},{"title":"x"},{"title":"x"},{"title":"x"},{"title":"x"},{"title":"x"},{"title":"x"},{"title":"x"},{"title":"x"}]}')
[ "$HTTP_CODE" = "400" ] && echo "✅ 超限 400 校验通过" || { echo "❌ 超限应返 400，实际 $HTTP_CODE"; exit 1; }

# Step 3: 空数组返 400
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/brain/decisions/bulk" \
  -H "Content-Type: application/json" \
  -d '{"decisions":[]}')
[ "$HTTP_CODE" = "400" ] && echo "✅ 空数组 400 校验通过" || { echo "❌ 空数组应返 400，实际 $HTTP_CODE"; exit 1; }

# Step 4: DB 验证插入记录存在
PSQL_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM decisions WHERE title LIKE 'bulk-test-%';" | xargs)
[ "$PSQL_COUNT" -ge 3 ] && echo "✅ DB 查到 $PSQL_COUNT 条 bulk-test 记录" || { echo "❌ DB 记录数不足，期望 ≥3，实际 $PSQL_COUNT"; exit 1; }

echo "✅ 全部 E2E 验收通过"
```

## journey_type: autonomous
## journey_type_reason: 纯 Brain API 后端路由新增，无 UI，无用户交互，系统内部调用
## target_environment: local_api
## target_environment_reason: 仅涉及 packages/brain/src/ 后端逻辑，evaluator 在本地用 curl localhost:5221 + psql 验证
