#!/bin/bash
# check-tests.sh — 测试有效性分析
REPO=${1:-.}
echo "=== 测试有效性分析 ==="
SOURCE=$(find $REPO/apps $REPO/src 2>/dev/null -name "*.ts" -o -name "*.tsx" -o -name "*.py" | grep -v "__tests__\|\.test\.\|\.spec\.\|node_modules\|dist" | wc -l | tr -d ' ')
TESTS=$(find $REPO/apps $REPO/src 2>/dev/null \( -name "*.test.*" -o -name "*.spec.*" \) | grep -v "node_modules\|dist" | wc -l | tr -d ' ')
[ "$SOURCE" -gt 0 ] && RATIO=$(echo "scale=1; $TESTS * 100 / $SOURCE" | bc) && echo "Source: $SOURCE | Tests: $TESTS | 比例: ${RATIO}%"
(( $(echo "$RATIO < 20" | bc -l) )) && echo "🔴 test_ratio_low: ${RATIO}% < 20%" || echo "✅ test_ratio: ${RATIO}%"
MOCK_COUNT=$(grep -r "vi.mock\|jest.mock" $REPO/apps $REPO/src 2>/dev/null | grep -v node_modules | wc -l | tr -d ' ')
REAL_DB=$(find $REPO/apps $REPO/src 2>/dev/null \( -name "*.test.*" -o -name "*.spec.*" \) | grep -v node_modules | xargs grep -l "pg\|prisma\|sequelize" 2>/dev/null | wc -l | tr -d ' ')
echo "Mock 调用: $MOCK_COUNT | 真实 DB 测试文件: $REAL_DB"
[ "$MOCK_COUNT" -gt 0 ] && [ "$REAL_DB" -eq 0 ] && echo "🔴 all_mocked: 全是 mock，无集成测试" || echo "✅ has_real_tests"
find $REPO -type d \( -name "e2e" -o -name "integration" \) 2>/dev/null | grep -v node_modules | head -3 | grep -q . && echo "✅ e2e 目录存在" || echo "⚠️  无 e2e/ 目录"
