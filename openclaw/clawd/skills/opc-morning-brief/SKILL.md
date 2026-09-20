---
name: opc-morning-brief
description: "Generate OPC's daily bottom-up operating brief from verified work-item evidence through Capability, Value Stream, Portfolio, and company conclusions. Use for morning reports, business operating reviews, capability health rollups, cross-agent status aggregation, or any request that requires drill-down from an executive conclusion to its source evidence."
---

# OPC Bottom-up Morning Brief

Build the report from evidence upward. Never draft the executive summary first.

Read:

- `references/taxonomy.md` for the hierarchy and capability map.
- `references/report-template.md` for fields, rollup rules, and output order.

## Workflow

1. Set the cutoff to report time in `Asia/Shanghai`; default evidence window is the previous report cutoff through now.
2. Load `/Users/administrator/openclaw-root/workspaces-root/clawd/OPC-OPERATING-MODEL.md` when present. It overrides the bundled taxonomy for company-specific additions, without weakening evidence rules.
3. Ask the configured specialists for fresh evidence using explicit `agentId`, **strictly one at a time (serial)**: spawn one specialist, then WAIT FOR IT INSIDE THE SAME TURN (poll its status; do NOT end your turn to wait — a cron run whose parent turn ends cannot be woken again: subagent announce fails with retry-limit, verified 2026-09-01). Give each specialist a hard budget of about 4 minutes; if it has not finished by then, record that line as GREY and move on to the next. Never run two or more specialists concurrently — five concurrent specialist sessions exhausted the gateway container memory cgroup (6 GiB) and were OOM-killed twice on 2026-09-01, which killed the brief itself:
   - `infra`: Gateway, channels, nodes, servers, backups, alerts, incidents.
   - `people`: task ledger, owners, deadlines, commitments, blockers, workload.
   - `media`: content pipeline, publishing, analytics, leads, account risks.
   - `dev`: repositories, commits, branches, tests, CI, releases, engineering blockers.
   - `fde`: opportunities, discovery, designs, deployments, evaluations, acceptance, handover.
4. Give every specialist the same evidence contract: return atomic observations with source, timestamp, owner, status, delta, blocker, next action, and evidence reference. Require `unknown` when a field cannot be verified.
5. Wait for the current specialist within the same turn before spawning the next; NEVER yield or end the turn while work remains — the entire workflow (all specialists + all report files in step 7) must complete inside one continuous turn. If a specialist fails or times out, record that capability as `GREY`; do not infer health from silence.
6. Normalize and deduplicate evidence. A task, incident, commit, deployment, content item, or lead should appear once at the lowest appropriate level.
7. Write LAYERED reports — one per department line, plus one company rollup (决策 2026-09-01：老板只看一页总览，明细分线存放):
   - Per-line reports: for each specialist, write that line's daily report to `/Users/administrator/openclaw-root/workspaces-root/clawd/reports/morning/YYYY-MM-DD/<agentId>.md` (agentId = infra|people|media|dev|fde). Structure per line: 状态灯 (RED/AMBER/GREEN/GREY, worst material item), 昨天完成（带证据引用）, 今天计划, 阻塞与需决策（owner + next action）, then that line's own Evidence Ledger table. ALL detail and evidence tables live here, never in the company file.
   - Company rollup: write `/Users/administrator/openclaw-root/workspaces-root/clawd/reports/morning/YYYY-MM-DD/company.md` — ONE SCREEN MAXIMUM. Contents, in order: (a) a status table with exactly one row per line: 部门 | 状态 | 昨天关键结果（一句话）| 今天关键动作（一句话）| 阻塞/待决策（一句话或无）; (b) 需要老板决定 section, at most 3 items, each one sentence with owner; (c) 数据缺口 one sentence naming which lines returned no evidence. NO evidence tables, NO capability matrices, NO per-item detail in this file — details belong in per-line files.
8. Do NOT write the legacy single-file `/Users/administrator/openclaw-root/workspaces-root/clawd/reports/morning/YYYY-MM-DD.md` anymore; the directory layout in step 7 replaces it. The HTML publisher renders the directory automatically within 10 minutes.
9. Final reply to the channel must be a SHORT digest only — NEVER paste the full report into the reply (it renders as an unreadable wall in Feishu). The full report is published automatically as HTML at https://docs.zenjoymedia.media/morning-brief/ (rendered from the saved Markdown within 10 minutes). Digest format, max ~15 lines:
   - 标题行：OPC 晨报 YYYY-MM-DD
   - 数据完整度一句话（哪些 Agent 返回了证据、哪些 GREY）
   - RED 数量 + 逐条一句话（没有则写 无）
   - AMBER 数量 + 最多 3 条最重要的
   - 需要老板决定的事项（最多 3 条；没有则写 无）
   - 结尾：完整报告 → https://docs.zenjoymedia.media/morning-brief/

## Evidence Rules

- Use observed data, not remembered impressions.
- Cite an evidence identifier on every non-trivial capability claim.
- Mark stale evidence explicitly. Default freshness limits: infrastructure 24h; tasks and delivery 48h; media metrics 72h; strategic reference data 7d.
- `No data` is `GREY`, never `GREEN`.
- Separate `fact`, `inference`, and `recommendation`.
- Do not expose credentials, tokens, private message contents, or unnecessary personal data.
- Read-only collection is allowed. Do not publish content, message employees, deploy, restart, rotate credentials, or change task ownership while producing the report.

## Rollup Rules

- `RED`: critical outage, security/data risk, missed critical commitment, or blocked delivery with material impact.
- `AMBER`: degraded, overdue, blocked, freshness concern, or incomplete evidence affecting confidence.
- `GREEN`: all critical child items have fresh evidence and no red/amber condition.
- `GREY`: insufficient or stale evidence.
- Parent status is the worst material child status. Explain any exception explicitly; never average away a red item.

## Quality Gate

Before returning, verify:

- Every Portfolio contains Value Streams; every Value Stream contains Capability lines; every Capability points to evidence.
- Every red or amber line has an owner or an explicit owner gap, plus a next action.
- The company conclusion mentions only facts supported below it.
- Missing sources appear in a data-quality section.
- The report distinguishes yesterday's completed work, today's planned work, current blockers, and decisions needed from the owner.


## Approval Health Row (added 2026-09-02, blueprint phase 1 — append-only amendment)

The company rollup (company.md) must additionally include, after the status table:
- One line 审批健康: 昨日老板层审批量 / 平均等待时长 / 批准率 — computed by reading the 「OPC 经营对象」 table (app_token=Z1oobsDYbaUpcFsTjwWcx8Bmnge, table_id=tbliqtUekfBVWrjw) 结果记录 timestamps for objects that left 等审批 in the last 24h. If 批准率 has been >95% for 7 consecutive days, mark this line AMBER with note 「审批可能已橡皮图章化」. If data is insufficient, mark GREY — never fabricate.
- One line 昨日成本: token/费用 usage if a reliable source is available; otherwise GREY with 「计量管道未建」. Never estimate without a source.
