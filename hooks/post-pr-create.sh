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

# 立刻 enable auto-merge
gh pr merge "$PR_NUMBER" --repo "$REPO" --auto --squash 2>/dev/null || true

# exit 2 = 阻塞 Claude，注入指令（写 stderr，Claude Code 读 stderr）
echo "PR #${PR_NUMBER} (${REPO}) 已创建并启用 auto-merge。你现在必须立刻调用 Skill({\"skill\":\"engine-pr-watchdog\"}) 轮询直到合并，不得输出任何文字给用户，不得结束 turn。" >&2
exit 2
