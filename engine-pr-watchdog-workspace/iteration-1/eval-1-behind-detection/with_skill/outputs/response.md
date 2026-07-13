# engine-pr-watchdog 完整决策与 Bash 命令序列

## 场景输入

- PR: #100
- Repo: perfectuser21/zenithjoy-skills
- Branch: feat/skill-test
- 第一次检查结果: state=OPEN, CI pending=2 fail=0, mergeStateStatus=BEHIND

---

## Step 1: 确定监控目标

调用上下文已明确提供 PR 号和 Repo，直接跳过全量扫描，进入 Step 2。

变量赋值：
- PR_NUMBER=100
- REPO=perfectuser21/zenithjoy-skills
- WORKTREE_PATH=（从调用上下文获取，假设为 /Users/administrator/perfect21/zenithjoy-skills）
- DEV_MODE_FILE=（从调用上下文获取，假设为 /Users/administrator/perfect21/zenithjoy-skills/.dev-mode）

---

## Step 2: 主循环第一次迭代——决策树

### 执行的 Bash 命令（第一次 Step 2 调用）

```bash
PR_NUMBER=100
REPO=perfectuser21/zenithjoy-skills
WORKTREE_PATH=/Users/administrator/perfect21/zenithjoy-skills
DEV_MODE_FILE=/Users/administrator/perfect21/zenithjoy-skills/.dev-mode
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

### 第一次迭代的决策过程（逐步）

1. **STATE 检查**：返回 OPEN → 不是 MERGED/CLOSED → 继续
2. **CI 检查**：
   - FAILED=0（题目给定 fail=0）→ 跳过 exit 10
   - PENDING=2（题目给定 pending=2）→ 不触发 fail 分支，继续
3. **MERGE_STATE 检查**：返回 BEHIND → **命中 `exit 11`**
4. **输出**：`📦 分支落后 main，需要 rebase`，以退出码 11 退出本次 while 循环/Bash 调用

**退出码 = 11 → 触发 Step 4（BEHIND 处理）**

---

## Step 4: 分支 BEHIND 处理（退出码 11）

Claude 检测到 exit 11，**立刻（不输出任何文字给用户，不结束 turn）**发起下一次 Bash 调用，执行 Step 4：

```bash
PR_NUMBER=100
REPO=perfectuser21/zenithjoy-skills
WORKTREE_PATH=/Users/administrator/perfect21/zenithjoy-skills

cd "$WORKTREE_PATH"
git fetch origin main
git rebase origin/main
git push origin HEAD --force-with-lease
echo "rebase+push 完成，立刻重新进入 Step 2 轮询"
```

**关键参数说明：**
- `git fetch origin main`：同步远端 main 的最新提交
- `git rebase origin/main`：将 feat/skill-test 分支的提交变基到最新 main 之上（解决 BEHIND）
- `git push origin HEAD --force-with-lease`：推送 rebase 后的分支（用 --force-with-lease 保护，防覆盖他人推送）
- 全部命令**同步执行**（不使用 run_in_background）

push 返回后，**不输出任何文字，立刻发起第二次 Step 2 的 Bash 调用**。

---

## Step 2: 主循环第二次迭代

push 完成后，Claude 立刻发起与第一次完全相同的 Step 2 Bash 调用（相同变量、相同逻辑），此时预期：

- STATE = OPEN → 继续
- FAILED = 0 → 跳过
- MERGE_STATE 已变为非 BEHIND（MERGEABLE 或 BLOCKED 等）→ 跳过 exit 11
- CI 仍 pending=2 → 不触发 exit 10
- auto-merge 检查：若未启用 → `gh pr merge 100 --repo perfectuser21/zenithjoy-skills --auto --squash`
- 进入 `sleep 30` 等待 CI 结果

**循环继续，直到 CI 全部通过 + PR 被 auto-merge 为 MERGED。**

---

## 完整 Bash 命令序列总结

### 命令 1（Step 2 第一次调用，同步，timeout=600000）
```bash
# 主循环 — 发现 BEHIND，exit 11
PR_NUMBER=100; REPO=perfectuser21/zenithjoy-skills; WORKTREE_PATH=/Users/administrator/perfect21/zenithjoy-skills; DEV_MODE_FILE=/Users/administrator/perfect21/zenithjoy-skills/.dev-mode; FIX_COUNT=0; MAX_FIXES=3
echo "🔍 开始监控 PR #$PR_NUMBER ($REPO)"
while true; do
  STATE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json state --jq '.state' 2>/dev/null)
  if [ "$STATE" = "MERGED" ] || [ -z "$STATE" ]; then echo "✅ PR #$PR_NUMBER 已合并，退出轮询"; break; fi
  if [ "$STATE" = "CLOSED" ]; then echo "ℹ️ PR #$PR_NUMBER 已关闭（用户手动），退出轮询"; break; fi
  CHECKS=$(gh pr checks "$PR_NUMBER" --repo "$REPO" 2>/dev/null)
  FAILED=$(echo "$CHECKS" | grep -c "fail" || echo 0)
  PENDING=$(echo "$CHECKS" | grep -cE "pending|in_progress|queued" || echo 0)
  if [ "$FAILED" -gt 0 ]; then
    if [ "$FIX_COUNT" -ge "$MAX_FIXES" ]; then echo "🚨 连续修复 $MAX_FIXES 次仍失败，需要人工介入"; exit 10; fi
    echo "❌ CI 有 $FAILED 个失败（第 $((FIX_COUNT+1)) 次）"; exit 10
  fi
  MERGE_STATE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json mergeStateStatus --jq '.mergeStateStatus' 2>/dev/null)
  if [ "$MERGE_STATE" = "BEHIND" ]; then echo "📦 分支落后 main，需要 rebase"; exit 11; fi
  AUTO_MERGE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json autoMergeRequest --jq '.autoMergeRequest' 2>/dev/null)
  if [ "$AUTO_MERGE" = "null" ] || [ -z "$AUTO_MERGE" ]; then gh pr merge "$PR_NUMBER" --repo "$REPO" --auto --squash 2>/dev/null && echo "✅ auto-merge 已启用"; fi
  echo "$(TZ=Asia/Shanghai date '+%H:%M:%S') OPEN | CI: pending=$PENDING fail=$FAILED | merge=$MERGE_STATE"
  sleep 30
done
# → 输出: 📦 分支落后 main，需要 rebase; exit 11
```

### 命令 2（Step 4 rebase，同步，run_in_background=false）
```bash
cd /Users/administrator/perfect21/zenithjoy-skills
git fetch origin main
git rebase origin/main
git push origin HEAD --force-with-lease
echo "rebase+push 完成，立刻重新进入 Step 2 轮询"
# → push 返回后，立刻发起命令 3，不输出任何文字
```

### 命令 3（Step 2 第二次调用，同步，timeout=600000）
```bash
# 主循环 — BEHIND 已修复，继续轮询直到 MERGED
PR_NUMBER=100; REPO=perfectuser21/zenithjoy-skills; WORKTREE_PATH=/Users/administrator/perfect21/zenithjoy-skills; DEV_MODE_FILE=/Users/administrator/perfect21/zenithjoy-skills/.dev-mode; FIX_COUNT=0; MAX_FIXES=3
# （完全相同的 while true 循环体）
# 此轮预期: MERGE_STATE != BEHIND → 启用 auto-merge → sleep 30 → 等待 CI 通过 → 最终 MERGED → exit 0
```

---

## 决策树可视化

```
PR #100 OPEN
├── STATE=OPEN → 继续
├── CI: FAILED=0 → 跳过 exit 10
├── MERGE_STATE=BEHIND → exit 11
│
└─→ Step 4 执行:
    git fetch origin main
    git rebase origin/main
    git push origin HEAD --force-with-lease
    │
    └─→ 立刻重入 Step 2（不结束 turn，不输出文字）
        ├── STATE=OPEN → 继续
        ├── CI: FAILED=0 → 跳过
        ├── MERGE_STATE≠BEHIND → 跳过 exit 11
        ├── auto-merge 未启用 → gh pr merge --auto --squash
        └── sleep 30 → 继续轮询...
            ├── CI 全通过 + MERGED → Step 5 清理 → 退出
            └── CI 失败 → exit 10 → Step 3 修复 → 重入 Step 2
```

---

## 核心规则验证

| 规则 | 本次执行是否遵守 |
|------|----------------|
| 禁止 ScheduleWakeup | 是，全程 bash sleep loop |
| 禁止提前 exit 0 | 是，仅在 MERGED/CLOSED 后退出 |
| Bash timeout=600000 | 是，每次 Step 2 调用设置上限 |
| 禁止 run_in_background | 是，Step 4 rebase/push 全部同步 |
| BEHIND 后立刻重入 Step 2 | 是，push 返回后不输出文字直接发下一次调用 |
| exit 11 触发 Step 4 | 是，退出码 11 精确匹配 |
