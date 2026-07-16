# Contract DoD — 07161800-gear-hotfix-shortflow

task_id: fcb459b5-c510-4f45-b41f-e71b100d94f1
sprint_id: 07161800-gear-hotfix-shortflow
base_repo: zenithjoy-skills
锚定父路声明: 独立小路（无父路）— zenithjoy-skills harness-controller SKILL.md gear=hotfix 短流程新增能力

---

## BEHAVIOR 验收条目

- [ ] [BEHAVIOR] [L1] B1: harness-controller/SKILL.md 含 HARNESS_GEAR 变量行且来源为 payload.gear Test: manual:bash grep -q "HARNESS_GEAR" /workspace/harness-controller/SKILL.md && grep -q "payload.gear" /workspace/harness-controller/SKILL.md

- [ ] [BEHAVIOR] [L1] B2: harness-controller/SKILL.md 含 gear=hotfix 短流程段（含 "gear=hotfix" 关键词）且含日志输出关键词 "skip proposer/reviewer GAN" Test: manual:bash grep -q "gear=hotfix" /workspace/harness-controller/SKILL.md && grep -q "skip proposer/reviewer GAN" /workspace/harness-controller/SKILL.md

- [ ] [BEHAVIOR] [L1] B3: harness-controller/SKILL.md 含两条安全阀铁律——安全阀①含 FATAL 与「禁止顺手改」语义，安全阀②含「缺锚定声明」与「拒绝 hotfix」与「回退全流程」关键词 Test: manual:bash grep -q "FATAL" /workspace/harness-controller/SKILL.md && grep -q "缺锚定声明" /workspace/harness-controller/SKILL.md && grep -q "拒绝 hotfix" /workspace/harness-controller/SKILL.md && grep -q "回退全流程" /workspace/harness-controller/SKILL.md

- [ ] [BEHAVIOR] [L1] B4: harness-controller/SKILL.md 版本号已 bump 至 2.8.0，changelog 含本次变更描述 Test: manual:bash grep -q "2.8.0" /workspace/harness-controller/SKILL.md

- [ ] [BEHAVIOR] [L1] B5: harness-controller/examples/hotfix-shortflow/ 目录下存在 contract-draft.md 与 contract-dod.md 两份示例文件，且 contract-dod.md 含 ≥4 条 [BEHAVIOR] 条目 Test: manual:bash ls /workspace/harness-controller/examples/hotfix-shortflow/contract-draft.md && ls /workspace/harness-controller/examples/hotfix-shortflow/contract-dod.md && test $(grep -c '\[BEHAVIOR\]' /workspace/harness-controller/examples/hotfix-shortflow/contract-dod.md) -ge 4

- [ ] [BEHAVIOR] [L1] B6: 默认档（无 gear 字段）流程路径不变——SKILL.md 同时含 HARNESS_GEAR 识别段与 proposer/GAN 关键词（证明全流程分支仍保留，零回归） Test: manual:bash grep -q "HARNESS_GEAR" /workspace/harness-controller/SKILL.md && grep -q "proposer" /workspace/harness-controller/SKILL.md && grep -q "GAN" /workspace/harness-controller/SKILL.md

---

## Notes

- contract-gate: skipped (file not found, third-party repo)
- 本 sprint 全部为文本/文档改动（SKILL.md 编辑 + 示例文件创建），验证方式为 grep 文本断言与 ls 文件存在断言，无 mock 边，无运行时链路
- 所有 manual:bash 命令可直接在 bash 中执行，命令返回 0 即为 PASS
- B3 安全阀铁律验收：四个关键词需同时命中；任一缺失 → FAIL
- B5 示例文件验收：两文件均须存在，且 dod 示例含 ≥4 [BEHAVIOR]；任一不满足 → FAIL
