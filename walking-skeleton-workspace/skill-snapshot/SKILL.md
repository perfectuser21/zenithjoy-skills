---
name: walking-skeleton
description: |
  Walking Skeleton 方法论 + Harness Pipeline 定义 + Notion 数据维护。任何 Area / repository 通用。
  核心职责：(1) 定义 Journey/Step/Feature/Phase 四层概念；(2) 维护 Brain DB 3张核心表（journeys/journey_steps/journey_features）；(3) Walking Skeleton 对话 → PrepPRD → 点火；(4) Harness Pipeline 标准定义（initiative level，multi-agent multi-session）。
  触发词：walking skeleton / 端到端 / journey / step / feature 多厚 / thin medium thick / 先跑通 / 加厚 / 跑 harness / 启动 sprint / 做 X 功能 / 智能发布 / 智能获客 / 我今天想做。
version: 2.1.0
created: 2026-05-06
updated: 2026-05-24
---

# Walking Skeleton — 用户路径定义、维护与 Harness 点火

**核心信念**：产品颗粒度永远是"用户路径（Journey）"，不是"feature 列表"。第一刀把整具骨架贯穿（每个 Step 都很薄但端到端通），然后用真实反馈驱动加厚。

---

## 本 skill 的职责

- ✅ Journey / Step / Feature / Phase 四层概念定义
- ✅ Walking Skeleton 多轮对话流程（PrepPRD 生成 + 人工确认）
- ✅ Brain DB 3 张表维护（journeys / journey_steps / journey_features）
- ✅ Notion AI Hub 数据同步（详见 `references/notion-schema.md`）
- ✅ Harness Pipeline 标准定义（initiative level）
- ✅ Sprint 点火（动作 5 `harness-bridge`，唯一正确入口）

---

## 第一部分：四层概念（必须读完才能用）

### 1.0 四层总览

```
Journey（路径）        — 端到端价值闭环，用户从冷启动到拿到价值
  └── Phase（阶段标签）— 概念分组，不进 DB，只是 Notion 分组标题
  └── Step（节点）     — 可追踪的用户能力单元，进 journey_steps 表
        └── Feature（脚本）— 一个可独立运行的自动化脚本，进 journey_features 表
```

### 1.1 Journey

- 完整价值闭环：用户从冷启动到拿到价值的端到端路径
- 能独立 demo，5-10 分钟讲清楚一个完整故事
- 整公司 10-15 条，每个 Area 1-4 条
- 例：智能发布 / 智能获客 / Cecelia 自驱动 / 管理员后台

### 1.2 Phase（阶段标签）— 不进 DB

- 帮你理解 Journey 结构的概念分组，**不是可追踪单元**
- 不存 `journey_steps` 表，只作为 Notion 视图里的分组标题
- 例：智能发布 Journey 里的"生成 / 发布 / 数据回取"
- **判断规则**：说"发布做完了吗？"但说不清楚具体指哪些 Step → 它是 Phase

### 1.3 Step（节点）— 进 journey_steps 表

**定义**：用户能独立感知到"这个能力我有了"的最小单元。

**判断测试**：能对客户说 **"我们现在支持 [Step名] 了"** 吗？
- "我们现在支持抖音发布了" ✅ → Step
- "我们现在支持视频格式了" ❌ → 太细，是 Feature
- "我们现在支持发布了" ❌ → 太粗，是 Phase

**粒度规则**：每条 Journey 5-20 个 Step。太少（< 5）→ 你定的是 Phase，需细化；太多（> 20）→ 你定的是 Feature，需合并。

**Step 可在多条 Journey 间共享**（注册/登录等基础节点）。

**例：智能发布 Journey 的 Steps**：
```
Step 1: 账号注册（共享）
Step 2: Agent 安装（共享）
Step 3: 抖音账号绑定
Step 4: 抖音内容发布      ← Phase"发布"下
Step 5: 小红书内容发布    ← Phase"发布"下
Step 6: 快手内容发布      ← Phase"发布"下
Step 7: 抖音智能生成      ← Phase"生成"下
Step 8: 抖音数据回取      ← Phase"数据回取"下
```

### 1.4 Feature（脚本）— 进 journey_features 表

**定义**：挂在某个 Step 上的**一个可独立运行的自动化脚本**。

- 1 Feature = 1 脚本 = 1 可执行的端到端自动化
- 有厚度：thin → medium → thick → mature（详见 `references/thickness-guide.md`）
- 多个 Feature 可挂在同一个 Step 上

**例：抖音内容发布 Step 下的 Features**：
```
抖音图文发布脚本   [thin]
抖音视频发布脚本   [thin]
抖音长文发布脚本   [planned]
```

**Feature 的三种来源**：

| 情况 | WS 对话怎么说 | Features 怎么处理 |
|------|------------|----------------|
| 已知脚本、未构建 | "有图文/视频/长文三个脚本" | 全部存 planned |
| 不知道有几个脚本 | "先跑通，不知道细节" | Run 过程中 GAN 发现，补录 |
| 脚本已在运行 | "已经有了，状态是 thin" | 存 done，填当前厚度 |

### 1.5 Step 的两个进化维度

**横向补全（广度）**：给同一个 Step 增加更多 Feature 脚本
```
Run 1 后：抖音发布 = [图文(thin)]
Run 2 后：抖音发布 = [图文(thin) + 视频(thin) + 长文(thin)]
```

**纵向加厚（深度）**：把已有 Feature 从 thin 升到 medium/thick
```
Run 3 后：抖音发布 = [图文(medium) + 视频(thin) + 长文(thin)]
```

两个维度独立演进，都算 Journey 推进。

### 1.6 Journey Type 4 类（Notion AI Journey DB 的字段）

| Type | 适用场景 | 例子 |
|---|---|---|
| `user_facing` | 终端客户用的 path | ZenithJoy「客户首次成功路径」 |
| `autonomous` | 系统自己跑、客户无感的 path | Cecelia Brain 自动决策→派任务→收结果 |
| `dev_pipeline` | 开发者用的 path | "commit → CI → 部署 → 客户用上"基建路径 |
| `agent_remote` | 远程 agent 跑的 path | 西安 Codex 自动测试生成 |

基建（CI/CD/部署）是 `dev_pipeline` 类型的**独立 Journey**，不混进 user_facing path。

> **Thin / Thickness / Maturity 详细标准** → 见 `references/thickness-guide.md`

---

## 第二部分：5 个动作

### 动作 1：`init journey` — 创建一条新 Journey

**触发**："建个 journey" / "做个 walking skeleton" / "定义一个新的用户路径"

**多轮对话收集**（能从上下文推断的自动填，不打断用户）：
1. Journey 名字（口语化，如"客户首次成功路径"）
2. 属于哪个 Area（ZenithJoy / Cecelia 等）
3. Journey Type（user_facing / autonomous / dev_pipeline / agent_remote）
4. 简短描述（1-3 句话讲清楚用户从哪到哪）
5. 端到端步骤（5-10 步，每步用户视角一句话）
6. E2E Test Path（smoke 文件路径，如 `.github/workflows/scripts/smoke/golden-path-1-smoke.sh`）

```bash
node ~/.claude/skills/walking-skeleton/scripts/init-journey.js \
  --name "客户首次成功路径" \
  --area "ZenithJoy" \
  --type "user_facing" \
  --description "客户从注册到第一条内容发布成功" \
  --e2e-path ".github/workflows/scripts/smoke/golden-path-1-smoke.sh" \
  --steps "注册|画像|绑平台|AI生成|发布|看回执"
```

输出：Notion 页面 URL + Journey ID（后续 add-feature 用）。

### 动作 2：`add feature <journey>` — 挂一个 Feature

**触发**："挂个 feature 到 X journey" / "在 Y 这步加个 feature"

**执行前必须查重**：拉取该 Journey 的现有 features，展示列表确认「新的 vs 已有 step 的更新」。**语义相近的 Step 名必须问用户确认**，不允许直接新建（见 5.4 语义查重规则）。已有 step 用 PATCH，不用 POST。

**关键**：本动作**只允许创建 thin** 默认值。

```bash
node ~/.claude/skills/walking-skeleton/scripts/add-feature.js \
  --name "Dashboard Agent 下载页" \
  --journey-id "<journey-page-id>" \
  --thickness "thin" \
  --area "ZenithJoy" \
  --unit-test-path "apps/dashboard/src/pages/__tests__/AgentDownload.test.tsx"
```

### 动作 3：`thicken <feature>` — 升级 Feature thickness

**触发**："这个 feature 升 medium" / "X feature 加厚到 thick"

**强制纪律 — 减肥后增肌**（避免 AI 只加不删导致代码累积矛盾）：

加厚 = 先删旧再写新，两段式 commit：
1. `remove old <thickness> implementation: <具体内容>` — 减肥
2. `implement <new-thickness> for <feature>` — 增肌

`replaces_old_thin` 必填，列出要删除的旧实现（mock / hardcode / stub 的具体路径/函数名）。脚本拒绝空值。

**升级校验**：
- thin → medium：证明"真实数据替代 mock"+"有基本错误处理"
- medium → thick：证明"核心场景完整"+"UI 可面客户"
- thick → mature：证明"边界情况覆盖"+"监控告警就位"

**询问用户**：升级理由（必填）+ 要替换/删除的旧实现（必填，具体到文件路径）

```bash
node ~/.claude/skills/walking-skeleton/scripts/thicken.js \
  --feature-id "<feature-page-id>" \
  --to "medium" \
  --reason "已接入真实 Claude API，错误处理完整，10 个真实客户已用过 1 周无 P0 问题" \
  --replaces-old-thin "apps/api/src/mocks/mockGenerateContent.ts, apps/api/src/content/__hardcoded_prompts.ts"
```

### 动作 4：`status <area>` — 查询某 Area 下所有 Journey + Feature 状态

**触发**："看一下 X area 的进度" / "ZenithJoy 现在啥状态" / "哪些 feature 还在 thin"

```bash
node ~/.claude/skills/walking-skeleton/scripts/status.js --area "ZenithJoy"
```

输出格式：
```
=== ZenithJoy ===
[Journey] 客户首次成功路径 (skeleton, user_facing)
  thin: 4 个 | medium: 1 | thick: 0 | mature: 0
  - [thin] 画像表单 3 字段
  - [medium] 注册 + auto license
```

### 动作 5：`harness-bridge` — Sprint 点火（唯一正确的 sprint 启动入口）

**触发**："跑 harness" / "开始做这个 feature" / "启动 sprint" / "做 X 功能" / "我今天想做..."

**禁止**：直接调 `/harness-planner`（绕过调度层，违反 zero-human-gate 原则）。

---

#### Walking Skeleton 对话（多轮，点火前必须走完）

这是多轮对话，不是一问到底。用户描述意图后，根据上下文**主动推断**目标 repo、Area、Journey 归属，推断不出的才问。

**第一步：查现有状态**
```bash
curl -s "localhost:5221/api/brain/journeys"
curl -s "localhost:5221/api/brain/journey_steps?journey_id=<id>"
curl -s "localhost:5221/api/brain/journey_features?journey_id=<id>&limit=50"
```

**第二步：语义对齐**

用户提到任何 Step 名词，**先查 `journey_steps` 做语义比对**：
- 名字完全一样 → 直接用，不新建
- 名字不同但语义相近 → **必须问用户**："你说的是不是已有 Step [name]（ID: xxx）？"
  - 用户确认 = 沿用该 Step，不新建
  - 用户说"不是" = 才允许新建
- 完全没有语义重叠 → 直接新建

**禁止**：跳过语义比对直接新建，导致同一件事存了两条记录。

**第三步：生成 PrepPRD（产品语言，存入 Notion AI Notes）**

PrepPRD 是 Walking Skeleton 对话的最终产出物。用产品语言，不出现 DB/表/WS/step_id 等技术词：

```markdown
# PrepPRD：[Journey 名] — [本次目标一句话]

## Journey 当前状态
- ✅ [Step 名] — [thin/medium/done]
- 🔄 [Step 名] — [进行中，已有X个脚本，还差Y个]
- ⬜ [Step 名] — [planned]

## 本次要做的
[用用户语言描述：谁能做什么，从哪到哪]

## 完成后用户能
[用一两句话描述用户可感知的变化]

## 涉及的脚本（Feature）
- [脚本名]（新增 / 加厚 thin→medium）

## 不包含
- [本次不做的事，防止范围蔓延]

## 用户确认的成功标准
- [可以验证的条件，用户语言]
```

**这是唯一的人工确认点。** 用户说"对" → 存 Notion → 点火。用户有疑问 → 继续对话修改 PrepPRD。

```bash
curl -X POST "localhost:5221/api/brain/notes" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"PrepPRD：[Journey]-[目标]\", \"type\": \"Notes\", \"body\": \"[PrepPRD内容]\"}"
```

---

#### 文件链条（Walking Skeleton 到交付）

```
Walking Skeleton 对话（多轮）
  → PrepPRD（用户语言，存 Notion AI Notes）← 唯一人工确认点
  → PRD（Planner 生成，结构化 What，存 sprint_dir）
  → Contract（GAN 生成，DoD + 具体行为，存 sprint_dir）
  → Workstreams（执行，每个 = 1 PR）
  → Final E2E → Report
```

---

#### 点火参数（用户确认 PrepPRD 后填写，能推断的自动填）

| 参数 | 来源 | 说明 |
|------|------|------|
| `feature_name` | 对话中 | 一句话，动词开头 |
| `thin_prd` | PrepPRD | 一句话 What，不写 How |
| `target_repo` | **上下文推断** | ZenithJoy 话题 → zenithjoy 路径；Cecelia 话题 → cecelia 路径；推断不出才问 |
| `sprint_dir` | 建议命名 | `sprints/<area-prefix><N>-<kebab-feature>` |

```bash
# 1. 在 Notion 注册 Feature（如还没有）
node ~/.claude/skills/walking-skeleton/scripts/add-feature.js \
  --name "<feature_name>" \
  --journey-id "<notion_journey_id>" \
  --thickness "thin" \
  --area "<area>"

# 2. 创建 Brain harness_initiative 任务（点火）
curl -s -X POST localhost:5221/api/brain/tasks \
  -H "Content-Type: application/json" \
  -d "{
    \"task_type\": \"harness_initiative\",
    \"title\": \"<feature_name>\",
    \"description\": \"<thin_prd>\",
    \"priority\": \"P1\",
    \"payload\": {
      \"sprint_dir\": \"<sprint_dir>\",
      \"thin_prd\": \"<thin_prd>\",
      \"journey_id\": \"<notion_journey_id>\",
      \"feature_id\": \"<notion_feature_id>\",
      \"base_repo\": \"<repo_path_if_not_cecelia>\"
    }
  }"
```

Brain tick 自动 pick up，无需人工干预。可用 `curl localhost:5221/api/brain/tasks/<task_id>` 查进度。

---

## 第三部分：6 条铁律

1. **任何"加 feature"的诉求都必须先回答"挂哪条 Journey"** — 不允许无主 feature
2. **新 Feature 默认 thin** — 不要让用户跳级建 medium/thick
3. **Maturity 不允许跳级** — `skeleton` 没到不能升 `mvp`
4. **Journey 第一刀只贯穿不加厚** — N 步 path 第一刀必须 N 个 thin feature 全在
5. **加厚要靠真实反馈** — 没人用的 feature 永远 thin 也 OK
6. **加厚必须先减肥再增肌** — thicken 前必填 `replaces_old_thin`，两段式 commit，杜绝 mock/hardcode 跟新实现并存

> **Thin/Thickness/Maturity 禁止妥协方案、升级硬指标** → 见 `references/thickness-guide.md`
> **Lead 客户机自验铁律** → 见 `references/lead-self-acceptance.md`

---

## 第四部分：Harness Pipeline 定义（Initiative Level）

### 4.1 什么是 Harness Pipeline

Harness Pipeline = **initiative level** 的多 Agent、多 Session 执行单元。不是单次 /dev，是跨 session 的协调机器。

```
Journey（长期演进路径，如"智能发布"）
  └── Run N（一次 Harness Pipeline 完整执行）← initiative level
        └── Workstream 1..N（每个 = 1 /dev session = 1 PR）
```

### 4.2 一个 Run 的固定结构（永不变）

```
点火（Sizing Check）
  → GAN（对抗审查 PRD）
  → Planner（拆 Workstreams）
  → Generator（并行/串行执行 2-5 个 WS）
  → Evaluator（逐 WS 验收）
  → Final E2E（跨 WS 集成验证）
  → Sync + Report（回写 Brain + 通知）
```

**核心规则：**
- `1 Workstream = 1 /dev session = 1 PR`（一个有边界的组件变更）
- `1 Run 目标 WS 数：2-5 个`（甜点区）
- `PRD 只写 What，不写 How`（Planner 负责把 What 拆成 WS How）

### 4.3 Sizing Check（点火阶段强制执行，不等跑完再打回）

Planner 读 PRD → 先估 WS 数 → 再决定是否执行：

| WS 预估数 | 处理方式 |
|-----------|---------|
| 1 个 | **降级**到 /dev，不启动 Harness（杀鸡用牛刀） |
| 2-5 个 | **正常执行**，这是 Harness 的甜点区 |
| 6 个以上 | **PRD 太大**，拆成两个 Run，分别执行 |

### 4.4 Planner 决策逻辑（读 3 张表）

Planner 只读：`journeys`（Maturity）+ `journey_steps`（已定义 Steps、顺序）+ `journey_features`（每个 Feature 厚度状态）

**决策规则：**
```
IF 骨架未通（有 Step 还没有 thin Feature）:
  → PRD = 补全缺失的 thin Features（优先横向贯穿）

ELSE IF 骨架已通（skeleton maturity）:
  → PRD = 选优先级最高的 Feature 升厚（thin → medium）

ELSE IF 需要横向扩展:
  → PRD = 新建下一个 Step 的 thin 骨架
```

**铁律：PRD 里的 Steps 必须来自 `journey_steps` 表，引用 step_id，禁止凭空创造新 Step 名称。**

### 4.5 正确 vs 错误案例

**✅ 正确 Run 定义（2-5 WS，有清晰 E2E 边界）：**
- `"抖音发布 thin"` — WS1: 注册+Agent安装，WS2: 本地连接，WS3: 点发布 → 3 WS ✅
- `"抖音发布 medium"` — WS1: 图文加厚，WS2: 视频加厚 → 2 WS ✅

**❌ 错误 Run 定义：**
- `"小红书图文发布"` — 只有 1 WS，用 /dev 就够 ❌
- `"全平台发布 thin"` — 8 平台 × 3 格式 = 24 WS，太大，必须拆成多个 Run ❌
- `"发布功能加个字段"` — 1 WS 级别的改动，直接 /dev ❌

### 4.6 Run 的验收标准

Run 完成 = 以下全部满足：

1. **Final E2E PASS** — 跨所有 WS 的集成验证通过
2. **所有 WS 的 PR merged** — N 个 PR 全部合入 main
3. **Brain journey_features 已更新** — thickness 状态已回写
4. **Notion 已同步** — harness-journey-state skill 执行完成

任何一条未满足 = Run 未完成，不能算作 Journey 推进。

---

## 启动凭据（执行任何 Notion 操作前）

所有脚本依赖 `~/.credentials/notion.env`。如果没有，先跑：

```bash
node -e "
const fs = require('fs');
const {execFileSync} = require('child_process');
const env = {};
fs.readFileSync(process.env.HOME + '/.credentials/1password.env', 'utf8')
  .split('\n').forEach(l => { const m = l.match(/^([^=]+)=(.+)/); if (m) env[m[1]]=m[2]; });
const token = execFileSync('op', ['item', 'get', 'Notion', '--vault', 'CS', '--fields', 'credential', '--reveal'],
  {env: {...process.env, ...env}}).toString().trim().replace(/^\"|\"$/g,'');
const note = execFileSync('op', ['item', 'get', 'Notion', '--vault', 'CS', '--fields', 'notesPlain', '--reveal'],
  {env: {...process.env, ...env}}).toString().trim().replace(/^\"|\"$/g,'');
const creds = 'NOTION_API_KEY=' + token + '\n' + note.split('\n').filter(l=>l.startsWith('NOTION_') && !l.startsWith('NOTION_API_KEY')).join('\n') + '\n';
fs.writeFileSync(process.env.HOME + '/.credentials/notion.env', creds, {mode: 0o600});
console.log('OK');
"
```

Notion DB ID 速查 → `references/notion-schema.md`
