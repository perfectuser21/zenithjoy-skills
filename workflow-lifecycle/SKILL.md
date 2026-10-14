---
name: workflow-lifecycle
description: >
  Workflow 生命周期总纲 + Commander 进退场规则 + 步骤表 SSOT 管理。任何新 workflow 立项、老 workflow
  迭代/翻车/加步骤、判断"这步该固化还是留AI"、"Commander 该不该在场/什么时候能退"时先读本 skill：
  把技能工厂七阶段、S1-S5 五段、熟化四态、实现阶梯 L0-L4 四套口径对齐成一张表，给出 Commander
  进场/按步骤退场/自动重进的判据。执行合同以仓库固定来源为准；运行及判定走 Brain，Notion 投影只读。
  触发:「workflow 到哪一段了」「更新步骤表」「这步该固化还是留AI」「新 workflow 立项」「Commander 什么时候退」。
version: 1.3.0
changelog:
  - 1.3.0 (2026-10-14): Activity按冻结版本、实现及环境取证；配套Skill保留；独立代码核验复用run-verify；取消次数自动转码与直写投影。
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

## Activity证据与配套实现（执行规则 v1）

- 证据按冻结 `activity_definition_version_id`、`implementation {kind,id,version,digest}`、`environment {id,fingerprint}` 归集，观测使用 `evidence.observed`；身份以正式冻结绑定与独立核验读回为准，不信自报PASS。
- `execution_role=primary` 的 Code 独立成功、Skill 独立成功、`fallback/rescue` 的接手与救场分别留原件。救场可以完成原任务；原Code失败不得覆盖，也不得进入Code独立晋级窗口。
- 次数只是证据；缺观测、混版本或环境、救场不能自动晋级。只升级一个Activity，其他Activity的有效证据保留，不按整条Workflow清零。
- Skill和Code满足同一业务要求：需求改变先验证S2再固化C2；S2已独立验证可先用，不必等C2。纯实现修bug沿原要求回归。C2失败只可接当前环境验收过的S2，失败不自动降成不兼容S1/C1。
- 任务起跑固定组合，在途不换版；正常纯代码阶段模型调用为0，程序发现异常才带进度、固定组合和动作结果唤醒Commander。运行救场不现场改代码，改进另进开发任务。
- 开发检查、PR合并、部署读回、独立业务核验分别记账，任何一项都不能代替其他项；本规矩不授予生产指针修改权。

## 实现阶梯 L0-L4（按步骤爬，不按 workflow 爬）

| 档 | 形态 | 谁干活 | 实例 |
|---|---|---|---|
| L0 | 纯 AI：有头或无头会话直接干 | 大模型 | 各平台探路 |
| L1 | Skill + AI：AI 照 SOP 干 | 大模型读 skill | 快手/小红书/视频号获客判定树（0919） |
| L2 | 脚本 + Skill + Agent：确定动作进 ADB 脚本，AI 只做判断与串联 | 脚本 + 大模型 | `douyin-phone-adb` |
| L3 | 守卫代码 + AI 兜底：判例已写成代码，程序发现异常才召唤 Commander；正常执行模型调用为0 | 代码为主 | `ruleJudge()`、`classify_failure` |
| L4 | 原生代码（Kotlin）+ 小模型：脱离 Mac 在端上跑，剩余语义判断交小模型 | 代码 + 小模型 | 暂无（0921 拍板 Kotlin 暂缓） |

- 同一 workflow 里各步可以在不同档，档位记在步骤表 `impl_now`。
- **升档靠熟化四态计数，不凭感觉**：同判例第 2 次 → 标 `[固化候选]`；次数仅提供证据；符合机械观测、变体覆盖和独立核验判据后，另建 /dev 任务固化，原 Skill 与判据保留。
- **代码化后必须按 skill-solidify 的独立代码核验契约，由另一会话使用 run-verify 读回真实产出，才可提出升档**：0928 补审 63 条判据，真读回只有 28 条，其余是自报、写死常量或缺失——字段齐全不等于检查还在。
- **L4 不是默认终点**：只有"脱离 Mac / 交付到客户手机"这类交付需求才上（0921 决策：脚本 → ADB → 未来再考虑 Kotlin）。

## Commander运行方式（执行判据）

| 条件 | 运行方式 | 验收 |
|---|---|---|
| 业务要求或实现尚未独立验证 | Commander陪跑，按冻结合同调配套Skill/Code | 正式独立读回当前版本产物、动作与收尾 |
| 当前版本Code已独立通过，异常探针及配套Skill在当前环境验收过 | 纯代码正常运行，程序检测异常后才召唤Commander | 正常阶段模型调用为0；故障时有完整上下文与去重结果 |
| Code失败或观测未知 | 保留原失败；授权范围内读回动作，交配套已验证Skill接手 | 救场独立留痕，结果未知/Skill也失败按期限收尾 |

原五档、K=10/M=20和两周抽样只是历史设计草案，不能作为当前生产自动路由或晋级规则。次数不决定成熟；改变稳定状态前必须取得独立业务核验和现行发布线放行。运行会话不修改生产指针。

每个Activity是否可固化，以机械观测、变体覆盖、当前环境、固定来源与独立代码核验同时成立判断。只升级B保留A/C证据；新异常记录独立开发任务，保留同业务配套Skill，不在救场现场重写实现。

## 行业对照（2026-09 调研）

| 做法 | 行业 | 我们 |
|---|---|---|
| 录一次 → 生成确定性脚本 → 重放不调模型 → 失败回退 agent 并改脚本 | browser-use workflow-use；Skyvern（首跑生成 Playwright 代码缓存，重复跑跳过模型，自称快 3–5 倍、省约 70%）；Stagehand（动作缓存 + selfHeal） | L0→L3 同一条路；多了熟化四态的显式计数和 独立代码核验闸 |
| 监管分级：人在环 → 人在环上 → 只管异常，按无事故运行量升级 | 分级自治实践常要数百次成功运行才升一级 | 历史阈值只是研究材料；执行仍按独立证据判据 |
| 大模型长期逐步审计每一步 | 一般不做（贵），用确定性检查 + 失败时才调模型 | 审计只在 S4 短期上岗，随后降为抽样 / 异常召唤 |
| 整体重写成原生 | 保留 agent 回退，不追求全原生 | L4 按交付需求才上 |

来源：[workflow-use](https://github.com/browser-use/workflow-use)、[Skyvern changelog](https://www.skyvern.com/docs/changelog)、[Stagehand caching](https://docs.stagehand.dev/examples/caching)、[HITL/HOTL 分级](https://www.famulor.io/blog/human-in-the-loop-vs-on-the-loop-vs-out-of-the-loop)、[graduated autonomy](https://gaper.io/human-in-the-loop-ai)。

## 迭代环（运营期，步骤级）

- 翻车步骤：自动降级留AI兜底(不停服)→重沉淀→重固化→版本+0.1
- 新增步骤：局部走 探索→沉淀→固化 →嫁接进步骤表
- 固化的每一步永远保留 AI 兜底路径。

## 步骤表 SSOT

- 历史整理材料：`steps/<workflow>.json`(order/stage/name/impl_now/target/deterministic/signal/status/history[]/evidence)
- 颗粒度标准：每步可独立验证成败(能说清"成了没"就是一步)
- 沉淀触发：AI连对N次→固化候选；反复漂→标留AI；翻车修好→history 加一条
- 建议新增字段（尚未改 JSON，需同步改 Notion 脚本）：`ladder`(L0-L4)、`clean_streak`(连续全过轮数)、`commander`(陪跑/已退场)、`code_verify`(通过/未过/未审)
- 真实合同与定义改仓库来源；登记和运行证据写 Brain 正式接口；Notion 步骤库是投影，禁止直接推写。
- Notion 仪表盘：总图页 3d9c40c2ba638171933af1746e19b60c / 步骤库 3d9c40c2ba638195a41bf529056a4aa8 / Workflows库 3d9c40c2-ba63-8145-bfa8-f4c0c006e0af

## 待拍板

1. 历史K/M与抽样阈值未作为现行执行规则启用。
2. 退场是否必须跨 2 台设备 / 2 个账号。
3. 成熟纯代码与异常召唤的真实实现仍需单独交付与验收，规则描述不等于已接通。
4. 技能工厂 AGENTS.md 里写着"未就绪"的⑥熟化阶段，是否直接采用本文的"陪跑 + 熟化四态 + 按步骤退场"作为定义。

## 配套 skill 网

已有：skill-explore / run-verify / skill-distill（技能工厂①②③）、run-verify（独立运行核验）、rpa-audit(S3守门)、systematic-debugging、设备台账+TTL锁、memory
缺：步骤记录 skill(S2)、标签判定 skill(S3)、Commander 收工判例计数器（把"自答能否固化"从人工变成自动记账）、固化步 AI 兜底机制
