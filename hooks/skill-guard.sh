#!/usr/bin/env bash
# Skill Guard Hook — code-review 写保护
# 当 SKILL_CONTEXT=code_review 时，拦截对非 docs/reviews/ 路径的 Write/Edit 操作。
# 确保 code-review agent 只能写报告文件，不能修改被审查的代码。

set -euo pipefail

# 仅在 SKILL_CONTEXT=code_review 时激活
if [[ "${SKILL_CONTEXT:-}" != "code_review" ]]; then
    exit 0
fi

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')

# 只拦截 Write 和 Edit 工具
if [[ "$TOOL_NAME" != "Write" && "$TOOL_NAME" != "Edit" ]]; then
    exit 0
fi

# 获取目标文件路径
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# 放行 docs/reviews/ 目录（报告输出目录）
if [[ "$FILE_PATH" == */docs/reviews/* ]]; then
    exit 0
fi

# 放行 /tmp/ 目录（临时文件）
if [[ "$FILE_PATH" == /tmp/* ]]; then
    exit 0
fi

# 其他任何路径 → 拦截
echo "" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
echo "  [SKILL GUARD] code-review 写保护" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
echo "" >&2
echo "  ⛔ code-review skill 禁止修改代码文件" >&2
echo "  文件: $FILE_PATH" >&2
echo "" >&2
echo "  ✅ 允许写入：<repo>/docs/reviews/*.md" >&2
echo "  ❌ 禁止写入：任何代码文件" >&2
echo "" >&2
echo "  如需修复代码问题，请通过 Cecelia 派发 /dev task。" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
exit 2
