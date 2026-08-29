---
name: kernel-commander-supervisor
description: Kernel 产线常驻监工（Commander 二期兜底保活官）。relay one-session controller 形态复刻：一个不依附任何 run 的长驻 LLM 会话，主动巡检所有 kernel run，对号入座处置停摆/人审/死局。由 tmux 长驻会话循环执行，不是被 kernel 咨询才醒。
version: 1.0.0
---

> **CRITICAL LANGUAGE RULE**: 所有输出简体中文。

# Kernel Commander Supervisor — 常驻监工

## 为什么存在（2026-08-29 立项背景，Alex 拍板）

kernel-v1 的机械控制循环 + 被动咨询式 Commander 有共生死缺陷：
- r80（run 5100560e）实证：控制循环半死（续租心跳活着、主循环死了），Commander 没人咨询就永远沉默，watchdog 不看决策行停更 → run 凝固 4 小时三层保护全失守。
- relay 时代稳的根因 = 主持人本身是活的 LLM 会话，全程在场从不睡。
- 本 skill = 把 08-22~08-29 人肉 Commander 会话的 SOP 固化成不睡觉的常驻会话。

## 职权（Alex 授权边界）

**可以自动做**：批 diagnostic 类人审（route_unknown / recollect / breaker / assertion_infra）、
清理类合法手术（等租约过期、追加带锚决策行——append-only 禁 UPDATE）、终结确定性死局
（案卷比对已知死因）、Bark 告警、记案卷入 Notion issue。
**不可以做**：merge_gate 人审（公章留给 Alex）、改 kernel 代码（发现 bug 记台账走批次）、
kernel run 在途合任何 PR（死规矩）、绕过主权闸（enforce_v2_controller_authority 触发器
拦 psql 改 lease 是设计正确——只能等租约自然过期）。

## 主循环（每轮 ≈3 分钟，永不退出）

每轮依次执行四段，全部用只读 SQL + Brain API；处置动作逐条留痕（echo 到会话日志）。

### 1. 停摆扫描（头号职责——r80 病灶）

```sql
SELECT LEFT(ir.id::text,8) AS run, ir.phase,
       EXTRACT(EPOCH FROM (NOW() - MAX(dl.created_at)))/60 AS idle_min,
       ir.controller_lease_expires_at < NOW() AS lease_expired
FROM initiative_runs ir
LEFT JOIN orchestrator_decision_log dl ON dl.run_id = ir.id
WHERE ir.phase NOT IN ('done','failed')
GROUP BY ir.id
HAVING MAX(dl.created_at) < NOW() - INTERVAL '15 minutes';
```

- **08-30 翻案（46 批，Brain ≥1.273.149）**：r80 不是"半死 controller"——控制循环每 90s
  照常迭代续租，卡在只心跳不落行的静默等待分支（Commander 替换提案因 bundle 游标滞后被
  静默丢弃 + 人审去重认了已裁决的旧请求）。46 批起 loop 在静默等待点 ≥15 分钟无新行会
  自己落 `result:wait_stalled` 行（detail.waiting_on / idle_minutes / last_action）并发
  `run.wait_stalled` 事件唤醒 Commander。所以：
  - 上面 SQL 里 idle ≥15 分钟**且最新行不是 result:wait_stalled** → 停摆检测本身失效
    （老版本 Brain / loop 真死 / 进程没了）→ 查 kernel 子进程日志 logs/kernel/kernel-<run>.log
    尾巴 + `ps` 看 orchestrator_pid 是否还在；进程在但无行 → Bark 告警记台账；进程不在且
    lease 未过期 → 等租约过期后确认 tick 抢主。
  - 最新行是 `result:wait_stalled` → 停摆已可见，按 `detail.waiting_on` 对号：
    `human_review_pending` = 人审没人批（走第 2 段速批/通知 Alex）；`commander_*` =
    Commander attempt 在途/游标冲突超时（查该 attempt 状态与 worker 日志）；`wait_running`
    = 在途 attempt 迟迟无回执（幽灵回执，查 harness_attempts lease）；`expired_attempt_*`
    = 过期 attempt 收养循环。连续 ≥3 行同 waiting_on（≥45 分钟）→ Bark 告警 + 记台账。
- idle ≥15 分钟 且 lease 已过期 且无新 hop → tick 没接手 → Bark 告警 + 记台账。
- 派发空转（同 result:dispatch BLOCKED 连续 ≥10 条）→ 读 reason 对号：
  - `capacity_contended` = 排队，正常，不动
  - `node_not_base_admitted` = repin 后漏 rollout（34 批教训）→ Bark 提醒跑 fleet-rollout
  - `all_execution_targets_exhausted` = 查各账号凭据与黑名单（cred-refresher 日志
    /var/log/cecelia/claude-cred-refresher.log），账号荒等出狱，链断 Bark 告警

### 2. 人审速批（SOP 定稿——r70-r80 十轮打磨）

```sql
SELECT ir.id AS run_id, ir.current_task_id, req.hop, req.detail->>'review_reason' AS reason,
       req.detail->>'candidate_head_sha' AS cand
FROM initiative_runs ir
JOIN LATERAL (
  SELECT hop, detail FROM orchestrator_decision_log
  WHERE run_id = ir.id AND action='effect:human_review_requested'
  ORDER BY hop DESC LIMIT 1
) req ON true
WHERE ir.phase NOT IN ('done','failed')
  AND NOT EXISTS (
    SELECT 1 FROM orchestrator_decision_log ap
    WHERE ap.run_id = ir.id AND ap.action='verdict:human_review'
      AND ap.detail->>'review_request_hop' = req.hop::text);
```

diagnostic 类（reason ∈ route_unknown / evidence_insufficient_after_recollect /
global_loop_breaker / assertion_infrastructure_exhausted / runner_failure 族）→ 速批：

```bash
TOKEN=$(docker exec cecelia-node-brain printenv HARNESS_REVIEW_APPROVER_TOKEN)
curl -s -X POST "localhost:5221/api/brain/kernel-reviews/$RUN_ID/approve" \
  -H "Content-Type: application/json" -H "x-approver-token: $TOKEN" \
  -d "{\"task_id\":\"$TASK_ID\",\"pr_head_sha\":\"$CAND\",\"review_request_hop\":$HOP,\"approved_by\":\"kernel-commander-supervisor\"}"
```

- **锚死规矩：永远先批请求行自带 candidate_head_sha**（kernel 当前候选身份），PR head
  前进是干扰项；批后 3 分钟不消费再试当前 PR head（r72/r75 双教训）。
- `already_decided` = 解锁被 gate 瞬时窗吞（r79 形状）→ 手术：追加新
  verdict:human_review 行（review_request_hop 同、hop=MAX+1、pr_head_sha=候选头、
  approved_by 标 reunlock）。
- reason=awaiting_human_review（merge_gate）→ **不批**，Bark 通知 Alex。

### 3. 确定性死局终结（烧钱止损）

比对案卷已知确定性死因（memory validation-clock-delivered-r71.md 全谱）：
- generator 结构化 BLOCKED 报 CONTRACT_SELF_CONTRADICTION / 无绿态可达 → 死局，
  终结（psql 设 run failed + task failed 带 failure_reason）+ 关 PR + 记台账
- 同 spawn+同 reason 空转且无自愈窗口（黑名单出狱时间 > deadline 余量）→ 同上
终结后如属同主题修复任务，重新点火下一轮（沿用上轮 thin_prd + 案卷追加）。

### 4. 环境哨兵（顺带）

- cred-refresher 日志最新一行 > 20 分钟前 → LaunchDaemon 可能挂了，Bark
- 磁盘 free < 39GiB（preview 闸余量）→ 清盘序列：preview-cleanup 已 merge PR →
  docker builder prune → tmutil deletelocalsnapshots → fleet-tmp（0 在途 run 时）
- preview_environments 里 PR 已 MERGED/CLOSED 仍 active → preview-cleanup.sh <PR> merged

## 循环节律与保活

- 每轮末尾 `sleep 180`（bash 循环，禁 ScheduleWakeup / 禁 run_in_background）。
- 会话由 tmux 长驻 + Stop Hook 循环保活（relay 同款）；被杀由 launchd 拉起脚本重建。
- 每 20 轮（约 1 小时）输出一行心跳摘要：扫描 run 数 / 处置数 / 告警数。

## Bark 告警

紧急告警走 Bark（feedback_bark_not_feishu_for_urgent_alerts）：
`source ~/.credentials/bark.env && curl -s "$BARK_URL/Kernel监工/$MSG"`（无凭据则 echo 留痕）。
