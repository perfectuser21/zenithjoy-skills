# Sprint PRD — 测试演练 B42

**Task ID**: eval-planner-001-baseline
**Sprint Dir**: /tmp/sprint-eval-planner-001-baseline
**创建时间**: 2026-05-30

---

## 1. 背景与目标

为 playground 服务添加一个健康检查/ping 路由，供监控和客户端连通性检测使用。

## 2. 需求描述

在 playground（后端服务）中新增 `GET /ping` HTTP 路由，响应固定 JSON 格式，包含活跃标志和当前服务器时间戳。

## 3. 验收标准（Acceptance Criteria）

| # | 条件 | 验证方式 |
|---|------|---------|
| 1 | `GET /ping` 返回 HTTP 200 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:<PORT>/ping` 输出 `200` |
| 2 | 响应 Content-Type 为 `application/json` | 响应头包含 `application/json` |
| 3 | 响应 body 包含 `pong: true` | `jq '.pong'` 输出 `true` |
| 4 | 响应 body 包含 `ts` 字段，值为合理的 Unix 时间戳（整数，≥ 1700000000） | `jq '.ts'` 输出整数且数值合理 |
| 5 | 每次调用 `ts` 值单调递增或相等（不回退） | 连续两次调用，第二次 `ts ≥` 第一次 |

## 4. 技术规格

### 4.1 路由定义

```
GET /ping
```

### 4.2 响应格式

```json
{
  "pong": true,
  "ts": 1748563200
}
```

- `pong`: 布尔值，固定为 `true`
- `ts`: 整数，Unix 时间戳（秒级），等于服务器处理请求时的 `Date.now() / 1000 | 0`（或 Python `int(time.time())`）

### 4.3 实现位置

根据 playground 服务的技术栈确定路由注册位置：
- **Node.js/Express**: 在主路由文件中添加 `app.get('/ping', ...)`
- **Python/FastAPI**: 在 `main.py` 或 router 文件中添加 `@app.get("/ping")`
- **其他框架**: 遵循对应框架的路由注册惯例

### 4.4 不需要

- 认证/鉴权（ping 是公开端点）
- 数据库查询
- 任何副作用（纯只读）

## 5. 测试要求

### 5.1 E2E Smoke Test（先写）

文件路径: `.github/workflows/scripts/smoke/ping-smoke.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3000}"

echo "=== /ping smoke test ==="

# 1. HTTP 200
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/ping")
[ "$STATUS" = "200" ] || { echo "FAIL: expected 200, got $STATUS"; exit 1; }
echo "PASS: HTTP 200"

# 2. JSON body
BODY=$(curl -s "$BASE_URL/ping")
PONG=$(echo "$BODY" | jq -r '.pong')
[ "$PONG" = "true" ] || { echo "FAIL: pong=$PONG"; exit 1; }
echo "PASS: pong=true"

# 3. ts is a reasonable unix timestamp
TS=$(echo "$BODY" | jq -r '.ts')
[ "$TS" -ge 1700000000 ] 2>/dev/null || { echo "FAIL: ts=$TS not a valid unix timestamp"; exit 1; }
echo "PASS: ts=$TS"

echo "=== All /ping checks passed ==="
```

### 5.2 Unit Test

对路由 handler 函数做单元测试，验证返回值结构正确。

## 6. 不在本 Sprint 范围内

- `/health` 或其他健康端点扩展
- 响应中添加服务版本号、环境信息等扩展字段
- 认证包装

## 7. 完成定义（Definition of Done）

- [ ] `GET /ping` 路由已实现
- [ ] ping-smoke.sh 通过（exit 0）
- [ ] Unit test 通过
- [ ] CI 全绿
- [ ] PR 已合并
