# /dev 执行记录：给 abilities 表加 group 字段

---

## 第零步 Phase 1：听懂意图

**用户原话：** 给 abilities 表加个 group 字段，字符串类型，用来做 Ability Group 聚合，比如抖音发布这个 group 下面有长视频/短视频/图文三个 Ability

**判断：**
- 关键词：「加个字段」、「字符串类型」→ 明确小改动
- 不是 bug，不是大功能立项
- **路径 B：小改动**

---

## 第零步 Phase 2：按路径 B 查上下文

### 执行的 3 个 curl（路径 B）

```bash
# 1. 查所有 Journey，确认改动挂哪条线
curl -s "localhost:5221/api/brain/journeys"

# 2. 匹配历史决策（关键词：abilities group 字段）
curl -s -X POST "localhost:5221/api/brain/decisions/match" \
  -H "Content-Type: application/json" \
  -d "{\"prd\": \"abilities group 字段 Ability Group 聚合 抖音发布\"}"

# 3. 查进行中任务，判断是否有相关 task 在进行
curl -s "localhost:5221/api/brain/tasks?status=in_progress&limit=20"
```

### 上下文解读（基于已探索的代码库）

Brain API 不可用（sandbox），但已通过代码库探索获得等效上下文：

**abilities 表当前结构**（来源：`/Users/administrator/perfect21/cecelia/packages/brain/migrations/294_abilities_goldenpath.sql`）：
```sql
CREATE TABLE IF NOT EXISTS abilities (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          VARCHAR(200) NOT NULL,
  area          VARCHAR(50)  NOT NULL,
  journey_id    UUID REFERENCES journeys(id) ON DELETE SET NULL,
  kind          VARCHAR(20)  NOT NULL DEFAULT 'ability',
  type          VARCHAR(50),
  workflow_ref  VARCHAR(500),
  status        VARCHAR(20)  NOT NULL DEFAULT 'planned',
  notion_id     VARCHAR(100),
  notion_synced_at TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  ...
);
```

**目前没有 `group` 字段**，与 CLAUDE.md 决策（2026-06-09）描述的「`abilities.group` 字段定义 Ability Group 聚合」一致，需要新增。

**涉及文件：**
- 迁移：`/Users/administrator/perfect21/cecelia/packages/brain/migrations/` → 需新建 `295_abilities_group.sql`
- 路由：`/Users/administrator/perfect21/cecelia/packages/brain/src/routes/abilities.js` → POST/PATCH 需支持 `group` 字段
- 测试：`/Users/administrator/perfect21/cecelia/packages/brain/src/routes/__tests__/abilities.test.js` → 需补 group 相关 test case

**相关 Journey：** Line 00（ZenithJoy 运营中枢）— abilities 表属于 Brain API 层，是平台基础设施，归 Line 00 管辖。也可关联到具体用例出现的 Line 01（智能发布）。

---

## PrepPRD

```markdown
# 小改动 PrepPRD：abilities 表新增 group 字段，支持 Ability Group 聚合

## 改什么
- **DB 层（cecelia Brain）**：`abilities` 表新增 `group VARCHAR(100)` 字段，可为 NULL（现有记录默认 null，不破坏存量数据）
- **API 路由层**：
  - `POST /api/brain/abilities`：接受 `group` 参数并写入
  - `PATCH /api/brain/abilities/:id`：接受 `group` 参数更新
  - `GET /api/brain/abilities`：查询结果里自然带出 `group` 字段（SELECT * 已覆盖）
  - 可选：支持 `?group=xxx` 过滤参数（方便后续查某 group 下的所有 ability）
- **测试层**：补充 `group` 字段的 POST/PATCH/GET 过滤 unit test

## 为什么改
CLAUDE.md 决策（2026-06-09）：Ability Group = Notion Project，同一 Journey 下相关 Ability/Feature 的聚合（如"抖音发布"含长视频/短视频/图文三个 Ability）由 `abilities.group` 字段定义。此字段是 Notion 同步和 Dashboard 分组渲染的前提。

## 关联上下文
- 相关 Journey：Line 00（ZenithJoy 运营中枢 — Brain 基础设施层）
- 相关历史决策：「decisions a6bf01ef」（Ability Group = Notion Project，abilities.group 字段承载聚合）
- 无相关 Issue

## 影响范围
- `SELECT *` 的 GET 接口自动带出新字段，前端/消费方无破坏性变更（字段 nullable）
- 存量 abilities 记录 `group = NULL`，不影响现有 API 输出语义
- Notion 同步逻辑如有（`notion_synced_at` 置 NULL 时触发）需适配新字段，但当前 Notion 同步未实现，暂不需处理
- 无 cascade 影响（golden_path 表不引用 group 字段）

## 验收标准
- [ ] 迁移文件 `295_abilities_group.sql` 存在，内容：`ALTER TABLE abilities ADD COLUMN IF NOT EXISTS "group" VARCHAR(100);` + 可选 index
- [ ] `POST /api/brain/abilities` 传 `group` 字段可正常写入，返回 201 含 group 字段
- [ ] `PATCH /api/brain/abilities/:id` 传 `group` 字段可正常更新
- [ ] `GET /api/brain/abilities?group=抖音发布` 返回该 group 下的 ability 列表（如实现过滤）
- [ ] 现有 abilities 相关 unit tests 全部通过（无 regression）
- [ ] CI 全绿
```

---

## Decision curl（路径 B 执行后立即写）

```bash
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d "{
    \"topic\": \"abilities 表新增 group 字段做 Ability Group 聚合\",
    \"decision\": \"在 Brain abilities 表加 group VARCHAR(100) 可空字段，POST/PATCH 路由支持读写，GET 支持 group 过滤；新增迁移 295_abilities_group.sql\",
    \"reason\": \"CLAUDE.md 决策(a6bf01ef)：Ability Group = Notion Project，由 abilities.group 字段定义聚合（如抖音发布含长视频/短视频/图文三个 Ability），是 Notion 同步和 Dashboard 分组的前提\",
    \"made_by\": \"user\",
    \"author\": \"user\",
    \"category\": \"small-change\"
  }"
```

---

## PrepPRD 落地命令

```bash
SPRINT_DIR="sprints/$(TZ=Asia/Shanghai date +%m%d%H%M)-abilities-group-field"
mkdir -p "/Users/administrator/perfect21/zenithjoy/$SPRINT_DIR"
cat > "/Users/administrator/perfect21/zenithjoy/$SPRINT_DIR/prep-prd.md" << 'EOF'
# 小改动 PrepPRD：abilities 表新增 group 字段，支持 Ability Group 聚合
...（PrepPRD 全文）...
EOF
echo "已保存 PrepPRD 到 $SPRINT_DIR/prep-prd.md"
```

（注：sprint 目录建在 **cecelia** repo，因为 abilities 表在 cecelia Brain 里，不在 zenithjoy repo。正确路径：`/Users/administrator/perfect21/cecelia/sprints/MMDDHHNN-abilities-group-field/`）

---

## 下一步：调用 engine-worktree

路径 B 确认后，下一个 tool call 必须是：

```
Skill({"skill": "engine-worktree"})
```

**Superpowers 接力链：**
`engine-worktree` → `brainstorming` → `writing-plans` → `subagent-driven-development` → `finishing (Option 2 push+PR)` → `engine-ship` → `engine-pr-watchdog`

---

## 实现摘要（给 engine-worktree 的 subagent 参考）

### 文件 1：新建迁移
**路径：** `/Users/administrator/perfect21/cecelia/packages/brain/migrations/295_abilities_group.sql`

```sql
-- Migration 295: abilities 表新增 group 字段（Ability Group 聚合）
-- Ability Group = Notion Project，由 group 字段定义同一 Journey 下相关 Ability/Feature 的聚合

ALTER TABLE abilities ADD COLUMN IF NOT EXISTS "group" VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_abilities_group ON abilities("group")
  WHERE "group" IS NOT NULL;
```

### 文件 2：更新路由（改动最小化）
**路径：** `/Users/administrator/perfect21/cecelia/packages/brain/src/routes/abilities.js`

改动点：
1. `POST /abilities` body 解构加 `group`，INSERT 语句加字段
2. `PATCH /abilities/:id` body 解构加 `group`，动态 SET 加 group 分支
3. `GET /abilities` query 加 `group` 过滤支持

### 文件 3：补 unit test（TDD iron law：commit-1 先写 failing test）
**路径：** `/Users/administrator/perfect21/cecelia/packages/brain/src/routes/__tests__/abilities.test.js`

新增 test case：
- `POST /abilities 带 group 字段返回 201 且 body.group === '抖音发布'`
- `PATCH /abilities/:id 可更新 group 字段`
- `GET /abilities?group=抖音发布 返回过滤结果`

---

## 路径判定总结

| 项目 | 结果 |
|------|------|
| 路径 | **B（小改动）** |
| 涉及 repo | `cecelia`（Brain API，不是 zenithjoy） |
| 核心文件 | `migrations/295_abilities_group.sql`、`src/routes/abilities.js`、`src/routes/__tests__/abilities.test.js` |
| 破坏性 | 无（nullable 字段，SELECT * 兼容） |
| 下一技能 | `engine-worktree` |
