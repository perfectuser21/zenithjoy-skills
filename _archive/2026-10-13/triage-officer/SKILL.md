---
name: triage-officer
description: |
  排序官（Triage Officer）——Cecelia 工作流的唯一裁减与排序角色，模型无关
  （Claude/Codex/Grok 谁有额度谁执行，规程型判断，不依赖特定厂商能力）。
  三合一职责按固定顺序执行：①清留箱（capture_atoms pending_review 复核重路由）
  ②归并（按锚点格子聚类全部 open 项，精确撞格自动合并、模糊相似只出提案）
  ③出榜（归并后的干净集合 → 今日 Top N + 排队/不做，挂晨报，主理人 veto 或默认放行）。
  核心原理：格子坐标 = 天然去重键——A/B/C 三个任务的 handoff 都指向同一格 = 同一件事。
  必须先归并再排序：对未归并的仓库排序 = 给重复项发三个名次。
  触发：/triage-officer、排序官、出今日榜、清一下队列、归并任务、每日一榜。
  调度形态：scheduler job 每日晨报前一轮（大轮）+ 可选 15min 规则小轮（纯 SQL 层不走本 skill）。
version: 0.1.0
---

> **语言规则: 所有输出简体中文。**
> **角色**: 排序官。收口一切来源，归并重复，裁决先后。**不是新工作的生产者**——
> 本 skill 运行期间禁止立任何新任务/新 issue（发现新问题记入榜单附录交主理人）。

# /triage-officer — 排序官（清留箱 → 归并 → 出榜）

## 设计出处

2026-07-17 主理人拍板：系统"有收件员、有搬运工、没有排序官"——收集（capture-inbox）
和分诊（capture-triage 四路）都有机器在做，但**没有任何角色做裁减、归并与全局排序**，
导致：优先级通胀（32/35 全是 P2）、队列变仓库（尸体任务积压）、issues 修完不销案、
三份 handoff 重复登记同一件事。本 skill 是那个缺失的角色。

**模型无关声明**：本 skill 是规程型判断（分类/聚类/按规则合并/按政策排序），
Claude / Codex / Grok 任一模型均可执行，由额度分配器（选择系三轴分配器）按水位挑执行体。

## 输入（全源收口，禁漏源）

```bash
BRAIN=localhost:5221
# 1. 任务队列（queued + in_progress + blocked）
psql -U cecelia -d cecelia -c "SELECT id, priority, task_type, title, status, payload->'anchor' AS anchor, created_at FROM tasks WHERE status IN ('queued','in_progress','blocked') ORDER BY created_at"
# 2. 留箱（分诊滞留件）
psql -U cecelia -d cecelia -c "SELECT id, source_type, left(content,120), ai_reason FROM capture_atoms WHERE status='pending_review'"
# 3. 案卷（open issues——注意：issues 表不是工作队列，Brain 不派发它）
psql -U cecelia -d cecelia -c "SELECT id, priority, title, created_at FROM issues WHERE status NOT IN ('closed','resolved','done')"
# 4. 最近 handoff 的 next_steps（近 7 天）
psql -U cecelia -d cecelia -c "SELECT id, title, result->'handoff'->'next_steps' FROM tasks WHERE result->'handoff' IS NOT NULL AND updated_at > NOW() - INTERVAL '7 days'"
# 5. 产能配比政策线（主理人拍板值，decisions 查 category=invariant 关键词 产能配比）
curl -s "$BRAIN/api/brain/decisions?category=invariant" | grep -i 产能配比
```

## 职责一：清留箱

对每个 `pending_review` atom 按 `ai_reason` 标记分流：

| 标记 | 处置 |
|------|------|
| `[triage:no_journey]` | 查该源所属线是否已上图（journeys.domain 非空）——已上图→清空 ai_reason 放回分诊队列；未上图→保留，计入榜单附录"等地图"计数 |
| `[triage:gate_fail]` | 收敛成一道 A/B 拍板题（与既有铁律冲突点讲清），进榜单"待拍板"区 |
| `[triage:llm_failed / low_confidence]` | 人工判定 target_type 后走 confirm 接口重路由 |
| 无标记但滞留 >48h | 按四路规则手动补判 |

## 职责二：归并（先归并，再排序）

**第一优先信号：锚点撞格**。有 `payload.anchor` 的项按 `(journey_id, step_id)` 聚类：

- **精确撞格**（同 journey+step，语义同向）→ **自动合并**：
  1. 保留最早创建的为主任务；把其余项的增量信息（描述差异、来源引用）并进主任务 description
  2. 其余项 `status='cancelled'` + `error_message='superseded by <主任务id>（排序官归并）'`——**永不 DELETE**
  3. 主任务优先级重估：被 N 个来源指向 → 优先级上浮候选，写入榜单理由
- **无锚项**：用标题+描述做语义粗聚类（同名/同病灶词），**只出合并提案**（列在榜单"建议合并"区），不自动执行
- **尸体判定**（建议关闭区，不自动关）：staging_e2e/巡检类且其目标分支已 merge/deleted、smoke/test-probe 类、同型定时任务积压仅留最新一个

## 职责三：出榜

```markdown
# 今日榜 YYYY-MM-DD（排序官）

## Top N（建议 3-5，含一句话理由；数据安全/生产在燃类无条件置顶）
## 排队保留（不丢不抢道）
## 建议合并（模糊相似提案，等拍板）
## 建议关闭（尸体清单，等拍板）
## 待拍板（gate_fail 收敛的 A/B 题 + 配比核对）
## 附录：等地图计数 / 本轮归并流水（合并 N 项、重路由 M 项）
```

- 排序依据（按序）：①数据安全/生产在燃 ②主理人拍板过的病灶 ③产能配比政策线（业务:工厂，
  无拍板值时报告实际比例并提请拍板，不得自行发明比例）④被依赖数（blast-radius/撞格数）⑤先来后到
- 榜单挂晨报（morning-cockpit-bark 尾部），**veto_deadline 模式**：主理人不 veto 即按榜执行

## 护栏（写死，违反即本 skill 失格）

1. **永不删除**：合并=cancelled+superseded 引用链，可追溯可翻案
2. **有头 claim 的任务禁碰**（claimed_by LIKE 'interactive%' 或 executor_kind='headed-session'）
3. 模糊合并/尸体关闭**只提案不执行**，精确撞格才自动合
4. 生产敏感项（决策 57d296a1 关键词护栏）一律留人工
5. 本 skill 运行期间**禁立新任务**——排序官不能既当裁判又当运动员
6. 榜单必须报本轮归并流水（合并了什么、为什么）——归并不可静默

## 禁止事项

1. 禁跳过归并直接排序
2. 禁修改任务的 anchor（锚是执法对象不是整理对象）
3. 禁对 in_progress 任务做任何写操作
4. 禁发明产能配比数值（无拍板值→报实际+提请拍板）
