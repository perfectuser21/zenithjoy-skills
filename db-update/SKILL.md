---
name: db-update
description: |
  系统数据写入唯一参考。写任何一张常用表之前，必须先查这个 skill。
  含 Brain API 规范、研发材料与六去向路由；知识及内容直接维护Notion真身。
  Notion 同步是自动副作用（Brain tick 每5分钟 push），不需要手动操作。
  触发场景：写 Journey / Step / Feature / Sprint / 任何 Note 类型 / Issue / Learning / Decision 时。
version: 1.2.0
created: 2026-06-01
updated: 2026-10-14
changelog:
  - 1.2.0: 按六去向区分Brain任务/决定与Notion知识/内容真身；AI Notes不再承载正式决定或知识。
  - 1.1.0: decisions 写入 judgment category 约定（decisions 27b57469/e035dad8）— 新增「判定点相关决策写法」段：判定点被纠正时经 ❌→Invariant Gate 写 category=invariant；新发现判定假设写 category=judgment；action_receipts 写法示例（migration 315 新表）
---

> **核心原则：改真身，不改投影。任务、事件、决定和研发登记走 Brain；知识与内容的真身在 Notion。凭据只进1Password。**

# /db-update — 系统数据写入规范

---

## 六去向路由

| 产出 | 真身与写法 |
|---|---|
| 要干/干成的、意外事件 | Brain tasks；开工登记，完成回写事实、证据、actor与handoff；总结按session |
| 用户决定及理由 | `POST /api/brain/strategic-decisions`；字段用category，不写AI Notes或Notion决定投影 |
| 无时效知识 | Notion `Knowledge_Reference` / `Knowledge_Operational` / `Insights`，更新已有真身 |
| 给外人的内容 | Notion Ideas → Content_Seed → Content_Core → 发布编排台；程序发布后回写任务事件 |
| 台账、凭据 | 对应真身；凭据只从1Password读取，设备在线/电量/心跳仅镜子维护 |
| 每次生效规矩 | 执行现场skill/hook/AGENTS，带窄锚点；Rules花名册只是投影 |

Brain拥有的真身通过正式API写入，Notion由同步器投影；知识和内容按Notion技能直接写真身。AI Hub、Events、Ops、决定、Rules等投影禁止直写。

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

### 2. journey_steps（历史遗留 Step 表，已废弃只读）

> ⚠️ 已废弃（2026-06-09）：不再写入，历史数据只读。
> ⚠️ 命名澄清（能力轴新定义，decision 13013a49）：这张表旧称"Golden Path 步骤"与新五层定义撞车，勿再沿用该叫法。新定义里 L4「step」的载体是 `golden_path`(303) 表（见下文），不是这张遗留表；本表的历史 step 数据仅供只读回溯。

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

### 4. journey_features（Ability/Feature 唯一存储）

**journey_features 是当前实际在用的 Ability/Feature 载体。**（能力轴新定义，decision 13013a49）
- **Ability**（kind=ability）= 客户为之而来的价值 workflow（发抖音视频）= 新定义 L3「Golden Path = Ability = function」
- **Feature**（kind=feature）= 使能件（登录/下载/cookie/保活）= 新定义 L5，经 step 挂到 L4
- ⚠️ `abilities`(migration 294) 是**遗留死表**：从未 DROP、仍在库里，但已不写入，待归并/DROP。别再说它"已删"（那是假话），也别往它写。当前 Ability/Feature 一律写 journey_features。

**API**：`POST /api/brain/journey_features`
**Notion**：AI Feature DB

```json
{
  "journey_id": "uuid",
  "name": "抖音视频发布",
  "kind": "ability",
  "status": "done",
  "thickness": "thin",
  "workflow_ref": "douyin-publisher",
  "version": "1.0.0"
}
```

**kind 合法值**：`ability` | `feature`
**status 合法值**：`planned` | `building` | `done` | `deprecated`
**thickness 合法值**：`thin` | `medium` | `thick` | `mature`

**禁止写入**：
- 名称含 `[Sprint]`、`KeysTest`、`MyRun`（测试污染）
- `journey_id` 为空

---

### golden_path（Step 表 — 一条 Golden Path 的有序 step，migration 303）

**这是能力轴新定义里的 L4「step」表**（decision 13013a49），不是"FR 台账"、也不是"Ability+Feature 有序组合"那种第三义描述——那些旧叫法已废止。一条 **Golden Path = 一个 Ability = 一个 function**（L3，落 journey_features kind=ability）；这张 `golden_path`(303) 表存的是**这条 Golden Path 的有序 step**，每行一个 step，按 `owner_task_id` 归属到所属 ability、按 `order_no` 排序。每个 step 可经 `feature_id` 指向 L5 使能件。

**API**：`POST /api/brain/golden_path`

```json
{
  "owner_task_id": "uuid",
  "order_no": 1,
  "feature_id": "uuid",
  "note": "接收并理解客户消息"
}
```

字段：`owner_task_id`（step 所属 ability 的执行 task）| `order_no`（step 顺序）| `feature_id`（该 step 指向的 L5 使能件）| `note`（step 说明）

> step 上的 **NFR 决策**挂在 `decisions`（`category='nfr'`, `level='step'`, `target_type='golden_path'`, `target_id=<step id>`），不新建表。

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

### 10. notes（研发材料与历史类型）

**API**：`POST /api/brain/notes`
**Notion**：AI Notes DB

这里只保留研发材料与历史类型说明。正式决定写decisions，知识写Notion知识真身；任务交付与session总结回写tasks.result，不把AI Notes当全局内容入口。

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

#### 历史 Type: Learning（旧记录只读）

新的可复用洞察写Notion Insights，指回任务的运行事实与证据。以下仅供旧记录回溯。
```json
{
  "title": "headless Chrome QR 扫码需 --disable-gpu",
  "type": "Learning",
  "content": "## 现象\nQR 码无法扫描\n## 洞察\n缺少 --disable-gpu flag\n## 建议\n所有 headless 配置统一加此 flag",
  "initiative_id": "sprint-task-uuid（可选）"
}
```

#### 历史 Type: Decision（旧记录只读）

新的正式决定写 `POST /api/brain/strategic-decisions`，包含topic/decision/reason/author/category。不要新增notes.type=Decision，不直写Notion决定投影。

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
