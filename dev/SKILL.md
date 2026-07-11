---
name: dev
version: 21.8.0
updated: 2026-07-10
description: Phase0 --task-id立即claim防tick抢跑→Phase1听懂意图→Phase2按路径按需查（路径A/B:3个curl，路径C:6个上下文源）→Phase2.5 GitHub撞车检查→比对已有Steps展示Golden Path草稿→确认前置工作全部到位→用户确认PrepPRD→路由执行
trigger: /dev, --task-id <id>, 我想做, 有个 bug, 改一下, 出问题了, walking skeleton, harness, journey, feature
changelog:
  - 21.8.0: 判定点显性化进 /dev（九要素 T5 — decisions e035dad8）— 步骤 1 综合呈现从两流改三流（新增【判定点】流：逐条登记候选/所选/依据/误判后果，误判后果严重的升拍板点主动请教用户）；大功能 PrepPRD 模板加「判定点登记表」段；用户确认后路径 A/B 立即写 decisions category=judgment（保鲜守卫「判定点活性」指标数据源），路径 C 由 harness reviewer Step 5 从合同统一写库不重复；用户纠正的判定方法按 e035dad8 第④条走 Invariant Gate 升铁律
  - 21.7.0: 新增 Phase 0「--task-id 立即 claim」（有头模式第一动作，PrepPRD/Phase1 之前）— 起因 2026-07-09 同一 task（f30dace8）被人工 /dev 流程和 Brain tick 自动派发同时抢跑，各自独立产出 PR #3665/#3663；根因是注册任务默认 queued+claimed_by=NULL，tick 每 2 分钟扫一次无主任务，不 claim 必被抢；这不是查重能防的问题（两边都还没开分支/PR，互相查不到），唯一防线是注册后立刻用现成的 POST /tasks/:id/claim 上锁
  - 21.6.0: 新增 Phase 2.5「GitHub 撞车检查」（三路径共用，PrepPRD 前必做）— 起因 2026-07-09 同一 PRD 被 4 个并发 session 各自实现产出 4 个重复 PR；新增 gh pr list --search 查重步骤，查到接近可合并的同语义 PR 就认领而非重新实现，查到 stale/冲突/CI真失败的就先关旧 PR 再动手
  - 21.5.0: 路径A/B 终态 handoff 说明（decisions cf998025）— engine-pr-watchdog 3.2.0 起，路径 A/B merge 后自动写 handoff（SSOT: tasks.result.handoff + 镜像 docs/handoffs/），无下一步写明「完成」；engine-ship 说明同步更新；无行为变更，仅文档对齐
  - 21.4.0: 路径C点火 payload 补 orchestrator=skill-relay 硬性字段 — cecelia #3554（2026-07-05）起 Brain 硬校验 payload.orchestrator==='skill-relay'，缺失/非法直接 terminal failed（missing_orchestrator_flag），LangGraph 图不再隐式兜底
  - 21.3.0: 新增「哨兵（回归守卫）死规矩」节（谁写/啥时候/写哪/CI闸门卡 + 失控程度越高守卫越重 + 一份代码两处用）；Bug PrepPRD 加 proven-to-fire 守卫指针与验收项
  - 21.2.0: decision 写入加内联警告注释（禁止把 category 改成 type；type 被 Brain API 忽略）；清理旧 eval 目录混入
  - 21.1.0: 步骤编号重排 — 步骤 0.5（对抗深挖）重命名为步骤 1，原步骤 1（前置工作核对）升为步骤 2，对齐逻辑顺序
  - 21.0.0: 步骤 0.5 升级为 GAN 对抗 + 并行补全 — Phase 1 Proposer/Challenger 串行（最多 5 轮收敛），Phase 2 三路并行（Agent B 正确路径/C 错误路径/D NFR）；路径 A/B 快跑版（Phase 1 仅 1 轮 + Phase 2 仅 Agent C）
  - 20.1.0: 链路审计修复 4 项 — target_environment 枚举补全为 6 种；PrepPRD Golden Path 改为单线性步骤序列；add-feature 脚本 vs Brain API 参数对照表
---

> **CRITICAL LANGUAGE RULE**: 所有输出简体中文。

---

## 第零步 Phase 0：收到 --task-id 立即 claim（防 Brain tick 抢跑）

如果本次调用带 `--task-id <id>`（有头模式：人工/交互先 `POST /api/brain/tasks` 注册了 Brain task，再调用本 skill）：

**这是本 skill 的第一个动作，必须在 Phase 1 之前执行，不可跳过、不可拖后到 PrepPRD 或更晚。**

```bash
curl -s -X POST "localhost:5221/api/brain/tasks/<task-id>/claim" \
  -H "Content-Type: application/json" -d '{"claimer": "interactive-dev-skill"}'
```

- 返回 200 → claim 成功，继续往下走正常流程
- 返回 409 → 已经被别的执行体抢先 claim（通常是 Brain tick 的自动派发）。**停下来**，把情况告诉用户：这个 task 已被 `<claimed_by>` 抢走，可能正在跑或已经产出 PR，先 `gh pr list`/查 task 状态确认，别在别人已经在跑的任务上再做一遍
- 没有 `--task-id`（本次不是先注册 Brain task 的场景）→ 跳过本步骤，直接进 Phase 1

**为什么必须做**：Brain tick 循环每 2 分钟扫一次 `status='queued' AND claimed_by IS NULL` 的任务自动派发到容器跑 headless claude。`POST /api/brain/tasks` 建出来的任务默认就是这个状态——注册后不立刻 claim，2 分钟内必然被 tick 当无主任务抢走，产出一份和你手动处理完全独立、互相不知情、大概率冲突的重复实现。2026-07-09 实测复现：task `f30dace8` 被人工 `/dev` 流程和 Brain 自动 tick 同时处理，各自独立开出 PR #3665（人工，已合并）和 #3663（Brain 自动，事后发现关闭），实现方式完全不同。这不是查重能防住的问题（两边都没查到对方，因为两边都还没来得及开分支/PR）——唯一有效的防线是注册后立刻上锁。

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
# 1: Journey 体系（journey_features 是 Ability/Feature 唯一正表）
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

## Phase 2.5：GitHub 撞车检查（三条路径都必做，PrepPRD 前）

**背景**：Brain 的 tasks/decisions 查询只能看到"这个系统知道的工作"，看不到"另一个并发 session 已经手动开了分支在改"。2026-07-09 曾出现同一个 PRD（补齐 journey_id 写入）被 4 个独立 session 各自实现一遍，产出 4 个内容几乎相同的 PR，其中 3 个还各自和 main 产生冲突——纯靠 Brain 查询查不出这种撞车，必须直接问 GitHub。

**动作**（从用户描述提炼 2-3 个关键词）：

```bash
gh pr list --search "<关键词>" --state open --json number,title,url,createdAt,statusCheckRollup
```

**分支处理**：

- **查到语义相近的 open PR，且它 CI 全绿或接近可合并** → 不要另起一份实现。改为"认领"这个已有 PR：切到它的分支，把它推向合并（解冲突 / 补测试 / 等 CI），完成后正常收尾。这比重新实现快，也不会再制造一份要被人工发现和清理的重复劳动。
- **查到语义相近的 open PR，但它已经 stale（长时间没动）、和 main 冲突严重、或 CI 有真实失败（非 flaky）** → 可以重新做，但动手前先把旧 PR 关掉，评论里写清楚"与 #<即将开的新 PR> 重复"，避免两份同时挂着让下一个人再撞一次。
- **没查到** → 正常往下走。

这一步的价值在动手写代码**之前**兑现——写完才发现撞车，返工成本已经付了；写之前查一遍，几秒钟的事。

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

5. **展示草稿后不要立即求确认**——先进入步骤 1（对抗深挖），把补全后的版本再给用户确认。

---

### ⚠️ 步骤 1（对抗深挖）：GAN 对抗 + 并行补全，挖完整再给用户

步骤 0 的草稿是用户的"顺利路径"，几乎一定不完整。**在求用户确认之前**，走两个阶段把所有漏洞堵上，**深度按路径缩放**：
- 路径 A/B（bug/小改）：Phase 1 快跑 1 轮 + Phase 2 仅 Agent C（错误路径）
- 路径 C（大功能）：Phase 1 跑到收敛 + Phase 2 三路并行全上

---

#### Phase 1（串行）：FR GAN 功能需求对抗

**先喂料**（不喂 = 退化成通用脑暴，照样漏）：

```bash
# 横切不变量登记表（铁律清单）
curl -s "localhost:5221/api/brain/decisions?category=invariant&limit=50"
# 相关历史教训
curl -s -X POST localhost:5221/api/brain/decisions/match \
  -H "Content-Type: application/json" -d "{\"prd\": \"<本次关键词>\"}"
```

**Proposer sub-agent**（角色：产品经理）：基于步骤 0 草稿，补全功能需求：
- 缺失的中间步骤（识别 / 路由 / 确认真成功 / 去重）
- 边界 case（并发 / 超时 / 空输入 / 特殊输入）
- 权限 / 租户 / 日志安全

**Challenger sub-agent**（角色：挑剔审查员）：逐维度挑战 Proposer 输出，必须输出结构化 JSON：

```json
{
  "new_issues": ["<具体缺口描述，空数组=收敛>"],
  "verified": {
    "completeness": "✅ 步骤1/3/5覆盖场景A/B/C",
    "consistency":  "✅ 无前后矛盾",
    "testability":  "✅ 每步有可验证输出",
    "edge_cases":   "✅ 空输入/并发/超时已定义",
    "error_paths":  "✅ 所有外部依赖有失败场景"
  }
}
```

**收敛条件**：`new_issues = []` 且每个维度有具体证据（不可省略证据、不可只写 ✅ 无说明）。
**安全上限**：5 轮（到达上限仍未收敛 → 将未解决 issues 列给用户拍板）。

---

#### Phase 2（并行，Phase 1 收敛后）：三路补全

Phase 1 收敛后，派三路 Agent 并行执行，各自输出覆盖声明：

| Agent | 角色 | 聚焦 | 输入 |
|-------|------|------|------|
| **Agent B** | 产品经理 | 正确路径补全（边界 case、中间确认步、去重） | FR GAN 收敛结果 |
| **Agent C** | 混沌工程师 | 错误路径补全（所有外部依赖 × 失败场景 × 降级策略） | FR GAN 收敛结果 |
| **Agent D** | 运维专家 | NFR 补全（延迟/频控/规模/可观测缺口 + 建议值） | FR GAN 收敛结果 + `decisions?category=nfr` |

每个 Agent 输出必须包含：检查了哪些维度 / 哪些有证据 / 哪些是缺口。

---

#### 综合：单次呈现给用户

合并四路结果，**产出分三流（关键，别混着砸用户）**：
- 【要用户拍的】policy / 阈值 / FR 范围（回所有还是名单？延迟几秒？失败重试几次？）→ **用人话列给用户，等他定**
- 【判定点】对模糊现实的判断假设（RPA 状态判定 / API 返回解读 / 真机反馈识别，decisions e035dad8）→ 逐条登记候选方法/所选/依据/误判后果；**误判后果严重的（静默丢数据/直接面客错误/不可逆动作）升为拍板点主动请教用户**——用户常有比 AI 自选更优的土办法
- 【机器铁律】登记表里命中的（租户隔离/不回自己/泄密…）→ **自动标注，不打扰用户**，留给合同阶段 enforce

**最终呈现格式**：
```
补全后的 Golden Path（含边界 + 错误路径）：
  步骤 1: ...
  步骤 1-失败: 若 <外部服务> 超时 → 重试3次 → 通知用户
  ...

需要你拍板的 N 个决策点：
  1. 回复延迟容忍：2秒还是5秒？
  2. 失败重试次数：3次还是不重试？
  3. ⚠️ 判定点「<名>」：AI 打算用 <所选方法>（候选还有 <B/C>），误判后果 <后果>——有更好的土办法吗？
  ...

判定点登记表（误判后果轻的自动登记，不打扰）：
  | 判定点 | 候选方法 | 所选方法 | 依据 | 误判后果 |

已命中的铁律（自动 enforce，无需拍板）：
  - 不回自己（decision #xxx）
  - 租户隔离（decision #xxx）
```

**用户对补全版说"对/走/可以"后 → 先写判定点，再进步骤 2。**

**判定点写库（确认后立即执行，每行一条 — 九要素 T5，保鲜守卫「判定点活性」指标数据源）**：

```bash
# ⚠️ 原样复制，category 必须是 judgment，禁止改成 type（type 被 Brain API 忽略）
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d "{\"topic\":\"判定点: <判定点名>\",\"decision\":\"所选方法: <所选>｜候选: <候选>\",\"reason\":\"依据: <依据>｜误判后果: <后果>｜来源: /dev PrepPRD\",\"made_by\":\"user\",\"author\":\"dev-skill\",\"category\":\"judgment\"}"
```

> 用户被 ⚠️ 判定点请教后给出了不同于 AI 所选的方法 → 写库时所选方法用用户的，reason 加 `用户纠正`；被用户明确❌过的判定方法按 e035dad8 第④条走 Invariant Gate 升铁律（另一条 category=invariant，不在此处写）。Brain API 不可用时跳过，不阻塞。**路径 C 不在此处写**（判定点会进 PrepPRD 登记表 → 合同 → reviewer Step 5 APPROVED 后统一写库，此处写会重复）；路径 A/B 没有合同阶段，是此处写库的唯一出口。

> 🔁 **闭环**：生产里新发现的坑（用户吐槽 / 事故）→ 提炼成一条铁律写回登记表（`POST /decisions category=invariant`）→ 下次 Phase 1 喂料时自动覆盖。这是让系统越跑越聪明、同类坑不再踩第二次的机制。

---

### ⚠️ 步骤 2（大功能必做）：核对前置工作

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

> ⚠️ 修完必须配一个 **proven-to-fire 的守卫**（见下方「哨兵（回归守卫）死规矩」节）。Regression test 只是逻辑类守卫；若 bug 碰到的是真实世界接缝（真机/生产 env/真实调用方），必须改用运行时/启动自检守卫，否则换台机器/换个人必复发。

## 验收标准
- [ ] failing test 先 commit（commit-1）
- [ ] 修复代码让 test 变绿（commit-2）
- [ ] 已为本 bug 配 proven-to-fire 守卫（亲眼看它报红过一次）
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

> ⛔ 写之前必须完成步骤 2（前置工作核对），禁止在"前置工作"栏保留任何未确认的 `[ ]` 空白项。

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

## 判定点登记表（对模糊现实的判断假设 — decisions e035dad8）

> 凡"系统自行推断外部真实状态"的地方（RPA 状态判定 / API 返回解读 / 真机反馈识别）逐条登记。
> 误判后果严重（静默丢数据/直接面客错误/不可逆动作）的行在判定点名前标 ⚠️——这些已在上方对抗深挖的拍板点里让用户拍过。
> 无接缝判定点显式写：`（本任务无接缝判定点，N/A）`

| 判定点 | 候选方法 | 所选方法 | 依据 | 误判后果 |
|--------|----------|----------|------|----------|
| | | | | |

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

## 哨兵（回归守卫）死规矩

> **反复出现的病**：bug 修了但没留下"会报警的守卫"，换台机器 / 换个人就再犯。
> **结论**：守卫不能靠人/AI 每次自觉判断，必须像 test 一样有死规矩（谁写 / 啥时候 / 写哪 / 谁卡）。

### 核心：每个 bug/功能 → 配一个【对种类、在对环境跑、且被机器卡】的守卫

守卫 = 让问题没法悄悄复发的东西。**regression test 只是守卫的一种（逻辑类）；环境类要用别的形态。**

### 谁写 / 啥时候 / 写哪 / 谁卡（照 test 的管法）

**谁写**：开发这个功能 / 修这个 bug 的人（AI），跟代码 + test 同一个 PR。**永远不是用户。**

**啥时候**：
1. pre-PRD/Contract 必答「这功能碰真实世界哪几个点」→ 接缝清单（已有规矩，见上方步骤 1/2 + Contract 阶段，引用即可）；
2. 接缝清单**每条配一个守卫，在同一个功能 PR 里写掉**；
3. **标 done 前必须 proven-to-fire**：故意把它弄坏一次（删 key / 制造 NOT-SILENT），亲眼看它**真报红**——没见过它报红的守卫不算守卫（等同于"从不失败的测试证明不了任何东西"）。

**写哪（按守卫种类）**：

| 守卫种类 | 接缝是什么 | 守卫形态 | 放哪 |
|---|---|---|---|
| **逻辑接缝** | 纯函数 / 解析 / 计算 / 数据逻辑 | CI test（regression test） | repo 里 |
| **环境接缝** | 碰真机 / 生产 env / 真实调用方 | **自检代码【打包进那个程序】**：agent 开机自检 / 中台启动自检 / 部署后冒烟 | 主 repo（见下「一份代码两处用」） |

> 环境接缝的自检 **CI 测不到**（CI 是干净假环境）——必须在真环境自检：agent 开机自检（打包进 Agent，装到客户机自跑自报中台）/ 中台开机自检（启动查关键 env，缺了红日志 + `/health` 报坏）/ 部署后冒烟。

**谁卡（机器闸门，最关键）**：
- **靠文档 / 自觉 = 祈祷，不算守卫。** 必须配 CI 闸门：
- **PR 碰了环境接缝（agent 运行时 / 中台启动 / 部署路径 / 新增关键 env 读取）却没带对应自检 → CI 红，合不进。**
- 与现有 `lint-feature-has-smoke` / `lint-tdd-commit-order` 同性质。（闸门实现在 zenithjoy repo，另一 PR 建。）

### 守卫的形态随"失控程度"变重

口诀：**失控程度越高 → 守卫越重。**

| 失控程度 | 例子 | 守卫形态 |
|---|---|---|
| 完全不控、无穷台机器 | Agent 在客户机 | 最重：**运行时自检 + 上报** |
| 你控的一台生产机 | 中台 | 较轻：**启动自检 + 部署后冒烟** |
| 一个部署 | Dashboard | **真 URL 冒烟** |
| 纯逻辑 | 解析 / 计算 | **CI test 就够，别画蛇添足** |

### 一份代码两处用（防误解）

环境自检的**检查代码只写一份、在主 repo**；
① 打包进 Agent → 到每台客户机自跑自报；
② 你的参考机（self-hosted runner）拉同一份、发版前先跑。
**不是每台机一个 repo，更不是各不一样。**

---

## 三条执行路径

### 路径 A：Bug

PrepPRD 落地后，**立即执行**这条 bash 命令写 decision：

```bash
# ⚠️ 原样复制，禁止把 category 改成 type（type 字段被 Brain API 忽略）
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d "{\"topic\":\"<bug 根因简述>\",\"decision\":\"[修法摘要]\",\"reason\":\"[根因]\",\"made_by\":\"user\",\"author\":\"user\",\"category\":\"bug-fix\"}"
```

> Brain API 不可用时跳过。

然后 **下一 tool call 必须是**：
```
Skill({"skill":"superpowers:systematic-debugging"})
```

systematic-debugging → engine-worktree → Superpowers autonomous 接力链 → fix PR → engine-ship → engine-pr-watchdog

> **终态 handoff**（decisions cf998025）：engine-pr-watchdog 3.2.0 起在 merge 确认后自动写 handoff（SSOT: `tasks.result.handoff` + 镜像 `docs/handoffs/<timestamp>-<taskId>.md`）。无下一步时写明「完成，无下一步」。路径 A merge 后即为本任务终态。

---

### 路径 B：小改动

PrepPRD 落地后，**立即执行**这条 bash 命令写 decision：

```bash
# ⚠️ 原样复制，禁止把 category 改成 type（type 字段被 Brain API 忽略）
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d "{\"topic\":\"<改动方向简述>\",\"decision\":\"[改动摘要]\",\"reason\":\"[原因]\",\"made_by\":\"user\",\"author\":\"user\",\"category\":\"small-change\"}"
```

> Brain API 不可用时跳过。

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

> **终态 handoff**（decisions cf998025）：engine-pr-watchdog 3.2.0 起在 merge 确认后自动写 handoff（SSOT: `tasks.result.handoff` + 镜像 `docs/handoffs/<timestamp>-<taskId>.md`）。无下一步时写明「完成，无下一步」。路径 B merge 后即为本任务终态。

**smoke.sh 强制（feat: 类 PR）：**
- ZenithJoy：必须有 `.github/workflows/scripts/smoke/<feature>-smoke.sh`
- CI smoke job 必须通过才能 merge

---

### 路径 C：大功能（Harness）

PrepPRD 落地后，**立即执行**这条 bash 命令写 decision：

```bash
# ⚠️ 原样复制，禁止把 category 改成 type（type 字段被 Brain API 忽略）
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d "{\"topic\":\"<功能方向简述>\",\"decision\":\"[功能方向摘要]\",\"reason\":\"[为什么做]\",\"made_by\":\"user\",\"author\":\"user\",\"category\":\"feature\"}"
```

> Brain API 不可用时跳过。

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
      \"orchestrator\": \"skill-relay\",
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

> ⚠️ **`orchestrator: "skill-relay"` 是硬性字段，禁止省略**（2026-07-05 cecelia #3554 起）：Brain 对 `harness_initiative` 做硬校验，`payload.orchestrator !== 'skill-relay'` 的任务立即 terminal failed（`missing_orchestrator_flag`）。这不是可选配置——旧 LangGraph 图编排已废弃（实测 relay 3/3~4/4 merged vs 旧图 30 天基线 21.7% 成功率），不存在隐式兜底。

Brain tick 自动 pick up 后 spawn 单 session skill-relay（harness-controller 接力跑完 planner → GAN → generator → evaluator → report），`curl localhost:5221/api/brain/tasks/<task_id>` 查任务状态，`curl localhost:5221/api/brain/orchestrator/relay-runs/summary` 查 relay 各 phase 汇总。

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
