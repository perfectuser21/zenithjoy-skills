# Step 4：分支 BEHIND 处理（rebase 流程）

## 场景参数

- PR 编号：#45
- Repo：perfectuser21/cecelia
- Worktree 路径：/tmp/test-worktree
- 分支名：cp-test

---

## 触发条件

在 Step 2 主循环中，`gh pr view` 返回 `mergeStateStatus = "BEHIND"`，主循环脚本以 `exit 11` 退出，触发 Step 4。

```
📦 分支落后 main，需要 rebase
```

---

## 实际执行的 Bash 命令（同步，不使用 run_in_background）

```bash
cd /tmp/test-worktree
git fetch origin main
git rebase origin/main
git push origin HEAD --force-with-lease
echo "rebase+push 完成，立刻重新进入 Step 2 轮询"
```

### 参数说明

| 命令 | 参数 | 含义 |
|------|------|------|
| `git fetch origin main` | `origin main` | 只拉取 origin 的 main 分支，不拉取全部 ref，速度更快，避免无关噪音 |
| `git rebase origin/main` | `origin/main` | 以远端 main 为基准做 rebase，将 cp-test 的提交摞到最新 main 之上 |
| `git push origin HEAD --force-with-lease` | `HEAD` 指向当前分支 cp-test；`--force-with-lease` | force-with-lease 只有在远端 ref 与本地预期一致时才允许强推，防止覆盖他人提交，比 `--force` 安全 |

---

## 执行细节

1. **`cd /tmp/test-worktree`**：切到 PR 对应的 git worktree，确保所有 git 操作都在正确的 worktree 里执行（不影响主仓库工作区）。

2. **`git fetch origin main`**：从 origin 拉取最新的 main 分支指针。此步骤不修改本地任何工作文件，只更新 `origin/main` 这个远端追踪引用。

3. **`git rebase origin/main`**：  
   - 将 cp-test 上相对于旧 main 的提交，一一重放到新 main 的顶部。  
   - 如果 rebase 出现冲突，需在 worktree 内解决冲突后 `git rebase --continue`，然后重新执行 push。  
   - rebase 成功后，cp-test 的提交历史将线性地接在最新 main 之后，`mergeStateStatus` 将从 `BEHIND` 变为 `CLEAN` 或 `BLOCKED`（取决于 CI 状态）。

4. **`git push origin HEAD --force-with-lease`**：  
   - `HEAD` 在当前分支 cp-test 指向最新 rebase 后的提交。  
   - 因为 rebase 改写了提交历史（SHA 变化），普通 `git push` 会被拒绝，必须强推。  
   - `--force-with-lease` 确保只有在远端 cp-test 没有被他人推送过新提交的情况下才会成功，避免意外覆盖。

---

## push 返回后立刻做什么

push 命令同步返回（**绝对不使用 `run_in_background: true`**）后：

1. **不输出任何提示文字给用户**
2. **不结束当前 turn**
3. **立刻发起下一次 Step 2 的 Bash 调用**，重新进入主轮询循环：

```bash
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
    echo "ℹ️ PR #$PR_NUMBER 已关闭（用户手动），退出轮询"
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
    echo "📦 分支落后 main，需要 rebase"
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

---

## rebase 后的预期后续路径

| rebase 后状态 | 下一步动作 |
|--------------|-----------|
| CI 重新触发，PENDING | Step 2 继续轮询，等待 CI 通过 |
| CI FAILED | exit 10 → Step 3 自动修复 |
| MERGE_STATE = CLEAN | 确认 auto-merge 已启用，继续轮询合并 |
| MERGED | exit 0 → Step 5 清理 worktree + Brain 回写 |

---

## 关键防护原则

- **禁止 `--force`（裸强推）**：一律使用 `--force-with-lease`，防止覆盖他人提交
- **禁止 `run_in_background: true`**：所有命令同步执行，确保 turn 不结束，Stop Hook 不触发
- **禁止 ScheduleWakeup**：轮询靠 `sleep 30` 的 bash loop，不依赖任何外部调度
- **rebase 冲突处理**：若 `git rebase origin/main` 报冲突，在 worktree 内解决后执行 `git rebase --continue`，再 push
