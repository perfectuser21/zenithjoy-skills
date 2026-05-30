# Sprint PRD — playground GET /ping 端点实现

## OKR 对齐

- **对应 KR**：N/A（dry-run eval sprint，无关联活跃 KR）
- **当前进度**：N/A
- **本次推进预期**：N/A

## 背景

在 playground 中新增 `GET /ping` 健康检查路由，返回固定 JSON shape `{pong: true, ts: <unix timestamp>}`，验证 playground server 框架可正确处理路由注册与 JSON 响应。

## Golden Path（核心场景）

调用方从 `GET /ping` → playground server 匹配路由 → 返回 HTTP 200 + JSON body → 调用方确认 `pong` 为 `true`、`ts` 为正整数

具体：
1. playground server 在 `playground/server.js` 注册 `GET /ping` 路由
2. 收到请求后，构造 `{ pong: true, ts: Math.floor(Date.now() / 1000) }` 并以 `application/json` 返回
3. curl 请求该端点，收到 HTTP 200，body 含 `pong: true`（boolean）和 `ts`（正整数，unix 秒级时间戳）

## Response Schema

### Endpoint: GET /ping

**Query Parameters**: 无

**Success (HTTP 200)**:
```json
{"pong": true, "ts": 1748563200}
```
- `pong` (boolean, 必填): 字面量 `true`，禁用变体 `"true"`（字符串）/ `1` / `"pong"`
- `ts` (integer, 必填): unix 秒级时间戳（`Math.floor(Date.now() / 1000)`），必须为正整数

**Error**: 该端点不应返回 4xx/5xx，无 error shape 定义

**禁用响应字段名**: `ping`/`status`/`ok`/`alive`/`healthy`/`timestamp`（generator 不得自由发挥 key 名）

**Schema 完整性**: response 顶层 keys 必须**完全等于** `["pong", "ts"]`，不允许多余字段

## 边界情况

- 路由大小写：仅响应 `/ping`（小写），不需要响应 `/PING` 或 `/Ping`
- 并发：无状态，天然并发安全
- `ts` 精度：[ASSUMPTION: unix 秒（`Math.floor(Date.now() / 1000)`），非毫秒]

## 范围限定

**在范围内**：
- `playground/server.js` 新增 `GET /ping` 路由
- 返回 `{pong: true, ts: <unix seconds>}` JSON

**不在范围内**：
- 鉴权 / rate-limiting
- 其他路由（/health、/status 等）
- 数据库交互
- Brain API 任何改动

## 假设

- [ASSUMPTION: `ts` 为 unix 秒级（`Math.floor(Date.now() / 1000)`），非毫秒]
- [ASSUMPTION: playground server 已有基础 HTTP 框架，仅需添加路由]
- [ASSUMPTION: 端口默认 3000，可由 `PLAYGROUND_PORT` 环境变量覆盖]

## 预期受影响文件

- `playground/server.js`: 新增 GET /ping 路由处理函数

## E2E 验收

```bash
#!/usr/bin/env bash
set -euo pipefail

PORT="${PLAYGROUND_PORT:-3000}"

# 启动 playground server（后台）
cd playground && node server.js &
SPID=$!
sleep 2

# Step 1: 验证 HTTP 200
curl -sf "http://localhost:${PORT}/ping" > /tmp/ping_resp.json
echo "✅ HTTP 200 OK"

# Step 2: pong 字段为 boolean true
jq -e '.pong == true' /tmp/ping_resp.json
echo "✅ pong == true"

# Step 3: ts 为正整数
jq -e '.ts | type == "number" and . > 0 and . == floor' /tmp/ping_resp.json
echo "✅ ts 为正整数"

# Step 4: 无多余字段
KEY_COUNT=$(jq '.| keys | length' /tmp/ping_resp.json)
[ "$KEY_COUNT" -eq 2 ] || { echo "FAIL: 响应字段数应为 2，实际 $KEY_COUNT"; exit 1; }
echo "✅ 顶层 keys 恰好为 2 个"

kill $SPID 2>/dev/null || true
echo "✅ playground /ping E2E 全部通过"
```

> **位置词检查**：e2e 使用 `localhost:${PORT}/ping`（playground 端口），禁止出现 `localhost:5221/api/brain/`

---

## journey_type: autonomous
## journey_type_reason: 纯后端路由添加，无 UI 交互，无 Dashboard 涉及
## target_environment: playground
## target_environment_reason: thin_prd 含位置词 "playground"，在本地 playground/server.js 运行并验收
