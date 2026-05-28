# /dev Skill 执行记录

## 第零步：查 Brain DB 上下文

**Brain API 状态：** localhost:5221 不可达（Connection refused，exit 7），假设返回空结果。

**查询的表：**
- `/api/brain/tasks` → 空
- `/api/brain/journeys` → 空
- `/api/brain/features` → 空
- `/api/brain/decisions` → 空

**补充上下文（从代码库直接读取）：**
- `journey_features` 表定义在 `/Users/administrator/perfect21/cecelia/packages/brain/migrations/282_dev_management_tables.sql`
- 当前表结构：`id`, `notion_id`, `journey_id`, `step_id`, `name`, `thickness`, `status`, `area_id`, `unit_test_path`, `version`, `notion_synced_at`, `created_at`, `updated_at`
- 无 `priority` 字段

---

## 类型判断

**任务：** "给 journey_features 表加个 priority 字段，P0/P1/P2，默认 P1"

- 改一个字段 → **小改动路径**（单 WS）
- 无报错，非 Bug
- 非新 Journey，不贯穿全链路

**结论：小改动（Small Change）**

---

## 小改动 PrepPRD

```
========================================
小改动 PrepPRD
========================================
任务：给 journey_features 表加 priority 字段
类型：小改动（DB schema + 对应 TypeScript model）
分支：cp-<timestamp>-journey-features-priority
========================================

【Why — 为什么做】
journey_features 当前没有优先级字段，无法在 Brain 系统中对 feature 按 P0/P1/P2
区分重要程度，harness 排期和 sprint-planner 无法按优先级筛选 feature。

【What — 做什么】
1. DB migration：在 journey_features 表新增 priority 列
   - 类型：VARCHAR(2)
   - CHECK 约束：IN ('P0', 'P1', 'P2')
   - DEFAULT 'P1'
   - NOT NULL

2. TypeScript 类型更新：在对应 interface/type 定义里加 priority 字段

3. API 层（如果有 journey_features CRUD）：确保 priority 字段可读写

【Files Changed（预估）】
- cecelia/packages/brain/migrations/284_journey_features_priority.sql  [新建]
- cecelia/packages/brain/src/types/journey.ts 或对应 model 文件         [修改]
- 若有 API handler：cecelia/packages/brain/src/routes/journeyFeatures.ts [修改]

【Migration SQL 草稿】
```sql
-- Migration 284: journey_features 加 priority 字段
ALTER TABLE journey_features
  ADD COLUMN IF NOT EXISTS priority VARCHAR(2) NOT NULL DEFAULT 'P1'
  CHECK (priority IN ('P0', 'P1', 'P2'));

CREATE INDEX IF NOT EXISTS idx_journey_features_priority ON journey_features (priority);
```

【Smoke Test（E2E-First）】
commit-1（失败的 smoke）：
  验证 journey_features 表有 priority 列、默认值 P1、CHECK 约束生效

commit-2（实现）：
  migration + model 更新，让 smoke 通过

【影响范围评估】
- 只加字段，DEFAULT P1 保证向后兼容，现有数据自动填 P1
- 无破坏性变更（No breaking change）
- 影响：journey_features 表的所有读写 API（新字段透传即可）

【完成标准（DoD）】
- [ ] Migration 跑通，psql 可查 priority 列
- [ ] 插入新 feature 不传 priority 时默认 P1
- [ ] 传 P3 时 DB 报 CHECK constraint violation
- [ ] TypeScript 类型有 priority 字段（不是 any）
- [ ] CI lint + type-check 通过

估时：30 分钟
========================================
```

---

## 接下来的动作

### Decision 写入 Brain DB

```json
{
  "table": "decisions",
  "payload": {
    "context": "给 journey_features 表加 priority 字段 P0/P1/P2 默认 P1",
    "decision": "走小改动路径，单 WS，建 migration 284_journey_features_priority.sql",
    "rationale": "纯 schema 变更 + model 更新，无新 Journey，无跨系统影响，30 min 内可完成",
    "branch": "cp-<timestamp>-journey-features-priority"
  }
}
```
（Brain API 不可用时跳过写入，继续执行）

### 路由到：`engine-worktree` skill

调用参数：
- **任务描述：** 给 journey_features 表加 priority 字段（P0/P1/P2，默认 P1）
- **分支名：** `cp-YYYYMMDD-journey-features-priority`
- **变更文件：**
  1. `packages/brain/migrations/284_journey_features_priority.sql`（新建 migration）
  2. 对应 TypeScript model/type 文件（加 `priority` 字段）
- **commit 顺序：**
  - commit-1：smoke/E2E test（定义验收条件）
  - commit-2：migration + model 实现
- **目标 repo：** `cecelia`（journey_features 在 Brain DB，Brain DB 在 cecelia repo）

> 不实际执行 engine-worktree，等待用户确认（"对"/"走"）。
