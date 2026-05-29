#!/bin/bash
# watch-pr.sh — 后台 PR 合并守卫
# 用法: bash watch-pr.sh <PR_NUMBER> <BRANCH> <CWD>
# 由 post-pr-create.sh PostToolUse hook 调用

PR_NUMBER="$1"
BRANCH="$2"
CWD="$3"
LOG="/tmp/watchdog-pr-${PR_NUMBER}.log"
MAX_CYCLES=20
CYCLE=0
FIX_COUNT=0
WTBASE="/Users/administrator/worktrees/cecelia"

log() { echo "[$(TZ=Asia/Shanghai date '+%H:%M:%S')] $*" >> "$LOG"; }

log "=== Watchdog 启动: PR #$PR_NUMBER branch=$BRANCH ==="

find_worktree() {
  find "$WTBASE" -maxdepth 2 -name ".dev-mode.${BRANCH}" 2>/dev/null \
    | head -1 | xargs -I{} dirname {} 2>/dev/null
}

cleanup_worktree() {
  local wt
  wt=$(find_worktree)
  if [ -n "$wt" ]; then
    git -C "$CWD" worktree remove "$wt" --force 2>/dev/null \
      && log "worktree $wt cleaned up" \
      || log "worktree cleanup failed: $wt"
  fi
}

while [ "$CYCLE" -lt "$MAX_CYCLES" ]; do
  CYCLE=$((CYCLE + 1))

  STATE=$(gh pr view "$PR_NUMBER" --json state -q '.state' 2>/dev/null)
  log "[$CYCLE/$MAX_CYCLES] PR #$PR_NUMBER state=${STATE:-empty}"

  if [ "$STATE" = "MERGED" ]; then
    log "PR #$PR_NUMBER merged. Cleaning up..."
    cleanup_worktree
    log "=== Watchdog done ==="
    exit 0
  fi

  if [ "$STATE" != "OPEN" ]; then
    log "PR #$PR_NUMBER state=${STATE:-not found}, stopping"
    exit 0
  fi

  CHECKS=$(gh pr checks "$PR_NUMBER" 2>/dev/null)
  FAILED=$(echo "$CHECKS" | grep -cE "fail|error" 2>/dev/null || echo 0)
  PENDING=$(echo "$CHECKS" | grep -cE "pending|in_progress|queued|running" 2>/dev/null || echo 0)
  log "CI: failed=$FAILED pending=$PENDING"

  if [ "$FAILED" -gt 0 ]; then
    if [ "$FIX_COUNT" -ge 3 ]; then
      log "3 fix attempts failed, giving up. See $LOG"
      exit 2
    fi
    FIX_COUNT=$((FIX_COUNT + 1))
    log "CI failed. Launching Claude fix session (attempt $FIX_COUNT)..."
    WT_PATH=$(find_worktree)
    FIX_PROMPT="gh pr checks $PR_NUMBER shows CI failure on branch $BRANCH. Worktree: ${WT_PATH:-unknown}. Check the failed CI logs, fix the code in the worktree, and push to fix the PR."
    nohup claude --dangerously-skip-permissions \
      --print "$FIX_PROMPT" \
      --cwd "${WT_PATH:-$CWD}" \
      >> "${LOG}.fix${FIX_COUNT}" 2>&1
    log "Claude fix session done. Waiting for CI rerun..."

  elif [ "$PENDING" -gt 0 ]; then
    log "CI running, waiting..."

  else
    AUTO=$(gh pr view "$PR_NUMBER" --json autoMergeRequest -q '.autoMergeRequest' 2>/dev/null)
    if [ -z "$AUTO" ] || [ "$AUTO" = "null" ]; then
      gh pr merge "$PR_NUMBER" --auto --squash 2>/dev/null \
        && log "auto-merge enabled" \
        || log "auto-merge failed (may need review)"
    else
      log "auto-merge already set, waiting for GitHub..."
    fi
  fi

  sleep 120
done

log "Timeout after $MAX_CYCLES cycles. Stopping watchdog for PR #$PR_NUMBER"
exit 1
