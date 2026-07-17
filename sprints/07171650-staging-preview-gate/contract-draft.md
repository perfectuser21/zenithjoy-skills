# Sprint Contract Draft (Round 1)

> **Sprint**: 07171650-staging-preview-gate
> **Task ID**: 8589b916-9b71-4dd8-a986-76670229b06d
> **journey_type**: dev_pipeline（纯 SKILL 文档改动，bash grep 验收）
> **target_environment**: local_api
> **版本目标**: harness-contract-proposer v9.16.0 + harness-report v6.9.0

---

## 锚定父路声明

独立小路（无父路）—— 本 sprint 专项修改两个 SKILL.md 文档，不属于任何已有 Golden Path 的子步骤。

---

## Response Schema（推导来源: N/A — 任务无 HTTP 响应）

N/A — 本 sprint 是纯 SKILL 文档改动，无 HTTP 端点新增或修改。无 DB 写路径，无第三方 API 调用。

---

## 已知约束（来自回归测试 + 累积 FR）

- [INV-1] autonomous 流程零回归：`journey_type=autonomous` 的合同不得含 staging 预览步强制要求
- [INV-2] 版本号单调递增：proposer 9.15.0→9.16.0，report 6.8.0→6.9.0
- [INV-3] 本 sprint 不实现 staging 部署/promote 逻辑，只写引用方式进 SKILL 文本
- [INV-4] 不改 harness-report Phase B 逻辑（db-update 调用不变）
- [累积FR] context-manifest 端点不可达：`/api/brain/line/context-manifest` 返回 Cannot GET；累积 FR 加载 N/A

---

## 八要素需求规范

| 要素 | 说明 | 本次答案 |
|------|------|----------|
| **FR（做什么）** | 功能需求 | (1) harness-contract-proposer SKILL.md 新增「staging 预览闸」硬规则段，仅限 user_facing；(2) harness-report SKILL.md Phase A 新增 Step 5.5，仅 user_facing 时执行 |
| **NFR（做得多好）** | 非功能需求 | 无性能要求；版本 bump 准确写入 changelog；Bark/Brain PATCH 失败为 CONCERN 非阻断 |
| **Invariant（永不违反）** | 不变量 | autonomous 流程零回归（INV-1）；版本单调递增（INV-2）；不实现 staging 脚本（INV-3）；不动 Phase B（INV-4） |
| **判定点（怎么知道）** | 判断假设 | 见下方判定点登记表 |
| **保质期（何时过期）** | 失效时机 | N/A — SKILL 文档无保质期，随版本迭代持续有效 |
| **死亡告警（停了谁知道）** | 告警手段 | N/A — 纯文档，无运行时告警路径 |
| **失败语义（挂了怎么办）** | 故障策略 | N/A — 纯文档改动，无运行时失败路径 |
| **效果确认（已发≠已生效）** | 确认方式 | 通过 bash grep 验收：文档已写入 + 关键词存在即为生效 |

### 判定点登记表

（本任务无接缝判定点，N/A）— 本 sprint 是纯文档修改，无真机/RPA/外部状态推断。

### 失败语义声明

| 场景 | 失败行为 | 重试幂等？ | 降级策略 |
|------|----------|-----------|----------|
| SKILL.md 文件写入失败 | bash Write 工具报错，任务停止 | 是（重跑 generator 覆盖写） | 无降级，必须文件写入成功 |

### 输入对抗面

N/A — 本 sprint 无对外暴露 agent，纯文档改动。

---

## Golden Path

[proposer 读 PRD] → [改 harness-contract-proposer/SKILL.md] → [改 harness-report/SKILL.md] → [bash 断言验收]

---

### Step 1: 读取 PRD 确认改动范围
**来源**: `[FROM_PRD]` — PRD「本次变更范围」段

**可观测行为**: 改动范围明确：两个 SKILL.md 文件，各自 bump 版本，新增指定内容段落。

**验证命令**:
```bash
# 确认 PRD 文件存在且 task id 一致
test -f sprints/07171650-staging-preview-gate/sprint-prd.md || { echo "FAIL: PRD 缺失"; exit 1; }
grep -q "8589b916" sprints/07171650-staging-preview-gate/sprint-prd.md || { echo "FAIL: Task ID 不符"; exit 1; }
echo "OK: PRD 确认"
```

**硬阈值**: 文件存在 + Task ID 匹配

---

### Step 2: 修改 harness-contract-proposer/SKILL.md（v9.15.0 → v9.16.0）
**来源**: `[FROM_PRD]` — PRD「改动①」段

**可观测行为**:
- 版本号从 9.15.0 更新为 9.16.0
- changelog 新增 9.16.0 条目
- 合同末尾新增「staging 预览闸」硬规则段，三步（落 staging / Final E2E / Bark 推送）
- 明确写出 Cecelia 通知式（24h 无异议自动放行 + `promote_after`）和 ZJ 阻塞式（`approval_required: true`）
- 明确写出 autonomous 零回归豁免语句

**验证命令**:
```bash
grep -qE "^version: 9\.16\.0" harness-contract-proposer/SKILL.md || { echo "FAIL: 版本未 bump 到 9.16.0"; exit 1; }
grep -q "staging 预览闸" harness-contract-proposer/SKILL.md || { echo "FAIL: 无 staging 预览闸段"; exit 1; }
grep -q "通知式" harness-contract-proposer/SKILL.md || { echo "FAIL: 无通知式条款"; exit 1; }
grep -q "阻塞式" harness-contract-proposer/SKILL.md || { echo "FAIL: 无阻塞式条款"; exit 1; }
grep -q "promote_after" harness-contract-proposer/SKILL.md || { echo "FAIL: 无 promote_after 字段"; exit 1; }
grep -qE "autonomous.*不受本规则|autonomous.*零回归|autonomous.*不强制|autonomous.*不受约束" harness-contract-proposer/SKILL.md || { echo "FAIL: 无 autonomous 豁免"; exit 1; }
echo "OK: proposer SKILL.md 验证通过"
```

**硬阈值**: 所有 grep 均命中，无一漏项

---

### Step 3: 修改 harness-report/SKILL.md（v6.8.0 → v6.9.0）
**来源**: `[FROM_PRD]` — PRD「改动②」段

**可观测行为**:
- 版本号从 6.8.0 更新为 6.9.0
- changelog 新增 6.9.0 条目
- Step 5（飞书通知）之后新增 Step 5.5 段，明确标注「仅 journey_type=user_facing 时执行」
- Step 5.5 包含：Bark 推送 + Brain PATCH（Cecelia→`promote_after`；ZJ→`approval_required: true`）
- 明确 Step 5.5 失败属 CONCERN 非阻断

**验证命令**:
```bash
grep -qE "^version: 6\.9\.0" harness-report/SKILL.md || { echo "FAIL: report 版本未 bump 到 6.9.0"; exit 1; }
grep -q "5\.5" harness-report/SKILL.md || { echo "FAIL: harness-report 无 Step 5.5"; exit 1; }
grep -q "user_facing" harness-report/SKILL.md || { echo "FAIL: Step 5.5 无 user_facing 限定"; exit 1; }
grep -q "promote_after" harness-report/SKILL.md || { echo "FAIL: harness-report 无 promote_after"; exit 1; }
grep -q "approval_required" harness-report/SKILL.md || { echo "FAIL: harness-report 无 approval_required"; exit 1; }
echo "OK: harness-report SKILL.md 验证通过"
```

**硬阈值**: 所有 grep 均命中

---

### Step 4: autonomous 零回归不变量验证
**来源**: `[FROM_PRD]` — PRD INV-1 + INV-4

**可观测行为**:
- proposer SKILL.md 中不存在「autonomous 必须执行 staging」或类似强制语句
- harness-report Phase B 内容未被修改（db-update 调用仍在）

**验证命令**:
```bash
# 检查 autonomous 不被错误纳入
grep -qE "autonomous.*必须.*staging|autonomous.*强制.*staging|autonomous.*要求.*staging" harness-contract-proposer/SKILL.md \
  && { echo "FAIL: autonomous 被错误纳入 staging 流程"; exit 1; } || true

# 检查 Phase B 中 db-update 调用仍存在
grep -q "db-update" harness-report/SKILL.md || { echo "FAIL: harness-report Phase B db-update 调用丢失"; exit 1; }
echo "OK: autonomous 零回归 + Phase B 不变量验证通过"
```

**硬阈值**: autonomous 无错误纳入，db-update 调用保留

---

## E2E 验收

**journey_type**: dev_pipeline
**target_environment**: local_api（纯文档改动，bash grep 断言，本地执行）

```bash
#!/bin/bash
set -euo pipefail
# ============================================================
# Final E2E — staging 预览闸 SKILL 文档改动验收
# 执行位置：zenithjoy-skills repo 根目录（/workspace）
# ============================================================

echo "=== E2E 验收开始：07171650-staging-preview-gate ==="

# AC-1: proposer SKILL.md 关键词验收
echo "[AC-1] 验证 harness-contract-proposer/SKILL.md..."
grep -qE "^version: 9\.16\.0" harness-contract-proposer/SKILL.md \
  || { echo "FAIL AC-1a: proposer 版本未 bump 到 9.16.0"; exit 1; }
grep -q "staging 预览闸" harness-contract-proposer/SKILL.md \
  || { echo "FAIL AC-1b: 无 staging 预览闸段"; exit 1; }
grep -q "通知式" harness-contract-proposer/SKILL.md \
  || { echo "FAIL AC-1c: 无通知式条款"; exit 1; }
grep -q "阻塞式" harness-contract-proposer/SKILL.md \
  || { echo "FAIL AC-1d: 无阻塞式条款"; exit 1; }
grep -q "promote_after" harness-contract-proposer/SKILL.md \
  || { echo "FAIL AC-1e: 无 promote_after"; exit 1; }
grep -qE "autonomous.*不受本规则|autonomous.*零回归|autonomous.*不强制|autonomous.*不受约束" harness-contract-proposer/SKILL.md \
  || { echo "FAIL AC-1f: 无 autonomous 豁免声明"; exit 1; }
echo "OK: AC-1 proposer SKILL.md 通过"

# AC-2: harness-report SKILL.md 关键词验收
echo "[AC-2] 验证 harness-report/SKILL.md..."
grep -qE "^version: 6\.9\.0" harness-report/SKILL.md \
  || { echo "FAIL AC-2a: report 版本未 bump 到 6.9.0"; exit 1; }
grep -q "5\.5" harness-report/SKILL.md \
  || { echo "FAIL AC-2b: 无 Step 5.5"; exit 1; }
grep -q "promote_after" harness-report/SKILL.md \
  || { echo "FAIL AC-2c: report 无 promote_after"; exit 1; }
grep -q "approval_required" harness-report/SKILL.md \
  || { echo "FAIL AC-2d: report 无 approval_required"; exit 1; }
echo "OK: AC-2 harness-report SKILL.md 通过"

# AC-3: autonomous 零回归（INV-1）
echo "[AC-3] 验证 autonomous 零回归..."
if grep -qE "autonomous.*必须.*staging|autonomous.*强制.*staging" harness-contract-proposer/SKILL.md; then
  echo "FAIL AC-3: autonomous 被错误纳入 staging 强制流程"
  exit 1
fi
echo "OK: AC-3 autonomous 零回归通过"

# AC-4: Phase B 不变量（INV-4）
echo "[AC-4] 验证 harness-report Phase B db-update 不变..."
grep -q "db-update" harness-report/SKILL.md \
  || { echo "FAIL AC-4: Phase B db-update 调用丢失"; exit 1; }
echo "OK: AC-4 Phase B 不变量通过"

echo ""
echo "=== ALL E2E AC PASS === sprint: 07171650-staging-preview-gate ==="
```

---

## 真实调用方请求 shape

N/A — 本 sprint 纯文档改动，无 HTTP 端点，无调用方请求。

---

## 禁 mock 边清单

（本单纯文档改动，无接缝边，N/A）

本 sprint 只修改 SKILL.md 文本文件，不涉及任何模块间调用、DB 写路径、状态机或生命周期钩子，无需禁 mock 边约定。

---

## 未覆盖真实链路清单

（本合同无 mock 豁免，N/A）— 纯文档/SKILL 改动，所有验收均为 bash grep 断言文件内容，无第三方 API 调用。

- **注**: cecelia auto-staging-deploy / ZJ staging-promote 脚本真实路径（本 sprint SKILL 文本只写规则占位引用，不做真实实现）
