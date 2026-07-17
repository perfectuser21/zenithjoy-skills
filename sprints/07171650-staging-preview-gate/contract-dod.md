# Contract DoD — staging 预览闸进合同法律

> **Sprint**: 07171650-staging-preview-gate
> **Task ID**: 8589b916-9b71-4dd8-a986-76660229b06d
> **journey_type**: dev_pipeline
> **目标**: harness-contract-proposer v9.16.0 + harness-report v6.9.0

---

## [BEHAVIOR] 条目

- [ ] [BEHAVIOR] B-1 [L1]: harness-contract-proposer SKILL.md 版本 bump 至 9.16.0
  - 动作：generator 在 harness-contract-proposer/SKILL.md 的 YAML header 将 `version: 9.15.0` 改为 `version: 9.16.0`，同时在 changelog 顶部插入 9.16.0 条目
  - 预期观察：文件头部 `version:` 字段值变为 `9.16.0`，changelog 第一条为 9.16.0 相关描述
  - 验证命令：`grep -qE "^version: 9\.16\.0" harness-contract-proposer/SKILL.md && echo "PASS" || echo "FAIL"`
  - Test: manual:bash

- [ ] [BEHAVIOR] B-2 [L1]: proposer SKILL.md 含 staging 预览闸段及三步逻辑
  - 动作：generator 在 harness-contract-proposer/SKILL.md 规则正文中插入「## staging 预览闸」段，包含步骤 A（落 staging）、步骤 B（Final E2E 在 staging 跑）、步骤 C（Bark 推主理人预览链接）
  - 预期观察：文件中可 grep 到「staging 预览闸」「通知式」「阻塞式」「promote_after」「BARK_URL」字样
  - 验证命令：
    ```bash
    grep -q "staging 预览闸" harness-contract-proposer/SKILL.md || { echo "FAIL: 无闸段"; exit 1; }
    grep -q "通知式" harness-contract-proposer/SKILL.md || { echo "FAIL: 无通知式"; exit 1; }
    grep -q "阻塞式" harness-contract-proposer/SKILL.md || { echo "FAIL: 无阻塞式"; exit 1; }
    grep -q "promote_after" harness-contract-proposer/SKILL.md || { echo "FAIL: 无 promote_after"; exit 1; }
    grep -q "BARK_URL" harness-contract-proposer/SKILL.md || { echo "FAIL: 无 BARK_URL"; exit 1; }
    echo "PASS"
    ```
  - Test: manual:bash

- [ ] [BEHAVIOR] B-3 [L1]: proposer SKILL.md 明确 autonomous/dev_pipeline 豁免，不被错误纳入
  - 动作：generator 在「staging 预览闸」段中写明豁免条款，注明 `journey_type=autonomous/dev_pipeline/agent_remote` 不受本规则约束
  - 预期观察：文件中存在 autonomous 豁免相关语句；负向检查 — 文件中不存在「autonomous 必须执行 staging」类强制语句
  - 验证命令：
    ```bash
    # 正向：autonomous 豁免声明存在
    grep -qE "autonomous.*不受本规则|autonomous.*零回归|autonomous.*不强制|autonomous.*不受约束|dev_pipeline.*不受|不受.*autonomous" harness-contract-proposer/SKILL.md \
      || { echo "FAIL: 无 autonomous 豁免声明"; exit 1; }
    # 负向：autonomous 未被错误纳入
    if grep -qE "autonomous.*必须.*staging|autonomous.*强制.*staging" harness-contract-proposer/SKILL.md; then
      echo "FAIL: autonomous 被错误纳入 staging 强制"; exit 1
    fi
    echo "PASS"
    ```
  - Test: manual:bash

- [ ] [BEHAVIOR] B-4 [L1]: harness-report SKILL.md 版本 bump 至 6.9.0 且新增 Step 5.5
  - 动作：generator 在 harness-report/SKILL.md 的 YAML header 将 `version: 6.8.0` 改为 `version: 6.9.0`，在 changelog 顶部插入 6.9.0 条目，并在 Phase A Step 5（飞书通知）之后插入 Step 5.5 块
  - 预期观察：文件头 version 为 6.9.0；正文出现「5.5」字样；含 `promote_after`、`approval_required`、`user_facing` 限定；含 BARK_URL 引用；Step 5.5 失败属 CONCERN 非阻断说明
  - 验证命令：
    ```bash
    grep -qE "^version: 6\.9\.0" harness-report/SKILL.md || { echo "FAIL: report 版本未 bump"; exit 1; }
    grep -q "5\.5" harness-report/SKILL.md || { echo "FAIL: 无 Step 5.5"; exit 1; }
    grep -q "promote_after" harness-report/SKILL.md || { echo "FAIL: 无 promote_after"; exit 1; }
    grep -q "approval_required" harness-report/SKILL.md || { echo "FAIL: 无 approval_required"; exit 1; }
    grep -q "BARK_URL" harness-report/SKILL.md || { echo "FAIL: 无 BARK_URL"; exit 1; }
    echo "PASS"
    ```
  - Test: manual:bash

- [ ] [BEHAVIOR] B-5 [L1]: harness-report Phase B db-update 调用不变（INV-4 回归）
  - 动作：generator 修改 harness-report/SKILL.md 时，Phase B 的 db-update 调用段保持不变
  - 预期观察：文件中仍存在 `db-update` 字样，未被删改
  - 验证命令：`grep -q "db-update" harness-report/SKILL.md && echo "PASS" || echo "FAIL: Phase B db-update 丢失"`
  - Test: manual:bash

---

## [ARTIFACT] 产物清单

- [ ] `harness-contract-proposer/SKILL.md` — version 改为 9.16.0，changelog 新增 9.16.0 条目，新增「staging 预览闸」规则段
- [ ] `harness-report/SKILL.md` — version 改为 6.9.0，changelog 新增 6.9.0 条目，Phase A Step 5 之后新增 Step 5.5 块

---

## 合同格式自查（proposer 交付前必跑）

```bash
#!/bin/bash
set -euo pipefail
SPRINT_DIR="sprints/07171650-staging-preview-gate"

echo "=== 合同格式自查 ==="

# 1. contract-draft.md 存在
test -f "${SPRINT_DIR}/contract-draft.md" || { echo "FAIL: contract-draft.md 缺失"; exit 1; }

# 2. contract-dod.md 存在
test -f "${SPRINT_DIR}/contract-dod.md" || { echo "FAIL: contract-dod.md 缺失"; exit 1; }

# 3. [BEHAVIOR] 条目 ≥ 4 条（行首 checkbox 格式）
BEHAVIOR_COUNT=$(grep -cE "^\- \[ \] \*\*\[BEHAVIOR\]" "${SPRINT_DIR}/contract-dod.md" || true)
[ "$BEHAVIOR_COUNT" -ge 4 ] || { echo "FAIL: [BEHAVIOR] 条目不足 4 条（当前: $BEHAVIOR_COUNT）"; exit 1; }
echo "OK: [BEHAVIOR] 条目数 = $BEHAVIOR_COUNT"

# 4. contract-draft.md 含 ## E2E 验收 段
grep -q "## E2E 验收" "${SPRINT_DIR}/contract-draft.md" || { echo "FAIL: contract-draft.md 无 ## E2E 验收 段"; exit 1; }

# 5. contract-dod.md 无预勾 [x]
if grep -qE "^\- \[x\]" "${SPRINT_DIR}/contract-dod.md"; then
  echo "FAIL: contract-dod.md 存在预勾 [x]，禁止提前勾选"
  exit 1
fi

# 6. [BEHAVIOR] 条目含 Test: manual:bash
BEHAVIOR_WITH_TEST=$(grep -cE "Test: manual:bash" "${SPRINT_DIR}/contract-dod.md" || true)
[ "$BEHAVIOR_WITH_TEST" -ge 4 ] || { echo "FAIL: [BEHAVIOR] 条目 Test: manual:bash 不足 4 条（当前: $BEHAVIOR_WITH_TEST）"; exit 1; }

# 7. 测试文件存在
test -f "${SPRINT_DIR}/tests/skill-changes.test.ts" || { echo "FAIL: tests/skill-changes.test.ts 缺失"; exit 1; }

echo "=== 合同格式自查 PASS ==="
```

---

## E2E 验收命令（evaluator 执行）

```bash
#!/bin/bash
set -euo pipefail
# 执行位置：zenithjoy-skills repo 根目录 /workspace

echo "=== Final E2E 验收：staging 预览闸 ==="

# AC-1: proposer SKILL.md 版本 + 关键词
grep -qE "^version: 9\.16\.0" harness-contract-proposer/SKILL.md \
  || { echo "FAIL AC-1a: proposer 版本未 bump"; exit 1; }
grep -q "staging 预览闸" harness-contract-proposer/SKILL.md \
  || { echo "FAIL AC-1b: 无 staging 预览闸段"; exit 1; }
grep -q "通知式" harness-contract-proposer/SKILL.md \
  || { echo "FAIL AC-1c: 无通知式"; exit 1; }
grep -q "阻塞式" harness-contract-proposer/SKILL.md \
  || { echo "FAIL AC-1d: 无阻塞式"; exit 1; }
grep -q "promote_after" harness-contract-proposer/SKILL.md \
  || { echo "FAIL AC-1e: 无 promote_after"; exit 1; }
grep -qE "autonomous.*不受本规则|autonomous.*零回归|autonomous.*不强制|autonomous.*不受约束|dev_pipeline.*不受|不受.*autonomous" harness-contract-proposer/SKILL.md \
  || { echo "FAIL AC-1f: 无 autonomous 豁免声明"; exit 1; }
grep -q "BARK_URL" harness-contract-proposer/SKILL.md \
  || { echo "FAIL AC-1g: 无 BARK_URL 引用"; exit 1; }
echo "PASS AC-1"

# AC-2: report SKILL.md 版本 + Step 5.5
grep -qE "^version: 6\.9\.0" harness-report/SKILL.md \
  || { echo "FAIL AC-2a: report 版本未 bump"; exit 1; }
grep -q "5\.5" harness-report/SKILL.md \
  || { echo "FAIL AC-2b: 无 Step 5.5"; exit 1; }
grep -q "promote_after" harness-report/SKILL.md \
  || { echo "FAIL AC-2c: report 无 promote_after"; exit 1; }
grep -q "approval_required" harness-report/SKILL.md \
  || { echo "FAIL AC-2d: report 无 approval_required"; exit 1; }
grep -q "BARK_URL" harness-report/SKILL.md \
  || { echo "FAIL AC-2e: report 无 BARK_URL"; exit 1; }
echo "PASS AC-2"

# AC-3: autonomous 零回归（负向）
if grep -qE "autonomous.*必须.*staging|autonomous.*强制.*staging" harness-contract-proposer/SKILL.md; then
  echo "FAIL AC-3: autonomous 被错误纳入 staging"
  exit 1
fi
echo "PASS AC-3"

# AC-4: Phase B 不变量
grep -q "db-update" harness-report/SKILL.md \
  || { echo "FAIL AC-4: Phase B db-update 丢失"; exit 1; }
echo "PASS AC-4"

echo ""
echo "=== ALL E2E AC PASS ==="
```
