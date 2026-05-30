# Harness Evaluator — 评估报告

## 评估目标

- **Workflow 文件**: `/tmp/eval-evaluator-fixtures/real-workflow.yml`
- **Sprint 类型**: windows_cloud Final E2E（模式 B）
- **合同 [BEHAVIOR] 条目（用户提供）**:
  1. session 写入路径验证
  2. DOUYIN_COOKIES 注入验证
  3. vitest 回归测试

---

## 读取的 Workflow 完整内容

```yaml
name: agent-qr-windows-verify
on:
  workflow_dispatch:
    inputs:
      artifact_path:
        description: 'Path to artifact'
        required: true

jobs:
  unit-tests:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm test

  e2e-business:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - name: Write session file
        shell: powershell
        run: |
          $sessionPath = "$env:APPDATA\ZenithJoy\session.json"
          New-Item -ItemType Directory -Force -Path (Split-Path $sessionPath)
          $session = @{ userId = "test-user-001"; token = "test-token-abc" } | ConvertTo-Json
          Set-Content -Path $sessionPath -Value $session
          Write-Host "PASS: session file written"

      - name: Verify session readable
        shell: powershell
        run: |
          $content = Get-Content "$env:APPDATA\ZenithJoy\session.json" | ConvertFrom-Json
          if ($content.userId -ne "test-user-001") { throw "Session userId mismatch" }
          Write-Host "PASS: session content verified"

      - name: Inject session to agent
        shell: powershell
        run: |
          $session = Get-Content "$env:APPDATA\ZenithJoy\session.json"
          Invoke-RestMethod -Uri "http://localhost:5221/api/agent/session" -Method POST -Body $session -ContentType "application/json"
          Write-Host "PASS: session injected"
```

---

## 分析过程

### Step B-1.1：空壳检测（SKILL.md v1.11.0 规则）

按 SKILL.md 正则检测业务步骤数量：

```
BUSINESS_STEPS 正则：(node -e|npx|npm run|npm test|npm ci|vitest|playwright|curl|
                      Invoke-RestMethod|session|publish|cookies|DOUYIN|Set-Content|
                      New-Item|ConvertTo-Json|Write-Host.*PASS)
```

- **BUSINESS_STEPS**: 15（npm ci、npm test、New-Item、Set-Content、ConvertTo-Json、Invoke-RestMethod、Write-Host PASS × 多处等）
- **SHALLOW_ONLY**（仅 Test-Path/文件大小检查）: 0

结论：**workflow 不是空壳，包含真实业务逻辑验证**，不触发空壳 FAIL。

---

### Step B-1.2：三条合同 BEHAVIOR 逐项覆盖分析

#### BEHAVIOR 1：session 写入路径验证

workflow 中存在以下步骤：
- `Write session file`：使用 `New-Item` 创建目录，`Set-Content` 写入 `$env:APPDATA\ZenithJoy\session.json`，内容含 `userId` + `token`
- `Verify session readable`：`Get-Content` 读回并用 `ConvertFrom-Json` 解析，断言 `userId -ne "test-user-001"` 则 throw

**覆盖状态**: ✅ **覆盖**（写入路径 + 读取验证均存在，有值断言 throw）

---

#### BEHAVIOR 2：DOUYIN_COOKIES 注入验证

全文搜索 `DOUYIN`、`cookies`、`cookie`（含大小写）：**无任何命中**。

workflow 的 `e2e-business` job 仅测试了 session 文件写入与 agent session 注入，**完全没有 DOUYIN_COOKIES 相关步骤**。

**覆盖状态**: ❌ **缺失**（合同第 2 条 BEHAVIOR 在 workflow 中无对应验证）

---

#### BEHAVIOR 3：vitest 回归测试

`unit-tests` job 包含 `npm ci` + `npm test`。

注意：`npm test` 是否真正运行 vitest 取决于 `package.json` 的 test 脚本配置，workflow 本身不能证明是 vitest（可能是 jest 或其他）。但从空壳检测角度，`npm test` 命中 SKILL.md 的 `npm test` 正则，被计入 `BUSINESS_STEPS`，不触发空壳 FAIL。

按 SKILL.md 反作弊规则 1："禁止把 vitest 输出 grep 'passed' 当 PASS 证据"，`npm test` 是 generator 自写的测试，不是 contract oracle。但 BEHAVIOR 3 的要求是 "vitest 回归测试存在于 workflow 中"（即覆盖性验证），而非"把 vitest 结果当评判通过依据"。

从 workflow **覆盖性**角度：存在 `npm test` 步骤，具备运行回归测试的能力。

**覆盖状态**: ⚠️ **弱覆盖**（`npm test` 存在但无法确认是 vitest，且无 `--reporter=verbose` 或 vitest 命令直调；在严格评判下属于不充分，但不是完全缺失）

---

### Step B-1.3：workflow_dispatch inputs 检查

SKILL.md 的 `windows_cloud` 触发逻辑需要向 workflow 传入 `task_id`、`sprint_dir`、`pr_branch` 三个参数（通过 `gh workflow run -f task_id=... -f sprint_dir=... -f pr_branch=...`）。

当前 workflow 只声明了 `artifact_path` 一个 input，**未声明 `task_id` / `sprint_dir` / `pr_branch`**。

这意味着 harness 触发时传入的参数会被 GHA 忽略（或报错），workflow 内部无法引用这些值做任务关联和结果回写。

**覆盖状态**: ❌ **缺失**（触发接口不兼容 harness 协议，无法关联 Brain task）

---

## 最终判断

### 结论：FAIL

**核心失败原因（按严重度排序）**：

1. **BEHAVIOR 2「DOUYIN_COOKIES 注入验证」完全缺失**
   - workflow 无任何 `DOUYIN`、`cookies` 相关步骤
   - 合同三条 BEHAVIOR 中有一条在 workflow 中没有对应实现
   - 按 SKILL.md 反作弊规则：合同 BEHAVIOR 未真跑 → FAIL

2. **workflow_dispatch inputs 不兼容 harness 协议**
   - 当前只有 `artifact_path` input，缺少 `task_id` / `sprint_dir` / `pr_branch`
   - harness evaluator 执行 `gh workflow run -f task_id=... -f sprint_dir=... -f pr_branch=...` 时，这些参数无法被 workflow 接收
   - 触发后无法关联 Brain task，Brain 无法读到结果回写

3. **BEHAVIOR 3「vitest 回归测试」弱覆盖**
   - `npm test` 存在但未明确调用 vitest（合同要求 vitest，不是任意测试框架）
   - 建议改为 `npx vitest run` 或在 `package.json` test 脚本中确认是 vitest

### 具体修复方向

**修复 1**（必须）：在 `e2e-business` job 中添加 DOUYIN_COOKIES 注入验证步骤，例如：
```yaml
- name: Inject DOUYIN cookies
  shell: powershell
  run: |
    $cookies = $env:DOUYIN_COOKIES
    if (-not $cookies) { throw "DOUYIN_COOKIES env var not set" }
    # 注入到 agent 或写入 cookie 文件
    Set-Content -Path "$env:APPDATA\ZenithJoy\douyin-cookies.json" -Value $cookies
    Write-Host "PASS: DOUYIN_COOKIES injected"
```

**修复 2**（必须）：在 `workflow_dispatch.inputs` 中添加 harness 协议必需的字段：
```yaml
inputs:
  task_id:
    description: 'Brain task ID'
    required: false
  sprint_dir:
    description: 'Sprint directory'
    required: false
  pr_branch:
    description: 'PR branch name'
    required: false
  artifact_path:
    description: 'Path to artifact'
    required: true
```

**修复 3**（建议）：将 `npm test` 改为显式 vitest 调用：
```yaml
- run: npx vitest run
```

---

## 空壳检测统计

| 检测维度 | 值 | 判定 |
|---|---|---|
| BUSINESS_STEPS（业务步骤数） | 15 | ✅ 非空壳 |
| SHALLOW_ONLY（仅文件检查） | 0 | ✅ 非空壳 |
| BEHAVIOR 1 覆盖 | session 写入+验证均存在 | ✅ 覆盖 |
| BEHAVIOR 2 覆盖 | DOUYIN_COOKIES 完全缺失 | ❌ 缺失 |
| BEHAVIOR 3 覆盖 | npm test 存在（弱） | ⚠️ 弱覆盖 |
| harness inputs 兼容性 | task_id/sprint_dir/pr_branch 缺失 | ❌ 不兼容 |

**最终判定：FAIL**
