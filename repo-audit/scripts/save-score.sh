#!/bin/bash
# save-score.sh — 写入 audit 分数到 Brain DB
REPO_NAME=${1:-"unknown"}; SCORE=${2:-0}; SUMMARY=${3:-""}; DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "=== 写入 audit 分数 ==="
RESULT=$(curl -s -X POST http://localhost:5221/api/brain/decisions \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Repo Audit: $REPO_NAME\",\"decision\":\"score=$SCORE/120 | $SUMMARY\",\"context\":\"repo-audit\",\"tags\":[\"repo-audit\",\"$REPO_NAME\"]}" 2>/dev/null)
echo "$RESULT" | grep -q '"id"' && echo "✅ 写入 Brain: $REPO_NAME $SCORE/120" || \
  (echo "{\"repo\":\"$REPO_NAME\",\"score\":$SCORE,\"date\":\"$DATE\",\"summary\":\"$SUMMARY\"}" >> ~/.claude/repo-audit-history.jsonl && echo "✅ 写入本地历史")
