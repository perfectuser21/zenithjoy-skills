# Harness Evaluator — 执行记录（Transcript）

## 执行时间
2026-05-30

## 任务描述
评估 `/tmp/eval-evaluator-fixtures/hollow-workflow.yml` 是否包含真实业务行为验证，判断是否允许触发 Final E2E。

---

## Step 1：读取 workflow 文件

执行命令：
```bash
cat /tmp/eval-evaluator-fixtures/hollow-workflow.yml
```

输出：
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

## Step 2：空壳检测分析

依据 harness-evaluator 技能文档中的 `windows_cloud` 空壳检测规则：

**业务步骤关键词扫描（BUSINESS_STEPS）：**
扫描对象：`node -e | npx | npm run | npm test | npm ci | vitest | playwright | curl | Invoke-RestMethod | session | publish | cookies | DOUYIN | Set-Content | New-Item | ConvertTo-Json | Write-Host.*PASS`

逐行检查：
- `Get-Item "zenithjoy-agent-setup.exe"` — 不匹配任何关键词
- `$file.Length -lt 1MB` — 不匹配任何关键词
- `Write-Host "File size OK: $($file.Length) bytes"` — 不匹配（Write-Host 但内容不含 "PASS"）

**BUSINESS_STEPS = 0**

**浅层检查关键词扫描（SHALLOW_ONLY）：**
扫描对象：`Test-Path | \.Length | \.Size | file.*exist | exist.*file`

逐行检查：
- `$file.Length -lt 1MB` — 匹配 `\.Length` ✓

**SHALLOW_ONLY = 1**

---

## Step 3：判定逻辑

```
if BUSINESS_STEPS == 0 AND SHALLOW_ONLY > 0:
    → 判定为空壳 workflow → FAIL，禁止触发
```

条件满足：
- BUSINESS_STEPS = 0 ✓
- SHALLOW_ONLY = 1 > 0 ✓

**判定：FAIL**

---

## Step 4：反作弊规则核查

依据 harness-evaluator 反作弊红线：

1. **禁止把 vitest 输出当 PASS 证据** — 本 workflow 无 vitest，不适用
2. **禁止以"代码看起来对"给 PASS** — 本 evaluator 未读源码，严格执行命令扫描，合规
3. **缺 [BEHAVIOR] Test: 命令** — 本次为 pre-trigger 空壳检测，workflow 本身即是被检测对象
4. **缺 jq -e 严匹配** — workflow 完全不含任何 jq 调用，FAIL 已在 Step 3 触发

全部红线合规。

---

## Step 5：写入结果文件

- 结果写入：`/tmp/eval-evaluator-001/eval-result.md`
- 记录写入：`/tmp/eval-evaluator-001/transcript.md`
- 复制到：`/Users/administrator/perfect21/zenithjoy-skills/harness-evaluator-workspace/iteration-2/eval-hollow-workflow-fail-before-trigger/with_skill/outputs/`

---

## 最终判定

```json
{
  "verdict": "FAIL",
  "failed_step": "workflow_content_check",
  "log_excerpt": "workflow agent-hollow-check 只包含文件大小检查（$file.Length），不含任何业务逻辑验证（node/npx/vitest/playwright/curl/Invoke-RestMethod）。合同 BEHAVIOR 断言无法通过此 workflow 真实验证。BUSINESS_STEPS=0, SHALLOW_ONLY=1。请更新 workflow 加入业务行为测试（如 Agent 安装启动 + API 健康检查 + Playwright 路径验证）后重新提交。"
}
```
