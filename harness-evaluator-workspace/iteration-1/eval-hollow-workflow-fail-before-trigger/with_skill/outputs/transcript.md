# Eval 执行 Transcript

**场景**：eval-hollow-workflow-fail-before-trigger（with_skill 版本）
**Skill**：harness-evaluator v1.11.0
**执行时间**：2026-05-30

---

## Step 1：读取 SKILL.md

读取 `/Users/administrator/.claude/skills/harness-evaluator/SKILL.md`

关键发现（v1.11.0 changelog）：
> windows_cloud 模式 B trigger 前新增 workflow 内容检查 — 在 gh workflow run 之前检查：
> (1) workflow 文件是否存在
> (2) 合同 contract-dod.md 是否有 [BEHAVIOR] 条目
> (3) workflow 是否只有文件存在/大小检查而不含业务逻辑验证（node/npx/vitest/playwright/curl 等）
> 第 3 条命中时直接 FAIL，防止 workflow 空壳导致假绿

Step B-2 windows_cloud 分支的空壳检测代码：

```bash
BUSINESS_STEPS=$(grep -cE "(node -e|npx|npm run|vitest|playwright|curl|Invoke-RestMethod|session|publish|cookies|DOUYIN)" "$WORKFLOW_FILE" 2>/dev/null || echo 0)
SHALLOW_ONLY=$(grep -cE "(Test-Path|\.Length|\.Size|file.*exist|exist.*file)" "$WORKFLOW_FILE" 2>/dev/null || echo 0)

if [[ "$BUSINESS_STEPS" -eq 0 && "$SHALLOW_ONLY" -gt 0 ]]; then
  # 直接 FAIL，exit 0（Brain 读文件）
}
```

---

## Step 2：读取 workflow 文件

读取 `/Users/administrator/perfect21/zenithjoy/.github/workflows/agent-qr-windows-verify.yml`

文件实际内容：
- `unit-tests-windows` job：checkout → setup-node → npm ci → npm test
- `sandbox-install` job：下载 tar.gz → 解压 → Test-Path 检查 exe → .Length 大小检查

---

## Step 3：确认模式

```
IS_FINAL_E2E=true → 模式 B
TARGET_ENV=windows_cloud
```

进入 Step B-2 的 windows_cloud 分支。

---

## Step 4：执行空壳检测（针对模拟的空壳 workflow）

模拟 workflow 内容（eval 任务指定）：
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

执行检测：

```
$ grep -cE "(node -e|npx|npm run|vitest|playwright|curl|Invoke-RestMethod|session|publish|cookies|DOUYIN)" hollow.yml
0

$ grep -cE "(Test-Path|\.Length|\.Size|file.*exist|exist.*file)" hollow.yml
2
```

结果：
- `BUSINESS_STEPS=0`
- `SHALLOW_ONLY=2`
- 条件 `BUSINESS_STEPS == 0 && SHALLOW_ONLY > 0` → TRUE

---

## Step 5：触发前 FAIL 判定

```bash
WORKFLOW_PREVIEW=$(head -30 "$WORKFLOW_FILE" | tr '\n' '|')
cat > "$WORKSPACE/.brain-result.json" << BREOF
{"verdict":"FAIL","task_id":"$TASK_ID","failed_step":"workflow_content_check","log_excerpt":"workflow agent-qr-windows-verify.yml 只包含文件存在/大小检查，不含任何业务逻辑验证（node/npx/vitest/playwright/curl）。合同 BEHAVIOR 断言无法通过此 workflow 真实验证。请更新 workflow 加入业务行为测试。workflow 前30行: ..."}
BREOF
exit 0
```

**`gh workflow run` 从未被执行。**

---

## Step 6：附加发现 — 真实 workflow 同样触发 FAIL

对真实 workflow 文件运行相同检测：

```
BUSINESS_STEPS=0  （npm test / npm ci 不匹配 "npm run" 正则）
SHALLOW_ONLY=3    （.Length × 2，Test-Path × 1）
```

真实 workflow 也会被判 FAIL，原因是 skill 正则 `npm run` 无法匹配 `npm test`。
这是 skill v1.11.0 的一个已知 gap，可在下一版本中补充 `npm test` 关键词。

---

## 最终 Verdict

```json
{
  "verdict": "FAIL",
  "failed_step": "workflow_content_check",
  "triggered_gh_workflow_run": false,
  "reason": "空壳 workflow 检测命中：BUSINESS_STEPS=0, SHALLOW_ONLY=2"
}
```
