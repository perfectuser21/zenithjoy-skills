#!/bin/bash
# =============================================================
# TDD 验收脚本 — 07171650-staging-preview-gate
# 验证 harness-contract-proposer v9.16.0 + harness-report v6.9.0
# 执行位置：zenithjoy-skills repo 根目录（/workspace）
# =============================================================

set -euo pipefail

PASS=0
FAIL=0

check() {
  local desc="$1"
  local cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    echo "  PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $desc"
    FAIL=$((FAIL + 1))
  fi
}

check_fail() {
  local desc="$1"
  local cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    echo "  FAIL (should not match): $desc"
    FAIL=$((FAIL + 1))
  else
    echo "  PASS (correctly absent): $desc"
    PASS=$((PASS + 1))
  fi
}

echo "=== TDD 验收: harness-contract-proposer SKILL.md ==="

check "version=9.16.0" \
  "grep -qE '^version: 9\.16\.0' harness-contract-proposer/SKILL.md"

check "changelog 含 9.16.0 条目" \
  "grep -q '9\.16\.0' harness-contract-proposer/SKILL.md"

check "含「staging 预览闸」段落" \
  "grep -q 'staging 预览闸' harness-contract-proposer/SKILL.md"

check "含「通知式」条款（Cecelia 24h 无异议）" \
  "grep -q '通知式' harness-contract-proposer/SKILL.md"

check "含「阻塞式」条款（ZJ 需放行）" \
  "grep -q '阻塞式' harness-contract-proposer/SKILL.md"

check "含 promote_after 字段引用" \
  "grep -q 'promote_after' harness-contract-proposer/SKILL.md"

check "含 autonomous 豁免声明" \
  "grep -qE 'autonomous.*不受本规则|autonomous.*零回归|autonomous.*不强制|autonomous.*不受约束' harness-contract-proposer/SKILL.md"

check_fail "autonomous 未被错误纳入 staging 强制" \
  "grep -qE 'autonomous.*必须.*staging|autonomous.*强制.*staging' harness-contract-proposer/SKILL.md"

echo ""
echo "=== TDD 验收: harness-report SKILL.md ==="

check "version=6.9.0" \
  "grep -qE '^version: 6\.9\.0' harness-report/SKILL.md"

check "changelog 含 6.9.0 条目" \
  "grep -q '6\.9\.0' harness-report/SKILL.md"

check "含 Step 5.5" \
  "grep -q '5\.5' harness-report/SKILL.md"

check "Step 5.5 附近含 user_facing 限定" \
  "grep -A 5 '5\.5' harness-report/SKILL.md | grep -q 'user_facing' || grep -B 2 '5\.5' harness-report/SKILL.md | grep -q 'user_facing'"

check "含 promote_after 字段" \
  "grep -q 'promote_after' harness-report/SKILL.md"

check "含 approval_required 字段" \
  "grep -q 'approval_required' harness-report/SKILL.md"

check "Phase B db-update 调用不变（INV-4）" \
  "grep -q 'db-update' harness-report/SKILL.md"

echo ""
echo "==================================================="
echo "结果: PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo "状态: FAIL（$FAIL 项未通过）"
  exit 1
else
  echo "状态: ALL PASS"
  exit 0
fi
