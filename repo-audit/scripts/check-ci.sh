#!/bin/bash
# check-ci.sh — CI 反模式扫描
REPO=${1:-.}
WORKFLOW_DIR="$REPO/.github/workflows"
HITS=0

echo "=== CI 反模式扫描 ==="
[ ! -d "$WORKFLOW_DIR" ] && echo "❌ no_ci: 无 .github/workflows/" && exit 1
echo "Workflow 文件: $(ls $WORKFLOW_DIR/ | tr '\n' ' ')"

# 1. admin_bypass
ENFORCE=$(gh api "repos/$(git -C $REPO remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]//' | sed 's/.git$//')/branches/main" 2>/dev/null | jq -r '.protection.required_status_checks.enforcement_level // "none"')
[ "$ENFORCE" != "everyone" ] && echo "🔴 admin_bypass: enforcement_level='$ENFORCE'" && HITS=$((HITS+1)) || echo "✅ admin_bypass"

# 2. audit_scope_wrong
AUDIT=$(grep -rn "npm audit" $WORKFLOW_DIR/ 2>/dev/null)
if [ -z "$AUDIT" ]; then
  echo "🔴 no_audit_in_ci: 无 npm audit" && HITS=$((HITS+1))
elif echo "$AUDIT" | grep -q "omit=dev"; then
  echo "🔴 audit_scope_wrong: 使用 --omit=dev" && HITS=$((HITS+1))
elif echo "$AUDIT" | grep "working-directory" | grep -qv "working-directory: \.$"; then
  echo "🔴 audit_scope_wrong: audit 在子目录（非根目录）" && HITS=$((HITS+1))
else
  echo "✅ audit_scope"
fi

# 3. no_coverage_gate
# thresholds 通常写在 vitest/jest config 里而非 workflow（vitest run --coverage 会读 config），
# 所以两处都找；heuristic 局限：只要任一 config 有 thresholds 即视为有门禁（不校验逐 app 覆盖）
COVERAGE=$(grep -rn "\-\-coverage" $WORKFLOW_DIR/ 2>/dev/null)
THRESHOLD_WF=$(grep -rn "thresholds\|coverageThreshold" $WORKFLOW_DIR/ 2>/dev/null)
THRESHOLD_CFG=$(find "$REPO" -maxdepth 4 \( -name "vitest.config.*" -o -name "jest.config.*" \) -not -path "*/node_modules/*" 2>/dev/null | xargs grep -l "thresholds\|coverageThreshold" 2>/dev/null)
[ -n "$COVERAGE" ] && [ -z "$THRESHOLD_WF$THRESHOLD_CFG" ] && echo "🔴 no_coverage_gate: 有 --coverage 无门禁" && HITS=$((HITS+1)) || echo "✅ coverage_gate（门禁在: $(echo $THRESHOLD_CFG | tr '\n' ' ' | head -c 120)）"

# 4. lint_too_lenient
echo "$( grep -rn "max-warnings" $WORKFLOW_DIR/ 2>/dev/null )" | grep -qE "max-warnings [2-9][0-9]|max-warnings [0-9]{3}" && echo "🔴 lint_too_lenient: $(grep -rn "max-warnings" $WORKFLOW_DIR/ | grep -oE 'max-warnings [0-9]+')" && HITS=$((HITS+1)) || echo "✅ lint_warnings"

# 5. l1_not_on_push
L1=$(ls $WORKFLOW_DIR/ci-l1* $WORKFLOW_DIR/*process* 2>/dev/null | head -1)
[ -n "$L1" ] && ! grep -A10 "^on:" "$L1" | grep -q "push" && echo "🔴 l1_not_on_push: L1 不覆盖 push" && HITS=$((HITS+1)) || echo "✅ l1_coverage"

echo ""
echo "=== 命中 $HITS 个反模式 ==="
[ $HITS -eq 0 ] && echo "CI 可信 ✅" || ([ $HITS -eq 1 ] && echo "CI 存在问题 ⚠️" || echo "CI 虚假绿 🔴❌")
