---
name: workflow-lifecycle
description: >
  Workflow 生命周期总纲 + Commander 进退场规则 + 步骤表 SSOT 管理。任何新 workflow 立项、老 workflow
  迭代/翻车/加步骤、判断"这步该固化还是留AI"、"Commander 该不该在场/什么时候能退"时先读本 skill：
  把技能工厂七阶段、S1-S5 五段、熟化四态、实现阶梯 L0-L4 四套口径对齐成一张表，给出 Commander
  进场/按步骤退场/自动重进的判据。步骤表本地 JSON 为唯一真相源，改完跑 scripts/sync-to-notion.mjs 推送 Notion。
  触发:「workflow 到哪一段了」「更新步骤表」「这步该固化还是留AI」「新 workflow 立项」「Commander 什么时候退」。
version: 1.2.0
changelog:
  - 1.2.0 (2026-10-12): 第一阶段起就是 workflow（决策 2186700a / 26df670a）：S1 先定大流程（共享外壳 + 业务空位写合同、登记树、Brain 派发入口）再补业务 skill；Commander 第一天就在（S1 由「不在场」改为陪跑）；新增陪跑 skill 线（合同 commander_skill 名+版本，Commander 自加载）。Brain 任务 c0fe7e30。
  - 1.1.0 (2026-09-28): 统一四套口径；新增实现阶梯 L0-L4；Commander 由"两身份"扩为五档在场并给出按步骤退场/整条降档/自动重进判据（阈值为草案待拍板）；新增行业对照。Brain 任务 592910f5。
  - 1.0.0 (2026-09-12): 首版（五段模型 + Commander 两身份 + 步骤表 SSOT），0928 才入库。
---

# workflow-lifecycle — Workflow 生命周期总纲

## 一句话

新活的一生：先定大流程（共享外壳 + 业务空位，写合同、登记树、Brain 能派）→ AI 在业务空位里干通 → 写成 skill →
Commander（第一天就在）陪着跑 N 轮、边跑边攒判例 → 判例逐条变成代码 → Commander 按步骤退场 → 只剩异常召唤。
**任何一步的 AI 兜底路径永不删除。**

## 第一阶段起就是 workflow（决策 2186700a / 26df670a，覆盖本文此前「S1 Commander 不在场」）

- 每次运行都走 **Brain → Commander → 共享外壳-准备 → 业务 skill → 共享外壳-收尾**。准备 = 领 Brain 手机锁 + 查手机 + 查账号；收尾 = 关 App + 放锁 + 交回结果。外壳全公司共享复用，新 skill 只写中间业务部分。
- **第一阶段第一步 = 先定大流程**：合同 `product-map/contracts/<流程>.yaml`（`execution_profile: codex_agent`，外壳活动 `ref` 共享正本，业务活动读回写清）、登记进树、Brain 有派发入口（`workflow_dispatch` + `config/factory-workflows.json` 调度单）；然后才让 Codex 补业务 skill。
- 熟化 = 中间业务块逐步拆细成活动、再逐个换脚本；验证归活动自带读回 + Brain 裁判，Commander 不当质检员（决策 7465d08f）。

## 两条熟化线（并行）

| 线 | 载体 | 第一阶段 | 熟化方向 | 版本落在 |
|---|---|---|---|---|
| 业务 skill 线 | 整流程 skill → 活动 skill → 脚本 | 一大块，Codex 跑 | 拆细 → 脚本化（L1 → L3） | skill 自己的 version + 合同 implementation |
| 陪跑 skill 线 | `wf-<能力>`（Commander 专属） | 可空（合同 `commander_skill: null`） | 从运行中攒判例变厚 → 重复的写成代码变薄 | 合同 `commander_skill.version` = skill frontmatter version（组装闸校验） |

Commander 加载方式：通用 skill `workflow-commander` 配在 agent 上；第一步读调度单的能力 → 读合同 `commander_skill` → 自己装上；空则只按通用规矩；汇报与账本记录所用陪跑 skill 版本。外壳不属于任何一条线，不随单条流程改。

## 四套口径对照（同一件事，颗粒度不同）

| 颗粒度 | 口径 | 回答什么 | 真身 |
|---|---|---|---|
| 单个动作 / skill | 技能工厂七阶段 | 一个新动作从跑通到上架、熟化、清理 | `clawd-skill-factory/AGENTS.md`（决策 bf7d8753） |
| 整条 workflow | S1-S5 五段（本文） | 多步骤流水线走到哪一段 | 本文 |
| 单个判例 | 熟化四态 | 一条经验何时进 SOP、何时写成代码 | zenithjoy-workspace `services/phone-adb-controller/COMMANDER.md` |
| 单个步骤的实现 | 实现阶梯 L0-L4（本文） | 这一步现在靠 AI 还是靠代码 | 本文 + `steps/<workflow>.json` 的 `impl_now` |

| S 段 | 技能工厂阶段 | 多数步骤所在档 | Commander 在场档 |
|---|---|---|---|
| S1 探索 | ⓪立大流程 ①探路 ②核验 | L0（外壳活动已是 L3） | 陪跑（第一天就在；陪跑 skill 可空） |
| S2 沉淀 | ③沉淀 ④验收 ⑤上架 | L1 | 陪跑救火 |
| S3 固化 | ⑥熟化（跑 N 轮）+ 转码核验 | L2 → L3 | 陪跑救火，按步骤开始退场 |
| S4 可靠 | ⑥熟化后段 | L3 | 审计（救火稳了才上） |
| S5 交付 / 稳态 | ⑦清理（常态修剪） | L3，有交付需求的步骤到 L4 | 抽样 → 异常召唤 |

## 五段模型（出生一次性）

| 段 | 目标 | 过关门槛 | 谁干活 |
|---|---|---|---|
| S1 探索 | 先立大流程，再端到端通1次 | 合同组装闸过 + Brain 能派 + 经外壳完整通1次(慢丑都行) | 外壳脚本 + AI 业务块 |
| S2 沉淀 | 出步骤表 | 连续2-3遍序列一致+每步有验证信号 | AI跑+记录 |
| S3 固化 | 稳→写死,漂→留AI | 每步有标签+证据,整轮稳M次 | 代码+AI混合 |
| S4 可靠 | 加审计(证据/哈希) | 带审计仍整轮稳 | +Commander审计 |
| S5 交付 | Kotlin+skill | 有交付需求+表齐全 | Kotlin机械+AI判断 |

## 实现阶梯 L0-L4（按步骤爬，不按 workflow 爬）

| 档 | 形态 | 谁干活 | 实例 |
|---|---|---|---|
| L0 | 纯 AI：有头或无头会话直接干 | 大模型 | 各平台探路 |
| L1 | Skill + AI：AI 照 SOP 干 | 大模型读 skill | 快手/小红书/视频号获客判定树（0919） |
| L2 | 脚本 + Skill + Agent：确定动作进 ADB 脚本，AI 只做判断与串联 | 脚本 + 大模型 | `douyin-phone-adb` |
| L3 | 守卫代码 + AI 兜底：判例已写成代码，代码判不了才叫 AI | 代码为主 | `ruleJudge()`、`classify_failure` |
| L4 | 原生代码（Kotlin）+ 小模型：脱离 Mac 在端上跑，剩余语义判断交小模型 | 代码 + 小模型 | 暂无（0921 拍板 Kotlin 暂缓） |

- 同一 workflow 里各步可以在不同档，档位记在步骤表 `impl_now`。
- **升档靠熟化四态计数，不凭感觉**：同判例第 2 次 → 标 `[固化候选]`；第 3 次 → 开 dev 单写成守卫代码（L2→L3），SOP 同步删掉该条。
- **代码化后必须过 `code-verify`（转码核验）才算升档**：0928 补审 63 条判据，真读回只有 28 条，其余是自报、写死常量或缺失——字段齐全不等于检查还在。
- **L4 不是默认终点**：只有"脱离 Mac / 交付到客户手机"这类交付需求才上（0921 决策：脚本 → ADB → 未来再考虑 Kotlin）。

## Commander：五档在场

Commander 干两件事：① 把这一轮跑完（运行时）；② 每轮收工自答"这个判例能否固化进 SOP/白名单/代码"并计数。
**第②件让它成为熟化四态的发动机**——没有它先陪跑攒下的真实判例，DoD 不知道该写哪几条。

| 档 | 何时 | 做什么 | 成本 |
|---|---|---|---|
| 陪跑救火 | S1 起（第一天就在） | 卡住能重做/换法子，不查证据；每轮收工记判例 | 高：每轮全程 |
| 审计 | S4，且救火形态整轮稳定后 | 一格一格查证据/哈希 | 高 |
| 抽样 | 大部分步骤已退场 | 每 N 轮抽查一轮 | 中 |
| 异常召唤 | 稳态 | 只在代码报"判不了/翻车"时被叫起 | 低：按次 |

病征：审计压在救火没稳的链上 = 整轮跑不完（0912 获客线实证）。

### 按步骤退场（阈值为草案，待拍板）

某一步不再被 Commander 逐轮盯，须同时满足：

1. 该步在 L3，且 `code-verify` 通过；
2. 最近连续 K 轮该步 DoD 全过、零新判例（草案 K=10，且跨至少 2 台设备或 2 个账号）；
3. 该步能机器可读地报"判不了"——否则异常召唤触发不了，不得退场。

### 整条 workflow 降档（草案）

- 陪跑 → 抽样：≥80% 步骤已退场，且整轮连续成功 M 轮（草案 M=20）。
- 抽样 → 异常召唤：连续 2 周抽样零发现。

### 自动重进（不等人）

- 任一步 DoD 连续失败 2 次或出现新判例 → 该步退回陪跑，Commander 重进；修好后 `history` 加一条，K 从 0 重计。
- 平台改版 / 账号风控 / 设备异常 → 整条 workflow 回到陪跑。
- **异常召唤档永久保留**：DoD 只能覆盖已知失败，新情况定义上写不进去。

## 行业对照（2026-09 调研）

| 做法 | 行业 | 我们 |
|---|---|---|
| 录一次 → 生成确定性脚本 → 重放不调模型 → 失败回退 agent 并改脚本 | browser-use workflow-use；Skyvern（首跑生成 Playwright 代码缓存，重复跑跳过模型，自称快 3–5 倍、省约 70%）；Stagehand（动作缓存 + selfHeal） | L0→L3 同一条路；多了熟化四态的显式计数和 code-verify 闸 |
| 监管分级：人在环 → 人在环上 → 只管异常，按无事故运行量升级 | 分级自治实践常要数百次成功运行才升一级 | Commander 五档；量小先定 K=10 / M=20，跑出数据再调 |
| 大模型长期逐步审计每一步 | 一般不做（贵），用确定性检查 + 失败时才调模型 | 审计只在 S4 短期上岗，随后降为抽样 / 异常召唤 |
| 整体重写成原生 | 保留 agent 回退，不追求全原生 | L4 按交付需求才上 |

来源：[workflow-use](https://github.com/browser-use/workflow-use)、[Skyvern changelog](https://www.skyvern.com/docs/changelog)、[Stagehand caching](https://docs.stagehand.dev/examples/caching)、[HITL/HOTL 分级](https://www.famulor.io/blog/human-in-the-loop-vs-on-the-loop-vs-out-of-the-loop)、[graduated autonomy](https://gaper.io/human-in-the-loop-ai)。

## 迭代环（运营期，步骤级）

- 翻车步骤：自动降级留AI兜底(不停服)→重沉淀→重固化→版本+0.1
- 新增步骤：局部走 探索→沉淀→固化 →嫁接进步骤表
- 固化的每一步永远保留 AI 兜底路径。

## 步骤表 SSOT

- 本地真相源：`steps/<workflow>.json`(order/stage/name/impl_now/target/deterministic/signal/status/history[]/evidence)
- 颗粒度标准：每步可独立验证成败(能说清"成了没"就是一步)
- 沉淀触发：AI连对N次→固化候选；反复漂→标留AI；翻车修好→history 加一条
- 建议新增字段（尚未改 JSON，需同步改 Notion 脚本）：`ladder`(L0-L4)、`clean_streak`(连续全过轮数)、`commander`(陪跑/已退场)、`code_verify`(通过/未过/未审)
- 改本地 → `node scripts/sync-to-notion.mjs steps/<workflow>.json` 推 Notion
- Notion 仪表盘：总图页 3d9c40c2ba638171933af1746e19b60c / 步骤库 3d9c40c2ba638195a41bf529056a4aa8 / Workflows库 3d9c40c2-ba63-8145-bfa8-f4c0c006e0af

## 待拍板

1. K=10、M=20、"2 周零发现"三个阈值。
2. 退场是否必须跨 2 台设备 / 2 个账号。
3. 审计档是否保留，还是救火稳定后直接进抽样。
4. 技能工厂 AGENTS.md 里写着"未就绪"的⑥熟化阶段，是否直接采用本文的"陪跑 + 熟化四态 + 按步骤退场"作为定义。

## 配套 skill 网

已有：skill-explore / run-verify / skill-distill（技能工厂①②③）、code-verify（转码核验）、rpa-audit(S3守门)、systematic-debugging、设备台账+TTL锁、memory
缺：步骤记录 skill(S2)、标签判定 skill(S3)、Commander 收工判例计数器（把"自答能否固化"从人工变成自动记账）、固化步 AI 兜底机制
