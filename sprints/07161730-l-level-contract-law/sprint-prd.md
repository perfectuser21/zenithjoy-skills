---
sprint_id: 07161730-l-level-contract-law
task_id: b6b6cca5-db2b-4a74-9ac2-27cefea48a9e
title: "建制W3: L级承诺进合同法律（skill文本侧）——GP提案模板/合同proposer加验证等级列+锚定父路声明"
decision_ref: 145014a4
base_repo: zenithjoy-skills
branch: cp-07161659-ws-b6b6cca5
---

## Invariant 约束

本 line 暂无历史 step/feature 级 invariant。

## 累积 FR

- FR-01: golden-path-proposer/SKILL.md 步骤表模板新增「验证等级承诺」列（L1替身/L2服务端真验/L3真机真验）
- FR-02: golden-path-proposer/SKILL.md 铁律新增：接缝步骤（碰真机/生产env/真实第三方）承诺必须 L3，三镜头对抗审查需回应「凭什么这步只需替身」
- FR-03: harness-contract-proposer/SKILL.md [BEHAVIOR] 条目格式新增 [L1|L2|L3] 标记，与 judge #4004 解析约定一致（behavior_tests[i].verification_level 字段）
- FR-04: harness-contract-proposer/SKILL.md 新增「锚定父路声明」规则：sprint GP 段首行必须写「覆盖父路 <golden_path名或id> 第 N-M 步」或「独立小路（无父路）」，禁留空
- FR-05: harness-evaluator/SKILL.md verdict 输出 .brain-result.json 顶层新增 verification_level 字段（缺省 L2）
- FR-06: harness-evaluator/SKILL.md behavior_tests 条目新增 verification_level 字段
- FR-07: 三个 SKILL.md 各自 bump 版本号并写 changelog 条目
- FR-08: 与 W2 judge #4004 schema 约定逐字一致：behavior_tests[i].verification_level = 'L1'|'L2'|'L3'，brainResult.verification_level = 'L1'|'L2'|'L3'

## NFR

- NFR-01: 新增段落可被 grep 断言验证（验收用 grep 逐文件检查关键词）
- NFR-02: 模板示例必须含 L 级列（L1/L2/L3 字样出现在示例表格行中）
- NFR-03: [L1]|[L2]|[L3] 标记格式与 judge 解析约定逐字一致（方括号包裹，大写字母）
- NFR-04: 三个文件改动互相独立，单文件可读性不降低

## Golden Path

### GP-01: 修改 golden-path-proposer/SKILL.md

步骤：
1. 读当前文件，定位「文档结构」段中的步骤表模板 [L3·真文件读取]
2. 在步骤表模板列头行新增「验证等级承诺」列，补示例行含 L1/L2/L3 标注 [L1·文本编辑]
3. 在「铁律」段新增第 N 条：接缝步骤承诺必须 L3 + 三镜头对抗审查规则 [L1·文本编辑]
4. bump 版本号（1.0.0 → 1.1.0），写 changelog 条目 [L1·文本编辑]
5. grep 验证：验证等级承诺、L3、三镜头 三词存在于文件中 [L1·grep验证]

### GP-02: 修改 harness-contract-proposer/SKILL.md

步骤：
1. 读当前文件，定位 [BEHAVIOR] 条目格式说明段 [L3·真文件读取]
2. 在 [BEHAVIOR] 格式说明中新增 [L1|L2|L3] 标记规范，注明与 judge 解析约定一致 [L1·文本编辑]
3. 新增「锚定父路声明」规则段：sprint GP 段首行必须写覆盖父路声明或独立小路声明，禁留空 [L1·文本编辑]
4. bump 版本号（9.12.0 → 9.13.0），写 changelog 条目 [L1·文本编辑]
5. grep 验证：verification_level、锚定父路、L1|L2|L3 三词存在于文件中 [L1·grep验证]

### GP-03: 修改 harness-evaluator/SKILL.md

步骤：
1. 读当前文件，定位 .brain-result.json 输出结构说明段 [L3·真文件读取]
2. 在顶层 verdict 输出新增 verification_level 字段说明（缺省 L2）[L1·文本编辑]
3. 在 behavior_tests 条目新增 verification_level 字段说明 [L1·文本编辑]
4. bump 版本号（1.24.0 → 1.25.0），写 changelog 条目 [L1·文本编辑]
5. grep 验证：verification_level 词存在于文件中（≥2 处覆盖顶层与条目级）[L1·grep验证]

## 验收断言

```bash
# GP-01 断言
grep -q "验证等级承诺" /workspace/golden-path-proposer/SKILL.md
grep -q "L3" /workspace/golden-path-proposer/SKILL.md
grep -q "三镜头" /workspace/golden-path-proposer/SKILL.md
grep -q "1.1.0" /workspace/golden-path-proposer/SKILL.md

# GP-02 断言
grep -q "verification_level" /workspace/harness-contract-proposer/SKILL.md
grep -q "锚定父路" /workspace/harness-contract-proposer/SKILL.md
grep -qE "\[L1\|L2\|L3\]|\[L1\]|\[L2\]|\[L3\]" /workspace/harness-contract-proposer/SKILL.md
grep -q "9.13.0" /workspace/harness-contract-proposer/SKILL.md

# GP-03 断言
grep -c "verification_level" /workspace/harness-evaluator/SKILL.md | grep -qv "^[01]$"
grep -q "1.25.0" /workspace/harness-evaluator/SKILL.md
```

journey_type: autonomous
target_environment: local_api
