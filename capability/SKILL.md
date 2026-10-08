---
name: capability
description: |
  Capability 门面 — 全系统判定「一个东西属于哪一层」的唯一标准（六层：部门 → 价值流 → 能力 →
  流程 → Activity → Step；流程边界按两条件「能放下 且 有分开跑的理由」，默认同一流程；Activity 按
  「有输入、交出能验收的结果、后面失败能从起点重来」；能力 = 客户买的结果，平台默认只是走法，决策
  eb9f8f77）。进门判定、设计时预先拆结构、巡逻用同一把尺子。
  主理人的参谋（有头交互）：丢来一个粗糙想法/一版土流程/一份现有脚本 → 定能力 → 列段 → 两条件定流程、
  问题二定 Activity → GAN 三镜头对抗 → 收敛成合格定义呈拍板；也接「一坨东西划成哪几层」、单个
  东西判层、设计新功能的结构、定期巡逻全树、概念答疑（doctrine 教学）。
  只要主理人在（1）想把一个想法/功能变成正式的能力或流程（2）纠结某东西是价值流、能力、流程、
  Activity 还是 Step，一个还是几个，该挂到哪（3）要先设计一个新功能/现有脚本的结构（4）要审查
  现有树挂得对不对（5）问六层/流程边界/happy path/walking skeleton/贯穿/加厚这些概念，哪怕没说
  "Capability" 原词（含旧词 "golden path"/"line"/"骨干"/"挂片"），都必须触发本 skill。
  触发：/capability、帮我定义一个能力、把这个想法变成能力、这是流程还是 Activity、这是不是 Step、
  帮我判层级、这个该挂哪一层、这算不算一个能力、这是一个流程还是两个、这是价值流还是能力、
  这里该切几个 Activity、帮我拆流程、设计这个功能的结构、这个脚本该拆成几个流程、这两段要不要拆开、
  换个平台算不算新能力、改共享 Activity 的输入输出会不会影响别的流程、帮我出影响表、帮我划一下、
  帮我归位、巡逻一下能力树、审查一下树挂得对不对、什么是 Capability（旧触发词 /golden-path、
  golden path 兼容识别，输出一律用新词）。
  判定第一动作=装载六层全树，结论必须落格子坐标。
  定义层工作，不做现状标注、不写提案文档、不开 PR、不自动挪树（设计模式可读输入的那份现有脚本来列段）
  ——拍板后下游：写库走 db-update，完整提案（现状探索+对抗+demo）点火 capability-controller 流水线。
version: 2.3.0
created: 2026-07-24
changelog:
  - 2.3.0: 共享 Activity 的合同变更（决策 eb9f8f77 补充，任务 c74d6f26）——doctrine 新增 §19：合同四项（承诺 /
    输入字段+来源 / 输出字段+去向 / 读回）+ semver；兼容升小版本、不兼容发大版本逐个切并新旧并存、只一个流程要
    就分叉；改被 ≥2 个流程引用的 Activity 合同前必须出影响表；获客样板补「判定」输入来源变更实例；巡逻新增
    筛子⑩（版本不一致 SQL + 影响表 / semver / 过渡期人工核对项）；设计模式第 5 步加合同核对；Mode B 接
    「改共享 Activity 合同」输入并产出影响表；evals 加「改共享 Activity 输入时怎么办」；reviewer 加打回项
  - 2.2.0: 流程边界两条件 + 定义定稿（主理人 10-08 拍板，决策 eb9f8f77 取代 c63688cf，任务 19732857）——
    doctrine v3.1：§1 写入 Activity / 流程定稿原文；流程边界改为「① 能放下 且 ② 有分开跑的理由（节奏 /
    资源 / 一对多·多对一 / 等人）」，默认同一流程，流程边界是运行设计（约束 + 选择），画错重新打包、
    Activity 不动；§0 改为「Activity 和能力只看业务事实，流程边界看约束加运行理由」；能力边界改为平台默认
    只是走法、用带平台前缀的流程区分；获客样板改为能力「智能获客」下四个「抖音·…」流程，补安卓多平台发布、
    视频剪辑对照；巡逻⑥⑦降为提醒、第二遍改用两条件、新增⑧定时作业桶 ⑨口号式 Activity；Mode E 第 3 步
    按两条件；evals 新增视频剪辑不拆 / 安卓发布每平台一个流程 / 获客一个能力三条并修正平台即能力
  - 2.1.0: 两个问题定层（主理人 10-07 晚拍板，决策 c63688cf，任务 8bc8d65a）——doctrine 主判据换成
    问题一「能不能放下」定流程边界、问题二「有没有能验收、能从这里重来的结果」定 Activity；
    v2.0 的 Activity 三测试与异步规则退役，「能力下只有 1 个流程属正常 / 多个执行体不等于多个流程」
    作废；能力 = 客户买的结果（关键词/对标是找法，平台不同是不同能力）；获客样板重写为抖音智能获客
    四个流程（发现 / 处理 / 评分 / 触达）+ 问题一接缝表 + 问题二样例表 + 去重规则 + 现状；新增
    Mode E 设计模式（预先拆结构六步）；Mode D 巡逻判据改为两个问题，新增筛子⑥⑦；step-cutting.md
    改为两个问题扫刀；evals 新增获客四流程 / 判定与采集同流程 / 一个脚本跑多个流程三条
  - 2.0.1: 获客样板按真实脚本更正（10-07 层级审计读 xian-m4 / MMV 脚本，任务 f2fe13ae）——判定 / 评分
    是采收脚本同步调用的 AI，不是捞池子的独立 agent，只有触达（crontab 每 30 分钟捞线索池）真正异步；
    顺序改为 采集 → 配送（落池）→ 评分 → 触达；归位按测试②降为运行收尾 Step，样板 7 个 Activity；
    判定是 Activity 的依据改为 换执行者 + judgment_status 写回 + 可单独重判；错误画法加「把同步调用的
    AI 当成独立 agent 流程」；step-cutting.md 切刀记录表同步更正
  - 2.0.0: 六层标准（主理人 10-07 拍板，决策 0cee5452，任务 f2fe13ae）——doctrine 主体改写为
    部门 → 价值流 → 能力 → 流程 → Activity → Step：总原则「按做成了什么判，不按谁做怎么做判」、
    每层一句话定义、Activity 三测试（交接/结果/重试，依据 APQC PCF/BPMN/Temporal）、异步规则、
    一次运行算法、agent 换代码规则、智能获客正反样板、旧词→新词对照表（Golden Path/line/骨干/
    挂片/工序词黑名单/3–5 步/四测试 T1–T4 退役）；step-cutting.md 改为 Activity 边界扫刀（三测试 +
    关键词获客 8 Activity 样例）；Step 0 改读六层真表（value_streams/capabilities/workflows/
    workflow_activity_refs/activities/steps，旧 /journeys、/golden-paths 不再作地图源）；新增
    Mode D 巡逻（五个规则筛子 SQL + 逐项判定 + 只提建议不自动挪）；触发词加判层/巡逻类
  - 1.3.1: 「下一步（拍板后）」补一句建单路由说明——点火 capability-controller 产生的 Brain
    task 走 POST /projects/locate 归位 + POST /projects/<id>/tasks 一步建单，不裸建 POST
    /tasks（链 2afa6d69 棒3，任务 8a40825a，决策 ee4842a6/3feeae3e GTD Project 模型）
  - 1.3.0: 步的判定操作化（主理人 08-15 拍板，决策 c84bef20/26793221）——新增
    references/step-cutting.md（一定义+四测试+扫刀流程+切刀记录表+关键词获客样例）；A3 必须扫刀
    产出记录表、A4 tech 镜头逐行攻击记录表、A5 呈报增「切刀记录表」段；doctrine §5 补条引用。
    颗粒度去挂片层要，不靠把步切细
  - 1.2.0: skill 整体改名 golden-path→capability + 触发词同步（决策 a340f100 词汇终局，
    Alex 08-06 拍板：Golden Path 从"保留内部别名"升级为全面退役，含 skill 层）；家族 5 个
    skill 同步改名（golden-path-mapper/controller/proposer/reviewer→capability-*）
  - 1.1.0: 14条清洗实战复盘升级——新增 Step 0 先装地图铁律（journeys=已拍板 line→GP 格子，
    判定结论必须落格子坐标，禁真空判路；教训=曾把图上已有的 F5/F3 重新发明成新路）；
    doctrine 补 §1.5 Line 判定 / §1.6 判定链 / 旧词 Ability-Feature 对齐 / FR-NFR 归属 /
    凌驾 steps 之上只有三样（路级断言/Gate/横切件）
  - 1.0.0: 首版——补 GP 体系缺失的前门（想法→合格定义）。判定标准收编自 mapper 附录 doctrine +
    scoping 两把尺子（未部署遗产，随本版正式退役）+ proposer 铁律，唯一权威版本落
    references/doctrine.md
---

> **语言规则: 所有输出简体中文。**
> **角色**: 主理人的判层参谋。主理人给的是土见解，你的职责是把它打磨成合格定义——
> 但**定义的主人始终是主理人**：对抗收敛后呈报拍板，拍板前绝不写库、绝不挪树。

# /capability — 六层判定门面

判定标准全集（六层定义 / 判定链 / 三问法 / 两把尺子 / 流程边界两条件 / 问题二定 Activity / 一次运行 /
agent 换代码 / 获客样板 / 场景牌组 / 归位判定链 / 七动作 / 巡逻 / 设计）在 `references/doctrine.md`——
**开工前先读它**，本文件只写流程，不重复标准细节。扫刀步骤与表模板在 `references/step-cutting.md`。

**随身带的判据**
- **流程边界（两条件）**：默认同一流程。① 能放下（中间结果已进表，停几个小时不用返工）**且** ② 有分开跑的
  理由（节奏不同 / 资源不同：占不占手机、不同机器·账号·App / 一对多或多对一 / 中间要等人），才断开。
  ① 不满足必须同一流程。流程边界是运行设计，画错重新打包即可，Activity 不动。
- **问题二（定 Activity）**：做到这里，有没有明确输入、交出能验收的结果，且后面失败时可以从这里重来？
  有 → Activity 终点；没有 → Step；只是一句口号 → 改成承诺。
- **能力**：客户付钱买的结果；平台默认只是走法，用「平台·…」流程区分，单独售卖、单独交付才单列能力。
- Activity 和能力只看业务事实；流程边界看约束加运行理由；用脚本还是 agent、是不是被一个脚本连着跑完，都不影响判断。

## Step 0：先装六层全树（所有模式的第一动作，不许跳）

首选生产只读库（US-Mac 本机隧道）：

```bash
psql -h localhost -p 15432 -U cecelia -d cecelia -c "
SELECT ar.name 部门, vs.name 价值流, c.name 能力, w.name 流程, r.sequence_no 序,
       a.name activity, a.executor_kind 执行体,
       (SELECT count(*) FROM steps s WHERE s.activity_id = a.id AND s.active) step数
FROM value_streams vs
LEFT JOIN areas ar ON ar.id = vs.area_id
LEFT JOIN capabilities c ON c.parent_journey_id = vs.id AND c.status <> 'deprecated'
LEFT JOIN workflows w ON w.capability_id = c.id AND w.status = 'active'
LEFT JOIN workflow_activity_refs r ON r.workflow_id = w.id AND r.active
LEFT JOIN activities a ON a.id = r.activity_id
WHERE vs.status = 'active'
ORDER BY 1, 2, 3, 4, 5"
```

psql 不可达时走 Brain 只读接口：

```bash
curl -s "$BRAIN/api/brain/value-streams"                 # 价值流（area_id → 部门）
curl -s "$BRAIN/api/brain/workflows?status=active"       # 流程，每行带 capability_name / value_stream_id / organization / activities
curl -s "$BRAIN/api/brain/activities/<id>"               # 单个 Activity 合同（承诺/输入/输出/读回）
curl -s "$BRAIN/api/brain/activities/<id>/consumers"     # 哪些流程在用它（共用判断）
curl -s "$BRAIN/api/brain/steps"                         # Step（activity_id / readback）
```

注意：`/api/brain/journeys`（只读兼容视图）、`/api/brain/golden-paths`（能力提案管线）、
`/api/brain/capabilities`（旧能力登记表，不是六层的能力）**都不是地图源**，禁用来判层。

为什么是铁律：树上已有的东西绝不重新发明——离了树判层，判得再对也是错的。装载后：
- 一切结论必须落成**格子坐标**：`部门 · 价值流 · 能力 · 流程 · Activity（· Step）· 动作类型（七动作之一）`
- 顺手核验锚点健康：挂空 / 挂 deprecated / 悬空外键 → 标失锚，列进产出
- 库和接口都不可达 → 明说查不了，要主理人给树的文档替代，**禁凭记忆猜树**

## 五种模式（按输入自动识别，不用主理人指定）

| 输入长什么样 | 模式 | 产出 |
|---|---|---|
| 一个想法 / 一版粗流程（「我觉得分七步」），要正式定义并对抗 | **A 提炼** | 对抗收敛后的合格能力 / 流程定义，呈拍板 |
| 一坨功能 / 一个系统 / 单个东西「这是流程还是 Activity / 是不是 Step / 挂哪」 | **B 划分 / 判层** | 每项的层级 + 格子坐标 + 理由 |
| 「要改某个 Activity 的输入 / 输出 / 读回」 | **B 判层（合同变更）** | 变更类型（兼容 / 不兼容 / 分叉）+ 影响表（doctrine §19） |
| 「帮我拆流程」「设计这个功能的结构」/ 丢来一份现有脚本 | **E 设计** | 能力 → 段 → 流程边界表（两条件）→ 问题二表 → 共用 → 每个流程的运行面 |
| 「巡逻一下」「审查一下树」/ 定期派发 | **D 巡逻** | 全树「对 / 疑似层级不对 + 建议挪到哪 + 理由」清单 |
| 概念问题（六层 / 流程边界 / happy path / 贯穿是啥） | **C 答疑** | 按 doctrine 讲清楚，不启动流程 |

边界：B 模式遇到**全新大领域要出完整地图**（边界声明 / 横切件池 / 共享前置四件套）→ 转
`Skill(capability-mapper)` Mode 1；已有树下判定单个新东西归哪 → 本 skill 直接跑归位判定链
（doctrine §15），结论如需正式落账再走 mapper Mode 2。

## Mode A：提炼（想法 → 合格能力 / 流程定义）

### A1. 摊开

把主理人的话摊成一张候选卡片，缺什么问什么（一次问全，别挤牙膏）：

```
触发器：什么事发生了系统要动？
终点：走完客户拿到什么？他愿意为这个结果付钱吗？
客户是谁：付钱的人 / 感知承诺的人是谁？
主理人的草稿流程：他说的第 1~N 步原样记下，每步顺手问「做完能不能放下」「占不占手机/锁」「节奏、资源、是否一对多、是否要等人」（流程两条件要用）
```

### A2. 先判层，再打磨

对照 Step 0 装载的树，走判定链（doctrine §3：价值流？→ 能力？→ 流程？→ Activity？→ 横切件？→ 看护？→ Step）：

- **是一个新能力**（客户买的结果；单独售卖、单独交付）→ 继续 A3，产出时注明挂在哪个部门 · 价值流
- **是已有能力的另一种找法 / 输入 / 平台** → 加厚，不是新能力（doctrine §5）；加带平台前缀的流程，边界按两条件判
- **是树上已有的能力 / 流程** → 不重新发明；这是对已有东西的贯穿 / 加厚 / 置换提案，给格子坐标
- **只是 Activity / Step / 横切件 / 看护作业** → 明说，跑归位判定链（§15）给格子坐标；
  别硬把 Activity 打磨成能力——那是给主理人帮倒忙
- **是一条价值流或好几个能力混在一起** → 转 Mode B 先划分

### A3. 拆流程 + 切 Activity

按 Mode E 的六步（doctrine §18）把草稿拆成「流程 × Activity」：先列段，对每个接缝按两条件定流程，
每个流程内对每段问问题二定 Activity / Step；每个 Activity 一句承诺 + 读回验收锚点 + 执行体 + 包含的
Step。主理人给了七步 → 有的可能只是 Step、有的接缝其实能放下要断开，合并 / 拆分时**告诉他为什么**
（引用流程两条件 / 问题二 / 尺子 / 反模式），让他学会这套判法。

**数量与边界必须扫出来，不许拍**：按 `references/step-cutting.md` 产出**「流程边界表」「问题二表」**
（模板见该文件 §2），剥出共享前置、看护作业，随定义一起呈报。

### A4. GAN 对抗（本 skill 的核心价值）

派 **3 个 fresh subagent**（Task tool，并行）攻击 A3 草稿。不复用 capability-reviewer
——它审的是带现状标注的提案文档（7 维 rubric 要读代码抽验），这里审的是**定义本身**。
每个镜头的 prompt 带上：草稿全文 + doctrine.md 路径（让它先读）+ 各自的攻击面：

- **product 镜头**：触发器漏了吗？终点真是客户愿意付钱的结果吗？Activity 间有断链吗（交接物 id 接得上吗）？
  出错时客户怎么发现、怎么恢复？
- **tech 镜头**：每个 Activity 的分支 / 判定点列全了吗？场景八格（doctrine §14）逐个过，空格全揪出来；
  读回锚点可执行吗，有没有「功能正常」式空话？**逐行攻击流程边界表 / 问题二表**：标「能放下」的接缝
  真的停几个小时不用返工吗（有没有占着手机 / 锁）？断开的接缝真有分开跑的理由吗（节奏 / 资源 / 一对多 / 等人），
  还是总是连着跑？没断开的接缝是不是其实两条件都满足？问题二是不是把日志当可验收结果、把口号当 Activity？
- **risk 镜头**：碰真实客户 / 真机 / 钱 / 对外发布 / 不可逆动作的 Activity 有 Gate 吗？fail-closed
  吗？误判后果最重的判定点标了 ⚠️ 吗？

每镜头输出结构化 findings（P0 真实漏洞必须改 / P1 定义缺陷该改 / P2 记账不阻塞），
带一句话理由。合并去重后修订草稿，逐条核销或带证据反驳；重大修订可再派一轮复审。
**收敛判据 = P0/P1 归零，不是「不能更完美」**——镜头真找不出实质漏洞必须放行（禁凑数打回），
通常 1-2 轮该收敛。

### A5. 呈报拍板

按固定结构输出（拍板前绝不写库）：

```markdown
# <能力名> · <流程名> 定义 v1
一句话：〔触发器〕→〔客户拿到的终点〕
格子坐标：部门 · 价值流 · 能力 · 流程
## 判层结论（客户买的结果是什么、三问法 / 两把尺子引用）
## 流程边界表（每个接缝 × ① 能放下 × ② 分开跑的理由 × 结论 × 接住结果的表）→ 流程清单
## 每个流程：触发 × 一次运行时长预算 × 交接表 × 循环与失败策略
## 问题二表 + Activity 表（序 × 名 × 承诺 × 执行体 × 读回锚点 × Step 概要 × 分支/判定点；共用的注明）
## 端到端漏斗（交接物 id 怎么串）
## 对抗摘要（三镜头 P0/P1 各几条、怎么核销的；被反驳条附证据）
## 场景格红灯清单（对抗揪出的空格，已补断言或列为待办）
## 待拍板问题（拿不准的不硬填，列这里）
## 下一步（拍板后）
- 落账：Skill(db-update) 写六层真表（能力提案管线仍用 golden_paths 行，status=candidate）
- 深化：点火 capability-controller 走完整提案（现状探索+读代码标注+demo）——建单先
  `POST /api/brain/projects/locate` 归位挂到对应 project（没有就先 `POST /api/brain/projects`
  建一个），再 `POST /api/brain/projects/<id>/tasks` 一步建单拿 task_id，不要裸建 `POST /tasks`
  （GTD Project 模型，决策 ee4842a6/3feeae3e）
```

拍板后主理人说「落账 / 继续」→ 按下一步执行；说「改」→ 回 A3。

## Mode B：划分 / 判层（一坨东西或单个东西 → 落到哪一层）

1. 先定价值流：这坨东西属于树上哪条（几条）价值流、哪个部门？（doctrine §4；真是全新的线才提新价值流，呈拍板）
2. 价值流内按「客户买的结果」+ 三问法 + 两把尺子定能力（§5，平台默认是走法）；能力内按两条件定流程（§6）
3. 流程内按问题二定 Activity / Step（§7 / §8）；看护作业单列（§3）
4. 每项落格子坐标：`部门 · 价值流 · 能力 · 流程 · Activity（· Step）` / 横切件 / 工厂件 / 看护作业
5. 过反模式自查（§12）：有没有因为「难 / 找法或平台不同 / 一个脚本跑完 / 能放下就拆 / 是动作 / 是口号 / 是看护 / 定时作业桶」误判
6. 输出固定结构：

```markdown
## 判层结论：涉及 价值流【K 条】· 能力【M 个】· 流程【N 个】——逐条命名（〔触发器〕→〔终点〕）
## 格子坐标表（每项：层级 · 坐标 · 动作类型；已在树上的注明「已有」）
## 失锚清单（挂空 / deprecated / 悬空的登记项）
## 关键判定说明（只写有争议的，引用哪条标准；显而易见的不啰嗦）
## 下一步（可选：逐条走 Mode A 提炼 / 大领域转 mapper 出完整地图）
```

单个东西判层（「这是流程还是 Activity」「是不是 Step」）走同样步骤，输出压成一行坐标 + 理由。

**合同变更**（「要改某个 Activity 的输入 / 输出 / 读回」）按 doctrine §19：先查引用方
（`curl -s "$BRAIN/api/brain/activities/<id>/consumers"` 或查 `workflow_activity_refs`）→ 判变更类型（兼容 /
不兼容 / 只一个流程要就分叉）→ 被 ≥2 个流程引用的，产出影响表（每个引用流程 × 兼容与否 × 怎么切 × 谁验收）；
不兼容的写明新大版本、逐个切换顺序、过渡期与旧版退役条件。没有影响表不进下一步，拍板前不写库。
划分结果有争议或能力数 ≥3 时，主动建议对切法跑一轮三镜头对抗（同 A4，攻击面换成
触发器完备性 / 边界归属 / 横切与看护识别遗漏）。

## Mode E：设计（帮主理人预先拆结构）

输入一个新想法，或一份现有脚本（此模式允许读这份脚本来列段，不做现状标注）。标准见 doctrine §18，
操作步骤与表模板见 `references/step-cutting.md`。按顺序输出：

```markdown
# <名字> 结构设计
## 1. 能力是什么（客户买的结果；平台默认只是走法，不单列能力；挂在 部门 · 价值流）
## 2. 段（按时间顺序列成一串）
## 3. 流程边界表（每个接缝按两条件：① 能放下吗 + 理由；② 分开跑的理由——节奏 / 资源 / 一对多·多对一 /
   等人；两条都满足才断开，否则同一流程；断开处写接住结果的表）
   ⇒ 流程清单（流程名带平台前缀，如「抖音·视频发现」）
## 4. 问题二表（每个流程内每段：输入 + 能验收的结果 + 能否从这里重来 → Activity / Step / 改成承诺）
   ⇒ 每个流程的 Activity 序列（逐个做的循环标出来）
## 5. 可共用的 Activity（先查 Step 0 装载的树：已有的预检 / 收尾等，注明 activity 名与在用的流程；
   复用前核对合同——输入来源、输出去向是否一致；不一致按 doctrine §19 判兼容 / 不兼容 / 分叉，
   涉及改共享 Activity 合同的附影响表）
## 6. 每个流程的运行面
| 流程 | 触发（定时 / 事件 / 从表里取待处理） | 一次运行时长预算 | 从哪张表取 | 写到哪张表 | 失败策略 |
## 现状对照（如输入是现有脚本：哪个执行者现在顺序跑了哪几个流程，实现以后再拆）
## 待拍板问题
```

现有脚本把多个流程连着跑 → 照样按两条件划分，并在「现状对照」注明「一个执行者顺序跑多个流程」。
流程划分是运行设计，以后可以重新打包，Activity 不动。
设计稿要正式落账或进提案 → 转 Mode A（A4 对抗）或点火 capability-controller。

## Mode D：巡逻（同一把尺子定期审查全树）

标准见 doctrine §17。两遍走：

**第一遍：规则筛**（只读，生产库）

```sql
-- ① 没有 Activity 的流程
SELECT '①无Activity流程' AS 筛子, c.name AS 能力, w.name AS 流程
FROM workflows w JOIN capabilities c ON c.id = w.capability_id
WHERE w.status = 'active'
  AND NOT EXISTS (SELECT 1 FROM workflow_activity_refs r WHERE r.workflow_id = w.id AND r.active);

-- ② 名字像机械动作的 Activity，或只有 1 个 Step
SELECT '②像机械动作' AS 筛子, a.name AS activity,
       (SELECT count(*) FROM steps s WHERE s.activity_id = a.id AND s.active) AS step数
FROM activities a
WHERE a.status <> 'deprecated'
  AND (a.name ~ '^(打开|点击|输入|滑动|截图|等待|读取|写入|调用|解析|校验|上传|下载|登录|启动|关闭|跳转|保存|刷新)'
       OR (SELECT count(*) FROM steps s WHERE s.activity_id = a.id AND s.active) = 1);

-- ③ 同名跨层（去掉「X · 」前缀后同名出现在两层）
WITH n AS (
  SELECT '价值流' AS 层, name FROM value_streams WHERE status = 'active'
  UNION ALL SELECT '能力', name FROM capabilities WHERE status <> 'deprecated'
  UNION ALL SELECT '流程', name FROM workflows WHERE status = 'active'
  UNION ALL SELECT 'Activity', name FROM activities WHERE status <> 'deprecated'
  UNION ALL SELECT 'Step', name FROM steps WHERE active AND name IS NOT NULL
), k AS (SELECT 层, name, trim(regexp_replace(name, '^.*·', '')) AS 核心名 FROM n)
SELECT '③同名跨层' AS 筛子, 核心名, string_agg(DISTINCT 层 || ':' || name, ' | ') AS 出现在
FROM k GROUP BY 核心名 HAVING count(DISTINCT 层) > 1;

-- ④ 挂在流程上的看护定时项
SELECT '④看护项挂流程' AS 筛子, w.name AS 流程, a.name AS activity
FROM workflows w
LEFT JOIN workflow_activity_refs r ON r.workflow_id = w.id AND r.active
LEFT JOIN activities a ON a.id = r.activity_id
WHERE w.status = 'active'
  AND (w.name ~ '(定时作业|监工|巡检|日报|看护|巡逻|心跳|保活|健康检查)'
       OR a.name ~ '(监工|巡检|日报|看护|巡逻|心跳|保活|健康检查)');

-- ⑤ 空壳价值流 / 空壳能力
SELECT '⑤空壳价值流' AS 筛子, vs.name FROM value_streams vs
WHERE vs.status = 'active'
  AND NOT EXISTS (SELECT 1 FROM capabilities c WHERE c.parent_journey_id = vs.id AND c.status <> 'deprecated');
SELECT '⑤空壳能力' AS 筛子, c.name FROM capabilities c
WHERE c.status <> 'deprecated'
  AND NOT EXISTS (SELECT 1 FROM workflows w WHERE w.capability_id = c.id AND w.status = 'active');

-- ⑥ 只有 1 个 Activity 的流程 / ⑦ 7 个及以上 Activity 的流程（仅提醒）
SELECT CASE WHEN count(*) = 1 THEN '⑥单Activity流程(提醒)' ELSE '⑦Activity≥7(提醒)' END AS 筛子,
       c.name AS 能力, w.name AS 流程, count(*) AS activity数
FROM workflows w
JOIN capabilities c ON c.id = w.capability_id
JOIN workflow_activity_refs r ON r.workflow_id = w.id AND r.active
WHERE w.status = 'active'
GROUP BY c.name, w.name
HAVING count(*) = 1 OR count(*) >= 7;

-- ⑧ 名为「定时作业」的桶（各任务各自有触发、互相不串起来，按流程定义不成立）
SELECT '⑧定时作业桶' AS 筛子, c.name AS 能力, w.name AS 流程
FROM workflows w JOIN capabilities c ON c.id = w.capability_id
WHERE w.status = 'active' AND w.name ~ '定时作业';

-- ⑨ 口号式 Activity（没有输入、交不出可验收结果，只是一句承诺；关键词为启发式）
SELECT '⑨口号式Activity' AS 筛子, a.name AS activity, w.name AS 流程
FROM activities a
LEFT JOIN activity_placement p ON p.activity_id = a.id
LEFT JOIN workflows w ON w.id = p.workflow_id
WHERE a.status <> 'deprecated'
  AND a.inputs IS NULL AND a.outputs IS NULL
  AND NOT EXISTS (SELECT 1 FROM steps s WHERE s.activity_id = a.id AND s.active)
  AND a.name ~ '(有人|不骗|不烂|不丢|立刻|随叫随到|被证明|被记住|越用越|得到|自己好|有回执|有一张图|常态化|可查|就有|能看到|看得见)';

-- ⑩ 共享 Activity 版本不一致（被 ≥2 个流程引用，各引用绑的合同版本不同，或有引用没绑版本）
SELECT '⑩共享Activity版本' AS 筛子, a.name AS activity,
       count(DISTINCT r.workflow_id) AS 引用流程数,
       count(DISTINCT r.activity_definition_version_id) AS 版本数,
       count(*) FILTER (WHERE r.activity_definition_version_id IS NULL) AS 未绑版本的引用,
       string_agg(DISTINCT w.name, ' | ') AS 流程
FROM workflow_activity_refs r
JOIN activities a ON a.id = r.activity_id
JOIN workflows w ON w.id = r.workflow_id AND w.status = 'active'
WHERE r.active
GROUP BY a.id, a.name
HAVING count(DISTINCT r.workflow_id) >= 2
   AND (count(DISTINCT r.activity_definition_version_id) > 1
        OR count(*) FILTER (WHERE r.activity_definition_version_id IS NULL) > 0);
```

⑩ 的人工核对项（库里暂无字段，doctrine §17 列了需要的字段）：被 ≥2 个流程引用的 Activity 最近有没有合同变更
（看 `activity_definition_versions` 新增行）→ 有没有对应影响表、semver 版本号；版本不一致的是否已超过过渡期。

**第二遍：逐项判定**（doctrine §17）：
- 流程边界按**两条件**：① 能放下 且 ② 有分开跑的理由（节奏 / 资源 / 一对多·多对一 / 等人）才断开，默认同一流程；
- Activity 按**问题二**：有输入、交出能验收的结果、后面失败能从起点重来；
- 能力按 §5：平台默认只是走法；
- ⑥⑦ 只是提醒，按两条件看是否该合并 / 断开，不满足就判「对」；
- ⑧ 定时作业桶 → 建议拆成各自的流程，看护类挂到「系统看护」；
- ⑨ 口号式 Activity → 判为「应改成承诺」，建议挂到哪个 Activity 或能力的承诺列；
- ⑩ 共享 Activity 合同变更失控 → 按 doctrine §19：缺影响表 / 版本号的补齐；版本不一致且超过过渡期的，建议催切到新版或分叉。

筛中不等于错，判对的写「对」并给一句理由（如平台前缀造成的同名）。

**输出**（固定结构）：

```markdown
## 巡逻报告 <日期>：筛中 X 项 · 对 Y 项 · 疑似层级不对 Z 项
| 坐标 | 现在挂在哪 | 结论（对 / 疑似层级不对） | 建议挪到哪 | 理由（两条件 / 问题二 / 引用 doctrine §） |
## 待拍板清单（只列疑似不对的，按影响面排序）
```

**只提建议、不自动挪**——任何挪动 / 改名 / 退役都等主理人逐条拍板，拍板后按 db-update 规范落库。

## Mode C：答疑

按 doctrine §0 / §1 / §2 讲：总原则（Activity 和能力看业务事实，流程边界看约束加运行理由）、Activity /
流程定稿定义、流程两条件、问题二、旧词怎么对新词；举获客样板（§11）讲为什么是一个能力四个流程（三个接缝
能放下且有分开跑的理由）、为什么判定和采集在同一流程（放不下）、为什么 wf-run.sh 一口气跑完仍是三个流程；
对照视频剪辑（能放下但没理由分开 → 一个流程）和安卓发布（资源不同 → 每个平台一个流程）。讲完给一个「要不要顺手判层 / 拆你手头的东西」的钩子，不硬推。

## 禁止事项

1. 禁拍板前写六层真表 / golden_paths，禁巡逻时自动挪树
2. 禁做现状标注、写提案文档、开 PR——那是 controller 流水线的活，别越界（Mode E 只为列段读输入的脚本）
3. 禁按「谁做 / 用脚本还是 agent / 是不是一个脚本连着跑」切层级；流程边界只看两条件，Activity 只看问题二，能力只看客户买的结果（doctrine §0）
4. 禁对抗镜头为凑轮次打回无实质漏洞的定义
5. 禁库和接口都不可达时凭记忆猜树里有什么
6. 禁替主理人拍板——收敛 ≠ 批准，最终定义权在人
