# Sprint Contract Draft (Round 1)

**Sprint**: [BEHAVIOR] 三段式剧本格式升级（proposer + evaluator SKILL.md）
**Task ID**: 38c0c94e-c7db-4252-97cb-f6e066cc2fc8

---

## 锚定父路声明

独立小路（无父路）— 本 sprint 为 harness 工具链文本升级，修改 skill 定义文件，无关联已有 Golden Path。

---

## Response Schema（推导来源: N/A — 任务无 HTTP 响应）

N/A — 本 sprint 任务为修改 SKILL.md 文本文件，无 HTTP 端点响应。Reviewer 第 6 维自动满分。

---

## 已知约束（来自回归测试）

（暂无已知约束）— zenithjoy-skills repo 无 `*.test.ts` 文件，无历史回归约束。

context-manifest: unavailable（BRAIN_URL=http://host.docker.internal:5221，容器内不可达）

---

## 禁 mock 边清单

（本单纯文档/工具链文本改动，无接缝边，N/A）

本 sprint 仅修改 `harness-contract-proposer/SKILL.md` 和 `harness-evaluator/SKILL.md` 两个纯文本文件，不涉及调度/状态机/跨模块数据传递/生命周期钩子/DB 写路径，无任何代码层接缝边需要禁 mock。

---

## 未覆盖真实链路清单

（本合同无 mock 豁免，N/A）— 本 sprint 为纯文本改动，E2E 为 grep 机检，无任何 force_*/stub/假数据。

---

## 八要素需求规范

| 要素 | 说明 | 本次答案（必填，可 N/A） |
|------|------|--------------------------|
| **FR（做什么）** | 功能需求：系统对外承诺做什么 | 1. `harness-contract-proposer/SKILL.md` 新增三段式 [BEHAVIOR] 剧本格式（动作/预期观察/验证命令）+ until-loop 等待预算范式 + legacy 兼容标记 + 样例剧本；2. `harness-evaluator/SKILL.md` 新增按剧本逐步执行流程 + behavior_tests 新增 action/expected 字段（与 command/exit_code/log_tail 共存） |
| **NFR（做得多好）** | 非功能需求：性能/可靠性/并发阈值等 | 样例剧本等待预算 within 60s（PRD 显式）；改动向后兼容（存量纯命令写法标 legacy，不删除） |
| **Invariant（永不违反）** | 任何情况下不得打破的不变量 | generator 只推 branch，merge 权归 controller；.github/workflows/ 未经合同授权不可修改；存量合同不得回改；新字段 action/expected 与现有 command/exit_code/log_tail 共存（不替换） |
| **判定点（怎么知道）** | 对模糊现实的判断假设 | 见下方登记表 |
| **保质期（何时过期）** | 该能力/数据/token 何时失效 | SKILL.md 版本随 harness 演进持续更新，本次 version bump 后进入常规版本管理 |
| **死亡告警（停了谁知道）** | 该功能停止工作后的告警手段 | N/A — 纯文本文件改动，无运行时服务，通过 GAN 合同格式自查脚本检测不合规 |
| **失败语义（挂了怎么办）** | 故障时放行还是拦截？ | grep 机检 FAIL → proposer 重写到过为止；harness-evaluator 格式不合规 → GAN reviewer REVISION 打回 |
| **效果确认（已发≠已生效）** | 每个对外动作如何确认真实生效 | grep 机检 PASS（exit 0）= 关键词存在于 SKILL.md 正确位置 |

### 判定点登记表

（本任务无接缝判定点，N/A）— 本 sprint 为纯文本改动，不涉及 RPA/真机/外部状态推断，无接缝判定点。

### 失败语义声明

| 场景 | 失败行为 | 重试幂等？ | 降级策略 |
|------|----------|-----------|----------|
| grep 机检 FAIL（关键词缺失） | E2E 脚本 exit 1，evaluator FAIL | 是（改完重跑） | 重写 SKILL.md 对应段落，补充缺失关键词 |
| SKILL.md 文件不存在 | ARTIFACT [BEHAVIOR] FAIL | 是 | generator 创建/恢复文件 |

### 输入对抗面

N/A — 本 sprint 为工具链文本修改，不暴露 agent 接口，无外部输入攻击面。

---

## contract-gate: skipped (file not found, third-party repo)

---

## Golden Path

[proposer 读新模板] → [写三段式 BEHAVIOR：动作/预期观察/验证命令] → [evaluator 按剧本逐步执行] → [behavior_tests 带 action/expected 字段]

---

### Step 1: 修改 harness-contract-proposer/SKILL.md — 新增三段式 [BEHAVIOR] 剧本格式

**来源**: `[FROM_PRD]` — PRD「范围限定」段明确："harness-contract-proposer/SKILL.md：三段式模板、until-loop 范式、legacy 标记、样例剧本、version bump"

**可观测行为**: `harness-contract-proposer/SKILL.md` 包含三段式 [BEHAVIOR] 模板（动作/预期观察/验证命令三段），包含 until-loop 等待预算范式，包含 legacy 兼容标记，包含样例剧本（"点设置 → within 60s 收到消息"），version 更新至 9.14.0。

**验证命令**:
```bash
P="/workspace/harness-contract-proposer/SKILL.md"
grep -q "动作" "$P" || { echo "FAIL: 缺 '动作' 关键词"; exit 1; }
grep -q "预期观察" "$P" || { echo "FAIL: 缺 '预期观察' 关键词"; exit 1; }
grep -q "验证命令" "$P" || { echo "FAIL: 缺 '验证命令' 关键词"; exit 1; }
grep -q "until" "$P" || { echo "FAIL: 缺 until-loop 范式"; exit 1; }
grep -q "legacy" "$P" || { echo "FAIL: 缺 legacy 兼容标记"; exit 1; }
grep -qE "within|60s" "$P" || { echo "FAIL: 缺样例等待预算（within/60s）"; exit 1; }
echo "OK: proposer SKILL.md 三段式格式验证通过"
```

**硬阈值**: 以上所有 grep 全部命中，exit 0

---

### Step 2: 修改 harness-evaluator/SKILL.md — 新增剧本逐步执行流程 + behavior_tests action/expected 字段

**来源**: `[FROM_PRD]` — PRD「范围限定」段明确："harness-evaluator/SKILL.md：按剧本逐步执行流程、behavior_tests action/expected 字段、version bump"

**可观测行为**: `harness-evaluator/SKILL.md` 包含按剧本逐步执行说明（执行动作 → 轮询预期观察 within 预算 → 跑验证命令），behavior_tests 条目新增 action/expected 字段说明（与 command/exit_code/log_tail 共存），version 更新至 1.26.0。

**验证命令**:
```bash
E="/workspace/harness-evaluator/SKILL.md"
grep -q "action" "$E" || { echo "FAIL: 缺 'action' 字段"; exit 1; }
grep -q "expected" "$E" || { echo "FAIL: 缺 'expected' 字段"; exit 1; }
grep -q "log_tail" "$E" || { echo "FAIL: log_tail 字段被删除（必须与 action/expected 共存）"; exit 1; }
grep -q "command" "$E" || { echo "FAIL: command 字段被删除（必须保留）"; exit 1; }
grep -q "exit_code" "$E" || { echo "FAIL: exit_code 字段被删除（必须保留）"; exit 1; }
echo "OK: evaluator SKILL.md action/expected 字段验证通过"
```

**硬阈值**: 以上所有 grep 全部命中，exit 0（特别验证 command/exit_code/log_tail 未被删除）

---

### Step 3: 三段式样例剧本完整性验证

**来源**: `[FROM_PRD]` — PRD Golden Path 第 1 步："proposer 读新模板，写出三段式 [BEHAVIOR]（含 until-loop 等待预算）"；PRD 背景："点设置 → 应该收到消息"

**来源**: `[AI_ADDED]` — 理由：样例剧本须同时体现"动作"+"预期观察"+"验证命令"+"until-loop 等待"四要素，缺一条都让 generator 无法理解格式；单独立一步确保合同显式覆盖样例完整性，防止 generator 只写了词但没写出完整剧本结构。

**可观测行为**: proposer SKILL.md 中存在完整样例剧本，三段式结构清晰（动作段、预期观察段、验证命令段），until-loop 等待预算写法可复制使用。

**验证命令**:
```bash
P="/workspace/harness-contract-proposer/SKILL.md"
# 验证样例剧本三段式结构关键词齐全
grep -q "动作" "$P" && grep -q "预期观察" "$P" && grep -q "验证命令" "$P" || { echo "FAIL: 三段式关键词不全"; exit 1; }
# 验证 until-loop 等待预算写法存在
grep -q "until" "$P" || { echo "FAIL: 缺 until-loop 等待预算写法"; exit 1; }
# 验证样例剧本关键场景词存在（点设置/消息 或 within）
grep -qE "within|60s|设置|消息" "$P" || { echo "FAIL: 缺样例剧本场景关键词"; exit 1; }
echo "OK: 样例剧本完整性验证通过"
```

**硬阈值**: 三段式关键词 + until-loop + 样例场景词全部命中，exit 0

---

### Step 4: legacy 兼容标记 + version bump 验证

**来源**: `[FROM_PRD]` — PRD「范围限定」："存量纯命令写法标 legacy 兼容不回改"；"version bump"

**来源**: `[AI_ADDED]` — 理由：version bump 是 SKILL.md 规范约定，不验证则 generator 可能忘记，下游 changelog 溯源断裂。

**可观测行为**: proposer SKILL.md version 字段更新（≥ 9.14.0），evaluator SKILL.md version 字段更新（≥ 1.26.0）；两个文件各自有 legacy 标记或兼容说明。

**验证命令**:
```bash
P="/workspace/harness-contract-proposer/SKILL.md"
E="/workspace/harness-evaluator/SKILL.md"
# 验证 proposer version bump（从 9.13.0 升级）
grep -qE "version: 9\.(1[4-9]|[2-9][0-9])\." "$P" || { echo "FAIL: proposer version 未升级到 9.14.x+"; exit 1; }
# 验证 evaluator version bump（从 1.25.0 升级）
grep -qE "version: 1\.2[6-9]\." "$E" || { echo "FAIL: evaluator version 未升级到 1.26.x+"; exit 1; }
# 验证 legacy 兼容标记存在于 proposer
grep -q "legacy" "$P" || { echo "FAIL: proposer 缺 legacy 兼容标记"; exit 1; }
echo "OK: legacy 标记 + version bump 验证通过"
```

**硬阈值**: 两文件 version 均升级，proposer 含 legacy 标记，exit 0

---

## E2E 验收

**journey_type**: autonomous
**target_environment**: local_api

> 本 sprint 产物为纯文本 SKILL.md，E2E 为 grep 机检格式合规性（PRD 显式指定此方式）。

```bash
#!/bin/bash
set -euo pipefail

PROPOSER_SKILL=/workspace/harness-contract-proposer/SKILL.md
EVALUATOR_SKILL=/workspace/harness-evaluator/SKILL.md

echo "=== Step 1: proposer SKILL.md three-section format ==="
node -e "
var c=require('fs').readFileSync(process.argv[1],'utf8');
['动作','预期观察','验证命令','until','legacy'].forEach(function(kw){
  if(!c.includes(kw)){process.stderr.write('FAIL: missing '+kw+'\n');process.exit(1);}
});
if(!(/within|60s/.test(c))){process.stderr.write('FAIL: missing wait budget\n');process.exit(1);}
process.stdout.write('PASS: proposer format ok\n');
" -- /workspace/harness-contract-proposer/SKILL.md

echo "=== Step 2: evaluator SKILL.md action/expected fields ==="
node -e "
var c=require('fs').readFileSync(process.argv[1],'utf8');
['action','expected','log_tail','command','exit_code'].forEach(function(kw){
  if(!c.includes(kw)){process.stderr.write('FAIL: missing '+kw+'\n');process.exit(1);}
});
process.stdout.write('PASS: evaluator fields ok\n');
" -- /workspace/harness-evaluator/SKILL.md

echo "=== Step 3: version bump ==="
node -e "
var p=require('fs').readFileSync(process.argv[1],'utf8');
var e=require('fs').readFileSync(process.argv[2],'utf8');
if(!/version: 9\.(1[4-9]|[2-9]\d)\./.test(p)){process.stderr.write('FAIL: proposer version\n');process.exit(1);}
if(!/version: 1\.2[6-9]\./.test(e)){process.stderr.write('FAIL: evaluator version\n');process.exit(1);}
process.stdout.write('PASS: version bump ok\n');
" -- /workspace/harness-contract-proposer/SKILL.md /workspace/harness-evaluator/SKILL.md

echo ""
echo "OK: three-section scenario format upgrade - all checks passed"
```

---

## Test Contract

| 功能 | Test File | BEHAVIOR 覆盖 | 预期红证据 |
|---|---|---|---|
| proposer SKILL.md 三段式格式 | `tests/skill-format.test.ts` | proposer 三段式关键词存在 | → 1 failure（文件改动前 grep 不到） |
| evaluator SKILL.md action/expected 字段 | `tests/skill-format.test.ts` | evaluator action/expected 字段存在 | → 1 failure |
| version bump 合规 | `tests/skill-format.test.ts` | proposer version 升级到 9.14.x+、evaluator version 升级到 1.26.x+ | → 2 failures |
| legacy 兼容标记 | `tests/skill-format.test.ts` | proposer legacy 标记存在 | → 1 failure |
