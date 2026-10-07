---
name: capability
description: |
  Capability 门面 — 全系统判定「一个东西属于哪一层」的唯一标准（六层：部门 → 价值流 → 能力 →
  流程 → Activity → Step，决策 0cee5452）。进门判定和巡逻用同一把尺子。主理人的参谋（有头交互）：
  丢来一个粗糙想法/一版土流程 → 判层 → 切 Activity → GAN 三镜头对抗 → 收敛成合格的能力/流程定义
  （承诺 + 读回验收锚点）呈拍板；也接「一坨东西划成哪几层」、单个东西判层、定期巡逻全树、
  概念答疑（doctrine 教学）。
  只要主理人在（1）想把一个想法/功能变成正式的能力或流程（2）纠结某东西是价值流、能力、流程、
  Activity 还是 Step，一个还是几个，该挂到哪（3）要审查现有树挂得对不对（4）问六层/三测试/
  happy path/walking skeleton/贯穿/加厚这些概念，哪怕没说 "Capability" 原词（含旧词 "golden
  path"/"line"/"骨干"/"挂片"），都必须触发本 skill。
  触发：/capability、帮我定义一个能力、把这个想法变成能力、这是流程还是 Activity、这是不是 Step、
  帮我判层级、这个该挂哪一层、这算不算一个能力、这是一个流程还是两个、这是价值流还是能力、
  这里该切几个 Activity、帮我划一下、帮我归位、巡逻一下能力树、审查一下树挂得对不对、
  什么是 Capability（旧触发词 /golden-path、golden path 兼容识别，输出一律用新词）。
  判定第一动作=装载六层全树，结论必须落格子坐标。
  定义层工作，不读实现代码不做现状标注、不写提案文档、不开 PR、不自动挪树——拍板后下游：写库走
  db-update，完整提案（现状探索+对抗+demo）点火 capability-controller 流水线。
version: 2.0.1
created: 2026-07-24
changelog:
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

判定标准全集（六层定义 / 判定链 / 三问法 / 两把尺子 / Activity 三测试 / 异步规则 / 一次运行算法 /
agent 换代码 / 获客样板 / 场景牌组 / 归位判定链 / 七动作 / 巡逻）在 `references/doctrine.md`——
**开工前先读它**，本文件只写流程，不重复标准细节。切 Activity 的操作步骤在 `references/step-cutting.md`。

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

## 四种模式（按输入自动识别，不用主理人指定）

| 输入长什么样 | 模式 | 产出 |
|---|---|---|
| 一个想法 / 一版粗流程（「我觉得分七步」） | **A 提炼** | 对抗收敛后的合格能力 / 流程定义，呈拍板 |
| 一坨功能 / 一个系统 / 单个东西「这是流程还是 Activity / 是不是 Step / 挂哪」 | **B 划分 / 判层** | 每项的层级 + 格子坐标 + 理由 |
| 「巡逻一下」「审查一下树」/ 定期派发 | **D 巡逻** | 全树「对 / 疑似层级不对 + 建议挪到哪 + 理由」清单 |
| 概念问题（六层 / 三测试 / happy path / 贯穿是啥） | **C 答疑** | 按 doctrine 讲清楚，不启动流程 |

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
主理人的草稿流程：他说的第 1~N 步原样记下，每步顺手问「谁来做、怎么启动」（这是属性，不是层级）
```

### A2. 先判层，再打磨

对照 Step 0 装载的树，走判定链（doctrine §3：价值流？→ 能力？→ 流程？→ Activity？→ 横切件？→ 看护？→ Step）：

- **是一个新能力** → 继续 A3，产出时注明挂在哪个部门 · 价值流
- **是已有能力的另一种业务走法** → 新流程（先过 doctrine §6：真的是业务走法不同，不是执行体 / 异步不同）
- **是树上已有的能力 / 流程** → 不重新发明；这是对已有东西的贯穿 / 加厚 / 置换提案，给格子坐标
- **只是 Activity / Step / 横切件 / 看护作业** → 明说，跑归位判定链（§15）给格子坐标；
  别硬把 Activity 打磨成能力——那是给主理人帮倒忙
- **是一条价值流或好几个能力混在一起** → 转 Mode B 先划分

### A3. 起草流程 + 切 Activity

按 doctrine §7 / §13 把草稿整形成 Activity 表：每个 Activity 一句承诺 + 读回验收锚点 + 执行体 +
怎么启动 + 包含的 Step。主理人给了七步 → 有的可能只是 Step、有的执行体切法不对，合并 / 拆分时
**告诉他为什么**（引用哪条测试 / 尺子 / 反模式），让他学会这套判法。

**Activity 数量与边界必须扫出来，不许拍**：先读 `references/step-cutting.md`，把粗流程摊成候选片段，
对每个相邻边界跑三测试（① 交接 / ② 结果 / ③ 重试），按判法切或并；剥出共享前置、看护作业和
「归下一个能力」的尾巴；产出**「切刀记录表」**（模板见该文件 §3）随 Activity 表一起呈报。

### A4. GAN 对抗（本 skill 的核心价值）

派 **3 个 fresh subagent**（Task tool，并行）攻击 A3 草稿。不复用 capability-reviewer
——它审的是带现状标注的提案文档（7 维 rubric 要读代码抽验），这里审的是**定义本身**。
每个镜头的 prompt 带上：草稿全文 + doctrine.md 路径（让它先读）+ 各自的攻击面：

- **product 镜头**：触发器漏了吗？终点真是客户愿意付钱的结果吗？Activity 间有断链吗（交接物 id 接得上吗）？
  出错时客户怎么发现、怎么恢复？
- **tech 镜头**：每个 Activity 的分支 / 判定点列全了吗？场景八格（doctrine §14）逐个过，空格全揪出来；
  读回锚点可执行吗，有没有「功能正常」式空话？**逐行攻击「切刀记录表」**：每一刀的三测试判定站得住吗
  （尤其测试②是不是把日志当业务结果、是不是按执行体硬切了流程）？有没有该切没切 / 不该切硬切？
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
## 判层结论（为什么它是能力 / 流程：三问法 / 两把尺子 / §6 引用）
## Activity 表（序 × 名 × 承诺 × 执行体 × 怎么启动 × 读回锚点 × Step 概要 × 分支/判定点；共用的注明）
## 切刀记录表（每个相邻边界 × ①②③ × 结论 × 一句话理由；前置件 / 看护作业 / 归下一个能力单列）
## 一次运行怎么算（交接物 id、端到端漏斗断言）
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
2. 价值流内按三问法 + 两把尺子定能力（§5）；能力内按「业务走法是否不同」定流程（§6）
3. 流程内按三测试定 Activity / Step（§7 / §8）；看护作业单列（§3）
4. 每项落格子坐标：`部门 · 价值流 · 能力 · 流程 · Activity（· Step）` / 横切件 / 工厂件 / 看护作业
5. 过反模式自查（§12）：有没有因为「难 / 平行 / 是阶段 / 执行体不同 / 异步 / 是看护」误判
6. 输出固定结构：

```markdown
## 判层结论：涉及 价值流【K 条】· 能力【M 个】· 流程【N 个】——逐条命名（〔触发器〕→〔终点〕）
## 格子坐标表（每项：层级 · 坐标 · 动作类型；已在树上的注明「已有」）
## 失锚清单（挂空 / deprecated / 悬空的登记项）
## 关键判定说明（只写有争议的，引用哪条标准；显而易见的不啰嗦）
## 下一步（可选：逐条走 Mode A 提炼 / 大领域转 mapper 出完整地图）
```

单个东西判层（「这是流程还是 Activity」「是不是 Step」）走同样步骤，输出压成一行坐标 + 理由。
划分结果有争议或能力数 ≥3 时，主动建议对切法跑一轮三镜头对抗（同 A4，攻击面换成
触发器完备性 / 边界归属 / 横切与看护识别遗漏）。

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
```

**第二遍：逐项判定**——筛中项逐个跑 doctrine §3 判定链 + §5 三问法 + §7 三测试。筛中不等于错，
判对的写「对」并给一句理由（如渠道前缀造成的同名）。

**输出**（固定结构）：

```markdown
## 巡逻报告 <日期>：筛中 X 项 · 对 Y 项 · 疑似层级不对 Z 项
| 坐标 | 现在挂在哪 | 结论（对 / 疑似层级不对） | 建议挪到哪 | 理由（引用 doctrine §） |
## 待拍板清单（只列疑似不对的，按影响面排序）
```

**只提建议、不自动挪**——任何挪动 / 改名 / 退役都等主理人逐条拍板，拍板后按 db-update 规范落库。

## Mode C：答疑

按 doctrine §0 / §1 / §2 讲：总原则（按做成了什么判）、六层每层一句话、旧词怎么对新词；
举获客样板（§11）讲 Activity 三测试、「多个执行体 ≠ 多个流程」和「同步调用的 AI ≠ 独立 agent 流程」。讲完给一个「要不要顺手判层 /
提炼你手头的东西」的钩子，不硬推。

## 禁止事项

1. 禁拍板前写六层真表 / golden_paths，禁巡逻时自动挪树
2. 禁读实现代码做现状标注、写提案文档、开 PR——那是 controller 流水线的活，别越界
3. 禁按「谁做 / 怎么做 / 同步异步 / 代码还是 agent」切层级（doctrine §0）
4. 禁对抗镜头为凑轮次打回无实质漏洞的定义
5. 禁库和接口都不可达时凭记忆猜树里有什么
6. 禁替主理人拍板——收敛 ≠ 批准，最终定义权在人
