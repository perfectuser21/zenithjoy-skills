---
name: db-update
description: |
  系统数据写入唯一参考。写任何一张常用表之前，必须先查这个 skill。
  包含 10 张手动写入表的 Brain API 规范和 Output Template，以及 AI Notes 的 5 种 Type 写法。
  Notion 同步是自动副作用（Brain tick 每5分钟 push），不需要手动操作。
  触发场景：写 Journey / Step / Feature / Sprint / 任何 Note 类型 / Issue / Learning / Decision 时。
version: 1.0.0
created: 2026-06-01
---

> **核心原则：Brain DB 是唯一真相源。所有写入先走 Brain API，Notion 自动同步，禁止直接写 Notion。**

# /db-update — 系统数据写入规范

---

## 架构

```
任何数据写入
    ↓
POST localhost:5221/api/brain/<table>   ← 唯一入口
    ↓
Brain DB（notion_synced_at = NULL）
    ↓ 自动（每5分钟）
Notion（展示层，只读）
```

---

## 10 张手动写入表

### 1. journeys（Journey 路径）

**API**：`POST /api/brain/journeys`
**Notion**：AI Journey DB

```json
{
  "name": "客户首次成功路径",
  "journey_type": "user_facing",
  "maturity": "skeleton",
  "description": "客户从注册到完成第一次AI发布的完整路径",
  "e2e_test_path": ".github/workflows/scripts/smoke/golden-path-1-smoke.sh"
}
```

**journey_type 合法值**：`user_facing` | `autonomous` | `dev_pipeline` | `agent_remote`
**maturity 合法值**：`not_started` | `skeleton` | `mvp` | `production` | `mature`

---

### 2. journey_steps（Golden Path 步骤）

**API**：`POST /api/brain/journey_steps`
**Notion**：AI Steps DB

```json
{
  "journey_id": "uuid",
  "name": "扫码绑定抖音主号",
  "step_id": "L01-S4",
  "maturity": "passing",
  "smoke_cmd": "curl -sf localhost:5200/api/sessions | grep active",
  "shared": false
}
```

**maturity 合法值**：`not_started` | `in_progress` | `passing` | `done`

**禁止写入**：
- `smoke_cmd` 为空（没有验收标准不是 Step）
- `journey_id` 为空的孤立 Step
- 名称含 "test"、"mock"、"placeholder"

---

### 3. journey_step_links（Journey-Step 连接）

**API**：`POST /api/brain/journey_step_links`
**Notion**：Journey-Step 连接表

```json
{
  "journey_id": "uuid",
  "step_id": "uuid",
  "step_order": 4,
  "status": "done"
}
```

Name 自动生成格式：`{JourneyCode}-S{step_order}`（如 `L01-S4`、`ZjOps-S3`）

**status 合法值**：`planned` | `in_progress` | `done`

---

### 4. journey_features（功能实现单元）

**API**：`POST /api/brain/journey_features`
**Notion**：AI Feature DB

```json
{
  "journey_id": "uuid",
  "step_id": "notion-step-uuid（可选）",
  "name": "QR 码 API 端点",
  "status": "done",
  "thickness": "thin",
  "version": "1.0.0"
}
```

**status 合法值**：`planned` | `building` | `done` | `deprecated`
**thickness 合法值**：`thin` | `medium` | `thick` | `mature`

**禁止写入**：
- 名称含 `[Sprint]`、`KeysTest`、`MyRun`（测试污染）
- `journey_id` 为空

---

### 5. initiative_contracts（Sprint 合同）

**API**：`POST /api/brain/notes`（Type: Contract）或直接写 initiative_contracts 表
**含义**：PRD 内容 + DOD 合同，同一张表两个字段

```json
{
  "title": "Contract: 小红书绑定",
  "type": "Contract",
  "content": "## PRD\n...\n## DOD\n...",
  "initiative_id": "sprint-task-uuid"
}
```

---

### 6. initiative_runs（Sprint 执行记录）

**API**：Harness 自动创建，不需要手动写
**字段参考**：`phase`（A_contract|B_task_loop|C_final_e2e|done|failed）

---

### 7. tasks（工作项）

**API**：`POST /api/brain/tasks`

```json
{
  "title": "修复小红书 QR 绑定 cookie 名",
  "task_type": "harness_initiative",
  "priority": "P1",
  "payload": {
    "sprint_dir": "sprints/line00-xiaohongshu-qr-bind",
    "journey_id": "uuid"
  }
}
```

---

### 8. issues（Bug 记录）

**API**：`POST /api/brain/issues`
**Notion**：Issues DB

```json
{
  "title": "小红书 QR 绑定后 session 未持久化",
  "priority": "P1",
  "status": "In progress",
  "sub_area": "agent",
  "body": "## 症状\n...\n## 根因\n...\n## 修法\n..."
}
```

**priority 合法值**：`P0` | `P1` | `P2` | `P3`

---

### 9. skill_registry（Skill 注册）

**API**：`POST /api/brain/skills`
**Notion**：Skill Registry DB

```json
{
  "name": "db-update",
  "description": "系统数据写入唯一参考，含10张表Output Template",
  "location": "~/.claude/skills/db-update/SKILL.md",
  "status": "active"
}
```

**status 合法值**：`active` | `deprecated`
**禁止重复**：同名 skill 做 UPSERT，不新建

---

### 10. notes（所有文档类 — 5 种 Type）

**API**：`POST /api/brain/notes`
**Notion**：AI Notes DB

这是最重要的一张表，所有文档走这里，靠 Type 区分：

#### Type: PrepPRD（Sprint 启动前）
```json
{
  "title": "PrepPRD: 小红书绑定",
  "type": "PrepPRD",
  "content": "## Golden Path\n1. 用户打开绑定页...",
  "initiative_id": "sprint-task-uuid"
}
```

#### Type: Report（Sprint 完成后，逐点评价）
```json
{
  "title": "Report: 小红书绑定",
  "type": "Report",
  "content": "## Usage\n模型:sonnet-4-6 | 时长:2h34m | 成本:$3.20\n\n## DOD 结果\n✅ Test1 ✅ Test2 ❌ Test3(超时)\n\n## E2E 证明\n[screenshot-url-1] [screenshot-url-2]\n\n## DB 回填\njourney_steps ✅ api_registry ✅",
  "initiative_id": "sprint-task-uuid"
}
```

**Report 必须包含**：
- Usage 表（模型/时长/成本）
- DOD 每条结果（✅/❌）
- E2E 截图 URL（公网 HTTPS）
- DB 回填状态

#### Type: Learning（洞察 + 建议，任何人）
```json
{
  "title": "headless Chrome QR 扫码需 --disable-gpu",
  "type": "Learning",
  "content": "## 现象\nQR 码无法扫描\n## 洞察\n缺少 --disable-gpu flag\n## 建议\n所有 headless 配置统一加此 flag",
  "initiative_id": "sprint-task-uuid（可选）"
}
```

#### Type: Decision（正式决策）
```json
{
  "title": "所有 headless Chrome 统一加 --disable-gpu",
  "type": "Decision",
  "content": "## 决定\n...\n## 原因\n基于 Learning: headless Chrome QR 扫码问题\n## 影响范围\n所有使用 Chromium 的服务",
  "related_note_id": "learning-uuid（可选）"
}
```

#### Type: Contract（DOD 合同）
```json
{
  "title": "Contract: 小红书绑定",
  "type": "Contract",
  "content": "## DOD\n- [ ] ARTIFACT: ...\n- [ ] BEHAVIOR: ...",
  "initiative_id": "sprint-task-uuid"
}
```

---

## 禁止规则（写入前检查）

```bash
FORBIDDEN_NAMES=("KeysTest" "MyRun" "[Sprint]" "placeholder" "mock" "test-entry")
for name in "${FORBIDDEN_NAMES[@]}"; do
  if echo "$RECORD_NAME" | grep -qi "$name"; then
    echo "❌ 拒绝写入：禁止名称 '$name'"; exit 1
  fi
done
```

---

## 自动扫描表（不需要手动写）

| 表 | 写入方式 |
|----|---------|
| api_registry | 代码扫描自动填 |
| db_schema_registry | migrations 扫描自动填 |
| test_registry | 测试文件扫描自动填 |

---

## 与其他 skill 的关系

| Skill | 调用此 skill 的时机 |
|-------|-------------------|
| harness-report Phase B | Sprint 完成后统一回填所有表 |
| harness-planner | 写 journey_features（Sprint 规划时）|
| notion-issue | 写 issues（专用入口，遵循此 skill 规范）|
