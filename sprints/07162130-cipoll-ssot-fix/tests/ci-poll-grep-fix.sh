#!/usr/bin/env bash
# ci-poll-grep-fix.sh — grep -c 双行输出修复 failing test + 三分支回归
# 用法：bash sprints/07162130-cipoll-ssot-fix/tests/ci-poll-grep-fix.sh
# 退出码：0=全部通过，1=有失败用例
# 纯 bash，无外部依赖，可在 CI runner 直接执行。

set -uo pipefail

PASS=0
FAIL=0
ERRORS=()

pass() { echo "  PASS: $1"; ((PASS++)); }
fail() { echo "  FAIL: $1"; ((FAIL++)); ERRORS+=("$1"); }

echo "=== ci-poll grep -c 修复测试套件 ==="
echo ""

# ---------------------------------------------------------------------------
# B1 — Failing Test（记录当前 bug）
# 模拟 grep -c 产生双行输出（正常计数行 + 额外错误行），验证旧版整数比较报错
# ---------------------------------------------------------------------------
echo "[B1] failing test: grep -c 双行输出 → 旧版整数比较应报错"

# 构造双行输出（模拟 grep -c 在 broken pipe 下输出：计数行 + 错误信息行）
MOCK_FAILED_VAR=$'1\ngrep: write error: Broken pipe'

# 旧版比较逻辑（不含 head -1）
OLD_COMPARE_RESULT=0
OLD_COMPARE_STDERR=""
OLD_COMPARE_STDERR=$(bash -c '
  FAILED='"'"''"$MOCK_FAILED_VAR"''"'"'
  if [ "${FAILED:-0}" -gt 0 ]; then
    exit 10
  fi
  exit 0
' 2>&1) || OLD_COMPARE_RESULT=$?

# 旧版应当因 integer expression expected 而失败（exit 2 on bash error）
# 或产生 stderr 含错误信息
if [ $OLD_COMPARE_RESULT -ne 0 ] || echo "$OLD_COMPARE_STDERR" | grep -qiE "integer|expression|expected|error"; then
  pass "B1: 旧版整数比较对双行输出报错（exit=$OLD_COMPARE_RESULT，stderr='${OLD_COMPARE_STDERR:-<empty>}'）"
else
  fail "B1: 旧版整数比较对双行输出未报错——bug 可能已被环境屏蔽（exit=$OLD_COMPARE_RESULT）"
fi
echo ""

# ---------------------------------------------------------------------------
# 回归测试辅助函数
# 使用 ci-poll.sh 的核心逻辑（内联版本），注入 mock 数据，不调用真实 gh CLI
# ---------------------------------------------------------------------------
# 内联核心判断逻辑（修复后版本，含 head -1）
run_fixed_logic() {
  local checks="$1"
  local merge_state="$2"

  # 修复后逻辑：| head -1 确保单行整数（即使 grep -c 产双行也安全）
  # 用 { ... ; } 包裹管道让 pipefail 不干扰 grep exit 1（无匹配）
  FAILED=$(echo "$checks" | { grep -c "fail" 2>/dev/null || true; } | head -1)
  FAILED="${FAILED:-0}"
  PENDING=$(echo "$checks" | { grep -cE "pending|in_progress|queued" 2>/dev/null || true; } | head -1)
  PENDING="${PENDING:-0}"

  if [ "${FAILED:-0}" -gt 0 ]; then
    echo "CI_FAILED: $FAILED 个失败 check" >&2
    return 10
  fi

  if [ "$merge_state" = "BEHIND" ]; then
    echo "BEHIND: 分支落后 main" >&2
    return 11
  fi

  if [ "${PENDING:-1}" -eq 0 ]; then
    echo "CI_GREEN" >&2
    return 0
  fi

  # 仍有 pending，不应在单次 mock 中出现（测试只做单次轮询）
  return 99
}

# ---------------------------------------------------------------------------
# B2 — 回归：CI 全绿（pending=0, fail=0, mergeStateStatus≠BEHIND）
# ---------------------------------------------------------------------------
echo "[B2] 回归: CI 全绿 → exit 0"

MOCK_CHECKS_GREEN="check1	pass	https://ci.example/1	https://ci.example/1
check2	pass	https://ci.example/2	https://ci.example/2"
MOCK_MERGE_GREEN="CLEAN"

B2_OUT=""
B2_EXIT=0
B2_STDERR=$(run_fixed_logic "$MOCK_CHECKS_GREEN" "$MOCK_MERGE_GREEN" 2>&1) || B2_EXIT=$?

if [ $B2_EXIT -eq 0 ] && echo "$B2_STDERR" | grep -q "CI_GREEN"; then
  pass "B2: CI 全绿场景 → exit=0，输出含 CI_GREEN"
else
  fail "B2: CI 全绿场景失败（exit=$B2_EXIT，stderr='$B2_STDERR'）"
fi
echo ""

# ---------------------------------------------------------------------------
# B3 — 回归：有 fail（fail>0）→ exit 10
# ---------------------------------------------------------------------------
echo "[B3] 回归: 有 fail → exit 10"

MOCK_CHECKS_FAIL="check1	fail	https://ci.example/1	https://ci.example/1
check2	pass	https://ci.example/2	https://ci.example/2"
MOCK_MERGE_FAIL="CLEAN"

B3_EXIT=0
B3_STDERR=$(run_fixed_logic "$MOCK_CHECKS_FAIL" "$MOCK_MERGE_FAIL" 2>&1) || B3_EXIT=$?

if [ $B3_EXIT -eq 10 ] && echo "$B3_STDERR" | grep -q "CI_FAILED"; then
  pass "B3: 有 fail 场景 → exit=10，输出含 CI_FAILED"
else
  fail "B3: 有 fail 场景失败（exit=$B3_EXIT，stderr='$B3_STDERR'）"
fi
echo ""

# ---------------------------------------------------------------------------
# B4 — 回归：BEHIND（mergeStateStatus=BEHIND, fail=0, pending=0）→ exit 11
# ---------------------------------------------------------------------------
echo "[B4] 回归: BEHIND → exit 11"

MOCK_CHECKS_BEHIND="check1	pass	https://ci.example/1	https://ci.example/1
check2	pass	https://ci.example/2	https://ci.example/2"
MOCK_MERGE_BEHIND="BEHIND"

B4_EXIT=0
B4_STDERR=$(run_fixed_logic "$MOCK_CHECKS_BEHIND" "$MOCK_MERGE_BEHIND" 2>&1) || B4_EXIT=$?

if [ $B4_EXIT -eq 11 ] && echo "$B4_STDERR" | grep -q "BEHIND"; then
  pass "B4: BEHIND 场景 → exit=11，输出含 BEHIND"
else
  fail "B4: BEHIND 场景失败（exit=$B4_EXIT，stderr='$B4_STDERR'）"
fi
echo ""

# ---------------------------------------------------------------------------
# 结果汇总
# ---------------------------------------------------------------------------
echo "=== 结果 ==="
echo "PASS: $PASS / $((PASS + FAIL))"

if [ ${#ERRORS[@]} -gt 0 ]; then
  echo "FAIL 用例："
  for e in "${ERRORS[@]}"; do
    echo "  - $e"
  done
  echo ""
  echo "SOME TESTS FAILED"
  exit 1
else
  echo ""
  echo "ALL TESTS PASSED"
  exit 0
fi
