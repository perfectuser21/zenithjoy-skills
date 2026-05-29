---
name: engine-pr-watchdog
version: 3.0.0
updated: 2026-05-29
description: PR 合并守卫。任何 PR 开完后立刻调用，监控所有 repo 的 open PR，阻塞轮询 CI + 合并状态，CI 失败自动修复，直到全部 PR 合并才退出。不使用 ScheduleWakeup，不提前 exit。
trigger: 任何 PR 开完之后（gh pr create 之后），立刻调用本 skill。engine-ship 完成后也调用。
---

> **CRITICAL LANGUAGE RULE**: 所有输出简体中文。

## 职责

监控所有 repo 的 open PR，**全程阻塞不退出**：
- CI 失败 → 自动诊断修复 → 继续轮询
- CI 通过但未 merge → 确认 auto-merge 已启用 → 继续轮询
- 分支 BEHIND → rebase → 继续轮询
- 已 merge → 清理 → 继续看下一个 PR
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

**退出码：**
- `0` = PR 已合并或关闭 → 执行 Step 5 清理，然后结束
- `10` = CI 失败 → 执行 Step 3 修复，修完后**立刻重新进入 Step 2**
- `11` = 分支 BEHIND → 执行 Step 4 rebase，完成后**立刻重新进入 Step 2**
- 超时（Bash call 到 10 分钟）→ **立刻重新发起 Step 2 的 Bash 调用，不输出任何文字**

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
  CHECKS=$(gh pr checks "$PR_NUMBER" --repo "$REPO" 2>/dev/null)
  FAILED=$(echo "$CHECKS" | grep -c "fail" || echo 0)
  PENDING=$(echo "$CHECKS" | grep -cE "pending|in_progress|queued" || echo 0)

  if [ "$FAILED" -gt 0 ]; then
    if [ "$FIX_COUNT" -ge "$MAX_FIXES" ]; then
      echo "🚨 连续修复 $MAX_FIXES 次仍失败，需要人工介入"
      exit 10
    fi
    echo "❌ CI 有 $FAILED 个失败（第 $((FIX_COUNT+1)) 次）"
    exit 10
  fi

  # ── 检查 BEHIND ───────────────────────────────────
  MERGE_STATE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json mergeStateStatus --jq '.mergeStateStatus' 2>/dev/null)
  if [ "$MERGE_STATE" = "BEHIND" ]; then
    echo "📦 分支落后 main，需要 rebase"
    exit 11
  fi

  # ── 确认 auto-merge ──────────────────────────────
  AUTO_MERGE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json autoMergeRequest --jq '.autoMergeRequest' 2>/dev/null)
  if [ "$AUTO_MERGE" = "null" ] || [ -z "$AUTO_MERGE" ]; then
    gh pr merge "$PR_NUMBER" --repo "$REPO" --auto --squash 2>/dev/null && echo "✅ auto-merge 已启用"
  fi

  echo "$(TZ=Asia/Shanghai date '+%H:%M:%S') OPEN | CI: pending=$PENDING fail=$FAILED | merge=$MERGE_STATE"
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
