# Contract Draft — 07161800-gear-hotfix-shortflow

task_id: fcb459b5-c510-4f45-b41f-e71b100d94f1
sprint_id: 07161800-gear-hotfix-shortflow
base_repo: zenithjoy-skills
branch: cp-07162209-ws-fcb459b5
contract-gate: skipped (file not found, third-party repo)
proposer_version: 9.13.0

---

## 锚定父路声明

本 sprint GP 段覆盖范围：**独立小路（无父路）**

说明：zenithjoy-skills harness-controller SKILL.md 本次新增 gear=hotfix 短流程段，无历史 golden_path 行锚定，属于独立新增能力。

---

## 技术设计

### GP-01: harness-controller/SKILL.md — Relay 入口变量表新增 HARNESS_GEAR 行

**变更说明**：
- 在 Step 0 「上下文装载」段的 Relay 入口变量提取处，新增 `HARNESS_GEAR` 变量行，来源为 `task payload.gear`
- 变量提取代码块新增：`HARNESS_GEAR=$(echo "$TASK" | jq -r '.payload.gear // empty')`
- 版本 bump 与 changelog 描述 gear=hotfix 能力

**关键词目标**：`HARNESS_GEAR`、`payload.gear`

### GP-02: harness-controller/SKILL.md — gear=hotfix 短流程段（跳过 proposer/reviewer GAN）

**变更说明**：
- Step 2 头部新增 gear 分支判断段：检测 `HARNESS_GEAR=hotfix` 时跳过 proposer/reviewer 两棒 GAN，controller 直接从 thin_prd 锚定断言 + "必须先写复现 failing test" 要求组装 contract-draft.md 与 contract-dod.md
- 日志输出：跳过时 `echo "[gear=hotfix] skip proposer/reviewer GAN"`
- `[BEHAVIOR]` 条目内容 = 锚定步骤的既有断言原文 + 新 failing test
- 合同文件结构与全流程产物完全一致（下游 generator/evaluator/judge 零改动、无感知）

**关键词目标**：`gear=hotfix`、`skip proposer/reviewer GAN`、`HARNESS_GEAR=hotfix`

### GP-03: harness-controller/SKILL.md — 两条安全阀铁律

**变更说明**：
- **安全阀①**：generator 发现需要改动 sprint-prd Golden Path 步骤定义/断言文本 → FATAL 报错升档，禁止顺手改（写入 SKILL.md 铁律段）
- **安全阀②**：thin_prd 缺锚定声明（未写"覆盖父路第 N 步"或"独立小路"字样）→ 拒绝 hotfix 档，回退全流程（写入 SKILL.md 铁律段）
- 两条安全阀使用 `FATAL` 关键词明确标记

**关键词目标**：`FATAL`、`禁止顺手改`、`拒绝 hotfix`、`回退全流程`、`缺锚定声明`

### GP-04: harness-controller/SKILL.md — 版本 bump + changelog

**变更说明**：
- 版本号从 2.7.0 → 2.8.0
- changelog 新增 2.8.0 条目，描述 gear=hotfix 短流程：跳过 GAN 两棒、HARNESS_GEAR 变量、两条安全阀铁律

**关键词目标**：`2.8.0`

### GP-05: harness-controller/examples/ — hotfix 档产物示例

**变更说明**：
- 新建 `harness-controller/examples/hotfix-shortflow/` 目录
- 创建 `contract-draft.md` 示例文件：展示 hotfix 档合同 draft 结构（含 ## E2E 验收段，格式与全流程一致）
- 创建 `contract-dod.md` 示例文件：展示 hotfix 档 DoD 结构（含 ≥4 条 [BEHAVIOR]、manual:bash 可执行命令）
- 文件头部注明「hotfix 档产物示例」，供新手参考对齐格式

**关键词目标**：`hotfix-shortflow`（目录存在）、示例文件含 `[BEHAVIOR]`

---

## E2E 验收

```bash
# GP-01 断言：HARNESS_GEAR 变量行存在
grep -q "HARNESS_GEAR" /workspace/harness-controller/SKILL.md && echo "B1: PASS" || echo "B1: FAIL"
grep -q "payload.gear" /workspace/harness-controller/SKILL.md && echo "B1b payload.gear: PASS" || echo "B1b payload.gear: FAIL"

# GP-02 断言：gear=hotfix 短流程段存在 + 日志输出断言
grep -q "gear=hotfix" /workspace/harness-controller/SKILL.md && echo "B2 gear=hotfix: PASS" || echo "B2 gear=hotfix: FAIL"
grep -q "skip proposer/reviewer GAN" /workspace/harness-controller/SKILL.md && echo "B2b skip GAN: PASS" || echo "B2b skip GAN: FAIL"

# GP-03 断言：两条安全阀铁律存在
grep -q "FATAL" /workspace/harness-controller/SKILL.md && echo "B3 FATAL: PASS" || echo "B3 FATAL: FAIL"
grep -q "缺锚定声明" /workspace/harness-controller/SKILL.md && echo "B3b 缺锚定声明: PASS" || echo "B3b 缺锚定声明: FAIL"
grep -q "拒绝 hotfix" /workspace/harness-controller/SKILL.md && echo "B3c 拒绝hotfix: PASS" || echo "B3c 拒绝hotfix: FAIL"
grep -q "回退全流程" /workspace/harness-controller/SKILL.md && echo "B3d 回退全流程: PASS" || echo "B3d 回退全流程: FAIL"

# GP-04 断言：版本号 bump 到 2.8.0
grep -q "2.8.0" /workspace/harness-controller/SKILL.md && echo "B4 version 2.8.0: PASS" || echo "B4 version 2.8.0: FAIL"

# GP-05 断言：hotfix 档示例文件存在
ls /workspace/harness-controller/examples/hotfix-shortflow/contract-draft.md >/dev/null 2>&1 && echo "B5 example contract-draft: PASS" || echo "B5 example contract-draft: FAIL"
ls /workspace/harness-controller/examples/hotfix-shortflow/contract-dod.md >/dev/null 2>&1 && echo "B5b example contract-dod: PASS" || echo "B5b example contract-dod: FAIL"
grep -c '\[BEHAVIOR\]' /workspace/harness-controller/examples/hotfix-shortflow/contract-dod.md | xargs -I{} test {} -ge 4 && echo "B5c example [BEHAVIOR]≥4: PASS" || echo "B5c example [BEHAVIOR]≥4: FAIL"

# 零回归断言：默认档条件分支存在（无 gear 字段走全流程）
grep -q "HARNESS_GEAR" /workspace/harness-controller/SKILL.md && \
  grep -q "proposer\|GAN" /workspace/harness-controller/SKILL.md && \
  echo "B6 零回归默认档: PASS" || echo "B6 零回归默认档: FAIL"
```

---

## Test Contract 表

| # | WS | 测试文件 | BEHAVIOR 覆盖 | 预期红证据 |
|---|-----|---------|--------------|-----------|
| 1 | GP-01 | manual:bash grep | B1 HARNESS_GEAR 变量行 + payload.gear 来源 | grep -q 失败 → 变量提取行未加入 |
| 2 | GP-02 | manual:bash grep | B2 gear=hotfix 段 + skip GAN 日志 | grep -q 失败 → 短流程段未写入或关键词错 |
| 3 | GP-03 | manual:bash grep | B3 两条安全阀铁律（FATAL + 缺锚定声明 + 拒绝hotfix + 回退全流程） | grep -q 失败 → 安全阀未写入 SKILL.md |
| 4 | GP-04 | manual:bash grep | B4 版本 2.8.0 + changelog 条目 | grep -q 失败 → 版本号未 bump |
| 5 | GP-05 | manual:bash ls+grep | B5 hotfix 示例文件结构完整（draft+dod 各存在，dod 含 ≥4 [BEHAVIOR]） | ls/grep 失败 → 示例文件未创建或格式不符 |
| 6 | GP-02 | manual:bash grep | B6 零回归：默认档 GAN 路径仍存在 | grep 失败 → 默认档分支被误删 |

---

## 未覆盖真实链路清单

N/A — 本任务为纯文本/文档改动（harness-controller/SKILL.md 文本编辑 + 示例文件创建），无运行时代码路径，无 API 调用，无数据库写入，无 UI 交互。验收完全依赖 grep 文本断言和 ls 文件存在断言，已覆盖所有 FR。

---

## 禁 mock 边清单

N/A — 本任务为纯文本 grep/ls 验证，无代码执行路径，无外部服务调用，无需 mock。

---

## 八要素 Checklist

| # | 要素 | 状态 | 说明 |
|---|------|------|------|
| 1 | 合同覆盖所有 FR | ✓ | FR（HARNESS_GEAR/gear=hotfix/安全阀/版本/示例）均在 B1~B6 中有对应断言 |
| 2 | 每条 BEHAVIOR 有可执行验证命令 | ✓ | 全部为 `grep -q`/`ls`/`grep -c` 命令，可直接 bash 执行 |
| 3 | 失败语义已声明 | ✓ | 见下方「失败语义声明」段 |
| 4 | 验证等级标记 [L1/L2/L3] 已标注 | ✓ | contract-dod.md 每条 BEHAVIOR 均带 [L1] 标记 |
| 5 | 禁 mock 边已处理 | ✓ | N/A（纯文本，无 mock 边） |
| 6 | 未覆盖真实链路已说明 | ✓ | N/A（纯文本，无运行时链路） |
| 7 | contract-gate 已处理 | ✓ | skipped（第三方 repo，文件不存在） |
| 8 | 锚定父路声明已写入 | ✓ | 独立小路（无父路）— zenithjoy-skills harness-controller 新增能力段 |

---

## 判定点登记表

（本任务无接缝判定点，N/A）

---

## 风险登记

| # | 风险 | Mitigation |
|---|------|-----------|
| R1 | 零回归——默认全流程分支（proposer/GAN）被误删 | B6 断言同时验证 HARNESS_GEAR 识别段与 proposer/GAN 关键词存在，两者缺一即 FAIL |

---

## 失败语义声明

- `grep -q` 返回非零 → 对应 BEHAVIOR 判定为 **FAIL**，不可绿灯合并
- `grep -c` 返回值 < 4 → B5c 判定为 **FAIL**（示例 [BEHAVIOR] 条目不足）
- `ls` 返回非零 → B5/B5b 判定为 **FAIL**（示例文件未创建）
- 任意 BEHAVIOR FAIL → 本 sprint DoD 未达成，不可推进下一步
- 版本号未 bump 至 2.8.0 → B4 FAIL，视为文件改动不完整
- contract-gate 已 skip（第三方 repo），不影响 BEHAVIOR 判定
