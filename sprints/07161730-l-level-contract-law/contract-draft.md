# Contract Draft — 07161730-l-level-contract-law

task_id: b6b6cca5-db2b-4a74-9ac2-27cefea48a9e
sprint_id: 07161730-l-level-contract-law
base_repo: zenithjoy-skills
branch: cp-07161659-ws-b6b6cca5
contract-gate: skipped (file not found, third-party repo)
proposer_version: 9.13.0

---

## 技术设计

### GP-01: golden-path-proposer/SKILL.md

**变更说明**：
- 在步骤表模板列头行新增「验证等级承诺」列（L1替身/L2服务端真验/L3真机真验）
- 补充示例行，含 L1/L2/L3 标注
- 在「铁律」段新增一条：接缝步骤（碰真机/生产env/真实第三方）承诺必须 L3，三镜头对抗审查需回应「凭什么这步只需替身」
- 版本号从 1.0.0 → 1.1.0，写 changelog 条目

**关键词目标**：`验证等级承诺`、`L3`、`三镜头`、`1.1.0`

### GP-02: harness-contract-proposer/SKILL.md

**变更说明**：
- 在 [BEHAVIOR] 条目格式说明段新增 [L1|L2|L3] 标记规范，注明与 judge #4004 解析约定一致（behavior_tests[i].verification_level 字段）
- 新增「锚定父路声明」规则段：sprint GP 段首行必须写「覆盖父路 <golden_path名或id> 第 N-M 步」或「独立小路（无父路）」，禁留空
- 版本号从 9.12.0 → 9.13.0，写 changelog 条目

**关键词目标**：`verification_level`、`锚定父路`、`[L1|L2|L3]`、`9.13.0`

### GP-03: harness-evaluator/SKILL.md

**变更说明**：
- 在顶层 verdict 输出结构（.brain-result.json）新增 `verification_level` 字段说明，缺省值 `L2`
- 在 behavior_tests 条目结构新增 `verification_level` 字段说明（逐条可独立覆盖）
- 版本号从 1.24.0 → 1.25.0，写 changelog 条目

**关键词目标**：`verification_level`（≥2 处，顶层 + 条目级）、`1.25.0`

---

## E2E 验收

```bash
# GP-01 断言
grep -q "验证等级承诺" /workspace/golden-path-proposer/SKILL.md && echo "B1: PASS" || echo "B1: FAIL"
grep -q "L3" /workspace/golden-path-proposer/SKILL.md && echo "L3: PASS" || echo "L3: FAIL"
grep -q "三镜头" /workspace/golden-path-proposer/SKILL.md && echo "三镜头: PASS" || echo "三镜头: FAIL"
grep -q "1.1.0" /workspace/golden-path-proposer/SKILL.md && echo "version 1.1.0: PASS" || echo "version 1.1.0: FAIL"

# GP-02 断言
grep -q "verification_level" /workspace/harness-contract-proposer/SKILL.md && echo "B3 verification_level: PASS" || echo "B3 verification_level: FAIL"
grep -q "锚定父路" /workspace/harness-contract-proposer/SKILL.md && echo "B4 锚定父路: PASS" || echo "B4 锚定父路: FAIL"
grep -qE "\[L1\|L2\|L3\]|\[L1\]|\[L2\]|\[L3\]" /workspace/harness-contract-proposer/SKILL.md && echo "B3 L级标记: PASS" || echo "B3 L级标记: FAIL"
grep -q "9.13.0" /workspace/harness-contract-proposer/SKILL.md && echo "version 9.13.0: PASS" || echo "version 9.13.0: FAIL"

# GP-03 断言
COUNT=$(grep -c "verification_level" /workspace/harness-evaluator/SKILL.md 2>/dev/null || echo 0)
[ "$COUNT" -ge 2 ] && echo "B5 verification_level x${COUNT}: PASS" || echo "B5 verification_level x${COUNT}: FAIL (需≥2处)"
grep -q "1.25.0" /workspace/harness-evaluator/SKILL.md && echo "version 1.25.0: PASS" || echo "version 1.25.0: FAIL"
```

---

## Test Contract 表

| # | WS | 测试文件 | BEHAVIOR 覆盖 | 预期红证据 |
|---|-----|---------|--------------|-----------|
| 1 | GP-01 | manual:bash grep | B1 验证等级承诺列头 | grep -q 失败 → 文件未改或关键词缺失 |
| 2 | GP-01 | manual:bash grep | B2 接缝步骤L3铁律+三镜头 | grep -q 失败 → 铁律段未写入 |
| 3 | GP-02 | manual:bash grep | B3 [L1\|L2\|L3]标记+verification_level | grep -q 失败 → 格式未加或字段名错 |
| 4 | GP-02 | manual:bash grep | B4 锚定父路声明规则 | grep -q 失败 → 新增规则段未写入 |
| 5 | GP-03 | manual:bash grep | B5 verification_level ≥2处 | grep -c <2 → 顶层或条目级字段缺一 |
| 6 | 全部 | manual:bash grep | B6 三文件版本号bump | grep -q 失败 → 版本号未更新 |

---

## 未覆盖真实链路清单

N/A — 本任务为纯文本/文档改动（三个 SKILL.md 文件），无运行时代码路径，无 API 调用，无数据库写入，无 UI 交互。验收完全依赖 grep 文本断言，已覆盖所有 FR。

---

## 禁 mock 边清单

N/A — 本任务为纯文本 grep 验证，无代码执行路径，无外部服务调用，无需 mock。grep 直接命中文件内容即为真实验证。

---

## 八要素 Checklist

| # | 要素 | 状态 | 说明 |
|---|------|------|------|
| 1 | 合同覆盖所有 FR | ✓ | FR-01~FR-08 均在 B1~B6 中有对应断言 |
| 2 | 每条 BEHAVIOR 有可执行验证命令 | ✓ | 全部为 `grep -q` 命令，可直接 bash 执行 |
| 3 | 失败语义已声明 | ✓ | 见下方「失败语义声明」段 |
| 4 | 验证等级标记 [L1/L2/L3] 已标注 | ✓ | contract-dod.md 每条 BEHAVIOR 均带 L 级标记 |
| 5 | 禁 mock 边已处理 | ✓ | N/A（纯文本，无 mock 边） |
| 6 | 未覆盖真实链路已说明 | ✓ | N/A（纯文本，无运行时链路） |
| 7 | contract-gate 已处理 | ✓ | skipped（第三方 repo，文件不存在） |
| 8 | 锚定父路声明已写入 | ✓ | 独立小路（无父路）— zenithjoy-skills 新工具链 |

---

## 判定点登记表

| 判定点 | 类型 | 命令 | 接缝级别 |
|--------|------|------|---------|
| 验证等级承诺列头存在 | grep 文本断言 | `grep -q "验证等级承诺" golden-path-proposer/SKILL.md` | L1 |
| 三镜头铁律存在 | grep 文本断言 | `grep -q "三镜头" golden-path-proposer/SKILL.md` | L1 |
| [L1\|L2\|L3] 标记格式存在 | grep 文本断言 | `grep -qE "\[L1\|L2\|L3\]" harness-contract-proposer/SKILL.md` | L1 |
| 锚定父路声明规则存在 | grep 文本断言 | `grep -q "锚定父路" harness-contract-proposer/SKILL.md` | L1 |
| verification_level ≥2处 | grep 计数断言 | `grep -c "verification_level" harness-evaluator/SKILL.md` ≥2 | L1 |
| 三文件版本号bump | grep 文本断言 | 分别 grep 1.1.0 / 9.13.0 / 1.25.0 | L1 |

无接缝判定点（L3 真机/生产环境）：本任务全部为文本编辑，不触碰真机/生产env/第三方服务，故无接缝判定点。显式标注 N/A。

---

## 锚定父路声明

本 sprint GP 段覆盖范围：**独立小路（无父路）**

说明：zenithjoy-skills 是新工具链，无历史 golden_path 行，三个 GP 均为独立小路，无需声明父路。

---

## 失败语义声明

- `grep -q` 返回非零 → 对应 BEHAVIOR 判定为 **FAIL**，不可绿灯合并
- `grep -c` 返回值 < 2 → B5 判定为 **FAIL**（verification_level 覆盖不足）
- 任意 BEHAVIOR FAIL → 本 sprint DoD 未达成，不可推进下一步
- 版本号未 bump → B6 FAIL，视为文件改动不完整
- contract-gate 已 skip（第三方 repo），不影响 BEHAVIOR 判定
