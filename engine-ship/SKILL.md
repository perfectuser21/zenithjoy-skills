---
name: engine-ship
version: 16.4.0
updated: 2026-07-14
description: Cecelia /dev 接力链终棒。Superpowers finishing 完成 push+PR 后，写 Learning + 触发 Brain fire-learnings-event + 标记 step_4_ship=done。完成后下一 tool call 必须 Skill(engine-pr-watchdog)。
trigger: Superpowers finishing-a-development-branch 完成后，按 /dev SKILL.md Phase 5 硬规则点火
---

> **CRITICAL LANGUAGE RULE**: 所有输出简体中文。

## Harness 模式检测

```bash
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
DEV_MODE_FILE=".dev-mode.${BRANCH_NAME}"
harness_mode=$(grep -m1 "^harness_mode:" "$DEV_MODE_FILE" 2>/dev/null | awk '{print $2}')
[[ "$harness_mode" == "true" ]] && { echo "harness mode — 跳 Learning/fire-event，直接标 done"; skip_learning=1; }
```

harness_mode=true 时跳过 §1.5、§2，直达 §3。

## 1. 完工清理检查（engine/ 有改动时必做）

```bash
bash packages/engine/skills/dev/scripts/check-cleanup.sh
```

检查 regression-contract 引用 / Shell 硬引用 / 6 个版本文件同步。有问题必修。

## 1.5 毕业步（测试入册，v16.4 — 配套 cecelia test-pyramid-guard 孤儿棘轮锁 0）

harness_mode=true 直接跳过本节（relay 路径的毕业由 harness-controller Step 6 负责）。

有头路径：若当前分支在 `sprints/*/tests/` 或 `sprints/*/e2e-verify.sh` 有本分支新增文件，且 repo 存在 `scripts/graduate-sprint-tests.mjs`，必须逐 sprint 跑毕业脚本把测试搬进永久池（tests/regression/<slug>/ + scripts/smoke/e2e/<slug>.sh），否则 test-pyramid-guard 会把 PR 拦红：

```bash
if [[ "$harness_mode" != "true" && -f scripts/graduate-sprint-tests.mjs ]]; then
  # 找出本分支新增的 sprint 测试/E2E 脚本（对比 merge-base）
  GRAD_SPRINTS=$(git diff --name-only --diff-filter=A "$(git merge-base origin/main HEAD)"..HEAD \
    | grep -E '^sprints/[^/]+/(tests/|e2e-verify\.sh)' | cut -d/ -f1-2 | sort -u)
  for SPRINT in $GRAD_SPRINTS; do
    # --update-refs：重写根 DoD.md 旧路径引用，防毕业 commit 被 dod-behavior-dynamic 拦死（#3870 实证）
    node scripts/graduate-sprint-tests.mjs --sprint "$SPRINT" --update-refs
  done
  if [[ -n "$GRAD_SPRINTS" ]] && ! git diff --quiet; then
    git add -A && git commit -m "chore(quality): 毕业 sprint 测试入册永久池（纯 rename）"
    git push origin HEAD
    # 此时 PR 已开、watchdog 尚未接手，追加 commit 会重触 CI——正常，由 engine-pr-watchdog 照常等绿
  fi
fi
```

## 2. 写 Learning + fire Brain 事件（harness_mode=false）

格式：`## <任务简述>（YYYY-MM-DD）` + `### 根本原因` + `### 下次预防` checklist。

```bash
LEARNING_FILE="docs/learnings/${BRANCH_NAME}.md"
mkdir -p docs/learnings
# 写 Learning 内容到 $LEARNING_FILE
git add "$LEARNING_FILE"
git commit -m "docs: add learning for ${BRANCH_NAME}

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push origin HEAD

bash packages/engine/skills/dev/scripts/fire-learnings-event.sh \
  --branch "$BRANCH_NAME" --pr "$PR_NUMBER" --task-id "$TASK_ID"

# 闭环回写 Brain task status=completed（CLAUDE.md §8）
bash packages/engine/skills/dev/scripts/callback-brain-task.sh \
  --branch "$BRANCH_NAME" --pr "$PR_NUMBER" --task-id "$TASK_ID"

bash scripts/write-current-state.sh
```

## 2.5 关 guardian + 写 done-marker（v23 心跳模型）

```bash
PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null || echo "")
PR_URL=$(gh pr view --json url -q .url 2>/dev/null || echo "")
bash packages/engine/scripts/ship-finalize.sh "$BRANCH_NAME" "$PR_NUMBER" "$PR_URL" || \
  echo "[engine-ship] ship-finalize 失败但不阻塞合并（灯文件可能已被 reaper 清）"
```

## 3. 标记完成

```bash
sed -i '' "s/step_4_ship: pending/step_4_ship: done/" "$DEV_MODE_FILE"
git push origin HEAD
```

## 完成标志

- `.dev-mode` 里 `step_4_ship: done`（两模式都必须）
- harness_mode=false 时额外：`docs/learnings/<branch>.md` 存在且已 push

---

## TERMINAL IMPERATIVE

engine-ship 是 /dev 接力链倒数第二棒。**完成后下一 tool call 必须是 `Skill({"skill":"engine-pr-watchdog"})`**，由它接管 CI 监控 + 自动合并 + cleanup。CI 红 → engine-pr-watchdog 内部调 `superpowers:systematic-debugging`。

## 终态 Handoff 说明（decisions cf998025 — engine-pr-watchdog 3.2.0）

engine-pr-watchdog 3.2.0 起，merge 确认后**自动写 handoff**，路径 A/B 无需手动写：
- **SSOT**：`tasks.result.handoff`（Brain DB，task_id 对应行）
- **镜像**：`docs/handoffs/<timestamp>-<taskId>.md`（仓库内，可 grep 查历史）
- **格式协议**：`packages/brain/src/handoff.js`（saveHandoff 函数）
- **无下一步时**：next_steps 字段显式写「完成，无下一步」，禁止留空

engine-ship 本身不写 handoff，只负责 Learning + fire-event + done-marker；handoff 是 engine-pr-watchdog 在 merge 后的收尾职责。
