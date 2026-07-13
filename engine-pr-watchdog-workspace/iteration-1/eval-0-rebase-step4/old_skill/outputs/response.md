# Step 4 Rebase 流程执行说明

## 场景参数

- PR: #45
- Repo: perfectuser21/cecelia
- Worktree: /tmp/test-worktree
- Branch: cp-test

## 触发条件

Step 2 主循环检测到 `mergeStateStatus = "BEHIND"`，退出码 11，进入 Step 4。

## 实际执行的 Bash 命令

```bash
cd /tmp/test-worktree
git fetch origin main
git rebase origin/main
git push origin HEAD --force-with-lease
```

### 命令参数说明

**`git fetch origin main`**
- `origin`：远程名称，拉取 perfectuser21/cecelia 的最新状态
- `main`：只拉取 main 分支的引用，更新本地 `origin/main` 指针
- 不切换分支，不修改工作区

**`git rebase origin/main`**
- 把当前分支 `cp-test` 的提交，接到最新的 `origin/main` 顶端
- 解决"落后"问题：将 cp-test 上领先 main 的 commit 移植到 main 的新 HEAD 之后
- 若有冲突会暂停，需要手动解决后 `git rebase --continue`

**`git push origin HEAD --force-with-lease`**
- `HEAD`：推送当前所在分支（cp-test），不依赖本地分支名称硬编码
- `--force-with-lease`：强制推送（rebase 改写了历史所以必须 force），但有安全保护——如果远程分支在此期间被别人更新了，推送会被拒绝，防止覆盖他人提交
- 不用 `--force`，避免盲目覆盖

## rebase 成功后接下来做什么

Step 4 完成后，**立刻重新进入 Step 2 主循环**（不退出，不输出等待提示），继续轮询：

```bash
# 重新进入 Step 2 主循环
PR_NUMBER=45
REPO=perfectuser21/cecelia
WORKTREE_PATH=/tmp/test-worktree

while true; do
  STATE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json state --jq '.state' 2>/dev/null)
  if [ "$STATE" = "MERGED" ] || [ -z "$STATE" ]; then
    echo "✅ PR #$PR_NUMBER 已合并，退出轮询"
    break
  fi
  if [ "$STATE" = "CLOSED" ]; then
    echo "ℹ️ PR #$PR_NUMBER 已关闭，退出轮询"
    break
  fi

  CHECKS=$(gh pr checks "$PR_NUMBER" --repo "$REPO" 2>/dev/null)
  FAILED=$(echo "$CHECKS" | grep -c "fail" || echo 0)
  PENDING=$(echo "$CHECKS" | grep -cE "pending|in_progress|queued" || echo 0)

  if [ "$FAILED" -gt 0 ]; then
    echo "❌ CI 有 $FAILED 个失败"
    exit 10
  fi

  MERGE_STATE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json mergeStateStatus --jq '.mergeStateStatus' 2>/dev/null)
  if [ "$MERGE_STATE" = "BEHIND" ]; then
    echo "📦 分支再次落后 main，需要重新 rebase"
    exit 11
  fi

  AUTO_MERGE=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json autoMergeRequest --jq '.autoMergeRequest' 2>/dev/null)
  if [ "$AUTO_MERGE" = "null" ] || [ -z "$AUTO_MERGE" ]; then
    gh pr merge "$PR_NUMBER" --repo "$REPO" --auto --squash 2>/dev/null && echo "✅ auto-merge 已启用"
  fi

  echo "$(TZ=Asia/Shanghai date '+%H:%M:%S') OPEN | CI: pending=$PENDING fail=$FAILED | merge=$MERGE_STATE"
  sleep 30
done
```

### 后续分支判断

| Step 2 检测结果 | 下一步 |
|---|---|
| STATE = MERGED | 执行 Step 5 清理 worktree + Brain 回写，退出 |
| CI FAILED（退出码 10） | 执行 Step 3 读失败日志、在 worktree 修复、push，重回 Step 2 |
| BEHIND（退出码 11） | 再次执行 Step 4 rebase，重回 Step 2 |
| 一切正常但未合并 | 确认 auto-merge 已启用，sleep 30 继续轮询 |
| Bash call 超时（10分钟） | 立刻重新发起 Step 2 调用，不输出任何文字 |

整个过程全程阻塞，不提前 exit，不使用 ScheduleWakeup，直到 PR #45 状态变为 MERGED 或 CLOSED 才结束。
