# /dev 执行响应

## Phase 1：意图判断

用户说："给 abilities 表加个 group 字段，字符串类型，用来做 Ability Group 聚合，比如抖音发布这个 group 下面有长视频/短视频/图文三个 Ability"

关键词匹配："加个字段" → **路径 B：小改动**

---

## Phase 2：上下文查询（路径 B — 3 个 curl）

### Curl 1：查 Journeys
```bash
curl -s "localhost:5221/api/brain/journeys"
```
**预期用途**：确认 abilities 表挂在哪条 Journey 下，理解改动对哪条 Line 有影响。

### Curl 2：历史决策匹配
```bash
curl -s -X POST "localhost:5221/api/brain/decisions/match" \
  -H "Content-Type: application/json" \
  -d "{\"prd\": \"abilities group 字段 Ability Group 聚合抖音发布\"}"
```
**预期用途**：检查是否有相关历史决策（例如之前讨论过 abilities 表结构调整）。

### Curl 3：进行中任务
```bash
curl -s "localhost:5221/api/brain/tasks?status=in_progress&limit=20"
```
**预期用途**：确认是否有正在进行的 sprint 涉及 abilities 表，避免冲突。

---

## 上下文分析（模拟）

基于已有代码探索结果：

- `abilities` 表定义在 Brain DB（Cecelia packages/brain）的 migration `294_abilities_goldenpath.sql`
- 当前字段：`id`, `name`, `area`, `journey_id`, `kind`, `type`, `workflow_ref`, `status`, `notion_id`, `notion_synced_at`, `created_at`, `updated_at`
- **无 `group` 字段**，与 CLAUDE.md 中"abilities 表待补字段：`group`（字符串，承载 Project 层聚合，如 "抖音发布"）"一致
- 最新 migration 编号：294，下一个应为 295

历史决策中，`2026-06-09 decisions a6bf01ef` 已明确：
> "Ability Group = Notion Project。同一 Journey 下相关 Ability/Feature 的聚合，由 `abilities.group` 字段定义"

---

## PrepPRD

```markdown
# 小改动 PrepPRD：给 abilities 表加 group 字段（Ability Group 聚合层）

## 改什么
在 Brain DB 的 `abilities` 表加一个 `group` 字段：
- 字段名：`group`（VARCHAR 或 TEXT）
- 类型：字符串，可为 NULL（无聚合时为空）
- 含义：Ability Group 名称，如"抖音发布"，承载 L3 Project 层聚合

## 为什么改
CLAUDE.md 层级映射决策（2026-06-09，decisions a6bf01ef）已明确：
- Ability Group = Notion Project，由 `abilities.group` 字段聚合定义
- 当前 `abilities` 表缺少此字段，Brain API 无法按 Group 筛选/聚合 Ability
- 用户举例：抖音发布这个 group 下包含长视频、短视频、图文三个 Ability

## 关联上下文
- 相关 Journey/Feature：所有 Journey（group 是跨 Journey 的聚合键）
- 相关历史决策：decisions a6bf01ef（2026-06-09）—— Ability Group = Notion Project，`abilities.group` 字段定义
- 当前最新 migration：`294_abilities_goldenpath.sql`（建 abilities + golden_path 表）

## 影响范围
1. Brain DB schema：新增 migration `295_abilities_add_group.sql`
2. Brain API（若有 `/api/brain/abilities` 端点）：GET 响应自动含新字段（无破坏性）
3. Notion 同步逻辑（若有）：可能需要在 ability 写 Notion 时携带 group → Notion Project 对应关系
4. 不影响 abilities 表现有字段；NULL 默认值不破坏已有记录

## 验收标准
- [ ] migration `295_abilities_add_group.sql` 执行后 `\d abilities` 显示 group 列存在
- [ ] 现有 abilities 记录 group 默认为 NULL（无破坏）
- [ ] 可通过 `UPDATE abilities SET group='抖音发布' WHERE name IN ('抖音长视频发布','抖音短视频发布','抖音图文发布')` 验证写入正常
- [ ] `GET /api/brain/abilities` 响应体包含 group 字段（null 或字符串）
- [ ] CI 全绿
```

---

## Decision Curl（路径 B，写入 strategic-decisions）

```bash
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d "{\"topic\":\"abilities 表加 group 字段\",\"decision\":\"给 abilities 表加 group VARCHAR 字段，用于 Ability Group 聚合，对应 Notion Project 层（如'抖音发布'含长视频/短视频/图文三个 Ability）\",\"reason\":\"CLAUDE.md 层级决策(a6bf01ef)要求 Ability Group = Notion Project，由 abilities.group 字段定义，当前表缺此字段\",\"made_by\":\"user\",\"author\":\"user\",\"category\":\"small-change\"}"
```

---

## PrepPRD 落地文件

```bash
SPRINT_DIR="sprints/$(TZ=Asia/Shanghai date +%m%d%H%M)-abilities-add-group"
mkdir -p "$SPRINT_DIR"
cat > "$SPRINT_DIR/prep-prd.md" << 'EOF'
# 小改动 PrepPRD：给 abilities 表加 group 字段（Ability Group 聚合层）
... (全文同上)
EOF
```

---

## 下一 skill 调用

路径 B 执行链：

```
Skill({"skill":"engine-worktree"})
```

engine-worktree 接力链：
brainstorming → writing-plans → subagent-driven-development → finishing（Option 2 push+PR）→ engine-ship → engine-pr-watchdog

---

## 实现指引（供 subagent 参考）

### 文件 1：新 migration
`/Users/administrator/perfect21/cecelia/packages/brain/migrations/295_abilities_add_group.sql`

```sql
-- Migration 295: abilities 表加 group 字段（Ability Group 聚合层）
-- group 字段承载 L3 Project 层聚合（如"抖音发布"含长视频/短视频/图文三个 Ability）
-- 对应 CLAUDE.md 决策 a6bf01ef：Ability Group = Notion Project

ALTER TABLE abilities
  ADD COLUMN IF NOT EXISTS "group" TEXT;

COMMENT ON COLUMN abilities."group" IS 'Ability Group 聚合名称，对应 Notion Project 层（如"抖音发布"）；NULL 表示未分组';
```

### 文件 2：smoke test（必须先 commit）
`/Users/administrator/perfect21/cecelia/packages/brain/scripts/smoke/abilities-group-smoke.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BRAIN_BASE_URL:-http://localhost:5221}"

echo "=== abilities group 字段 smoke test ==="

# 1. 验证字段存在（通过 API 返回值含 group key）
echo "[1] GET /api/brain/abilities 返回体含 group 字段..."
RESP=$(curl -sf "$BASE_URL/api/brain/abilities?limit=1")
echo "$RESP" | grep -q '"group"' && echo "PASS" || { echo "FAIL: 响应中无 group 字段"; exit 1; }

# 2. 创建一个带 group 的 ability，验证写入
echo "[2] POST 创建带 group 的 ability..."
CREATE_RESP=$(curl -sf -X POST "$BASE_URL/api/brain/abilities" \
  -H "Content-Type: application/json" \
  -d '{"name":"smoke-test-ability","area":"zenithjoy","kind":"ability","group":"抖音发布"}')
ABILITY_ID=$(echo "$CREATE_RESP" | grep -oP '"id":"\K[^"]+')
echo "created id=$ABILITY_ID"

# 3. 验证 group 字段回写正确
echo "[3] GET /api/brain/abilities/$ABILITY_ID 验证 group='抖音发布'..."
GET_RESP=$(curl -sf "$BASE_URL/api/brain/abilities/$ABILITY_ID")
echo "$GET_RESP" | grep -q '"group":"抖音发布"' && echo "PASS" || { echo "FAIL: group 字段值不符"; exit 1; }

# 4. 清理测试数据
curl -sf -X DELETE "$BASE_URL/api/brain/abilities/$ABILITY_ID" > /dev/null || true

echo "=== ALL PASS ==="
```

### commit 顺序（强制，TDD）
- commit-1：写 smoke test（`295_abilities_add_group.sql` 还不存在，smoke 会 FAIL）
- commit-2：写 migration + API 更新，让 smoke PASS
