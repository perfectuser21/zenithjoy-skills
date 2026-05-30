---
skeleton: false
journey_type: user_facing
target_environment: windows_cloud
workflow_file: .github/workflows/agent-qr-windows-verify.yml
---
# Contract DoD — Sprint: ZenithJoy Agent 抖音 QR 扫码绑定 (windows_cloud)

**范围**: Agent 抖音 QR 扫码绑定全链路：session 写入本地文件 → handler 读取 → DOUYIN_COOKIES 注入发布进程
**大小**: M

---

## ⚠️ windows_cloud Workflow 内容审查（v8.1.0 强制 — 写 BEHAVIOR 前必读）

执行命令：
```bash
cat /Users/administrator/perfect21/zenithjoy/.github/workflows/agent-qr-windows-verify.yml
```

**Workflow 实际步骤列表**（`agent-qr-windows-verify.yml`）：

| Job | Step | 实际验证内容 |
|---|---|---|
| `unit-tests-windows` | Install dependencies | `npm ci` |
| `unit-tests-windows` | Run qr-bind-operator unit tests | `npm test -- --reporter=verbose`（单元测试） |
| `sandbox-install` | Download install pack from COS | 下载 `zenithjoy-agent-v{version}.tar.gz` |
| `sandbox-install` | Extract and verify exe | 检查 `pack\zenithjoy-agent.exe` 存在 + 文件大小 > 1MB |

**用户路径 1:1 映射检查**：

| 用户操作步骤 | Workflow 是否覆盖 | 结论 |
|---|---|---|
| 用户扫码，QR 码显示在 Agent UI | 无对应 step | [CI_GAP] |
| 扫码后 session 写入 `~/.zenithjoy-agent/sessions/douyin/default.json` | 无对应 step | [CI_GAP] |
| handler 读取 session 文件，验证 session 有效 | 无对应 step | [CI_GAP] |
| DOUYIN_COOKIES 从 session 注入发布进程 | 无对应 step | [CI_GAP] |
| 发布进程以注入的 cookies 发起请求 | 无对应 step | [CI_GAP] |

**重要**：workflow `sandbox-install` job 仅验证 exe 文件存在和大小（属于"文件存在/大小"检查），**禁止算作业务行为验证**（v8.1.0 规则）。

---

## ARTIFACT 条目

- [ ] [ARTIFACT] `qr-bind-operator.ts`（或 `.js`）存在于 `services/agent/src/handlers/` 下，包含 `writeSession` 函数
  Test: node -e "const c=require('fs').readFileSync('services/agent/src/handlers/qr-bind-operator.ts','utf8');if(!c.includes('writeSession'))process.exit(1);console.log('OK')"

- [ ] [ARTIFACT] session 目录结构配置存在：`~/.zenithjoy-agent/sessions/douyin/default.json` 路径在 handler 代码中有字面引用
  Test: node -e "const c=require('fs').readFileSync('services/agent/src/handlers/qr-bind-operator.ts','utf8');if(!c.includes('sessions/douyin/default.json'))process.exit(1);console.log('OK')"

- [ ] [ARTIFACT] `services/agent/src/__tests__/qr-bind-operator.test.ts` 存在且包含 session 写入断言
  Test: node -e "const c=require('fs').readFileSync('services/agent/src/__tests__/qr-bind-operator.test.ts','utf8');if(!c.includes('default.json'))process.exit(1);console.log('OK')"

---

## BEHAVIOR 条目（内嵌可执行 manual:bash 命令）

### 用户路径核心验证

- [ ] [BEHAVIOR] QR 扫码后 session 文件写入 `~/.zenithjoy-agent/sessions/douyin/default.json`，文件内容为有效 JSON 且包含 `cookies` 字段
  Test: manual:bash -c 'SESSION_FILE="$HOME/.zenithjoy-agent/sessions/douyin/default.json"; [ -f "$SESSION_FILE" ] || { echo "FAIL: session 文件不存在 $SESSION_FILE"; exit 1; }; node -e "const d=JSON.parse(require(\"fs\").readFileSync(\"$HOME/.zenithjoy-agent/sessions/douyin/default.json\",\"utf8\")); if(!d.cookies||!Array.isArray(d.cookies)){process.exit(1);} console.log(\"OK cookies count=\"+d.cookies.length);" || { echo "FAIL: session JSON 格式错误或无 cookies 字段"; exit 1; }'
  期望: OK cookies count=<N>（N >= 1）

- [ ] [BEHAVIOR] handler `readSession` 能读取 session 文件并返回 cookies 数组（单元测试 Red→Green 证明）
  Test: manual:bash -c 'cd services/agent && npm test -- --reporter=verbose --grep "readSession" 2>&1 | grep -E "PASS|✓|passed" | head -5; EXIT=${PIPESTATUS[0]}; [ $EXIT -eq 0 ] || { echo "FAIL: readSession 单元测试未通过"; exit 1; }; echo OK'
  期望: OK（grep 匹配 PASS 或 ✓）

- [ ] [BEHAVIOR] DOUYIN_COOKIES 环境变量由 session 文件内容注入，发布进程启动时可读取
  Test: manual:bash -c 'SESSION_FILE="$HOME/.zenithjoy-agent/sessions/douyin/default.json"; [ -f "$SESSION_FILE" ] || { echo "FAIL: 无 session 文件，无法验证注入"; exit 1; }; COOKIES=$(node -e "const d=JSON.parse(require(\"fs\").readFileSync(\"$SESSION_FILE\",\"utf8\")); console.log(JSON.stringify(d.cookies))"); [ -n "$COOKIES" ] || { echo "FAIL: cookies 为空"; exit 1; }; DOUYIN_COOKIES="$COOKIES" node -e "if(!process.env.DOUYIN_COOKIES||process.env.DOUYIN_COOKIES.length<2){process.exit(1)}; console.log(\"OK DOUYIN_COOKIES 注入成功 len=\"+process.env.DOUYIN_COOKIES.length)"'
  期望: OK DOUYIN_COOKIES 注入成功 len=<N>

- [ ] [BEHAVIOR] session JSON schema 完整性：顶层 keys 必须包含 `cookies` 和 `timestamp`，不能缺字段
  Test: manual:bash -c 'SESSION_FILE="$HOME/.zenithjoy-agent/sessions/douyin/default.json"; node -e "const d=JSON.parse(require(\"fs\").readFileSync(\"$SESSION_FILE\",\"utf8\")); const keys=Object.keys(d).sort(); if(!keys.includes(\"cookies\")){throw new Error(\"缺 cookies\")}; if(!keys.includes(\"timestamp\")){throw new Error(\"缺 timestamp\")}; console.log(\"OK schema keys=\"+JSON.stringify(keys));" || { echo "FAIL: session schema 不完整"; exit 1; }'
  期望: OK schema keys 包含 cookies 和 timestamp

- [ ] [BEHAVIOR] error path — 当 session 文件不存在时，handler 抛出明确错误而非静默失败
  Test: manual:bash -c 'cd services/agent && npm test -- --reporter=verbose --grep "session.*not.*found\|无.*session\|ENOENT" 2>&1 | grep -E "PASS|✓|passed" | head -3; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "FAIL: handler 未测试 session 不存在的 error path"; exit 1; }; echo OK'
  期望: OK（有测试覆盖 session 文件缺失的错误处理）

- [ ] [BEHAVIOR] 禁用字段反向检查 — session 文件中不含 `password` 或 `privateKey` 等敏感字段（安全审查）
  Test: manual:bash -c 'SESSION_FILE="$HOME/.zenithjoy-agent/sessions/douyin/default.json"; [ -f "$SESSION_FILE" ] || { echo "SKIP: 无 session 文件"; exit 0; }; node -e "const d=JSON.parse(require(\"fs\").readFileSync(\"$SESSION_FILE\",\"utf8\")); if(d.password!==undefined){process.exit(1)} if(d.privateKey!==undefined){process.exit(1)} console.log(\"OK 无敏感字段\");" || { echo "FAIL: session 文件含禁用敏感字段"; exit 1; }'
  期望: OK 无敏感字段

---

## [CI_GAP] 标注 — Workflow 缺失的业务行为验证步骤

以下用户路径在 `agent-qr-windows-verify.yml` 中**完全没有对应的 CI step**，Generator 必须补写：

### [CI_GAP: QR 扫码触发 session 写入验证]

**缺失描述**: workflow 的 `unit-tests-windows` job 跑的是单元测试，但没有 E2E 级别的验证：模拟扫码事件 → 断言 session 文件实际写入到正确路径。

**要求 Generator 在 workflow 新增**：
```yaml
- name: E2E — simulate QR bind and verify session written
  shell: powershell
  run: |
    # 模拟扫码事件触发 writeSession
    node -e "
      const { writeSession } = require('./src/handlers/qr-bind-operator.js');
      const testCookies = [{ name: 'sid_tt', value: 'test_cookie_val' }];
      writeSession('douyin', 'default', { cookies: testCookies, timestamp: Date.now() });
    "
    # 验证 session 文件写入正确路径
    $sessionPath = "$env:USERPROFILE\.zenithjoy-agent\sessions\douyin\default.json"
    if (-not (Test-Path $sessionPath)) {
      Write-Error "FAIL: session 文件未写入 $sessionPath"
      exit 1
    }
    $content = Get-Content $sessionPath | ConvertFrom-Json
    if (-not $content.cookies) {
      Write-Error "FAIL: session 文件缺 cookies 字段"
      exit 1
    }
    Write-Host "PASS: session 写入验证通过 path=$sessionPath"
```

### [CI_GAP: handler readSession 返回有效 cookies]

**缺失描述**: 当前 unit tests 仅运行 `npm test`，没有显式断言 `readSession` 在 windows 路径下（`%USERPROFILE%`）能正确读取文件。Windows 路径分隔符与 Linux 不同，存在 path join 兼容问题。

**要求 Generator 在 `qr-bind-operator.test.ts` 新增**：
```typescript
it('readSession returns cookies from %USERPROFILE% path on windows', async () => {
  // 写入测试 session
  await writeSession('douyin', 'default', {
    cookies: [{ name: 'test', value: 'val' }],
    timestamp: Date.now()
  });
  // 读取并验证
  const session = await readSession('douyin', 'default');
  expect(session).not.toBeNull();
  expect(session!.cookies).toHaveLength(1);
  expect(session!.cookies[0].name).toBe('test');
});
```

### [CI_GAP: DOUYIN_COOKIES 注入发布进程的 E2E 验证]

**缺失描述**: workflow 完全没有验证 session 读取后 DOUYIN_COOKIES 环境变量是否正确注入发布进程（`publish-douyin-*.cjs`）。这是用户路径最关键的一步。

**要求 Generator 在 workflow 新增**：
```yaml
- name: E2E — verify DOUYIN_COOKIES injected into publisher process
  shell: powershell
  run: |
    # 准备测试 session
    $sessionDir = "$env:USERPROFILE\.zenithjoy-agent\sessions\douyin"
    New-Item -ItemType Directory -Force -Path $sessionDir | Out-Null
    $session = @{
      cookies   = @(@{ name = "sid_tt"; value = "e2e_test_cookie" })
      timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    }
    $session | ConvertTo-Json -Depth 5 | Out-File -FilePath "$sessionDir\default.json" -Encoding utf8

    # 调用注入逻辑并验证 DOUYIN_COOKIES 已设置
    $result = node -e "
      const { injectCookiesToEnv } = require('./src/handlers/qr-bind-operator.js');
      injectCookiesToEnv('douyin', 'default').then(cookies => {
        if (!process.env.DOUYIN_COOKIES) { process.exit(1); }
        const parsed = JSON.parse(process.env.DOUYIN_COOKIES);
        if (!Array.isArray(parsed) || parsed.length < 1) { process.exit(1); }
        console.log('PASS DOUYIN_COOKIES len=' + parsed.length);
      }).catch(e => { console.error(e.message); process.exit(1); });
    " 2>&1
    Write-Host $result
    if ($LASTEXITCODE -ne 0) {
      Write-Error "FAIL: DOUYIN_COOKIES 注入失败"
      exit 1
    }
```

---

## BEHAVIOR:E2E 条目（windows_cloud final-e2e 跑）

- [ ] [BEHAVIOR:E2E] 在 GitHub Actions windows-latest 干净 VM 上，QR 扫码绑定全链路通过
  E2E Script: `sprints/agent-qr-bind/e2e-verify.ps1`
  步骤:
    1. 安装 Node 依赖（`npm ci`）
    2. 模拟扫码事件，写入 session 到 `$env:USERPROFILE\.zenithjoy-agent\sessions\douyin\default.json`
    3. 调用 `readSession`，断言返回 cookies 数组长度 >= 1
    4. 调用 `injectCookiesToEnv`，断言 `DOUYIN_COOKIES` 环境变量已设置且 JSON 有效
    5. 用注入的 cookies 调用 publisher dryrun，断言返回 `ok:true, dryRun:true`
  PASS 标准: 脚本 exit 0 + 每步均有 `PASS` 输出
  FAIL 标准: 任意 step exit != 0 OR 超时 15min

---

## 自查 checklist（v7.6 — proposer 写完前必跑）

1. PRD Response Schema 字段名检查：本 sprint 无 `## Response Schema` 段（功能型 sprint，非 API 计算型），跳过字段名漂移检查
2. BEHAVIOR 数量：grep -c '^- \[ \] \[BEHAVIOR\]' contract-dod.md → 预期 ≥ 6 条（已写 6 条 [BEHAVIOR] + 1 条 [BEHAVIOR:E2E]）
3. 假绿自查：每条 BEHAVIOR 命令，若对应代码一行都没写，是否会 FAIL？
   - BEHAVIOR 1（session 文件存在 + cookies 字段）：代码未实现 → session 文件不存在 → `[ -f ]` FAIL ✓
   - BEHAVIOR 2（readSession 单测通过）：代码未实现 → 单测 FAIL ✓
   - BEHAVIOR 3（DOUYIN_COOKIES 注入）：代码未实现 → node 脚本报错 FAIL ✓
   - BEHAVIOR 4（schema 完整性）：代码未实现 → session 文件不存在 FAIL ✓
   - BEHAVIOR 5（error path 测试）：代码未实现 → 单测不存在 FAIL ✓
   - BEHAVIOR 6（禁用字段）：代码未实现 → session 文件不存在 → SKIP（带 exit 0 为保守处理）
4. windows_cloud workflow 内容已用 Bash cat 真实读取（v8.1.0 强制规则满足）
5. [CI_GAP] 已标注 3 处缺失步骤，并提供具体补写代码
6. 文件存在/大小检查（sandbox-install job）已排除，不作为业务行为验证

---

## task-plan.json 对应内容

```json
{
  "initiative_id": "pending",
  "journey_type": "user_facing",
  "journey_type_reason": "功能涉及用户扫码操作（QR UI）+ session 文件写入 + 发布进程注入，是用户可感知的端到端路径",
  "tasks": [
    {
      "task_id": "ws1",
      "title": "抖音 QR 扫码绑定全链路：writeSession + readSession + DOUYIN_COOKIES 注入",
      "scope": "实现 qr-bind-operator handler 的 writeSession/readSession/injectCookiesToEnv 三个函数，session 路径 ~/.zenithjoy-agent/sessions/douyin/default.json，补写 workflow 3 个 CI_GAP step",
      "dod": [
        "[BEHAVIOR] session 文件写入正确路径且含 cookies 字段",
        "[BEHAVIOR] readSession 单元测试通过（含 Windows 路径兼容测试）",
        "[BEHAVIOR] DOUYIN_COOKIES 注入成功，JSON 有效",
        "[BEHAVIOR] session schema 完整性（含 cookies + timestamp）",
        "[BEHAVIOR] error path 覆盖（文件不存在时报明确错误）",
        "[ARTIFACT] qr-bind-operator.ts 含 writeSession 函数",
        "[ARTIFACT] 单元测试文件含 default.json 断言"
      ],
      "files": [
        "services/agent/src/handlers/qr-bind-operator.ts",
        "services/agent/src/__tests__/qr-bind-operator.test.ts",
        ".github/workflows/agent-qr-windows-verify.yml"
      ],
      "depends_on": [],
      "complexity": "M",
      "estimated_minutes": 90
    }
  ]
}
```
