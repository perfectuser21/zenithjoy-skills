---
name: dev
version: 20.1.0
updated: 2026-06-11
description: Phase1听懂意图→Phase2按路径按需查（路径A/B:3个curl，路径C:6个上下文源）→比对已有Steps展示Golden Path草稿→确认前置工作全部到位→用户确认PrepPRD→路由执行
trigger: /dev, --task-id <id>, 我想做, 有个 bug, 改一下, 出问题了, walking skeleton, harness, journey, feature
changelog:
  - 20.1.0: 链路审计修复 4 项 — (a) 路径 C payload target_environment 枚举补全为 6 种（mac_web|windows_cloud|windows_wechat|linux_server|local_api|playground）；(b) PrepPRD Golden Path 模板改为单线性步骤序列（Step 1→2→…，每步=用户动作+系统可观察响应），与 proposer 1:1 映射对齐，三段式作补充；(c) abilities 注释改准确（表已删但 endpoint 仍可用、后端映射 journey_features）；(d) 加 add-feature 脚本 vs Brain API 参数对照表
---

> **CRITICAL LANGUAGE RULE**: 所有输出简体中文。

---

## 第零步 Phase 1：听懂意图（不查表，纯解析）

**先听用户说了什么，不查任何 DB，直接判断类型：**

```
用户描述
  ├── 有 bug / 出问题了 / 不对 / 报错 / 崩了    → 【路径 A：Bug】
  ├── 改一下 / 小改动 / 加个字段 / 调一下配置   → 【路径 B：小改动】
  └── 想做 X / 新功能 / 立项 / 做一个 / 贯穿    → 【路径 C：大功能/Harness】
```

**模糊时（无法区分路径）：只问 1 个问题，不多问。**
- 示例："这是一个已有功能出问题，还是你想新增一个功能？"

判断完成后，立即进入 Phase 2。

---

## 第零步 Phase 2：按路径按需查上下文

### 路径 A（Bug）— 3 个 curl

```bash
curl -s "localhost:5221/api/brain/journeys"
curl -s "localhost:5221/api/brain/issues?limit=20"
curl -s -X POST "localhost:5221/api/brain/decisions/match" \
  -H "Content-Type: application/json" -d "{\"prd\": \"<用户描述关键词>\"}"
```

### 路径 B（小改动）— 3 个 curl

```bash
curl -s "localhost:5221/api/brain/journeys"
curl -s -X POST "localhost:5221/api/brain/decisions/match" \
  -H "Content-Type: application/json" -d "{\"prd\": \"<用户描述关键词>\"}"
curl -s "localhost:5221/api/brain/tasks?status=in_progress&limit=20"
```

### 路径 C（大功能）— 5 个上下文源

```bash
# 1: Journey 体系（journey_features 是唯一正表）
# abilities 表已删（2026-06-09）；/api/brain/abilities endpoint 仍可用、后端已映射到 journey_features
# 查询 Ability/Feature 推荐直接用 journey_features（语义最清晰）；abilities endpoint 是兼容别名
curl -s "localhost:5221/api/brain/journeys"
curl -s "localhost:5221/api/brain/journey_features?limit=50"

# 2: 进行中任务
curl -s "localhost:5221/api/brain/tasks?status=in_progress&limit=20"

# 3: Harness 历史 Run
curl -s "localhost:5221/api/brain/harness/runs?limit=20"

# 4: 历史决策匹配
curl -s -X POST "localhost:5221/api/brain/decisions/match" \
  -H "Content-Type: application/json" -d "{\"prd\": \"<用户描述关键词>\"}"
```

> 路径 C 不查 api_registry / db_schema_registry / test_registry / issues / skills / OKR（已移到 Proposer 阶段）。

---

## PrepPRD（三种格式，用户说"对"/"走"后才执行）

**PrepPRD 是唯一的人工确认点。**

### ⚠️ 步骤 0（大功能前必做）：比对已有 Abilities，展示 Golden Path 草稿

在生成 PrepPRD 之前，必须完成这一步（基于路径 C 已查的 5 个源）：

1. **确定本次 Journey**：从 `journeys` 结果里找用户描述对应的那条 Journey（语义匹配）。

2. **过滤已有 Abilities**：在 `journey_features` 结果里，过滤属于该 Journey 且 `status = working/done` 的能力，列出"已完成"清单。

3. **从用户描述提炼本次需要的 Ability/Feature**：结合用户意图，从 `journey_features` 结果里找出本次需要新建或推进的项。

4. **提炼 Golden Path**，补全用户没说出口的隐含步骤，格式：

   ```
   已有（✅ 不动）：
   - ✅ [Ability/Feature 名] — [当前状态]

   本次新增/推进（➕ 本 sprint 范围）：
   - ➕ [Ability/Feature 名] — [计划厚度/目标]

   建议 Golden Path（用户视角，不写系统组件，单线性步骤序列）：
   Step 1: [谁] [做了什么操作] → 系统 [可观察响应] → [下一状态]
   Step 2: [下一步操作] → 系统 [可观察响应] → [下一状态]
   Step 3: ...（到出口）
   （可选补充：首次/日常差异、出错恢复——出错场景至少一条 [用户如何知道出错] → [用户如何恢复]）
   ```

   提炼规则：
   - 写"用户操作"，不写"系统组件"（❌ "建 check-health.js" ✅ "用户点'抖音登录'"）
   - 必须覆盖异常场景：掉线了 → 用户怎么知道 → 用户怎么恢复

5. **用户说"对"/"走"/"可以"后**，立即进入步骤 1（前置工作核对）。

---

### ⚠️ 步骤 1（大功能必做）：核对前置工作

**Golden Path 确认后、PrepPRD 写作前，必须完成此步。这是硬门槛。**

从 Golden Path 推断本次 sprint 需要哪些外部依赖，逐条核对：

| 前置类型 | 检查方式 | 未到位怎么办 |
|---|---|---|
| API Key / 凭据 | `source ~/.credentials/<service>.env` 能读到变量，或确认 GHA Secrets 名称已配 | 停下来问用户要 |
| 用户本地脚本 | 路径存在且文件非空（`ls -la <path>`）| 让用户提供路径或上传到 repo |
| 测试 fixture（视频/图片/数据）| 文件存在且大小合理（`ls -lh <path>`）| 让用户提供，或用 ffmpeg 合成最小合法素材 |
| 外部服务接入 | API 端点、鉴权方式、示例 curl 已知 | 问用户要文档 |

**全部 ✅ 才继续写 PrepPRD。有任何一项 ❌ → 停下来明确告诉用户缺什么，拿到后再继续。**

> 唯一例外：用户主动说"只要 thin 骨架、不验真实行为" → 可继续，但 PrepPRD 验收标准里**禁止写** ffprobe / 真实 API 输出 / 真实文件等无法达到的条件，只能写 API schema / 服务启动 / 路由响应。

---

### Bug PrepPRD

```markdown
# Bug PrepPRD：[问题描述一句话]

## 症状
[用户看到了什么]

## 根因假设
[基于上下文 + 代码推断]

## 关联上下文
- 相关 Journey/Ability：[如有]
- 相关 Issue：[Issue ID，如有]
- 相关历史决策：[decisions 里有没有相关记录]

## 修法
[具体改哪个文件，改什么逻辑]

## Regression Test 计划
[一个能复现 bug 的 failing test，修完永久留 CI]

## 验收标准
- [ ] failing test 先 commit（commit-1）
- [ ] 修复代码让 test 变绿（commit-2）
- [ ] CI 全绿
```

### 小改动 PrepPRD

```markdown
# 小改动 PrepPRD：[改动描述一句话]

## 改什么
[具体改哪个文件/字段/逻辑]

## 为什么改
[业务或技术原因]

## 关联上下文
- 相关 Journey/Ability：[如有]
- 相关历史决策：[decisions 里有没有相关记录]

## 影响范围
[会不会影响其他地方]

## 验收标准
- [ ] [可验证的条件]
- [ ] CI 全绿
```

### 大功能 PrepPRD（Harness）

> ⛔ 写之前必须完成步骤 1（前置工作核对），禁止在"前置工作"栏保留任何未确认的 `[ ]` 空白项。

```markdown
# PrepPRD：[Journey 名] — [本次目标一句话]

## 本次对话涵盖的所有事项（防信息丢失）
- [x] 本 PrepPRD 包含：[列出本次做的事]
- [ ] 另立 Sprint（本次不做）：[列出聊过但本次跳过的事]
- [ ] 待讨论：[列出还不确定的事]

## Journey 当前状态
- ✅ [Ability/Feature 名] — [thin/medium/done]
- 🔄 [Ability/Feature 名] — [进行中]
- ⬜ [Ability/Feature 名] — [planned]

## 本次要做的
[用用户语言描述]

## Golden Path（用户操作流程，单线性步骤序列，逐步不跳过）

> 这是唯一决定"做什么"的锚点。合同、E2E 全部从这里派生。
> **主体是单线性步骤序列**（Step 1→2→3→…），每步 = `用户动作 + 系统可观察响应`，与 proposer 的 [BEHAVIOR] 1:1 映射对齐（一步 = 一条 [BEHAVIOR]）。

1. [谁] [做了什么操作] → 系统 [可观察响应] → [下一状态]
2. [谁] [下一步操作] → 系统 [可观察响应] → [下一状态]
3. ...（一直到出口：用户拿到最终可感知的结果）

> **补充场景（可选，不替代主线）**：若功能有明显的"首次使用 / 日常使用 / 出错恢复"差异，可在主线之后补三段式说明，但**主体必须是上面的单线性序列**。出错/掉线场景至少覆盖一条：[用户如何发现问题] → [用户做什么] → 系统 [恢复动作]。

## 客户视角（用户打开产品能感知到什么）
[不写技术细节，只写客户会看到/感受到的变化]

## 完成后用户能
[用户可感知的变化，列举 1-3 条]

## 涉及的 Ability / Feature
- [名称]（新增 / 加厚 thin→medium）

## 不包含
- [本次不做的事]

## 前置工作（已逐项确认，无 TBD）

### 账号与登录
- [x] [平台/账号] — [已登录 / 凭据在 ~/.credentials/xxx.env]

### API 与凭据
- [x] [API key 名] — [已在 ~/.credentials/xxx.env / GHA Secret: XXX_KEY]

### E2E 测试账号
- [x] 测试账号邮箱：[email]
- [x] 登录方式：[邮箱密码 / 扫码 / 其他]

### 测试 Fixture
- [x] [素材名] — [路径 / 已在 repo / ffmpeg 合成方法]

### 基础设施
- [x] [服务/端口] — [已就绪 / 启动命令]

## 验收标准（Final E2E）
- [ ] [可验证的条件，如：ffprobe 验证输出视频有视频流+音频流+时长>0]
- [ ] CI 全绿
```

---

## PrepPRD 落地：确认后写文件

用户确认 PrepPRD（说"对"/"走"/"可以"）后，**在写 decision 之前**，先生成落地文件：

1. 根据功能名生成 `sprint_dir`，格式：`sprints/MMDDHHNN-功能名slug`（MMDDHHNN 取当前上海时间）
2. 创建目录并写入 PrepPRD：
   ```bash
   SPRINT_DIR="sprints/$(TZ=Asia/Shanghai date +%m%d%H%M)-<功能名slug>"
   mkdir -p "$SPRINT_DIR"
   cat > "$SPRINT_DIR/prep-prd.md" << 'EOF'
   <PrepPRD全文>
   EOF
   ```
3. 输出确认：`已保存 PrepPRD 到 $SPRINT_DIR/prep-prd.md`

路径 C 点火时，`sprint_dir` 写入 Brain task payload（见下方路径 C 执行部分）。

---

## 三条执行路径

### 路径 A：Bug

PrepPRD 落地后，**立即执行**这条 bash 命令写 decision：

```bash
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d "{\"topic\":\"<bug 根因简述>\",\"decision\":\"[修法摘要]\",\"reason\":\"[根因]\",\"made_by\":\"user\",\"author\":\"user\",\"category\":\"bug-fix\"}"
```

> **必填字段**：`decision`、`reason`、`made_by="user"`、`category="bug-fix"`（Brain API 只认 `category`，写 `type` 会被忽略）。Brain API 不可用时跳过。

然后 **下一 tool call 必须是**：
```
Skill({"skill":"superpowers:systematic-debugging"})
```

systematic-debugging → engine-worktree → Superpowers autonomous 接力链 → fix PR → engine-ship → engine-pr-watchdog

---

### 路径 B：小改动

PrepPRD 落地后，**立即执行**这条 bash 命令写 decision：

```bash
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d "{\"topic\":\"<改动方向简述>\",\"decision\":\"[改动摘要]\",\"reason\":\"[原因]\",\"made_by\":\"user\",\"author\":\"user\",\"category\":\"small-change\"}"
```

> **必填字段**：`decision`、`reason`、`made_by="user"`、`category="small-change"`。Brain API 不可用时跳过。

然后 **下一 tool call 必须是**：
```
Skill({"skill":"engine-worktree"})
```

Superpowers autonomous 接力链：
brainstorming → writing-plans → subagent-driven-development → finishing（Option 2 push+PR）→ engine-ship → engine-pr-watchdog

**Autonomous 规则（必遵守）：**

绝不停下问用户，所有交互点 → Research Subagent 代答。

Tier 1 固定默认：
- brainstorming design approval → Research Subagent APPROVE（除非发现硬阻碍）
- brainstorming clarifying question → Research Subagent 查代码 + `curl localhost:5221/api/brain/decisions/match` (payload `{"prd":"<关键词>"}`) + `docs/learnings/` 回答
- brainstorming spec 必须含「测试策略」段（E2E / integration / unit / trivial 四档，缺则 reject）
- writing-plans → subagent-driven
- subagent prompt 必须 inline TDD iron law：
  - "NO PRODUCTION CODE WITHOUT FAILING TEST FIRST"
  - "每 plan task commit 顺序：commit-1 fail test / commit-2 impl"
- finishing → Option 2 (push+PR)
- finishing 完成 → 下一 tool call 必须 `Skill({"skill":"engine-ship"})` → engine-ship 完成 → 下一 tool call 必须 `Skill({"skill":"engine-pr-watchdog"})`
- BLOCKED 第 3 次 → `superpowers:dispatching-parallel-agents`

**smoke.sh 强制（feat: 类 PR）：**
- ZenithJoy：必须有 `.github/workflows/scripts/smoke/<feature>-smoke.sh`
- CI smoke job 必须通过才能 merge

---

### 路径 C：大功能（Harness）

PrepPRD 落地后，**立即执行**这条 bash 命令写 decision：

```bash
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d "{\"topic\":\"<功能方向简述>\",\"decision\":\"[功能方向摘要]\",\"reason\":\"[为什么做]\",\"made_by\":\"user\",\"author\":\"user\",\"category\":\"feature\"}"
```

> **必填字段**：`decision`、`reason`、`made_by="user"`、`category="feature"`。Brain API 不可用时跳过。

在 Notion 注册 Ability/Feature（如还没有）：
```bash
node ~/.claude/skills/dev/scripts/add-feature.js \
  --name "<feature_name>" --journey-id "<notion_journey_id>" \
  --thickness "thin" --area "<area>"
# 若脚本不存在，直接调 Brain API：
# curl -s -X POST localhost:5221/api/brain/journey_features -H "Content-Type: application/json" \
#   -d '{"name":"<name>","journey_id":"<id>","kind":"ability","area":"ZenithJoy"}'
```

**两种方式参数对照（推荐脚本，自带语义查重 + 默认值）**：

| 概念 | add-feature.js 参数 | Brain API 字段 | 说明 |
|---|---|---|---|
| 名称 | `--name "<feature_name>"` | `name` | 必填 |
| 所属 Journey | `--journey-id "<id>"` | `journey_id` | 必填 |
| 厚度 | `--thickness "thin"` | （无对应字段，写 `thickness`）| 脚本默认 thin |
| 类型 | （脚本默认 ability）| `kind: "ability" \| "feature"` | API 必须显式写 kind |
| 所属 Area | `--area "<area>"` | `area` | 如 ZenithJoy |

> **推荐用 `add-feature.js`**：执行前自动语义查重（避免重复建 Ability）、默认 thin、默认 kind=ability，少踩坑。只有脚本不可用时才回退裸 Brain API（此时必须手动带 `kind`）。

点火：
```bash
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
      \"prep_prd_body\": \"<PrepPRD全文Markdown>\",
      \"journey_id\": \"<notion_journey_id>\",
      \"feature_id\": \"<notion_feature_id>\",
      \"base_repo\": \"<见下方规则>\",
      \"target_environment\": \"<mac_web|windows_cloud|windows_wechat|linux_server|local_api|playground>\"
    }
  }"
```

> **target_environment 枚举（6 种，与 planner/proposer/evaluator 全链一致）**：`mac_web`（Cecelia Dashboard，本机 Playwright）/ `windows_cloud`（GHA windows-latest）/ `windows_wechat`（xian-rog self-hosted 真机微信）/ `linux_server`（SSH hk-vps/us-vps）/ `local_api`（本地 Brain curl+psql）/ `playground`（playground 训练 sprint）。

**`base_repo` 规则：**

| target_environment | base_repo 格式 |
|---|---|
| `windows_cloud` / `windows_wechat` / `mac_web` | **必须 GitHub URL**（Actions runner / 远端真机访问不到本地路径）|
| `linux_server` | **必须 GitHub URL**（远端机器 SSH 后 clone）|
| `local_api` / `playground` | 本地路径或 GitHub URL 均可 |

> ❌ 错误：`windows_cloud` + `base_repo=/Users/administrator/...` → Harness 入队失败
> ✅ 正确：`windows_cloud` + `base_repo=https://github.com/perfectuser21/zenithjoy-workspace.git`

Brain tick 自动 pick up，`curl localhost:5221/api/brain/tasks/<task_id>` 查进度。

---

## Walking Skeleton 概念（路径 C 参考）

### 层级结构

```
Journey — 端到端价值闭环
  └── Phase — 阶段（发布/生成/剪辑），客户视角的流程分组
        └── Ability — 客户价值 workflow（journey_features 表 kind=ability）
              · Feature — 使能件（登录/下载/cookie/保活，journey_features 表 kind=feature）
Golden Path — 横切：Ability+Feature 的有序组合（golden_path 表，按 scope 筛 + 按 order 排）
```

- **Ability** = 客户为之而来的价值 workflow（发抖音视频）；判据：会不会写进客户交付清单
- **Feature** = 使能件，客户不为它来（登录/下载/cookie/保活）
- **Golden Path** = 客户真实流程 = Ability+Feature 有序组合

Ability 判断：能对客户说"我们现在支持 [Ability名] 了"吗？
- "我们支持抖音发布了" ✅ → Ability
- "我们支持视频格式了" ❌ → 太细，是 Feature
- "我们支持发布了" ❌ → 太粗，是 Phase

### Journey Type

| Type | 场景 |
|---|---|
| `user_facing` | 终端客户用的路径 |
| `autonomous` | 系统自己跑、客户无感 |
| `dev_pipeline` | CI/CD/部署等开发者路径 |
| `agent_remote` | 远程 agent 跑的路径 |

### Feature 厚度

thin → medium → thick → mature

**加厚纪律 — 先减肥再增肌（两段式 commit）：**
1. `remove old <thickness> implementation`
2. `implement <new-thickness>`

升级标准：
- thin → medium：真实数据替代 mock + 基本错误处理
- medium → thick：核心场景完整 + UI 可面客户
- thick → mature：边界覆盖 + 监控告警就位

### 5 个管理动作

```bash
# init journey
node ~/.claude/skills/dev/scripts/init-journey.js \
  --name "客户首次成功路径" --area "ZenithJoy" --type "user_facing" \
  --description "..." --e2e-path "..." --steps "注册|画像|发布"

# add ability/feature（默认 thin，执行前语义查重）
node ~/.claude/skills/dev/scripts/add-feature.js \
  --name "<feature_name>" --journey-id "<id>" --thickness "thin" --area "<area>"

# thicken（必填 replaces_old_thin）
node ~/.claude/skills/dev/scripts/thicken.js \
  --feature-id "<id>" --to "medium" --reason "..." \
  --replaces-old-thin "path/to/old/mock.ts"

# status
node ~/.claude/skills/dev/scripts/status.js --area "ZenithJoy"
```

### 6 条铁律

1. 任何"加 ability/feature"必须先回答"挂哪条 Journey"
2. 新 Ability/Feature 默认 thin，不允许跳级
3. Maturity 不允许跳级（skeleton 没到不能升 mvp）
4. Journey 第一刀只贯穿不加厚
5. 加厚要靠真实反馈
6. 加厚必须先减肥再增肌

---

## Harness Pipeline 定义

### Run 固定结构

```
点火 → Planner（PRD）→ GAN（合同）→ Generator（1 WS）→ Evaluator（pre-merge 验证）→ Report
```

- 1 Sprint = 1 Generator = 1 PR（无 WS 拆分概念）
- Planner 只写 PRD（What），不拆任务
- GAN 结束后 Proposer 输出 task-plan.json（始终只有 ws1 一个任务）

### 多角色检测

发现"客户端 + 管理端"混合 → 提示拆成两条 Journey。

### 语义查重

用户提到 Ability 名 → 先查 journey_features catalog（`GET /api/brain/journey_features`），语义相近必须复用引用，不直接新建。

### Planner 决策逻辑

```
骨架未通 → 补全 thin Abilities（横向贯穿优先）
骨架已通 → 选优先级最高的 Ability 升厚
需横向扩展 → 新建下一个 Ability 的 thin 骨架
```

PRD 里的 Ability/Feature 必须来自 `journey_features` 表，引用 `feature_id`，禁止凭空创造。

### Run 验收标准

1. Final E2E PASS
2. 该 Sprint 对应的唯一 PR 已 merged
3. Brain `journey_features` 表 thickness 已回写
4. Notion 已同步

---

## Notion DB ID 速查

| 表 | Notion DB ID |
|---|---|
| AI Journey | `358c40c2-ba63-8148-bde7-e313d789931a` |
| AI Steps | `369c40c2-ba63-812c-9f35-e7e43db25014` |
| Journey-Step 连接表 | `369c40c2-ba63-81e2-b95a-e5e3d0592676` |
| AI Feature | `358c40c2-ba63-81e3-96c5-d762b3d34dff` |
| Skill Registry | `353c40c2-ba63-81bf-ae3e-f0e6fa3753d7` |
| API Registry | `365c40c2-ba63-81a3-9060-fcef565e5291` |
| DB Schema Registry | `365c40c2-ba63-8181-9a57-ed760fd68ba3` |
| Tests Registry | `365c40c2-ba63-8164-8037-eb72e713809e` |
| Issues | `a17c40c2-ba63-82fb-9888-8152cefe29ec` |
| AI Notes（Decision）| `185c40c2-ba63-828c-973f-81a9c4582cd6`（Type=Decision）|
| Goals（Objectives）| `29ec40c2-ba63-8301-99c1-8110bfd84d9b` |
| Key Results | `684c40c2-ba63-83a7-b6ba-8161f110a18c` |

凭据：`source ~/.credentials/1password.env && export OP_SERVICE_ACCOUNT_TOKEN && NOTION_KEY=$(op item get "Notion" --vault CS --fields credential --reveal | tr -d '"')`
