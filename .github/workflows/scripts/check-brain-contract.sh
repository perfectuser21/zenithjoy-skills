#!/usr/bin/env bash
# check-brain-contract.sh — skill 文档与 cecelia Brain 契约的一致性守卫
#
# 背景：skills 仓库（本仓库）描述的调用契约，真正的校验代码在 cecelia 仓库的 Brain 里。
# 两边分属不同 repo，靠人脑同步必然漂移（2026-07-05 实例：cecelia #3554 上线
# orchestrator 硬校验后，/dev 点火模板一度缺 orchestrator 字段，路径C 点火会被秒拒）。
# 本脚本把"当前 Brain 契约的硬性断言"固化进 CI：契约变了但 skill 没跟上 → PR 直接红。
#
# 维护规则：cecelia 侧任何改动 harness_initiative / Brain API 契约的 PR，
# 必须同步在这里增/改断言并更新对应 skill（参照该 PR 的 ROLLOUT NOTE）。
set -uo pipefail
cd "$(dirname "$0")/../../.."

FAIL=0
err() { echo "❌ $1"; FAIL=1; }
ok()  { echo "✅ $1"; }

# ── 契约 1：/dev 路径C 点火 payload 必须带 orchestrator=skill-relay ──
# 来源：cecelia #3554（2026-07-05）executor.js _driveHarnessInitiative 硬校验，
# payload.orchestrator !== 'skill-relay' → terminal failed (missing_orchestrator_flag)
if grep -q 'orchestrator.*skill-relay' dev/SKILL.md; then
  ok "dev/SKILL.md 点火模板含 orchestrator=skill-relay"
else
  err "dev/SKILL.md 点火模板缺 orchestrator=skill-relay（Brain 会秒拒任务，见 cecelia #3554）"
fi

# ── 契约 2：LangGraph 图编排已废弃，不得再被描述为现行路径 ──
# 提到 LangGraph 的行必须带废弃/历史标注（废弃|过时|deprecated|历史|观察期|不再|替代|切换）
STALE=$(grep -rn "LangGraph" --include="SKILL.md" . 2>/dev/null \
  | grep -vE "废弃|过时|deprecated|历史|观察期|不再|替代|切换" || true)
if [ -z "$STALE" ]; then
  ok "无 skill 将 LangGraph 图描述为现行编排路径"
else
  err "以下行仍把 LangGraph 当现行路径描述（须补废弃标注或改写为 skill-relay 语义）："
  echo "$STALE"
fi

# ── 契约 3：harness 编排相关 skill 必须自洽声明 skill-relay ──
for f in harness-controller/SKILL.md harness-planner/SKILL.md; do
  if grep -q "skill-relay" "$f"; then
    ok "$f 已声明 skill-relay 语义"
  else
    err "$f 未提及 skill-relay——编排语义可能还停留在图时代"
  fi
done

echo
if [ "$FAIL" -eq 1 ]; then
  echo "❌ Brain 契约一致性检查失败。修法：更新对应 SKILL.md；若是契约本身变了，同步更新本脚本断言。"
  exit 1
fi
echo "✅ Brain 契约一致性检查全部通过"
