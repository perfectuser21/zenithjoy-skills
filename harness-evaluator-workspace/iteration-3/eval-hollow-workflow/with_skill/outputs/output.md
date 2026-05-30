# Harness Evaluator — 空壳 Workflow 评估报告

## 评估目标

**Workflow 文件**：`/tmp/eval-evaluator-fixtures/hollow-workflow.yml`
**Sprint 类型**：windows_cloud Final E2E
**合同 [BEHAVIOR] 要求**：
1. session 写入路径验证
2. DOUYIN_COOKIES 注入验证
3. vitest 回归测试

---

## 读取到的 Workflow 内容

```yaml
name: agent-hollow-check
on:
  workflow_dispatch:
    inputs:
      artifact_path:
        description: 'Path to artifact'
        required: true

jobs:
  verify:
    runs-on: windows-latest
    steps:
      - name: Download artifact
        uses: actions/download-artifact@v3
        with:
          name: zenithjoy-agent

      - name: Check file exists
        shell: powershell
        run: |
          $file = Get-Item "zenithjoy-agent-setup.exe"
          if ($file.Length -lt 1MB) {
            throw "File too small"
          }
          Write-Host "File size OK: $($file.Length) bytes"
```

---

## 空壳检测分析

按照 harness-evaluator SKILL v1.11.0 的 windows_cloud 前置检查逻辑：

**业务步骤计数（BUSINESS_STEPS 正则）**：
检测模式：`node -e|npx|npm run|npm test|npm ci|vitest|playwright|curl|Invoke-RestMethod|session|publish|cookies|DOUYIN|Set-Content|New-Item|ConvertTo-Json|Write-Host.*PASS`

逐行扫描结果：
- `node -e`：❌ 未出现
- `npx`：❌ 未出现
- `npm run` / `npm test` / `npm ci`：❌ 未出现
- `vitest`：❌ 未出现
- `playwright`：❌ 未出现
- `curl`：❌ 未出现
- `Invoke-RestMethod`：❌ 未出现
- `session`：❌ 未出现
- `publish`：❌ 未出现
- `cookies` / `DOUYIN`：❌ 未出现
- `Set-Content` / `New-Item` / `ConvertTo-Json`：❌ 未出现
- `Write-Host.*PASS`：❌ 未出现（`Write-Host "File size OK:..."` 不含 `PASS`）

**BUSINESS_STEPS = 0**

**浅层检查计数（SHALLOW_ONLY 正则）**：
检测模式：`Test-Path|\.Length|\.Size|file.*exist|exist.*file`

逐行扫描结果：
- `$file.Length -lt 1MB`：✅ 匹配 `\.Length`
- `Write-Host "File size OK: $($file.Length) bytes"`：✅ 匹配 `\.Length`

**SHALLOW_ONLY = 2**

**空壳判定条件**：`BUSINESS_STEPS == 0 && SHALLOW_ONLY > 0` → **成立**

---

## 合同 [BEHAVIOR] 覆盖性验证

| 合同 BEHAVIOR 要求 | workflow 中是否存在 | 结论 |
|---|---|---|
| session 写入路径验证 | ❌ 无任何 session 相关命令 | 未覆盖 |
| DOUYIN_COOKIES 注入验证 | ❌ 无 DOUYIN 或 cookies 关键词 | 未覆盖 |
| vitest 回归测试 | ❌ 无 vitest/npm test 命令 | 未覆盖 |

三条合同 BEHAVIOR 断言全部未在 workflow 中体现。workflow 仅检查安装包文件大小（`$file.Length`），与业务逻辑验证完全无关。

---

## 结论

**判定：FAIL**

**理由**：

1. **空壳检测命中**：workflow `agent-hollow-check.yml` 只包含文件大小检查（`$file.Length -lt 1MB`），没有任何业务逻辑验证步骤（BUSINESS_STEPS = 0，SHALLOW_ONLY = 2）。

2. **合同 BEHAVIOR 零覆盖**：合同要求的三条 BEHAVIOR 断言（session 写入路径验证、DOUYIN_COOKIES 注入验证、vitest 回归测试）在 workflow 中全部缺失。即使触发此 workflow 并成功执行，也无法验证任何业务行为，属于典型"假绿"陷阱。

3. **无法触发 Final E2E**：此 workflow 不能作为 windows_cloud Final E2E 的执行载体。触发它只会验证安装包文件是否存在且大小超过 1MB，与合同要求的真实业务验证毫无关联。

**修复方向**：

更新 workflow，加入以下步骤：
- **session 写入验证**：在 runner 上运行 `node -e` 或 PowerShell 脚本，检查 session 文件写入指定路径，验证内容结构正确（如含 `cookie`/`userId` 字段）
- **DOUYIN_COOKIES 注入验证**：通过 `$env:DOUYIN_COOKIES` 或 `Invoke-RestMethod` 验证 cookies 值已正确注入运行时环境
- **vitest 回归测试**：加入 `npm ci && npm test` 或 `npx vitest run` 步骤，确保回归测试套件在 windows-latest runner 上通过

---

## 对应 brain-result.json（模拟输出）

```json
{
  "verdict": "FAIL",
  "task_id": "$TASK_ID",
  "failed_step": "workflow_content_check",
  "log_excerpt": "workflow agent-hollow-check.yml 只包含文件存在/大小检查（BUSINESS_STEPS=0，SHALLOW_ONLY=2），不含任何业务逻辑验证（node/npx/vitest/playwright/curl/DOUYIN/session）。合同 3 条 BEHAVIOR 断言（session 写入路径验证、DOUYIN_COOKIES 注入验证、vitest 回归测试）全部未覆盖。请更新 workflow 加入业务行为测试步骤。"
}
```
