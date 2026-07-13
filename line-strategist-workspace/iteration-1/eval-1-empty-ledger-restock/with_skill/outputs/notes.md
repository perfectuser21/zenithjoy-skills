# 军师决策理由 — Line04「客户私域 AI 接管」(DRY_RUN)

- LINE_ID: `bfeed805-deed-46c3-8624-87f0028101d4`
- TRIGGER: `manual`　DRY_RUN: `true`　执行时间: 2026-07-08（快照 generated_at 2026-07-08T09:52:33Z）
- 最终决策: **fix_bug（路径A）**，目标 issue `4ed0b9dd-78d3-4441-a794-f1ddfcdc2758`
- confidence: **0.72**（≥0.6，不触发停线上报）

## 一、快照事实清单（每条带证据来源）

1. **防抖通过**：`GET /api/brain/tasks?status=queued` 中本 line 的 strategist_decision 任务数 = 0。
2. **line 基本面**：`GET /api/brain/warroom/line/{id}` → name=客户私域 AI 接管，status=active，maturity=not_started。
3. **推进项账本为空**：`GET /api/brain/warroom/line/{id}/advancements` → `items: []`。todo=0、doing=0，账本尚未铺开——这是本 line 的真实结构性缺口。
4. **近期 run 终局**（warroom tasks 字段）：
   - 最近失败：07-03 `桌面租约仲裁层第一刀`（8594ef9a，verdict=FAIL，死因=ARTIFACT 门执行 `python3` 命令 not found——门禁环境问题，基础设施味道）；06-26 `CRM·Glide 客户列表页`（8cc738e2，死在 generator）。两次根因**不同**。
   - 但 07-07 有两个任务 **done**（客服回复判断内核接入 e74341f4、CRM客户状态历史追踪 5d090237）——失败链已被成功打断，**不满足停线条件**（连续 ≥2 run 同根因失败）。
   - 06-23 有一批历史失败与 harness Contract Gate 误杀有关（对应 open issue 7c2d19fe，sub_area=harness，跨线基础设施，已有人 track）。
5. **本 line open P0/P1**（`GET /api/brain/issues?status=open`，按标题 [line04]/[line04-cs]/客服语义归属过滤）：
   - **P0 4ed0b9dd**：agent 装 2.0.28 连上中台但找不到微信（line04 模块日志无输出 / UIA 找不到窗口）——**最新版本上核心功能瘫痪**。
   - **P0 c1432195**：dashboard 设客服白名单点保存→整页白屏（配置做不了）。
   - **P0 bbd27b4d**：2.0.25 exe 起不来（rcedit 破坏 pkg overlay）——针对旧版，2.0.28 已能启动并连中台，疑似被取代但未关闭。
   - P1 若干：5109ba34 无单实例锁、96db53be 权限划分未实现、ecf13d74 汇总页缺失、defe1a42 人设串台等。
6. **无进行中的修复**：`GET tasks?status=in_progress` = 空；`status=queued` 仅 5 条 content-pipeline 任务，与 Line04 无关。所有 P0/P1 均无 fix 任务在跑。
7. **ability/feature 台账**（`GET /api/brain/abilities?journey_id=…`）：29 条；building×4（桌面租约仲裁层 8358dd63、Agent形态收口 00de40bd、客服每日工作报告 7bf891b8、客服工作汇总统计页 7b5b403c），planned×15+，done×6。存在补货候选。

## 二、决策阶梯逐级判断（第一个命中即停）

| 级 | 条件 | 判定 |
|---|---|---|
| 1 停线 | 连续 ≥2 run 同根因失败 / 失败指向基础设施 | **不命中**。两次最近失败根因不同；07-07 已有两任务成功落地，失败非连续。ARTIFACT 门 python3 缺失属 harness 门禁环境（跨线，已有 issue 在 track），未构成本 line 持续烧产能 |
| 2 P0/P1 bug 无修复在跑 | 本 line 有 open P0×3、P1×多，in_progress=0 | **命中，即停** |
| 3-6 | — | 不再评估 |

**目标选择**（三个 P0 中挑最高阻断）：选 **4ed0b9dd**。理由：它发生在**最新版本 2.0.28** 上，客户机装好、连上中台，微信却找不到 → 「AI 接管个微」这条 line 的核心 workflow 在客户端完全不可用，是产品级瘫痪；c1432195（白名单白屏）是配置面，影响次之；bbd27b4d 针对旧版 2.0.25，大概率已被 2.0.28 取代（修 4ed0b9dd 时应顺带确认并关闭）。

**关于「账本为空要不要补货」**：账本 items=[] 是事实缺口，但阶梯规定 bug 优先于补货，不跳级。预期 P0 修完后下一次唤醒将命中第 5 级「补货」（候选：building 且推进项耗尽的 ability，如 8358dd63 桌面租约仲裁层）。本次遵守「一次只建 1 个任务」，不并行派补货。

**跨界登记（不执行）**：8594ef9a 的失败根因（门禁环境缺 python3）与 7c2d19fe（Contract Gate 误杀 Line04 sprint）均属 harness 基础设施，scope=cross-line，随晨报浮给主理人，本军师不建跨线任务。

## 三、自审打分

```
依据: ① issues API 直证三个 open P0 属本 line；② in_progress=0、queued 无 line04 任务，无重复修复；
      ③ 阶梯 bug > 补货，账本空不改变优先序；④ 4ed0b9dd 是最新版本核心功能瘫痪，阻断度最高
confidence: 0.72
质量预期: 修复后客户机 agent 2.0.28 可发现微信窗口、line04 模块激活，恢复端到端可用性，
          也让后续推进项（桌面租约等）有可运行的真机环境
风险: 若 4ed0b9dd 实为个案环境问题（如微信版本闸误拦，关联 P2 222cb545）而非代码 bug，
      则损失约一个 dev 任务的排查产能，且 c1432195 被推后一个决策周期
```

## 四、DRY_RUN 说明

按 skill 规定：Step 4（建任务）与 Step 5（写 note 留痕）全部跳过，零 DB 写入、零通知。应留痕全文已放入 result.json 的 `decision_note_draft` 字段。若非 DRY_RUN，将建 1 个任务：`fix: agent 2.0.28 line04 模块找不到微信窗口`，task_type=dev，priority=P0，payload 带 journey_id + issue_id=4ed0b9dd + harness_mode:false。

## 五、实际执行过的全部 curl 命令清单（逐条标注读/写）

| # | 命令 | 类型 |
|---|---|---|
| 1 | `curl -s "localhost:5221/api/brain/tasks?status=queued&limit=50"`（防抖过滤 strategist_decision） | **GET（只读）** |
| 2 | `curl -s "localhost:5221/api/brain/warroom/line/bfeed805-deed-46c3-8624-87f0028101d4"` | **GET（只读）** |
| 3 | `curl -s "localhost:5221/api/brain/warroom/line/bfeed805-deed-46c3-8624-87f0028101d4/advancements"` | **GET（只读）** |
| 4 | `curl -s "localhost:5221/api/brain/warroom/line/bfeed805-deed-46c3-8624-87f0028101d4"`（二次解析 tasks 全量） | **GET（只读）** |
| 5 | `curl -s "localhost:5221/api/brain/issues?status=open&limit=50"` | **GET（只读）** |
| 6 | `curl -s "localhost:5221/api/brain/tasks?status=in_progress&limit=50"` | **GET（只读）** |
| 7 | `curl -s "localhost:5221/api/brain/tasks?status=queued&limit=50"`（查占用） | **GET（只读）** |
| 8 | `curl -s "localhost:5221/api/brain/journeys/{id}/features"`（404，端点不存在） | **GET（只读）** |
| 9 | `curl -s "localhost:5221/api/brain/journey-features?journey_id={id}"`（404，端点不存在） | **GET（只读）** |
| 10 | `curl -s "localhost:5221/api/brain/abilities?journey_id={id}"`（命中，返回 29 条） | **GET（只读）** |
| 11 | `curl -s "localhost:5221/api/brain/features?journey_id={id}"`（返回全局 feature registry，未采用） | **GET（只读）** |
| 12 | `curl -s "localhost:5221/api/brain/issues?status=open&limit=50"`（提取候选 issue 完整 UUID） | **GET（只读）** |

**写操作（POST/PATCH/DELETE）总数：0。** 未创建任务、未写 note、未发 Bark/飞书通知。
