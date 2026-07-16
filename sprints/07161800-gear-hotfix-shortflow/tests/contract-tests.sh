#!/usr/bin/env bash
# Contract Tests — gear=hotfix 短流程 sprint
# Sprint: 07161800-gear-hotfix-shortflow
# TDD Red 阶段：当前 SKILL.md 未修改时必须失败（exit 非零）

FAIL=0

echo "=== B1: HARNESS_GEAR 变量行 + payload.gear 来源 ==="
if grep -q "HARNESS_GEAR" /workspace/harness-controller/SKILL.md && grep -q "payload.gear" /workspace/harness-controller/SKILL.md; then
  echo "PASS B1"
else
  echo "FAIL B1: SKILL.md 缺少 HARNESS_GEAR 变量行或 payload.gear 来源"
  FAIL=1
fi

echo "=== B2: gear=hotfix 短流程段 + skip proposer/reviewer GAN 日志关键词 ==="
if grep -q "gear=hotfix" /workspace/harness-controller/SKILL.md && grep -q "skip proposer/reviewer GAN" /workspace/harness-controller/SKILL.md; then
  echo "PASS B2"
else
  echo "FAIL B2: SKILL.md 缺少 gear=hotfix 段或 'skip proposer/reviewer GAN' 关键词"
  FAIL=1
fi

echo "=== B3: 安全阀铁律（FATAL + 禁止顺手改 / 缺锚定声明 + 拒绝 hotfix + 回退全流程）==="
if grep -q "FATAL" /workspace/harness-controller/SKILL.md && grep -q "缺锚定声明" /workspace/harness-controller/SKILL.md && grep -q "拒绝 hotfix" /workspace/harness-controller/SKILL.md && grep -q "回退全流程" /workspace/harness-controller/SKILL.md; then
  echo "PASS B3"
else
  echo "FAIL B3: SKILL.md 缺少安全阀铁律关键词（FATAL / 缺锚定声明 / 拒绝 hotfix / 回退全流程）"
  FAIL=1
fi

echo "=== B4: 版本号 2.8.0 ==="
if grep -q "2.8.0" /workspace/harness-controller/SKILL.md; then
  echo "PASS B4"
else
  echo "FAIL B4: SKILL.md 版本号未 bump 至 2.8.0"
  FAIL=1
fi

echo "=== B5: examples/hotfix-shortflow/ 示例文件存在 + contract-dod.md 含 ≥4 条 [BEHAVIOR] ==="
if ls /workspace/harness-controller/examples/hotfix-shortflow/contract-draft.md && ls /workspace/harness-controller/examples/hotfix-shortflow/contract-dod.md && test "$(grep -c '\[BEHAVIOR\]' /workspace/harness-controller/examples/hotfix-shortflow/contract-dod.md)" -ge 4; then
  echo "PASS B5"
else
  echo "FAIL B5: 示例文件缺失或 contract-dod.md 含 [BEHAVIOR] 条目不足 4"
  FAIL=1
fi

echo "=== B6: HARNESS_GEAR 识别段 + proposer + GAN 关键词（全流程分支零回归）==="
if grep -q "HARNESS_GEAR" /workspace/harness-controller/SKILL.md && grep -q "proposer" /workspace/harness-controller/SKILL.md && grep -q "GAN" /workspace/harness-controller/SKILL.md; then
  echo "PASS B6"
else
  echo "FAIL B6: SKILL.md 缺少 HARNESS_GEAR / proposer / GAN 关键词（全流程分支被移除）"
  FAIL=1
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "ALL PASS — 所有合同测试通过"
  exit 0
else
  echo "FAIL — 部分合同测试未通过"
  exit 1
fi
