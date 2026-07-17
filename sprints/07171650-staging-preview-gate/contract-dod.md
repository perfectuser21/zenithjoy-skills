# Contract DoD — 07171650-staging-preview-gate

> **Sprint**: user_facing 交付 staging 预览闸进合同法律
> **Task ID**: 8589b916-9b71-4dd8-a986-76670229b06d
> **journey_type**: autonomous
> **版本目标**: proposer v9.16.0 + report v6.9.0

---

## [ARTIFACT] 产出物清单

- [ ] [ARTIFACT] `harness-contract-proposer/SKILL.md` 版本更新为 `9.16.0`，changelog 含 9.16.0 条目
- [ ] [ARTIFACT] `harness-contract-proposer/SKILL.md` 含完整「staging 预览闸」硬规则段（步骤A/B/C + Cecelia通知式 + ZJ阻塞式 + autonomous豁免）
- [ ] [ARTIFACT] `harness-report/SKILL.md` 版本更新为 `6.9.0`，changelog 含 6.9.0 条目
- [ ] [ARTIFACT] `harness-report/SKILL.md` Phase A Step 5 之后含 Step 5.5 段（仅 user_facing 执行 + Bark推送 + Brain PATCH + 非阻断声明）

---

## [BEHAVIOR] 行为验证清单

- [ ] [BEHAVIOR] [L2] proposer SKILL.md 版本号已 bump 至 9.16.0
  动作: 检查 `harness-contract-proposer/SKILL.md` frontmatter version 字段
  预期观察: 文件首行 version 字段为 `9.16.0`
  Test: manual:bash
  ```bash
  grep -qE "^version: 9\.16\.0" harness-contract-proposer/SKILL.md \
    || { echo "FAIL: proposer 版本未 bump 到 9.16.0"; exit 1; }
  echo "OK: proposer version=9.16.0"
  ```

- [ ] [BEHAVIOR] [L2] proposer SKILL.md 含 staging 预览闸关键词三元组（通知式/阻塞式/promote_after）
  动作: grep 检查 `harness-contract-proposer/SKILL.md` 关键内容
  预期观察: 文件中同时存在「staging 预览闸」「通知式」「阻塞式」「promote_after」四个关键词
  Test: manual:bash
  ```bash
  grep -q "staging 预览闸" harness-contract-proposer/SKILL.md \
    || { echo "FAIL: 无 staging 预览闸段"; exit 1; }
  grep -q "通知式" harness-contract-proposer/SKILL.md \
    || { echo "FAIL: 无通知式条款"; exit 1; }
  grep -q "阻塞式" harness-contract-proposer/SKILL.md \
    || { echo "FAIL: 无阻塞式条款"; exit 1; }
  grep -q "promote_after" harness-contract-proposer/SKILL.md \
    || { echo "FAIL: 无 promote_after 字段"; exit 1; }
  echo "OK: staging 预览闸关键词三元组验证通过"
  ```

- [ ] [BEHAVIOR] [L2] proposer SKILL.md autonomous 豁免声明存在且 autonomous 不被错误纳入
  动作: grep 检查 autonomous 相关内容正反两侧
  预期观察: 有豁免声明（autonomous 不受约束/零回归/不强制），且不存在「autonomous 必须 staging」类语句
  Test: manual:bash
  ```bash
  grep -qE "autonomous.*不受本规则|autonomous.*零回归|autonomous.*不强制|autonomous.*不受约束" harness-contract-proposer/SKILL.md \
    || { echo "FAIL: 无 autonomous 豁免声明"; exit 1; }
  if grep -qE "autonomous.*必须.*staging|autonomous.*强制.*staging|autonomous.*要求.*staging" harness-contract-proposer/SKILL.md; then
    echo "FAIL: autonomous 被错误纳入 staging 强制流程（INV-1 违反）"
    exit 1
  fi
  echo "OK: autonomous 豁免声明正确，零回归通过"
  ```

- [ ] [BEHAVIOR] [L2] harness-report SKILL.md 版本号已 bump 至 6.9.0，且含 Step 5.5 段
  动作: 检查 `harness-report/SKILL.md` 版本字段和 Step 5.5 内容
  预期观察: version=6.9.0，文件中存在 Step 5.5（含 promote_after 和 approval_required）
  Test: manual:bash
  ```bash
  grep -qE "^version: 6\.9\.0" harness-report/SKILL.md \
    || { echo "FAIL: report 版本未 bump 到 6.9.0"; exit 1; }
  grep -q "5\.5" harness-report/SKILL.md \
    || { echo "FAIL: harness-report 无 Step 5.5"; exit 1; }
  grep -q "promote_after" harness-report/SKILL.md \
    || { echo "FAIL: report Step 5.5 无 promote_after"; exit 1; }
  grep -q "approval_required" harness-report/SKILL.md \
    || { echo "FAIL: report Step 5.5 无 approval_required"; exit 1; }
  echo "OK: harness-report version=6.9.0 且 Step 5.5 内容完整"
  ```

- [ ] [BEHAVIOR] [L2] harness-report Phase B db-update 调用保持不变（INV-4）
  动作: 检查 `harness-report/SKILL.md` 中 db-update 引用仍存在
  预期观察: Phase B 部分仍含「db-update」字样，调用链未被打断
  Test: manual:bash
  ```bash
  grep -q "db-update" harness-report/SKILL.md \
    || { echo "FAIL: harness-report Phase B db-update 调用丢失（INV-4 违反）"; exit 1; }
  echo "OK: Phase B db-update 不变量通过"
  ```

- [ ] [BEHAVIOR] [L2] Step 5.5 明确限定仅 user_facing 执行
  动作: 检查 Step 5.5 段落是否含 user_facing 限定语
  预期观察: Step 5.5 段落内含「user_facing」限定，不对 autonomous 产生约束
  Test: manual:bash
  ```bash
  # 获取 Step 5.5 附近内容，检查 user_facing 限定词
  grep -A 5 "5\.5" harness-report/SKILL.md | grep -q "user_facing" \
    || grep -B 2 "5\.5" harness-report/SKILL.md | grep -q "user_facing" \
    || { echo "FAIL: Step 5.5 附近未发现 user_facing 限定词"; exit 1; }
  echo "OK: Step 5.5 user_facing 限定存在"
  ```

---

## [BEHAVIOR] INV 铁律覆盖

- [ ] [BEHAVIOR] [L2] INV-1: autonomous 流程零回归验证
  Test: manual:bash
  ```bash
  grep -qE "autonomous.*必须.*staging|autonomous.*强制.*staging" harness-contract-proposer/SKILL.md \
    && { echo "FAIL: INV-1 违反：autonomous 被错误纳入"; exit 1; } || true
  echo "OK: INV-1 autonomous 零回归"
  ```

- [ ] [BEHAVIOR] [L2] INV-2: 两个 SKILL.md 版本均单调递增验证
  Test: manual:bash
  ```bash
  grep -qE "^version: 9\.16\.0" harness-contract-proposer/SKILL.md \
    || { echo "FAIL: INV-2 proposer 版本未递增到 9.16.0"; exit 1; }
  grep -qE "^version: 6\.9\.0" harness-report/SKILL.md \
    || { echo "FAIL: INV-2 report 版本未递增到 6.9.0"; exit 1; }
  echo "OK: INV-2 版本单调递增通过"
  ```

- [ ] [ARTIFACT] INV-3: 本 sprint 不实现 staging 脚本，SKILL 文本只写规则引用
  （验收方式：代码审查确认 SKILL.md 只有规则描述，无具体 staging 脚本实现）

- [ ] [BEHAVIOR] [L2] INV-4: harness-report Phase B db-update 调用不变
  Test: manual:bash
  ```bash
  grep -q "db-update" harness-report/SKILL.md \
    || { echo "FAIL: INV-4 违反：Phase B db-update 调用丢失"; exit 1; }
  echo "OK: INV-4 Phase B 不变"
  ```
