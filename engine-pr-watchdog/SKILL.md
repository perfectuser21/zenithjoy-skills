---
name: engine-pr-watchdog
version: 2.0.0
updated: 2026-05-27
description: PR 合并守卫。engine-ship 完成后调用，阻塞轮询 CI + 合并状态，CI 失败自动修复，直到 PR 合并才退出。不使用 ScheduleWakeup，不提前 exit。
trigger: engine-ship 完成后（step_4_ship: done），下一 tool call 必须是 engine-pr-watchdog
---

> **CRITICAL LANGUAGE RULE**: 所有输出简体中文。

## 职责

本 Skill 是 PR 合并的唯一自动保障机制，**全程阻塞不退出**：
- CI 失败 → 自动诊断修复 → 继续轮询
- CI 通过但未 merge → 确认 auto-merge + 检查 BEHIND → 继续轮询
- 已 merge → 清理 worktree → 退出
- **禁止使用 ScheduleWakeup。禁止提前 exit。轮询直到合并。**

---

## Step 1: 确定监控目标

优先从调用上下文拿 PR 号和 worktree 路径。没有的话扫描：

```bash
WTBASE="/Users/administrator/perfect21/cecelia/.claude/worktrees"
find "$WTBASE" -maxdepth 2 -name ".dev-mode.*" 2>/dev/null | while read f; do
  branch=$(basename "$f" | sed 's/^\.dev-mode\.//')
  ship=$(grep "^step_4_ship:" "$f" 2>/dev/null | awk '{print $2}')
  echo "$branch | ship=$ship | $f"
done
```

对每个 `step_4_ship: done` 的分支执行后续步骤。
若没有活跃分支 → **直接退出，不调度**。

---

## Step 2: 阻塞轮询主循环

**用单个 Bash 工具调用跑完整轮询，timeout 设 600000（10 分钟）。**
若 10 分钟内未合并，结束后立即再发起一次 Bash 调用继续轮询，直到合并为止。

```bash
PR_NUMBER=<PR号>
REPO=<owner/repo>          # 如 perfectuser21/cecelia
WORKTREE_PATH=<worktree路径>
DEV_MODE_FILE=<.dev-mode文件路径>
FIX_COUNT=0
MAX_FIXES=3

echo "🔍 开始监控 PR #$PR_NUMBER ($REPO)"

while true; do
  # ── 检查是否已合并 ──────────────────────────────
  STATE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json state --jq '.state' 2>/dev/null)
  if [ "$STATE" = "MERGED" ] || [ -z "$STATE" ]; then
    echo "✅ PR #$PR_NUMBER 已合并，退出轮询"
    break
  fi
  if [ "$STATE" = "CLOSED" ]; then
    echo "ℹ️ PR #$PR_NUMBER 已关闭（用户手动），退出轮询"
    break
  fi

  # ── 检查 CI ──────────────────────────────────────
  FAILED=$(gh pr checks "$PR_NUMBER" --repo "$REPO" 2>/dev/null | grep -c "fail" || echo 0)
  PENDING=$(gh pr checks "$PR_NUMBER" --repo "$REPO" 2>/dev/null | grep -cE "pending|in_progress|queued" || echo 0)

  if [ "$FAILED" -gt 0 ]; then
    echo "❌ CI 有 $FAILED 个失败，准备修复（第 $((FIX_COUNT+1)) 次）"
    if [ "$FIX_COUNT" -ge "$MAX_FIXES" ]; then
      echo "🚨 连续修复 $MAX_FIXES 次仍失败，需要人工介入"
      break
    fi
    # 退出 bash loop，让 Claude 读日志并修复（见 Step 3）
    echo "NEED_FIX:$PR_NUMBER"
    exit 10   # 特殊退出码，Claude 识别后执行 Step 3
  fi

  # ── 检查 BEHIND ───────────────────────────────────
  MERGE_STATE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json mergeStateStatus --jq '.mergeStateStatus' 2>/dev/null)
  if [ "$MERGE_STATE" = "BEHIND" ]; then
    echo "📦 分支落后 main，需要 rebase"
    echo "NEED_REBASE:$WORKTREE_PATH"
    exit 11   # 特殊退出码，Claude 识别后执行 Step 4
  fi

  # ── 确认 auto-merge ──────────────────────────────
  AUTO_MERGE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json autoMergeRequest --jq '.autoMergeRequest' 2>/dev/null)
  if [ "$AUTO_MERGE" = "null" ] || [ -z "$AUTO_MERGE" ]; then
    gh pr merge "$PR_NUMBER" --repo "$REPO" --auto --squash 2>/dev/null && echo "✅ auto-merge 已启用"
  fi

  echo "$(date '+%H:%M:%S') OPEN | CI: ${PENDING} pending ${FAILED} fail | merge_state: $MERGE_STATE"
  sleep 20
done
```

**退出码说明：**
- `0` = 正常退出（合并或关闭）
- `10` = CI 失败，需要执行 Step 3 修复
- `11` = 分支 BEHIND，需要执行 Step 4 rebase

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

```bash
cd "$WORKTREE_PATH"
git fetch origin main
git rebase origin/main
git push origin HEAD --force-with-lease
```

rebase 成功后**重新进入 Step 2 主循环**（不退出）。

---

## Step 5: 合并后清理

```bash
# 读取 task_id
TASK_ID=$(grep "^task_id:" "$DEV_MODE_FILE" 2>/dev/null | awk '{print $2}')

# 清理 worktree
git -C /Users/administrator/perfect21/cecelia worktree remove "$WORKTREE_PATH" --force 2>/dev/null \
  && echo "✅ worktree 已清理" || echo "⚠️ worktree 清理失败（可能已不存在）"

# Brain 回写
if [ -n "$TASK_ID" ] && [ "$TASK_ID" != "unknown" ]; then
  PR_URL=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json url -q '.url' 2>/dev/null || echo "")
  curl -s -X PATCH "localhost:5221/api/brain/tasks/$TASK_ID" \
    -H "Content-Type: application/json" \
    -d "{\"status\":\"completed\",\"result\":{\"merged\":true,\"pr_url\":\"$PR_URL\"}}" \
    | jq -r '"Brain 回写: " + (.status // .error // "unknown")' 2>/dev/null || true
fi

echo "✅ PR #$PR_NUMBER 合并清理完成"
```

---

## 防护规则

1. **禁止 ScheduleWakeup**：任何情况下不得调用 ScheduleWakeup，用 bash sleep loop 代替
2. **禁止提前 exit 0**：只有合并/关闭/fix_count≥3 才能退出
3. **Bash timeout 设 600000**：单次轮询最长 10 分钟，超时后立即再发起一次
4. **无 worktree 也能轮询**：找不到 worktree 时跳过修复步骤，仍持续轮询合并状态
5. **`gh pr list` 返空 = 已合并**：视为正常退出

---

## 完成标志

所有活跃 PR 均为 MERGED 或 CLOSED，worktree 已清理，Brain 已回写。
