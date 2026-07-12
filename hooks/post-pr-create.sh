#!/bin/bash
# post-pr-create.sh — PostToolUse hook
# Source: ~/perfect21/zenithjoy-skills/hooks/post-pr-create.sh

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)

if ! echo "$COMMAND" | grep -qE 'gh pr create'; then
  exit 0
fi

STDOUT=$(echo "$INPUT" | jq -r '.tool_response.stdout // ""' 2>/dev/null)
PR_URL=$(echo "$STDOUT" | grep -oE 'https://github\.com/[^/]+/[^/]+/pull/[0-9]+' | head -1)
PR_NUMBER=$(echo "$PR_URL" | grep -oE '[0-9]+$')
REPO=$(echo "$PR_URL" | grep -oE 'github\.com/[^/]+/[^/]+' | sed 's|github.com/||')

if [ -z "$PR_NUMBER" ]; then
  exit 0
fi

# Harness 容器（generator/evaluator/planner）不启用 auto-merge
# Brain 的 evaluator pre-merge gate 负责验证后才 merge（HARNESS_NODE 由 harness-task.graph.js 注入）
if [[ -n "${HARNESS_NODE:-}" ]]; then
  echo "[post-pr-create] HARNESS_NODE=${HARNESS_NODE}: 跳过 auto-merge，evaluator PASS 后 Brain 执行 merge" >&2
  echo "PR #${PR_NUMBER} (${REPO}) 已创建，等待 Brain harness 处理。" >&2
  exit 0
fi

# rewrite/* 重写 PR 停人工 review（decision e6c57e2f，skills#127 教训）：
# 不启用 auto-merge、不强制 watchdog，等主理人批准。
# skills#129 残留修：gh 偶发失败时以 git branch --show-current 作兜底：
#   - gh 成功 → 用 gh 结果判断分支
#   - gh 失败 + git 成功 → 以本地分支名作兜底继续判断
#   - gh 失败 + git 也失败 → fail-closed：保守跳过 auto-merge，不因网络抖动静默放行
LOCAL_BRANCH=$(git branch --show-current 2>/dev/null)
HEAD_BRANCH=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json headRefName -q .headRefName 2>/dev/null)
if [[ -z "$HEAD_BRANCH" ]]; then
  if [[ -z "$LOCAL_BRANCH" ]]; then
    echo "[post-pr-create] gh pr view 失败且 git branch 失败，fail-closed: 跳过 auto-merge。" >&2
    exit 0
  fi
  echo "[post-pr-create] gh pr view 失败，使用本地分支 ${LOCAL_BRANCH} 作兜底。" >&2
  HEAD_BRANCH="$LOCAL_BRANCH"
fi
if [[ "$HEAD_BRANCH" == rewrite/* ]]; then
  echo "[post-pr-create] rewrite/* 分支（${HEAD_BRANCH}）：跳过 auto-merge，重写 PR 停人工 review，等主理人批准。" >&2
  exit 0
fi

# 立刻 enable auto-merge
gh pr merge "$PR_NUMBER" --repo "$REPO" --auto --squash 2>/dev/null || true

# exit 2 = 阻塞 Claude，注入指令（写 stderr，Claude Code 读 stderr）
echo "PR #${PR_NUMBER} (${REPO}) 已创建并启用 auto-merge。你现在必须立刻调用 Skill({\"skill\":\"engine-pr-watchdog\"}) 轮询直到合并，不得输出任何文字给用户，不得结束 turn。" >&2
exit 2
