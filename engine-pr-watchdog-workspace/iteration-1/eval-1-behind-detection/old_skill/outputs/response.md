# engine-pr-watchdog 执行响应

## 场景参数

- PR: #100
- Repo: perfectuser21/zenithjoy-skills
- Branch: feat/skill-test
- 首次检查结果: state=OPEN, CI pending=2 fail=0, mergeStateStatus=BEHIND

---

## Step 1: 确定监控目标

调用上下文已明确提供 PR 号和 Repo，直接跳过扫描步骤，使用：

```
PR_NUMBER=100
REPO=perfectuser21/zenithjoy-skills
```

---

## Step 2: 进入阻塞轮询主循环

初始化变量，启动主循环：

```bash
PR_NUMBER=100
REPO=perfectuser21/zenithjoy-skills
WORKTREE_PATH=$(find /Users/administrator/perfect21/zenithjoy-skills -name ".git" -prune -o -type d -print 2>/dev/null | grep "cp-" | head -1 || echo "/Users/administrator/perfect21/zenithjoy-skills")
DEV_MODE_FILE="$WORKTREE_PATH/.dev-mode"
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

## 首次轮询决策树（基于题目给定数据）

### 输入状态

| 字段 | 值 |
|------|----|
| state | OPEN |
| CI pending | 2 |
| CI fail | 0 |
| mergeStateStatus | BEHIND |

### 决策路径

```
STATE == "OPEN"
  → 不触发合并退出，继续
FAILED == 0
  → 不触发 Step 3（CI 修复），继续
MERGE_STATE == "BEHIND"
  → exit 11
  → 执行 Step 4（rebase）
```

**结论：主循环在检测到 BEHIND 后执行 `exit 11`，触发 Step 4。**

注意：CI pending=2 表示仍有检查在跑，但因为 fail=0，主循环**不会**等 pending 清零，而是继续往下走到 BEHIND 检测。BEHIND 优先于 auto-merge 设置。

---

## Step 4: 分支 BEHIND 处理（exit 11 触发）

```bash
cd "$WORKTREE_PATH"
git fetch origin main
git rebase origin/main
git push origin HEAD --force-with-lease
```

执行说明：
1. `git fetch origin main` — 拉取 main 最新状态
2. `git rebase origin/main` — 将 feat/skill-test 分支变基到 main 最新 commit
3. `git push origin HEAD --force-with-lease` — 强制推送（--force-with-lease 保证安全，仅在本地预期一致时推送）

rebase 成功后，**立刻重新进入 Step 2 主循环**（不输出任何文字给用户，不结束 turn，直接再发起一次 Bash 调用）。

---

## Step 2 第二轮轮询（rebase 完成后）

rebase push 触发 CI 重新运行，进入新一轮主循环 Bash 调用：

```bash
# 变量继承上轮：PR_NUMBER=100, REPO=perfectuser21/zenithjoy-skills, FIX_COUNT=0
while true; do
  STATE=$(gh pr view 100 --repo "perfectuser21/zenithjoy-skills" --json state --jq '.state' 2>/dev/null)
  # 预期: STATE=OPEN → 继续

  CHECKS=$(gh pr checks 100 --repo "perfectuser21/zenithjoy-skills" 2>/dev/null)
  FAILED=$(echo "$CHECKS" | grep -c "fail" || echo 0)
  PENDING=$(echo "$CHECKS" | grep -cE "pending|in_progress|queued" || echo 0)
  # rebase 后 CI 重新触发，预期 pending>0, fail=0 → 继续

  MERGE_STATE=$(gh pr view 100 --repo "perfectuser21/zenithjoy-skills" --json mergeStateStatus --jq '.mergeStateStatus' 2>/dev/null)
  # rebase 后预期 MERGE_STATE=BLOCKED 或 MERGEABLE → 不再 BEHIND，不触发 exit 11

  AUTO_MERGE=$(gh pr view 100 --repo "perfectuser21/zenithjoy-skills" --json autoMergeRequest --jq '.autoMergeRequest' 2>/dev/null)
  if [ "$AUTO_MERGE" = "null" ] || [ -z "$AUTO_MERGE" ]; then
    gh pr merge 100 --repo "perfectuser21/zenithjoy-skills" --auto --squash 2>/dev/null && echo "✅ auto-merge 已启用"
  fi

  echo "$(TZ=Asia/Shanghai date '+%H:%M:%S') OPEN | CI: pending=$PENDING fail=$FAILED | merge=$MERGE_STATE"
  sleep 30
done
```

---

## 完整 Bash 命令序列摘要

```
# [1] 初始化 + 第一轮主循环
# 结果: 检测到 BEFORE_BEHIND → exit 11

# [2] Step 4 rebase
git fetch origin main
git rebase origin/main
git push origin HEAD --force-with-lease

# [3] 立刻重新进入 Step 2（第二轮主循环）
# 等待 CI 通过，MERGE_STATE 变为 MERGEABLE
# 确认 auto-merge 已启用 → sleep 30 → 继续轮询

# [4] 当 STATE=MERGED 时
# → break，执行 Step 5 清理

# [5] Step 5 清理
TASK_ID=$(grep "^task_id:" "$DEV_MODE_FILE" 2>/dev/null | awk '{print $2}')
git -C /Users/administrator/perfect21/zenithjoy-skills worktree remove "$WORKTREE_PATH" --force 2>/dev/null
if [ -n "$TASK_ID" ] && [ "$TASK_ID" != "unknown" ]; then
  PR_URL=$(gh pr view 100 --repo "perfectuser21/zenithjoy-skills" --json url -q '.url' 2>/dev/null || echo "")
  curl -s -X PATCH "localhost:5221/api/brain/tasks/$TASK_ID" \
    -H "Content-Type: application/json" \
    -d "{\"status\":\"completed\",\"result\":{\"merged\":true,\"pr_url\":\"$PR_URL\"}}" \
    | jq -r '"Brain 回写: " + (.status // .error // "unknown")' 2>/dev/null || true
fi
echo "✅ PR #100 合并清理完成"
```

---

## 关键防护规则执行确认

| 规则 | 本次执行状态 |
|------|------------|
| 禁止 ScheduleWakeup | ✅ 全程使用 bash sleep loop |
| 禁止提前 exit 0 | ✅ 仅在 MERGED/CLOSED 才 break |
| Bash timeout 设 600000 | ✅ 单次轮询最长 10 分钟 |
| BEHIND → rebase 后立刻重新进入 Step 2 | ✅ 不输出文字，直接再发起 Bash 调用 |
| fix_count 未超限 | ✅ 本轮 FIX_COUNT=0，无 CI 失败 |
