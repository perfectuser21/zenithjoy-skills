# PrepPRD：工厂 · F1 开发闭环 — GP锚定闭环 刀3（skill层三处接线）

## 本次对话涵盖的所有事项（防信息丢失）
- [x] 本 PrepPRD 包含：`dev/SKILL.md` Stage 0 锚点检查（跨repo file-existence gated）+ `harness-contract-proposer/SKILL.md` 合同模板GP-Anchor必填段 + `harness-contract-reviewer/SKILL.md` 审查维度补充（均在 `perfectuser21/zenithjoy-skills` 仓库）
- [x] 配套小改动（另开小PR，在 `perfectuser21/zenithjoy-workspace` 仓库）：`.claude/CLAUDE.md` 的"harness-planner前必填6问"第1问措辞升级
- [ ] 另立 Sprint（本次不做）：刀4（Brain层tasks API锚校验+evaluator判据+report回写）、刀5（patrol棘轮+历史归户）

## 关键架构约束（Phase1自查发现，非目标外）
`dev`/`harness-contract-proposer`/`harness-contract-reviewer` 三个 skill 是**跨repo通用**的（cecelia、zenithjoy-workspace、zenithjoy-skills等仓库共用同一份skill文件）。`product-map/generated/product-map.json` 只存在于 `zenithjoy-workspace` 仓库。所有新增的GP锚点检查逻辑必须做**file-existence gated**：文件不存在（在cecelia等其他仓库工作时）→ 优雅跳过 + 记一行说明，不报错、不阻塞。此模式在 `harness-contract-proposer/SKILL.md` 里已有先例（changelog 9.7.0"跨repo化刀3"，与本项目"刀3"编号巧合但完全无关，是不同项目的既有惯例）。

## Journey 当前状态
- Journey：工厂 · F1 开发闭环（`e6f803f2-8c48-4cce-a7a1-5b1bda5e9c29`，maturity=mvp）
- ✅ GP锚定校验（97400e37...）— feature/thin，刀1(product-map SSOT)+刀2(CI硬闸)已交付
- 🔄 本次刀3推进同一Ability：把锚定检查从"仅CI机械拦截"前移到"规划/合同阶段就提醒"，减少浪费（孤儿任务在第0步死掉而不是烧完整个pipeline才死在CI）

## 本次要做的
让 `/dev`（交互式路径）、`harness-planner`（Brain路径C规划阶段）、`harness-contract-proposer`/`harness-contract-reviewer`（合同GAN阶段）三处在动手写代码**之前**就提醒开发者/AI"这个改动该挂哪条GP"，而不是等CI在最后一步才拦截。

## Golden Path（开发者/AI-agent 操作流程，覆盖 /dev 和 harness-planner 两条入口）

### 分支A：交互式 /dev 入口
1. 开发者/AI 对 Claude 说"想做X功能" → `/dev` Phase1判定路径C → 既有Phase2查5源+Phase2.5撞车检查+步骤0 Golden Path草稿（均不变）→ **新增Stage 0锚点检查**：检测当前仓库根目录是否存在 `product-map/generated/product-map.json`
2. 存在（zenithjoy-workspace场景）→ 从用户描述/task上下文推断这个功能该挂哪条line/GP → 用jq查该id是否真实存在于JSON → 存在则继续PrepPRD；不存在/推断不出 → 停下来问用户"这个功能该挂哪条GP，还是走backlog"，不开工
3. 不存在（cecelia/zenithjoy-skills等其他仓库场景）→ 跳过本检查，PrepPRD里记一行 `gp-anchor: skipped (product-map.json not found, non-zenithjoy-workspace repo)`，继续原有流程
4. 大功能PrepPRD模板新增"GP-Anchor（推进/keep-green/none）"段，呼应刀2的三形态声明，用户确认PrepPRD时一并确认这一行

### 分支B：Brain自动派发 harness-planner 入口
5. harness-planner 收到task后写 sprint-prd.md（不变）；ZenithJoy项目CLAUDE.md的"harness-planner前必填6问"第1问从"prose+Notion URL"升级为"product-map里机器可查的GP id"——填不出机器可查id的6问不通过，不允许启动harness-planner（本项已有的6问机制本身在ZenithJoy项目CLAUDE.md里，本刀只改第1问措辞，机制外壳不动）

### 分支C：合同GAN阶段（proposer/reviewer）
6. `harness-contract-proposer` 起草合同时，若当前仓库有product-map.json → 合同必须含"GP-Anchor"必填段（推进#stepN/keep-green/none三形态之一），id经jq查证存在；product-map.json不存在（第三方repo）→ 显式记`gp-anchor: skipped`，不阻塞
7. `harness-contract-reviewer` 的Golden Path覆盖审查清单新增一条：合同的GP-Anchor声明与product-map真实数据是否一致（id不存在/格式不合法 → 对应维度扣分打回）

### 错误路径
- Stage 0锚点检查在非zenithjoy-workspace仓库运行 → 优雅跳过，不报错（file-existence gated，见"关键架构约束"）
- 用户描述的功能确实挂不上任何已知GP → 引导走backlog分类（本刀不新增判断逻辑，直接复用刀2 `none(backlog)` 的既有形态定义），不强行编造锚点
- proposer写的GP-Anchor id与product-map.json实际不符 → reviewer该维度扣分，REVISION

## 客户视角
无终端客户可感知变化（dev_pipeline内部机制，同刀1/刀2）。"客户"是使用这几个skill的开发者/AI-agent。

## 完成后开发者/AI能
1. 在动手写代码**之前**（PrepPRD阶段/6问阶段/合同阶段），如果这个改动挂不上任何GP，就会被提醒，而不是等到PR推送后CI才红
2. 在cecelia等其他仓库正常使用这几个skill，不受product-map检查影响

## 涉及的 Ability / Feature
- GP锚定校验（GP-Anchor Enforcement，97400e37...）— 推进，thin

## 不包含
- Brain tasks API 锚校验、evaluator PASS判据、report回写 — 刀4
- ci-patrol棘轮、历史无锚PR归户 — 刀5
- 新增判断"该功能到底该挂哪条GP"的推理逻辑 — 只做检查+提醒，具体挂哪条GP仍是开发者/AI结合PRD判断，本刀不做智能推荐
- 修改 harness-planner/harness-contract-proposer/harness-contract-reviewer 之外的其他harness skill（如harness-generator/harness-evaluator）— 那些在刀4范围（evaluator判据）

## 判定点登记表
（本任务无接缝判定点，N/A——纯skill prompt文字改动，无对真实世界模糊状态的判断假设）

## 前置工作（已逐项确认，无 TBD）

### 账号与登录
- [x] 不涉及

### API 与凭据
- [x] 不涉及外部API

### 测试 Fixture
- [x] 不涉及（skill prompt文字无法用传统单测验证行为，用grep做ARTIFACT级存在性验证）

### 基础设施
- [x] `~/perfect21/zenithjoy-skills` 本地仓库已确认可写，已建独立worktree `/Users/administrator/worktrees/zenithjoy-skills/cp-07290752-gp-anchor-cut3-skills`
- [x] 配套的 `.claude/CLAUDE.md` 改动在 `zenithjoy-workspace` 仓库另开小PR，本次会话在同一sprint内一并完成

## 验收标准（Final E2E）
- [ ] `dev/SKILL.md` 含Stage 0锚点检查段落，且明确写出file-existence gated逻辑（grep确认含product-map/generated/product-map.json路径引用+"跳过"/"skipped"关键词）
- [ ] `harness-contract-proposer/SKILL.md` 合同模板段落含"GP-Anchor"必填要求
- [ ] `harness-contract-reviewer/SKILL.md` Golden Path覆盖审查清单含GP-Anchor一致性检查项
- [ ] `zenithjoy-workspace` 仓库 `.claude/CLAUDE.md` 的6问第1问措辞已升级为机器可查GP id
- [ ] 三个skill文件改动后，用真实的近期案例（如刀1/刀2的PrepPRD）走一遍脑内模拟，确认新增段落读起来逻辑自洽、不产生跨repo误伤
- [ ] CI（zenithjoy-skills仓库若有）全绿
