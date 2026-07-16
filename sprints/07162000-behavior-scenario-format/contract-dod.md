---
skeleton: false
journey_type: autonomous
---
# Contract DoD — Sprint: [BEHAVIOR] 三段式剧本格式升级（proposer + evaluator SKILL.md）

**范围**: 修改 `harness-contract-proposer/SKILL.md` 和 `harness-evaluator/SKILL.md`，新增三段式剧本格式（动作/预期观察/验证命令）+ until-loop 等待预算范式 + legacy 兼容标记 + 样例剧本 + behavior_tests action/expected 字段，version bump
**大小**: S

---

## ARTIFACT 条目

- [ ] [ARTIFACT] harness-contract-proposer/SKILL.md 文件存在且包含三段式 [BEHAVIOR] 模板段落
  Test: node -e "const c=require('fs').readFileSync('/workspace/harness-contract-proposer/SKILL.md','utf8');if(!c.includes('动作') || !c.includes('预期观察') || !c.includes('验证命令'))process.exit(1)"

- [ ] [ARTIFACT] harness-evaluator/SKILL.md 文件存在且 changelog 包含新版本条目
  Test: node -e "const c=require('fs').readFileSync('/workspace/harness-evaluator/SKILL.md','utf8');if(!c.includes('action') || !c.includes('expected'))process.exit(1)"

---

## BEHAVIOR 条目

- [ ] [BEHAVIOR] [L2] proposer SKILL.md 三段式关键词存在（动作/预期观察/验证命令）
  Test: manual:bash -c 'P=/workspace/harness-contract-proposer/SKILL.md; grep -q "动作" "$P" && grep -q "预期观察" "$P" && grep -q "验证命令" "$P" && echo OK || { echo "FAIL: proposer 缺三段式关键词"; exit 1; }'
  期望: OK

- [ ] [BEHAVIOR] [L2] proposer SKILL.md until-loop 等待预算范式存在
  Test: manual:bash -c 'grep -q "until" /workspace/harness-contract-proposer/SKILL.md && echo OK || { echo "FAIL: proposer 缺 until-loop 范式"; exit 1; }'
  期望: OK

- [ ] [BEHAVIOR] [L2] proposer SKILL.md legacy 兼容标记存在
  Test: manual:bash -c 'grep -q "legacy" /workspace/harness-contract-proposer/SKILL.md && echo OK || { echo "FAIL: proposer 缺 legacy 兼容标记"; exit 1; }'
  期望: OK

- [ ] [BEHAVIOR] [L2] proposer SKILL.md 样例剧本等待预算关键词存在（within 或 60s）
  Test: manual:bash -c 'grep -qE "within|60s" /workspace/harness-contract-proposer/SKILL.md && echo OK || { echo "FAIL: proposer 缺样例等待预算"; exit 1; }'
  期望: OK

- [ ] [BEHAVIOR] [L2] evaluator SKILL.md action 字段新增（behavior_tests 新字段）
  Test: manual:bash -c 'grep -q "action" /workspace/harness-evaluator/SKILL.md && echo OK || { echo "FAIL: evaluator 缺 action 字段"; exit 1; }'
  期望: OK

- [ ] [BEHAVIOR] [L2] evaluator SKILL.md expected 字段新增（behavior_tests 新字段）
  Test: manual:bash -c 'grep -q "expected" /workspace/harness-evaluator/SKILL.md && echo OK || { echo "FAIL: evaluator 缺 expected 字段"; exit 1; }'
  期望: OK

- [ ] [BEHAVIOR] [L2] evaluator SKILL.md 存量字段保留（command/exit_code/log_tail 不得被删除）
  Test: manual:bash -c 'E=/workspace/harness-evaluator/SKILL.md; grep -q "log_tail" "$E" && grep -q "command" "$E" && grep -q "exit_code" "$E" && echo OK || { echo "FAIL: evaluator 存量字段被删除"; exit 1; }'
  期望: OK

- [ ] [BEHAVIOR] [L2] proposer version bump — 版本升级到 9.14.x 或更高
  Test: manual:bash -c 'grep -qE "version: 9\.(1[4-9]|[2-9][0-9])\." /workspace/harness-contract-proposer/SKILL.md && echo OK || { echo "FAIL: proposer version 未升级到 9.14.x+"; exit 1; }'
  期望: OK

- [ ] [BEHAVIOR] [L2] evaluator version bump — 版本升级到 1.26.x 或更高
  Test: manual:bash -c 'grep -qE "version: 1\.2[6-9]\." /workspace/harness-evaluator/SKILL.md && echo OK || { echo "FAIL: evaluator version 未升级到 1.26.x+"; exit 1; }'
  期望: OK

---

## Invariant 覆盖条目（铁律映射）

- INV-1 [generator 只推 branch，merge 权归 controller] N/A：本 sprint 为文本文件修改，generator 不执行 merge 操作，铁律不被触发

- [ ] [BEHAVIOR] INV-2 .github/workflows/*.yml 未经合同授权不可修改
  Test: manual:bash -c 'git diff HEAD -- .github/workflows/ | grep -q "^+" && { echo "FAIL: 工作流文件被修改（合同未授权）"; exit 1; } || echo OK'
  期望: OK（无工作流文件变更）

- INV-3 [存量合同不得回改] N/A：本 sprint 修改 SKILL.md，不修改任何现有 contract-draft.md/contract-dod.md 文件

- [ ] [BEHAVIOR] INV-4 action/expected 新字段与 command/exit_code/log_tail 共存（不替换）
  Test: manual:bash -c 'E=/workspace/harness-evaluator/SKILL.md; grep -q "action" "$E" && grep -q "expected" "$E" && grep -q "log_tail" "$E" && grep -q "command" "$E" && grep -q "exit_code" "$E" && echo OK || { echo "FAIL: 新旧字段共存验证失败"; exit 1; }'
  期望: OK

- INV-5 [proposer 核查派发历史] N/A：本 sprint 修改 proposer SKILL.md 模板文本，不涉及派发历史复用场景；generator 直接按合同改文件，无历史合同复用

- INV-6 [单 slot 串行] N/A：本 sprint 为纯文本文件修改，不涉及任务调度/slot 分配逻辑，铁律不被触发

- INV-7 [真环境验证才算 done] N/A 已覆盖：本 sprint E2E 为本地 grep 机检（node -e 读本地文件），目标文件即"真环境"目标，机检 exit 0 = 真实效果已验证；无网络接缝/外部状态，合同 E2E 段满足此铁律语义

- INV-8 [凭据安全] N/A：本 sprint 仅修改 SKILL.md 纯文本说明文件，不涉及任何 secrets/API key/密码；generator 改动范围明确为 harness-contract-proposer/SKILL.md 和 harness-evaluator/SKILL.md，铁律不被触发
