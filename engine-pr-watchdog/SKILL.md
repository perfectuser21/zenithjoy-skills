---
name: engine-pr-watchdog
version: 3.5.1
updated: 2026-11-04
description: PR 合并守卫。任何 PR 开完后立刻调用，监控所有 repo 的 open PR，阻塞轮询 CI + 合并状态，CI 失败自动修复，直到全部 PR 合并才退出。不使用 ScheduleWakeup，不提前 exit。
trigger: 任何 PR 开完之后（gh pr create 之后），立刻调用本 skill。engine-ship 完成后也调用。
---

> **CRITICAL LANGUAGE RULE**: 所有输出简体中文。

## 职责

监控所有 repo 的 open PR，**全程阻塞不退出**：
- CI 失败 → 自动诊断修复 → 继续轮询
- CI 通过但未 merge → 确认 auto-merge 已启用 → 继续轮询
- 分支 BEHIND → rebase → 继续轮询
- 已 merge → 清理 + **写 handoff 交接单（三入口统一终态）** → 继续看下一个 PR
- 全部合并 → 退出
- **禁止使用 ScheduleWakeup。禁止提前 exit。**

---

## Step 1: 确定监控目标

优先从调用上下文拿 PR 号和 REPO。没有的话，直接查所有 repo 的 open PR：

```bash
WATCH_REPOS="perfectuser21/cecelia perfectuser21/zenithjoy-workspace perfectuser21/zenithjoy-skills"
for REPO in $WATCH_REPOS; do
  gh pr list --repo "$REPO" --json number,headRefName,title \
    --jq '.[] | "\(.number) \(.headRefName)"' 2>/dev/null \
    | while read num branch; do
      echo "REPO=$REPO PR=$num BRANCH=$branch"
    done
done
```

对每个找到的 PR 执行 Step 2。若没有任何 open PR → 直接退出。

---

## Step 2: 阻塞轮询主循环

> **工具限制**：Bash 工具 timeout 硬上限为 600000ms（10 分钟）。这不是轮询时长，只是单次调用上限。
>
> **核心规则**：每次 Bash 调用结束后（无论是超时、CI 失败还是 BEHIND），Claude 必须立刻检查退出码并决定下一步。**只要 PR 未合并/关闭，就必须立刻发起下一次 Bash 调用，不得输出文字给用户，不得结束 turn。** Stop Hook 只在 turn 结束时触发——只要 Claude 一直在发 tool call，session 就不会中断。
>
> **禁止 run_in_background**：本 skill 的所有 Bash 调用（包括 git push、git rebase）必须**同步执行**，绝不使用 `run_in_background: true`。后台执行会导致 turn 结束，Stop Hook 触发，轮询循环断裂。

**退出码：**
- `0` = 已读到 PR 合并或关闭 → Step 5 再次验真；MERGED 记 completed/PASS，CLOSED 记 failed/FAIL
- `10` = CI 失败 → 执行 Step 3 修复，修完后**立刻重新进入 Step 2**
- `11` = 分支 BEHIND → 执行 Step 4 rebase，完成后**立刻重新进入 Step 2**
- `12` = 状态未知（API 错误、检查缺失或格式异常）→ 保持任务未完成，恢复状态读取后重新核验；不得当作已合并、CI 测试失败或继续合并的依据
- 超时（Bash call 到 10 分钟）→ **立刻重新发起 Step 2 的 Bash 调用，不输出任何文字**

```bash
PR_NUMBER=<PR号>
REPO=<owner/repo>          # 如 perfectuser21/cecelia
WORKTREE_PATH=<worktree路径>
DEV_MODE_FILE=<.dev-mode文件路径>
MAX_FIXES=3
# FIX_COUNT 持久化到文件，防止 Bash 重新调用时计数归零
FIX_COUNT_FILE="/tmp/watchdog-fix-count-${PR_NUMBER}"
FIX_COUNT=$(cat "$FIX_COUNT_FILE" 2>/dev/null || echo 0)

echo "🔍 开始监控 PR #$PR_NUMBER ($REPO)"

while true; do
  # ── 检查是否已合并 ──────────────────────────────
  if ! STATE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json state --jq '.state' 2>/dev/null); then
    echo "CI_UNKNOWN: 无法读取 PR 状态，不能判定已合并" >&2
    exit 12
  fi
  case "$STATE" in
    OPEN|MERGED|CLOSED) ;;
    *) echo "CI_UNKNOWN: PR 状态缺失或未知" >&2; exit 12 ;;
  esac
  if [ "$STATE" = "MERGED" ]; then
    echo "✅ PR #$PR_NUMBER 已合并，退出轮询"
    rm -f "$FIX_COUNT_FILE"
    break
  fi
  if [ "$STATE" = "CLOSED" ]; then
    echo "ℹ️ PR #$PR_NUMBER 已关闭（用户手动），退出轮询"
    break
  fi

  # ── CI 轮询（共享脚本，sleep 30 在脚本内）───────
  POLL_EXIT=0
  bash ~/perfect21/zenithjoy-skills/scripts/ci-poll.sh "$PR_NUMBER" "$REPO" || POLL_EXIT=$?

  if [ "$POLL_EXIT" -eq 10 ]; then
    if [ "$FIX_COUNT" -ge "$MAX_FIXES" ]; then
      echo "🚨 连续修复 $MAX_FIXES 次仍失败，需要人工介入"
      rm -f "$FIX_COUNT_FILE"
      exit 10
    fi
    FIX_COUNT=$((FIX_COUNT+1))
    echo "$FIX_COUNT" > "$FIX_COUNT_FILE"
    echo "❌ CI 有失败（第 $FIX_COUNT 次）"
    exit 10
  fi

  if [ "$POLL_EXIT" -eq 11 ]; then
    echo "📦 分支落后 main，需要 rebase"
    exit 11
  fi

  if [ "$POLL_EXIT" -ne 0 ]; then
    echo "CI_UNKNOWN: 无法确认检查通过（exit=${POLL_EXIT}），不进入合并" >&2
    exit "$POLL_EXIT"
  fi

  # ── CI 全绿：确认 auto-merge ─────────────────────
  AUTO_MERGE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json autoMergeRequest --jq '.autoMergeRequest' 2>/dev/null)
  if [ "$AUTO_MERGE" = "null" ] || [ -z "$AUTO_MERGE" ]; then
    gh pr merge "$PR_NUMBER" --repo "$REPO" --auto --squash 2>/dev/null && echo "✅ auto-merge 已启用"
  fi

  sleep 30
done
```

---

## Step 3: CI 失败自动修复（退出码 10 时执行）

### 3a. 读取失败日志

```bash
RUN_ID=$(gh pr checks "$PR_NUMBER" --repo "$REPO" --json name,conclusion,databaseId 2>/dev/null \
  | jq -r '[.[] | select(.conclusion=="failure")] | sort_by(.databaseId) | last | .databaseId // empty')
gh run view "$RUN_ID" --repo "$REPO" --log-failed 2>/dev/null | tail -200
```

### 3b. 在 worktree 里修复

```bash
cd "$WORKTREE_PATH"
# 分析日志 → 定位根因 → 修改文件
git add -A
git commit -m "fix(ci): <原因简述>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push origin HEAD
```

修复 fix_count + 1，**重新进入 Step 2 主循环**（不退出）。

若 fix_count ≥ 3：
```
Skill({"skill":"superpowers:systematic-debugging"})
```
然后停止。

---

## Step 4: 分支 BEHIND 处理（退出码 11 时执行）

> **绝对禁止 run_in_background**：本 Step 所有命令必须**同步执行**（不设 `run_in_background: true`）。push 命令返回后，必须**立刻在同一个 turn 内**重新进入 Step 2，不得输出任何文字，不得结束 turn。

```bash
cd "$WORKTREE_PATH"
git fetch origin main
git rebase origin/main
git push origin HEAD --force-with-lease
echo "rebase+push 完成，立刻重新进入 Step 2 轮询"
```

push **同步返回**后，**不输出任何文字，立刻发起下一次 Step 2 的 Bash 调用**（不退出，不结束 turn）。

---

## Step 5: 合并后清理

```bash
# 清理前再次验真；只有精确终态才可清理或写任务账本。
if ! FINAL_STATE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json state --jq '.state' 2>/dev/null); then
  echo "CI_UNKNOWN: 清理前无法读取 PR 状态" >&2
  exit 12
fi
case "$FINAL_STATE" in
  MERGED|CLOSED) ;;
  *) echo "CI_UNKNOWN: PR 尚未到可确认终态，不清理、不回写" >&2; exit 12 ;;
esac

# 读取 task_id
TASK_ID=$(grep "^task_id:" "$DEV_MODE_FILE" 2>/dev/null | awk '{print $2}')
PR_URL="https://github.com/${REPO}/pull/${PR_NUMBER}"

# MERGED 才 completed/PASS；关闭未合并只能 failed/FAIL。
if [ -n "$TASK_ID" ] && [ "$TASK_ID" != "unknown" ]; then
  if ! PATCH_BODY=$(python3 - "$TASK_ID" "$FINAL_STATE" "$PR_URL" <<'PY'
import datetime, json, sys
id, state, url = sys.argv[1:]
merged = state == "MERGED"
handoff = {
    "schema_version": 1, "task_id": id,
    "initiative_id": None, "journey_id": None,
    "title": "PR 终态验真", "verdict": "PASS" if merged else "FAIL",
    "done": ["已独立回读 PR 终态: " + state],
    "not_done": [] if merged else ["PR 已关闭且未合并，未完成代码交付"],
    "next_steps": [{"kind": "note", "title": "PR 已合并" if merged else "PR 关闭未合并；保留失败交接"}],
    "data_sources": [url], "decision_refs": [],
    "artifacts": {"pr_urls": [url], "docs": []},
    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
print(json.dumps({"status": "completed" if merged else "failed", "result": {
    "actor": "engine-pr-watchdog", "merged": merged, "closed": not merged,
    "pr_state": state, "pr_url": url, "handoff": handoff,
}}))
PY
  ); then
    echo "CI_UNKNOWN: 无法生成终态回执" >&2
    exit 12
  fi
  if ! curl -sf -X PATCH "localhost:5221/api/brain/tasks/$TASK_ID" \
    -H "Content-Type: application/json" -d "$PATCH_BODY"; then
    echo "CI_UNKNOWN: 任务终态回写失败，保留工作树" >&2
    exit 12
  fi
fi

# 状态已验真且回执已交付，才清理对应工作树。
git -C "$WORKTREE_PATH" worktree remove "$WORKTREE_PATH" 2>/dev/null \
  && echo "✅ worktree 已清理" || echo "⚠️ worktree 清理失败（可能已不存在）"
echo "PR #${PR_NUMBER} 终态 ${FINAL_STATE} 收尾完成"
```

### Step 5.5: 补充 handoff 交接单（三入口统一终态）

Step 5 已按验真的终态写入最小 handoff。补充产物与交接时保留该 verdict：关闭未合并必须 FAIL，不得覆盖为 PASS；Step 5 返回 12 时不执行收尾。

> **规矩（Alex 2026-07-06 拍板）**：/dev 三条路径（A Bug / B 小改动 / C Harness）的落尾都必须是
> handoff。路径 C 由 harness reportNode 自动产；路径 A/B 的公共尾巴就是本 skill——merge 确认后
> 在这里产。**没有下一步就在 next_steps 写「完成，无下一步」，不要在对话里催用户"现在就改吗"。**
> 协议 = packages/brain/src/handoff.js + lib/relay-baton.js：tasks.result.handoff（SSOT）+ docs/handoffs/ 镜像。
>
> **next_steps 每条必须是带 kind 的对象（主理人 2026-10-11 决策，四类）**：
>
> | kind | 含义 | Brain 怎么处理 |
> |---|---|---|
> | `resume_headed` | 有头续接：要人在场/有头会话接着做 | **不派发**；原任务 `result.pending_resume` 挂「待续」，新有头会话开场 `GET /api/brain/handoffs/pending-resume` 能拉到，接上后 `POST /api/brain/handoffs/pending-resume/<task_id>/ack` 销账 |
> | `dispatch_headless` | 无头派发：机器可以自己做完 | 自动建 queued 子任务挂同一条链（旧值 `task` 等同） |
> | `decision` | 待主理人拍板 | 写 decisions 表 status=pending，链停在这里 |
> | `note` | 备注/留痕 | 只留痕（旧值 `done` 等同；「完成，无下一步」恒为 note） |
>
> 不标 kind 的后果：有头任务（/dev 有头会话都是）默认当 `resume_headed`，无头任务默认当 `note`。
> 写入 API 会在响应 `handoff_next_steps.coerced` 里列出每条被当成了什么，**看到 unrecognized 要改正重写**。

用 python3 按协议双写（TASK_ID 从 .dev-mode 拿；内容由你根据本次 PR 实际情况填写，禁止套空话）：

```python
# python3 - <<'EOF' 形式执行；镜像目录 = <主仓>/docs/handoffs/
import json, subprocess, datetime, os
h = {
  "schema_version": 1,
  "task_id": TASK_ID,                # .dev-mode 的 task_id
  "initiative_id": None, "journey_id": JOURNEY_ID_OR_NONE,
  "title": PR_TITLE, "verdict": "PASS",   # 未合并被关/放弃 → FAIL，同样必须写
  "done": [...],                     # 本次真正交付了什么（面向下一个大脑，不是给人客套）
  "not_done": [...],                 # 显式声明范围外/遗留（没有写 []）
  "next_steps": [                    # 每条带 kind；没有下一步 → [{"kind":"note","title":"完成，无下一步"}]
    {"kind": "resume_headed", "title": "...", "detail": "有头会话接手要知道的上下文"},
    {"kind": "dispatch_headless", "title": "...", "detail": "...", "task_type": "dev", "change_kind": "bugfix"},  # 改代码才带 change_kind（new_capability|capability_change|bugfix|parameter_only）
    {"kind": "decision", "title": "要主理人拍板的问题", "detail": "选项与影响"},
    {"kind": "note", "title": "..."},
  ],
  "data_sources": [...],             # 下一个大脑要加载的文件/表/键
  "decision_refs": [...], 
  "artifacts": {"pr_urls": [PR_URL], "sprint_dir": None, "branch": BRANCH, "docs": []},
  "created_at": datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
}
# 走 Brain API（生产 Brain 在 us-vps，本机 5221 直达）：PATCH 补写 result.handoff 会触发接棒
# （dispatch_headless 建子任务 / decision 建待拍板 / resume_headed 挂待续）。不要再 psql 直写本地库。
import urllib.request
req = urllib.request.Request(f"http://localhost:5221/api/brain/tasks/{h['task_id']}", method='PATCH',
  data=json.dumps({"result": {"handoff": h}}, ensure_ascii=False).encode(), headers={'Content-Type': 'application/json'})
resp = json.load(urllib.request.urlopen(req, timeout=15))
fb = resp.get('handoff_next_steps') or {}
print('handoff 已写；各条 kind =', fb.get('kinds'), '；被改判 =', fb.get('coerced'), '；接棒 =', resp.get('relay'))
if fb.get('unrecognized'): raise SystemExit(f"next_steps 有认不出的 kind，改正后重写: {fb['unrecognized']}")
# 镜像 markdown：格式照 handoff.js renderHandoffMarkdown（# Handoff：标题 + 完成/没完成/下一步/数据源/决策引用/产物指针）
# 文件名 docs/handoffs/<YYYYMMDDHHmm>-<task_id前8>.md
EOF
```

要求：
1. **PASS/FAIL 都写**——PR 被关闭/放弃也要 FAIL handoff，说明为什么
2. TASK_ID 缺失（.dev-mode 无 task_id）→ 跳过 DB 写，只写 docs/handoffs/ 镜像并在文件里注明 task_id=unknown
3. 写完 handoff 才算本 PR 真正收尾；多 PR 场景每个 PR 各写各的
```

### Step 5.6: 自杀式 tmux 关窗（全部 PR 都收尾完之后，真正最后一步）

> **背景**：有头派发的 tmux 会话跑完任务（handoff 写好 + Brain task status=completed）后不会自己关掉所在的 tmux 窗口，全靠控制会话手动 `send-keys /exit` + `tmux kill-session` 才能收尾。2026-07-08/09 派发的 T2/T3/T4 三个任务就因为控制会话没盯到底，空转了两天没人关。
>
> 只在**所有活跃 PR 都已 MERGED/CLOSED、Step 5.5 handoff 全部写完**之后执行一次，绝不能在轮询循环中途触发——杀早了会把还没收尾完的会话一起带走。

```bash
if [ -n "$TMUX" ]; then
  SESSION_NAME=$(tmux display-message -p '#S' 2>/dev/null)
  if [ -n "$SESSION_NAME" ]; then
    (sleep 2 && tmux kill-session -t "$SESSION_NAME") >/dev/null 2>&1 &
    disown
    echo "✅ 已安排 2 秒后自杀 tmux 会话: $SESSION_NAME（收尾完成，自动关窗）"
  else
    echo "⚠️ tmux 环境检测到但无法读取会话名，跳过自动关窗（非阻塞）"
  fi
else
  echo "ℹ️ 非 tmux 会话，跳过自动关窗步骤"
fi
```

延迟 2 秒 + 后台 + `disown` 是为了让上面这句 echo 先正常输出完，不被 kill-session 截断；tmux 不存在或读不到会话名一律降级为提示，不阻塞本 skill 的收尾判定。

---

## 防护规则

1. **禁止 ScheduleWakeup**：任何情况下不得调用 ScheduleWakeup，用 bash sleep loop 代替
2. **禁止提前 exit 0**：只有合并/关闭/fix_count≥3 才能退出
3. **Bash timeout 设 600000**：单次轮询最长 10 分钟，超时后立即再发起一次
4. **无 worktree 也能轮询**：找不到 worktree 时跳过修复步骤，仍持续轮询合并状态
5. **`gh pr list` 返空 = 已合并**：视为正常退出

---

## 完成标志

所有活跃 PR 均为 MERGED 或 CLOSED，worktree 已清理，Brain 已回写，**每个 PR 的 handoff 已写（tasks.result.handoff + docs/handoffs/ 镜像）**，且已尝试自杀 tmux 会话（Step 5.6，非 tmux 环境视为已满足）。
