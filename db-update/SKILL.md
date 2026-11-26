---
name: db-update
description: |
  系统数据写入唯一参考。写任何一张常用表之前，必须先查这个 skill。
  六层结构按 tree 现行真表核实；提供任务、决策、记录等 Brain API 写入规范。
  Notion 投影由 Brain 正常每5分钟分批自动推送；不是5分钟完成全量，完成以目标页面读回为准。
  触发场景：写 Journey / Step / Feature / Sprint / 任何 Note 类型 / Issue / Learning / Decision 时。
version: 1.2.1
created: 2026-06-01
updated: 2026-10-15
changelog:
  - "1.2.1: 明确Brain真身与Notion知识/内容例外；移除退役harness建单与直接写库指引。"
  - "1.2.0: 删除旧五层及 journeys/golden_path/journey_features 作为现行树的写入示例；六层表与接口先实查，兼容名不作层级依据。"
  - 1.1.0: decisions 写入 judgment category 约定（decisions 27b57469/e035dad8）— 新增「判定点相关决策写法」段：判定点被纠正时经 ❌→Invariant Gate 写 category=invariant；新发现判定假设写 category=judgment；action_receipts 写法示例（migration 315 新表）
---

> **边界：任务、决定、运行和业务树以 Brain 为真身，写入走 Brain API；Notion 投影由 Brain 同步。知识与内容以 Notion 为真身，按 notion skill 写对应库；凭据只进 1Password。禁止直改投影或直接 SQL 写业务表。**

# /db-update — 系统数据写入规范

---

## 架构

```
以 Brain 为真身的数据写入
    ↓
POST localhost:5221/api/brain/<table>   ← 唯一入口
    ↓
Brain DB（notion_synced_at = NULL）
    ↓ 自动（每5分钟）
Notion（展示层，只读）
```

---

## 六层结构写入前先核实（现行口径）

涉及部门、价值流、能力、流程、Activity、Step 时，先读 `../tree/SKILL.md` 与其
`references/doctrine.md`，装载目标环境的实体表及父子关系。结构判定只认 tree，不沿用旧五层。

| 层级 | 实体表 | 归属字段 |
|---|---|---|
| Department | areas | parent_area_id → 上级组织 |
| Value Stream | value_streams | area_id → areas.id |
| Capability | capabilities | parent_journey_id → value_streams.id |
| Workflow | workflows | capability_id → capabilities.id |
| Activity | activities | workflow_activity_refs.workflow_id / activity_id / sequence_no |
| Step | steps | activity_id → activities.id |

2026-10-15 已直接核验 us-vps 的生产 `cecelia`：以上为实体表，`journeys` 为
`value_streams UNION ALL capabilities` 的兼容视图。字段名 `parent_journey_id` 保留旧名，
外键实际指向 `value_streams`，不能仅凭字段名推断仍用旧模型。

每次操作先核实运行进程的环境与连接目标，再在只读事务中查询 `current_database()`、
`pg_class.relkind`、实际外键；本机端口号、健康版本和本地 migration 不能单独证明库的身份或现状。
本次核验的本机 5221 是 socat 转发到 us-vps，不是本机 staging。其他会话仍需重新核实。

`/api/brain/journeys`、`/api/brain/value-streams` 当前可能通过兼容实现混回两种 kind；
查全分页并按 `kind` 区分。`/api/brain/capabilities` 是旧登记接口，不能当六层能力源。
结构写入前须查运行服务的现行路由和字段校验，确认写入目标实体表；本文件不编造新 CRUD 端点。

旧 `journey_steps`、`journey_step_links`、`journey_features`、`golden_path` 的历史业务与提案用途
须单独核实，不作为当前六层结构的写入规范；旧五层示例已从执行入口移除。

## 通用任务与记录写入

### 5. initiative_contracts（Sprint 合同）

**API**：`POST /api/brain/notes`（Type: Contract）；旧 Sprint 合同模板只供历史对象维护，现役开发按 dev skill
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

建单后立即通过 `/tasks/:id/claim` 领取并管理状态。代码任务按 dev skill 的现行有头 /dev 流程登记并立即 claim；需要 Agent 编码时使用普通 codex_dev 派发。旧 coding_workflow / harness_initiative 自动编排入口已退役。

**API**：`POST /api/brain/tasks`

```json
{
  "title": "核对生产树与Notion目录",
  "task_type": "research",
  "priority": "P1",
  "payload": {
    "work_kind": "coding_review"
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

## 判定点相关决策写法（decisions 27b57469/e035dad8 — migration 315）

### decisions 表 — category=judgment（新发现判定假设）

当 Proposer 首次在合同里登记一个判定点（对模糊现实的判断假设），写入 decisions 表：

```bash
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "<判定点简述，如：微信群是否发送成功的判定方法>",
    "decision": "<所选方法及依据>",
    "reason": "<为什么选此方法而非候选方法>",
    "category": "judgment",
    "made_by": "cecelia",
    "author": "cecelia"
  }'
```

`category=judgment` 约定（decisions e035dad8）：用于标记系统自行选择的判定假设，供 Invariant Gate 追踪与 Alex 复盘纠正。

### decisions 表 — category=invariant（判定点被 Alex 纠正后）

当 Alex 纠正了某个判定方法（经 ❌→Invariant Gate 流程），写入 decisions 表固化为铁律：

```bash
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "<纠正后的判定方法>",
    "decision": "<正确判定方法>",
    "reason": "Alex 纠正：<旧方法> 误判后果=<后果>；改为 <新方法>",
    "category": "invariant",
    "made_by": "user",
    "author": "user"
  }'
```

`category=invariant` 表示此判定方法已升级为铁律，后续合同的判定点登记表必须引用。

### action_receipts 表 — 对外动作效果回执（migration 315 新表）

每个对外动作（发飞书/发 Bark/调 API/触发部署）完成后写回执，对应八要素的「效果确认」要素：

```bash
# 发送动作后立即写 pending
curl -s -X POST localhost:5221/api/brain/action-receipts \
  -H "Content-Type: application/json" \
  -d '{
    "action_id": "<唯一动作 ID，如 task_id+动作类型>",
    "kind": "<动作类型：bark_notify|feishu_msg|deploy_trigger|api_call>",
    "target": "<接收方：手机/飞书群/服务名>",
    "receipt_status": "pending"
  }'

# 确认生效后更新为 confirmed（或 failed/timeout）
curl -s -X PATCH localhost:5221/api/brain/action-receipts/<action_id> \
  -H "Content-Type: application/json" \
  -d '{
    "receipt_status": "confirmed",
    "evidence": {"screenshot": "...", "response_code": 200}
  }'
```

**receipt_status 合法值**：`pending` | `confirmed` | `failed` | `timeout`（已发送≠已生效，必须等待回执）

---

## 与其他 skill 的关系

| Skill | 调用此 skill 的时机 |
|-------|-------------------|
| harness-report Phase B | Sprint 完成后统一回填所有表 |
| harness-planner | 写 journey_features（Sprint 规划时）|
| notion-issue | 写 issues（专用入口，遵循此 skill 规范）|
