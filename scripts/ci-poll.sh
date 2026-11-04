#!/usr/bin/env bash
# ci-poll.sh — CI 状态轮询真身，供 engine-pr-watchdog 复用。
# 用法：scripts/ci-poll.sh <PR_NUMBER> <owner/repo>
# 退出码：0=已取得完整成功状态；10=明确失败；11=BEHIND；12=未知/不可判定。
# 依赖 gh、python3；只报状态，不执行 merge/rebase/fix。
set -euo pipefail

PR_NUMBER="${1:?需要 PR 号}"
REPO="${2:?需要 repo（格式：owner/repo）}"

unknown() { echo "CI_UNKNOWN: $1" >&2; exit 12; }
command -v python3 >/dev/null 2>&1 || unknown '缺少 JSON 解析器 python3'

while true; do
  # 同一次 PR 查询取得当前 head 的检查和合并状态；API 失败不能当空检查。
  if ! SNAPSHOT=$(gh pr view "$PR_NUMBER" --repo "$REPO" \
    --json mergeStateStatus,statusCheckRollup 2>/dev/null); then
    unknown '无法读取 PR 检查状态'
  fi
  if ! STATE=$(printf '%s' "$SNAPSHOT" | python3 -c '
import json, sys

def classify(data):
    if not isinstance(data, dict):
        return "UNKNOWN"
    merge = data.get("mergeStateStatus")
    if merge not in {"CLEAN", "UNSTABLE", "HAS_HOOKS", "BLOCKED", "DRAFT", "BEHIND"}:
        return "UNKNOWN"
    checks = data.get("statusCheckRollup")
    if not isinstance(checks, list) or not checks:
        return "UNKNOWN"
    states = []
    for item in checks:
        if not isinstance(item, dict):
            return "UNKNOWN"
        kind = item.get("__typename")
        if kind == "CheckRun":
            status, conclusion = item.get("status"), item.get("conclusion")
            if status in {"QUEUED", "IN_PROGRESS", "WAITING", "PENDING", "REQUESTED"} and conclusion is None:
                states.append("PENDING")
            elif status == "COMPLETED":
                if conclusion == "SUCCESS":
                    states.append("SUCCESS")
                elif conclusion in {"NEUTRAL", "SKIPPED"}:
                    states.append("SKIPPED")
                elif conclusion in {"FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE", "STALE"}:
                    states.append("FAILED")
                else:
                    return "UNKNOWN"
            else:
                return "UNKNOWN"
        elif kind == "StatusContext":
            state = item.get("state")
            if state == "SUCCESS":
                states.append("SUCCESS")
            elif state in {"PENDING", "EXPECTED"}:
                states.append("PENDING")
            elif state in {"FAILURE", "ERROR"}:
                states.append("FAILED")
            else:
                return "UNKNOWN"
        else:
            return "UNKNOWN"
    if "FAILED" in states:
        return "FAILED"
    if merge == "BEHIND":
        return "BEHIND"
    if "PENDING" in states:
        return "PENDING"
    # 全部跳过没有成功证据，不能宣称全绿。
    return "GREEN" if "SUCCESS" in states else "UNKNOWN"

try:
    print(classify(json.load(sys.stdin)))
except (ValueError, TypeError):
    print("UNKNOWN")
'); then
    unknown '检查状态解析失败'
  fi

  case "$STATE" in
    FAILED) echo 'CI_FAILED: 存在明确失败的 check' >&2; exit 10 ;;
    BEHIND) echo 'BEHIND: 分支落后 main' >&2; exit 11 ;;
    GREEN) echo 'CI_GREEN' >&2; exit 0 ;;
    PENDING) echo "$(TZ=Asia/Shanghai date '+%H:%M:%S') CI polling | pending" >&2 ;;
    *) unknown '检查缺失、格式异常或状态不可判定' ;;
  esac
  sleep 30
done
