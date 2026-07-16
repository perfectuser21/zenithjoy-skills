#!/usr/bin/env bash
# 合同测试：L级承诺进合同法律 [TASK:b6b6cca5]
# Red = 修改前应失败；Green = 修改后应全部通过
set -e
PASS=0; FAIL=0

check() {
  local name="$1"; shift
  if "$@" 2>/dev/null; then
    echo "PASS: $name"; PASS=$((PASS+1))
  else
    echo "FAIL: $name"; FAIL=$((FAIL+1))
  fi
}

# B1: golden-path-proposer 含「验证等级承诺」
check "B1-验证等级承诺" grep -q "验证等级承诺" /workspace/golden-path-proposer/SKILL.md

# B2: golden-path-proposer 含接缝L3铁律（三镜头 + L3）
check "B2a-三镜头" grep -q "三镜头" /workspace/golden-path-proposer/SKILL.md
check "B2b-L3" grep -q "L3" /workspace/golden-path-proposer/SKILL.md

# B3: harness-contract-proposer 含 [L1|L2|L3] 格式标记 + verification_level
check "B3a-L级格式" grep -qE '\[L[123]\]' /workspace/harness-contract-proposer/SKILL.md
check "B3b-verification_level" grep -q "verification_level" /workspace/harness-contract-proposer/SKILL.md

# B4: harness-contract-proposer 含「锚定父路」
check "B4-锚定父路" grep -q "锚定父路" /workspace/harness-contract-proposer/SKILL.md

# B5: harness-evaluator 含 verification_level ≥2处
check "B5-verification_level-2处" bash -c 'test $(grep -c "verification_level" /workspace/harness-evaluator/SKILL.md) -ge 2'

# B6: 三文件版本号已 bump
check "B6-gpp-1.1.0" grep -q "1\.1\.0" /workspace/golden-path-proposer/SKILL.md
check "B6-hcp-9.13.0" grep -q "9\.13\.0" /workspace/harness-contract-proposer/SKILL.md
check "B6-hev-1.25.0" grep -q "1\.25\.0" /workspace/harness-evaluator/SKILL.md

echo ""; echo "总计: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
