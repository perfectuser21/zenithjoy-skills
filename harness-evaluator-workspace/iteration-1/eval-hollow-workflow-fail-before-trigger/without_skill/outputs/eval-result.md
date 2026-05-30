# Eval 结果：hollow-workflow BEHAVIOR 断言覆盖判断

**版本**：without_skill（baseline，不加载 harness-evaluator skill）  
**日期**：2026-05-30  
**场景**：windows_cloud Sprint Final E2E，workflow 为空壳版本

---

## 判断结论

**结论：直接 FAIL，不触发 workflow run。**

---

## 逐条分析

### 待验 BEHAVIOR 断言（来自 contract-dod.md）

1. **[BEHAVIOR] session 写入路径验证**  
   要求：E2E 执行后，session 文件出现在正确路径（如 `%APPDATA%\zenithjoy\sessions\` 或约定路径）。  
   workflow 覆盖情况：**无覆盖**。workflow 只检查 exe 是否存在 + 文件大小，没有任何步骤启动 Agent、触发 session 写入、或验证写入路径。

2. **[BEHAVIOR] DOUYIN_COOKIES 注入验证**  
   要求：Agent 启动时能正确读取/注入抖音 cookies（通常验证方式是启动后调 API 或查日志）。  
   workflow 覆盖情况：**无覆盖**。workflow 没有启动 Agent 进程，没有注入 env var，没有验证任何 cookie 状态。

3. **[BEHAVIOR] vitest 回归测试**  
   要求：跑 vitest 单元/集成测试套件，断言全部通过。  
   workflow 覆盖情况：**无覆盖**。workflow 没有任何 `npm run test` / `npx vitest` 步骤。

### 现有 workflow 实际验证了什么

| 步骤 | 验证内容 | 是否属于 BEHAVIOR 断言 |
|------|----------|----------------------|
| 下载 installpack | 网络可达、tar.gz 可下载 | 否（基础前提，不是 BEHAVIOR） |
| 验证 exe 存在 | 文件打包是否包含 exe | 否（是 artifact 检查，不是行为验证） |
| 验证 exe 大小 ≥1MB | 文件未损坏/未截断 | 否（是 sanity check，不是 BEHAVIOR） |

**结论：这个 workflow 是一个 artifact sanity check，不是 BEHAVIOR E2E。**

---

## 决策依据

BEHAVIOR 断言的定义是"系统在运行时表现出的可观测行为"，必须：
- 让被测系统实际运行（启动 Agent 进程）
- 触发被测行为（session 写入、cookie 注入）
- 观测结果（查文件/API/日志）

当前 workflow 三步均未满足：**系统从未启动，行为从未触发，结果无从观测。**

触发 workflow run 毫无意义——即使 CI 绿，BEHAVIOR 断言仍然 0% 覆盖。

---

## 正确的修复方向

要让这个 workflow 能验证上述 3 条 BEHAVIOR，最少需要补充：

```yaml
- name: 启动 Agent（后台）
  run: Start-Process -FilePath "pack\zenithjoy-agent.exe" -ArgumentList "--headless" -PassThru

- name: 等待 Agent 就绪
  run: |
    $maxWait = 30
    $elapsed = 0
    while ($elapsed -lt $maxWait) {
      try { $r = Invoke-WebRequest http://localhost:7070/health -ErrorAction Stop; break }
      catch { Start-Sleep 1; $elapsed++ }
    }
    if ($elapsed -ge $maxWait) { Write-Error "Agent 启动超时"; exit 1 }

- name: 验证 session 写入路径
  run: |
    $sessionPath = "$env:APPDATA\zenithjoy\sessions"
    if (-not (Test-Path $sessionPath)) { Write-Error "session 路径不存在"; exit 1 }
    Write-Host "PASS: session path $sessionPath exists"

- name: 验证 DOUYIN_COOKIES 注入
  env:
    DOUYIN_COOKIES: ${{ secrets.DOUYIN_COOKIES_TEST }}
  run: |
    $r = Invoke-WebRequest http://localhost:7070/api/platform/status -ErrorAction Stop
    $body = $r.Content | ConvertFrom-Json
    if (-not $body.douyin_ready) { Write-Error "DOUYIN_COOKIES 未注入"; exit 1 }
    Write-Host "PASS: douyin_ready=$($body.douyin_ready)"

- name: vitest 回归测试
  run: |
    cd pack
    npx vitest run --reporter=verbose
```

---

## 最终判断

| 项目 | 结果 |
|------|------|
| 是否触发 workflow run | **否** |
| BEHAVIOR 覆盖率 | **0 / 3 条** |
| 最终评级 | **FAIL** |
| 原因 | workflow 是空壳 artifact check，未启动被测系统，BEHAVIOR 断言全部未覆盖 |
