# Contract DoD — 07161730-l-level-contract-law

task_id: b6b6cca5-db2b-4a74-9ac2-27cefea48a9e
sprint_id: 07161730-l-level-contract-law
base_repo: zenithjoy-skills
锚定父路声明: 独立小路（无父路）— zenithjoy-skills 新工具链，无历史 golden_path 行

---

## BEHAVIOR 验收条目

- [ ] [BEHAVIOR] [L1] B1: golden-path-proposer/SKILL.md 含「验证等级承诺」列头关键词 Test: manual:bash grep -q "验证等级承诺" /workspace/golden-path-proposer/SKILL.md

- [ ] [BEHAVIOR] [L1] B2: golden-path-proposer/SKILL.md 含接缝步骤 L3 铁律（含「L3」和「三镜头」两词） Test: manual:bash grep -q "三镜头" /workspace/golden-path-proposer/SKILL.md && grep -q "L3" /workspace/golden-path-proposer/SKILL.md

- [ ] [BEHAVIOR] [L1] B3: harness-contract-proposer/SKILL.md 含 [L1|L2|L3] 格式标记且含 verification_level 字段声明 Test: manual:bash grep -qE "\[L1\|L2\|L3\]|\[L1\]|\[L2\]|\[L3\]" /workspace/harness-contract-proposer/SKILL.md && grep -q "verification_level" /workspace/harness-contract-proposer/SKILL.md

- [ ] [BEHAVIOR] [L1] B4: harness-contract-proposer/SKILL.md 含「锚定父路」声明规则 Test: manual:bash grep -q "锚定父路" /workspace/harness-contract-proposer/SKILL.md

- [ ] [BEHAVIOR] [L1] B5: harness-evaluator/SKILL.md 含 verification_level 字段不少于 2 处（顶层 + 条目级各一） Test: manual:bash test $(grep -c "verification_level" /workspace/harness-evaluator/SKILL.md) -ge 2

- [ ] [BEHAVIOR] [L1] B6: 三个 SKILL.md 版本号已 bump（golden-path-proposer 1.1.0 / harness-contract-proposer 9.13.0 / harness-evaluator 1.25.0） Test: manual:bash grep -q "1.1.0" /workspace/golden-path-proposer/SKILL.md && grep -q "9.13.0" /workspace/harness-contract-proposer/SKILL.md && grep -q "1.25.0" /workspace/harness-evaluator/SKILL.md

---

## Notes

- contract-gate: skipped (file not found, third-party repo)
- 本 sprint 全部为文本/文档改动，验证方式为 grep 文本断言，无 mock 边，无运行时链路
- 所有 manual:bash 命令可直接在 bash 中执行，grep -q 返回 0 即为 PASS
