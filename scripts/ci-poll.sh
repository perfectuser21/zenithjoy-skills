#!/usr/bin/env bash
# ci-poll.sh — CI 状态轮询（SSOT：zenithjoy-skills/scripts/ci-poll.sh）
# 用法：ci-poll.sh <PR号> [owner/repo]
# 退出码：0=CI全绿  10=有CI失败  11=分支BEHIND
#
# 调用方负责决策（merge/fix/rebase），本脚本只报状态。

set -euo pipefail

PR_NUMBER="${1:?'用法: ci-poll.sh <PR号> [owner/repo]'}"
REPO="${2:-}"

if [ -n "$REPO" ]; then
  REPO_ARGS=("--repo" "$REPO")
else
  REPO_ARGS=()
fi

while true; do
  CHECKS=$(gh pr checks "$PR_NUMBER" "${REPO_ARGS[@]}" 2>/dev/null || true)

  if echo "$CHECKS" | grep -qiE "fail"; then
    echo "[ci-poll] CI 有失败项"
    exit 10
  fi

  MERGE_STATE=$(gh pr view "$PR_NUMBER" "${REPO_ARGS[@]}" --json mergeStateStatus \
    --jq '.mergeStateStatus' 2>/dev/null || echo "")
  if [ "$MERGE_STATE" = "BEHIND" ]; then
    echo "[ci-poll] 分支落后 main（BEHIND）"
    exit 11
  fi

  PENDING=$(echo "$CHECKS" | grep -cE "pending|in_progress|queued" || echo 0)
  if [ "$PENDING" -eq 0 ]; then
    echo "[ci-poll] CI 全绿"
    exit 0
  fi

  echo "[ci-poll] $(TZ=Asia/Shanghai date '+%H:%M:%S') pending=$PENDING，等待 30s..."
  sleep 30
done
