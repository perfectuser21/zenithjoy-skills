# Harness Evaluator 评估结果

## 评估对象

- 文件路径：`/tmp/eval-evaluator-fixtures/real-workflow.yml`
- 评估时间：2026-05-30
- 评估模式：windows_cloud workflow 内容检查（pre-merge gate）

## 判定结论

**PROCEED** — workflow 包含真实业务行为验证，可以触发最终 E2E 运行。

## 详细分析

### Job 1：`unit-tests`

| 步骤 | 命令 | 类型 |
|------|------|------|
| 安装依赖 | `npm ci` | 构建层 |
| 运行测试 | `npm test` | 代码层测试 |

分类：代码层验证（cheap layer），不是真实业务行为，但属于 CI 合法组成部分。

### Job 2：`e2e-business`

| 步骤 | 关键命令 | 业务验证指标 |
|------|---------|------------|
| Write session file | `New-Item` + `ConvertTo-Json` + `Set-Content` | ✅ 命中 `New-Item` / `Set-Content` / `ConvertTo-Json` |
| Verify session readable | `Get-Content` + `ConvertFrom-Json` + 字段比对 | ✅ 有 `userId` 值校验（`-ne` 抛异常） |
| Inject session to agent | `Invoke-RestMethod -Uri ... -Method POST` | ✅ 命中 `Invoke-RestMethod` / `session` |

### 空壳检测结果

```
BUSINESS_STEPS = 命中：npm test, npm ci, Invoke-RestMethod, session, Set-Content,
                        New-Item, ConvertTo-Json, Write-Host.*PASS
SHALLOW_ONLY   = 未命中（无 Test-Path / .Length / .Size / file exist 等纯文件检查）
```

判定逻辑：`BUSINESS_STEPS > 0 && SHALLOW_ONLY == 0` → 非空壳 → **不触发 FAIL**。

## 潜在风险提示（不阻断，供参考）

1. **`Inject session to agent` 步骤无响应校验**：`Invoke-RestMethod` 调用后未验证 HTTP 响应状态码或 body 内容。若 API 返回 4xx/5xx，步骤可能仍 PASS（PowerShell 默认对 2xx 以外才抛异常，实际行为取决于端点实现）。建议补充 `if ($response.status -ne "ok") { throw ... }`。

2. **session 是硬编码测试数据**：`userId = "test-user-001"` 是静态 mock 值，若合同 BEHAVIOR 要求验证真实用户登录态，此处存在弱 oracle 风险（schema 可通过但业务语义未验证）。

3. **`localhost:5221/api/agent/session`**：此端点在 windows-latest runner 上运行时，`localhost:5221` 必须是 runner 本地启动的服务。若 agent 服务未在前序步骤启动，此调用将 fail（`Connection refused`）。当前 workflow 未见 agent 启动步骤，请确认该步骤是否在其他 job 或前置 workflow 中完成。

## 最终判定

```
verdict: PROCEED
reason: workflow 含 8+ 个业务行为验证指标，包含真实 API 调用（Invoke-RestMethod POST）
        和字段级断言（userId 比对），非空壳 workflow。
action: 可触发最终 E2E 运行。
```
