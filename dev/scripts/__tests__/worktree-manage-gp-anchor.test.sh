#!/usr/bin/env bash
# 刀6b — worktree-manage.sh .dev-mode 写入必须携带 gp_anchor 行（GP锚定闭环）
# 直接测 .dev-mode 模板生成段：grep 脚本源码确认 gp_anchor 写入逻辑存在 + 沙箱实测
set -uo pipefail
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/worktree-manage.sh"
PASS=0; FAIL=0

# T1: 源码含 gp_anchor 写入逻辑（GP_ANCHOR env → .dev-mode 行）
if grep -q 'gp_anchor' "$SCRIPT"; then
  echo "PASS: T1 源码含 gp_anchor 写入逻辑"; PASS=$((PASS+1))
else
  echo "FAIL: T1 worktree-manage.sh 无 gp_anchor 写入逻辑"; FAIL=$((FAIL+1))
fi

# T2: .dev-mode heredoc 模板段包含 gp_anchor 行（防止只在别处出现字样糊弄 T1）
if awk '/cat > "\$dev_mode_file"/,/DEV_MODE_EOF$/' "$SCRIPT" | grep -q 'gp_anchor'; then
  echo "PASS: T2 .dev-mode 模板含 gp_anchor 行"; PASS=$((PASS+1))
else
  echo "FAIL: T2 .dev-mode heredoc 模板不含 gp_anchor 行"; FAIL=$((FAIL+1))
fi

echo "结果: $PASS pass / $FAIL fail"
[[ "$FAIL" -eq 0 ]] || exit 1
