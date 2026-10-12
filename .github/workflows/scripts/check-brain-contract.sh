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

# ── 契约 1：编码入口改投 coding_workflow，旧无头 harness 已退役 ──
# 来源：cecelia #6356（2026-10-12）。检查当前路径 C 的命令块，
# 不允许历史 changelog 中的字符串充当点火模板已更新的证据。
if python3 .github/workflows/scripts/check-coding-workflow-entry.py; then
  ok "编码入口与旧 harness 废弃标注一致"
else
  err "编码入口仍引用旧无头 harness，或缺少 runner 必填字段/废弃标注"
fi

# ── 契约 2：LangGraph 图编排已废弃，不得再被描述为现行路径 ──
# 提到 LangGraph 的行必须带废弃/历史标注（废弃|过时|deprecated|历史|观察期|不再|替代|切换）
STALE=$(grep -rn "LangGraph" --include="SKILL.md" . 2>/dev/null \
  | grep -vE "废弃|过时|deprecated|历史|观察期|不再|替代|切换" || true)
if [ -z "$STALE" ]; then
  ok "无 skill 将 LangGraph 图描述为现行编排路径"
else
  err "以下行仍把 LangGraph 当现行路径描述（须补废弃标注或改写为 coding_workflow 语义）："
  echo "$STALE"
fi

# 契约 3（旧 skill-relay 声明）已被上方七个技能的废弃标注检查替代。
# 下方 exact-run 安全约束继续保护历史回溯，不删除在用的有头 hooks。

# ── 契约 4：Controller 的 Run 写入必须只按 canonical run_id 精确命中 ──
# 来源：cecelia convergence repair PR2。initiative_id 只用于聚合/创建，不能再作为
# 中间进度、verdict、PR URL 或终态的 mutation key。
CONTROLLER="harness-controller/SKILL.md"
if grep -q 'HARNESS_RUN_ID' "$CONTROLLER"; then
  ok "$CONTROLLER 保存 canonical HARNESS_RUN_ID"
else
  err "$CONTROLLER 未保存 HARNESS_RUN_ID，无法精确回写当前 run"
fi

if grep -q 'relay-runs/by-id/${HARNESS_RUN_ID}' "$CONTROLLER"; then
  ok "$CONTROLLER 使用 exact-run mutation endpoint"
else
  err "$CONTROLLER 未使用 relay-runs/by-id/\${HARNESS_RUN_ID} 精确更新"
fi

if grep -q "\\.run\\.id // empty" "$CONTROLLER"; then
  ok "$CONTROLLER 从 canonical create 响应的 run.id 取得 identity"
else
  err "$CONTROLLER 未从 canonical create 响应的 .run.id 读取 run identity"
fi

if grep -q 'created_source:\"foreground_handoff\"' "$CONTROLLER"; then
  ok "$CONTROLLER 使用 Brain 允许的 foreground_handoff source"
else
  err "$CONTROLLER canonical create 使用了 Brain 不接受的 created_source"
fi

LEGACY_MUTATION=$(grep -nE 'curl .*-(X )?PATCH .*relay-runs/(\$|\$\{)HARNESS_INITIATIVE_ID' "$CONTROLLER" || true)
if [ -z "$LEGACY_MUTATION" ]; then
  ok "$CONTROLLER 不再按 initiative_id PATCH run"
else
  err "$CONTROLLER 仍按 initiative_id PATCH，可能批量改写历史："
  echo "$LEGACY_MUTATION"
fi

if grep -q '\\"run_id\\":\\"$HARNESS_RUN_ID\\"' "$CONTROLLER"; then
  ok "$CONTROLLER Judge 请求携带 run_id"
else
  err "$CONTROLLER Judge 请求缺 run_id，裁决无法绑定 exact run"
fi

echo
if [ "$FAIL" -eq 1 ]; then
  echo "❌ Brain 契约一致性检查失败。修法：更新对应 SKILL.md；若是契约本身变了，同步更新本脚本断言。"
  exit 1
fi
echo "✅ Brain 契约一致性检查全部通过"
