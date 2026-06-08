---
name: feature-update
description: |
  Feature Registry 更新与 Notion 同步。新 feature 上线、状态变更、版本迭代时触发。
  触发词：更新 feature registry、同步 feature 到 Notion、新增 feature、feature 废弃、
  feature 版本升级、feature 状态变更、feature 注册。
---

> ⚠️ 本 skill 已废弃（2026-06-08）：feature registry 的角色由 abilities catalog 取代，改用 /api/brain/abilities。保留仅作历史。

# Feature Update Skill

## Notion Feature Registry

- **DB ID**: `352c40c2-ba63-810c-bb52-ced1cfb6fea1`
- **Notion 页面**: `cp-cecelia-feature-hierarchy`
- **同步脚本**: `packages/brain/scripts/sync-features-to-notion.mjs`

---

## 场景 1：全量同步到 Notion

Brain feature registry → Notion，用于批量更新 smoke 状态、新增一批 feature 后同步。

```bash
cd /Users/administrator/perfect21/cecelia
node packages/brain/scripts/sync-features-to-notion.mjs
```

---

## 场景 2：新增一个 Feature

**Step 1** — 在 Brain DB 插入记录

```sql
INSERT INTO features (id, name, domain, priority, status, smoke_cmd)
VALUES (
  'feature-id',
  'Feature 中文名',
  'domain-name',   -- tick/task/health/memory/content...
  'P1',
  'active',
  'curl -sf http://localhost:5221/api/brain/your-endpoint | grep -q "ok"'
);
```

或通过 Migration 文件（推荐，走 PR 流程）：
```sql
-- packages/brain/migrations/XXX_add_feature.sql
INSERT INTO features (id, name, domain, priority, status, smoke_cmd) VALUES (...);
```

**Step 2** — 同步到 Notion

```bash
node packages/brain/scripts/sync-features-to-notion.mjs
```

Notion 会自动创建新条目，挂到对应 Module 下（根据 domain 自动映射）。

---

## 场景 3：Feature 状态变更

```bash
# 废弃
curl -X PATCH http://localhost:5221/api/brain/features/feature-id \
  -H "Content-Type: application/json" \
  -d '{"status": "deprecated"}'

# 重新激活
curl -X PATCH http://localhost:5221/api/brain/features/feature-id \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'
```

然后重新同步 Notion：
```bash
node packages/brain/scripts/sync-features-to-notion.mjs
```

---

## 场景 4：Feature 版本升级（重新设计）

当 feature 被大幅重新设计时，Version +1，Since 保持不变。

```bash
# 查当前 Brain 版本
cat packages/brain/package.json | python3 -c "import json,sys; print(json.load(sys.stdin)['version'])"

# 更新 Notion 上的 Version 字段（通过同步脚本会自动保留现有值）
# 需要手动在 Notion 中将 Version 字段 +1，或：
node -e "
const DB_ID = '352c40c2-ba63-810c-bb52-ced1cfb6fea1';
// ... PATCH specific feature page
"
```

---

## Domain → Module 映射

| Domain | Module |
|--------|--------|
| tick | Tick Engine |
| schedule | Scheduled Jobs |
| health | System Health |
| operation | Operations |
| admin | System Config |
| task | Task Lifecycle / Task Intelligence |
| planning | Harness & Planning |
| proposal | Proposals |
| immune | Immune System |
| quarantine | Quarantine |
| cortex | Cortex |
| memory | Memory & Knowledge |
| goal | OKR Management / OKR Intelligence |
| desire | Desire System |
| alertness | Alertness System |
| agent | Agent Execution |
| collaboration | Notifications / Brain Interface |
| dashboard | Dashboard UI |
| content | Content Pipeline / Topic Management |
| analytics | Analytics |

---

## 字段说明

| 字段 | 含义 | 修改时机 |
|------|------|---------|
| `Status` | 生命周期：active/planned/deprecated | feature 上线/废弃时 |
| `Smoke Status` | 健康状态：passing/failing/unknown | CI 自动更新 |
| `Version` | feature 自身迭代版本（从 1 开始） | 大幅重新设计时 +1 |
| `Since` | 引入时的 Brain 版本（如 v1.226.0） | 新增时填写，此后不变 |
