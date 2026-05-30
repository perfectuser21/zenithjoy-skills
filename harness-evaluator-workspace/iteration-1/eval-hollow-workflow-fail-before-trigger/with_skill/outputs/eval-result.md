# Eval 结果：空壳 Workflow 触发前 FAIL 验证

**Eval 场景**：空壳 workflow（仅 exe 文件大小检查）是否在触发前被 FAIL
**Skill 版本**：harness-evaluator v1.11.0
**执行时间**：2026-05-30
**模式**：模式 B（Final E2E，`IS_FINAL_E2E=true`）
**target_environment**：windows_cloud

---

## 执行步骤重现

### Step 0：确认模式

```
IS_FINAL_E2E=true → 模式 B — 最终 E2E
TARGET_ENV=windows_cloud
WINDOWS_CLOUD_WORKFLOW=agent-qr-windows-verify.yml
```

### Step B-1：提取 E2E 验收脚本

从 `contract-draft.md` 的 `## E2E 验收` 区块提取 `.ps1` 脚本，写入 `sprint_dir/e2e-verify.ps1`。
（本次 eval 聚焦 Step B-2 的 workflow 内容检查，B-1 假设已通过）

### Step B-2：windows_cloud 前置检查（v1.11.0 新规则）

**模拟空壳 workflow 内容**（eval 指定的场景）：

```yaml
steps:
  - name: 下载 installpack
    run: Invoke-WebRequest -Uri $url -OutFile "agent.tar.gz"
  - name: 验证 exe
    run: |
      if (-not (Test-Path "pack/zenithjoy-agent.exe")) { exit 1 }
      $size = (Get-Item "pack/zenithjoy-agent.exe").Length
      if ($size -lt 1000000) { exit 1 }
      Write-Host "PASS: exe $size bytes"
```

**Skill 执行的检测逻辑**：

```bash
WORKFLOW_FILE=".github/workflows/agent-qr-windows-verify.yml"

# 检查 1：workflow 文件是否存在
# → 文件存在，通过

# 检查 2：合同 contract-dod.md 是否有 [BEHAVIOR] 条目
BEHAVIOR_COUNT=$(grep -c '\[BEHAVIOR\]' "${SPRINT_DIR}/contract-dod.md")
# → 假设合同有 [BEHAVIOR] 条目（session 写入、DOUYIN_COOKIES 注入、vitest 回归），通过

# 检查 3：空壳检测
BUSINESS_STEPS=$(grep -cE "(node -e|npx|npm run|vitest|playwright|curl|Invoke-RestMethod|session|publish|cookies|DOUYIN)" "$WORKFLOW_FILE")
SHALLOW_ONLY=$(grep -cE "(Test-Path|\.Length|\.Size|file.*exist|exist.*file)" "$WORKFLOW_FILE")
```

**实际计算结果**：

| 指标 | 值 | 说明 |
|------|-----|------|
| `BUSINESS_STEPS` | **0** | 无 node/npx/npm run/vitest/playwright/curl/Invoke-RestMethod/session/publish/cookies/DOUYIN |
| `SHALLOW_ONLY` | **2** | 命中：`Test-Path`（1次）、`.Length`（1次）|
| 条件 `BUSINESS_STEPS == 0 && SHALLOW_ONLY > 0` | **TRUE** | 触发空壳判定 |

**判定结果**：

```
条件成立 → 直接输出 FAIL，不触发 gh workflow run
```

---

## 最终输出（brain-result.json）

```json
{
  "verdict": "FAIL",
  "task_id": "$TASK_ID",
  "failed_step": "workflow_content_check",
  "log_excerpt": "workflow agent-qr-windows-verify.yml 只包含文件存在/大小检查，不含任何业务逻辑验证（node/npx/vitest/playwright/curl）。合同 BEHAVIOR 断言无法通过此 workflow 真实验证。请更新 workflow 加入业务行为测试。workflow 前30行: steps:|  - name: 下载 installpack|    run: Invoke-WebRequest ...|  - name: 验证 exe|    run: |...|      if (-not (Test-Path ...)) { exit 1 }|      $size = (...).Length|..."
}
```

---

## 结论

**Evaluator 在触发 gh workflow run 之前就 FAIL 了。**

**原因**：skill v1.11.0 的 Step B-2 windows_cloud 前置检查第 3 条：
> workflow 只有文件存在/大小检查（`Test-Path`、`.Length`），无任何业务逻辑验证关键词（node/npx/vitest/playwright/curl 等）→ 判定为空壳 → 直接 FAIL

`gh workflow run` **从未被执行**，因为 evaluator 在内容检查阶段就终止。

---

## 附注：真实 workflow 的检测结果

实际 `/Users/administrator/perfect21/zenithjoy/.github/workflows/agent-qr-windows-verify.yml` 文件也会被判定为 FAIL，原因：

- 文件中有 `npm ci` 和 `npm test`，但 skill 的正则是 `npm run`（不匹配 `npm test`）
- 因此 `BUSINESS_STEPS=0`，`SHALLOW_ONLY=3`（含 `.Length`、`Test-Path`）
- 触发空壳判定

**这是 skill v1.11.0 的一个潜在 gap**：`npm test` 属于业务逻辑验证（运行 vitest 单元测试），但正则 `npm run` 无法匹配到它。真实 workflow 的 `unit-tests-windows` job 包含 vitest 单元测试，应当被识别为业务逻辑，但当前正则漏掉了 `npm test` 和 `npm ci` + test 的组合。

---

## 修复建议（给 Generator）

将 workflow `agent-qr-windows-verify.yml` 更新，在现有 exe 大小检查基础上补充真实业务验证步骤：

1. session 写入路径验证（对应合同 [BEHAVIOR]）
2. DOUYIN_COOKIES 注入验证（对应合同 [BEHAVIOR]）
3. vitest 回归测试（通过 `npm test` 或 `npx vitest run`）

其中 `npx vitest` 或 `npm run test` 可被 skill 正则识别为业务步骤，从而通过空壳检测。
