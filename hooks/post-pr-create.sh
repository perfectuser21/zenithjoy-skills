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
# gh 查询优先；偶发失败时用 git branch --show-current 本地兜底；
# 两者均失败 → fail-closed：保守跳过 auto-merge，不因信息缺失静默放行。
HEAD_BRANCH=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json headRefName -q .headRefName 2>/dev/null)
if [[ -z "$HEAD_BRANCH" ]]; then
  HEAD_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
fi
if [[ -z "$HEAD_BRANCH" ]]; then
  echo "[post-pr-create] 无法获取分支名（gh 和 git 均失败），保守跳过 auto-merge (fail-closed)" >&2
  exit 0
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
