---
name: line-report
version: 1.0.0
description: 按业务线（Line/Journey）维度生成经营日报/周报/月报：每条 Line 当期完成了多少任务、做了多少决策、合并了多少 PR，并与上一周期环比（今天 vs 昨天、本周 vs 上周、本月 vs 上月）。数据源 Brain API（localhost:5221）。只要用户想看"每条 Line 今天/这周/这个月干了什么"、"Line 2 和 Line 4 的日报"、"今天完成了多少任务做了多少决策"、"各条线进展汇总"、"经营日报"，哪怕没说"line-report"原词，都要触发本 skill。注意区分：客户销售日报（Line04 客服复盘）走 daily-report，CI 健康巡检走 ci-patrol，本 skill 是任务/决策维度的 Line 经营报告。
---

# Line 经营报告（日报/周报/月报）

> **语言规则：所有输出简体中文。**

为每条业务线（Line = Brain 的 journey）生成一份经营报告，回答主理人的核心问题：
**这条线今天/这周/这个月干了什么？和上一个周期比是快了还是慢了？**

与相邻 skill 的分工：
- `daily-report` = Line04 客户销售复盘日报（客户维度），不是这里。
- `ci-patrol` = CI/测试健康度巡检（工程质量维度），不是这里。
- 本 skill = **任务完成量 + 决策产出 + PR 合并**的经营维度，跨所有 Line。

## Step 0：确定周期与范围

从用户输入判断：
- 周期：`daily`（默认）/ `weekly` / `monthly`。"日报"→daily，"周报"→weekly，"月报"→monthly，没说就 daily。
- Line 范围：用户点名（如"Line 2 和 Line 4"）→ 只报点名的；没点名 → 报所有活跃 Line。
- Line 编号 ↔ journey 名称映射见 `references/line-registry.md`（用户说"Line 2"时先查这张表翻译成 journey 名称）。

## Step 1：拉数据（跑取数脚本，不要手工 curl 拼数据）

取数脚本全文在 `references/fetch-script.md`（本仓库政策：skill 不放 .py 文件，代码以 markdown 内联块保存）。执行方式：

1. 读 `references/fetch-script.md`，把其中唯一的 python 代码块原样写到 scratchpad（如 `<scratchpad>/fetch_line_data.py`）。
2. 运行：

```bash
python3 <scratchpad>/fetch_line_data.py --period daily
# 可选：--period weekly|monthly
# 可选：--lines "客户智能获客路径,客户私域 AI 接管"（journey 名称，逗号分隔）
# 可选：--date 2026-07-12（报告基准日，默认今天，时区 Asia/Shanghai）
```

不要即兴改写脚本逻辑（窗口口径、排除规则都是有意设计的）；脚本报错才允许修，修完把差异反馈给用户。

脚本输出一个 JSON（stdout），关键结构：

- `lines[]`：每条活跃 Line 的 `current` / `previous` 两个窗口的聚合——`tasks_completed`、`prs_merged`、`tasks_in_progress`、`completed_task_titles`。
- `decisions.current[]`：当前窗口新增的决策（topic + 摘要 + `attributed_line`，硬字段归属不到时为 null）。
- `decisions.previous_count`：上一窗口决策总数（用于环比）。
- `unattributed_tasks[]`：窗口内完成、但硬字段归属不到任何 Line 的任务。

脚本只做**硬字段归属**（task 的 `payload.journey_id` / `ability_id` → journey）。归属不到的任务和决策原样吐出来，交给 Step 2。

## Step 2：语义归属补齐（AI 的活）

Brain 里大量 tasks/decisions 没挂 `journey_id`（元数据卫生债，line-strategist 同款问题）。归属纪律与它保持一致：

1. **先信硬字段**——脚本已经做了，不要推翻。
2. `unattributed_tasks` 和 `decisions.current` 里 `attributed_line` 为 null 的条目，按标题/topic/决策文本做语义推断归属到某条 Line（对照 `references/line-registry.md` 的关键词列）。
3. **推断归属的条目必须标注"（归属靠语义推断）"**，不许冒充硬数据。实在推断不出的归入报告的"未归属"一节，不许静默丢弃——静默丢弃会让日报总数对不上 Brain 实际发生量，主理人会失去对报告的信任。

## Step 3：输出报告

按 `references/report-template.md` 的模板输出。核心结构：

1. **总览表**：每条 Line 一行——完成任务数（环比±）、决策数、PR 合并数、进行中任务数。
2. **分 Line 明细**：每条有动静的 Line 一节，列完成的任务标题、相关决策、环比一句话（"比昨天多完成 2 个任务"）。没动静的 Line 合并成一行"本期无产出：Line X、Line Y"。
3. **未归属**：语义也归不了的任务/决策清单（顺带提醒元数据卫生债在涨还是在还）。
4. **数据口径**脚注：完成 = `completed_at` 落在窗口内；决策 = `created_at` 落在窗口内且 status=active；PR = `pr_merged_at` 落在窗口内。

报告默认直接输出在对话里。用户要落盘/发飞书/放 dashboard 时才做，走对应 skill（docs-center / dashboard-deploy），本 skill 不自带发布逻辑。

## 无头模式（Brain 定时触发）

task description 含 `[LINE_REPORT]` 时为无头模式：不提问，按 payload 里的 `period` 直接跑全部活跃 Line，输出 markdown 后通过 db-update skill 写一条 AI Note（type=report）。没有 `payload.period` 就默认 daily。

## 常见坑

- **别用不带 status 的 tasks 列表数数**：`GET /api/brain/tasks?limit=N`（无 status 过滤）缺 `payload`/`completed_at` 字段且截断在旧数据；带 `status=` 过滤才返回全字段并按 updated_at 降序，脚本用的是后者。
- **completed_at 大面积缺章**：约 3/4 的 completed 任务没盖 `completed_at`（数据卫生债），脚本用 `updated_at` 兜底并在 `fallback_ts_count` 里计数——报告口径脚注要如实写"其中 N 条按 updated_at 估算"。
- **窗口用 Asia/Shanghai 自然日/周/月**，不是滚动 24h。周 = 周一起算；月 = 自然月。环比窗口等长紧邻（昨天/上周/上月）。
- **smoke/废弃 journey 要排除**：名称含 `[smoke]`、`[v1]`、`gp-agg-smoke` 或 status=deprecated 的不算 Line（脚本已排除，语义归属时也不要归给它们）。
