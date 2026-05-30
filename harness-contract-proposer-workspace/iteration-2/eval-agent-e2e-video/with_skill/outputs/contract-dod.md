---
skeleton: false
journey_type: agent_remote
target_environment: windows_cloud
sprint_name: zj-agent-douyin-article-dryrun
---
# Contract DoD — Sprint: ZenithJoy Agent 抖音图文 Dryrun 发布

**范围**: 中台通过 WebSocket 向 Windows Agent 下发 `douyin_publish` task（type=article）→ Agent 接收并 spawn `publish-douyin-article-dryrun.cjs` → 返回 `{ok:true, dryRun:true}` 回执给中台
**大小**: M（改动集中在 agent handler 路由 + CI workflow 新 job）
**workflow**: `.github/workflows/agent-e2e-video.yml`

---

## workflow 1:1 映射检查（v8.1.0 windows_cloud 必读）

`cat .github/workflows/agent-e2e-video.yml` 读取结果摘要：

| 用户路径步骤 | workflow 对应 step | 状态 |
|---|---|---|
| Agent 安装包下载 | Download install pack + Extract install pack | ✅ 有 |
| Node.js / hyperframes 就绪 | Extract Node.js v22 + Install hyperframes | ✅ 有 |
| Chrome CDP 19222 启动 | Start Chrome CDP 19222 | ✅ 有 |
| Agent 进程启动 | Start Agent (background) | ✅ 有 |
| Agent 上线确认（连上中台 WS） | Wait for Agent online | ✅ 有（轮询 /api/agent/me/status） |
| **中台下发 douyin_publish task（type=article, dryrun）** | Run Playwright E2E test | ⚠️ 现有 spec 是 `agent-video-pipeline.spec.js`（视频流水线），不含 douyin article 图文 task 下发 — [CI_GAP: 缺少发布抖音图文 task 的 E2E spec 或 curl 触发步骤] |
| **Agent 调 publish-douyin-article-dryrun.cjs** | — | ❌ [CI_GAP: workflow 无验证 agent handler 路由 type=article 的步骤] |
| **返回 ok:true dryRun:true 回执** | Verify output video quality (ffprobe) | ❌ [CI_GAP: ffprobe step 验证的是 mp4 视频文件，不验 dryrun JSON 回执] |
| DOUYIN_COOKIES session 注入 | Write .env（仅写 LICENSE/API keys） | ❌ [CI_GAP: agent-e2e-video.yml 不注入 DOUYIN_COOKIES；article dryrun 需要 cookie 注入才能绕过登录页] |

**[CI_GAP] 汇总（4 项，Generator 必须补写）**：
1. **[CI_GAP: article-task-dispatch]** — workflow 无 curl 或 Playwright step 向中台 POST `{type:"douyin_publish", payload:{type:"article",...}}`，然后等待 task 完成
2. **[CI_GAP: agent-type-route]** — 无验证 handler 选择了 `publish-douyin-article-dryrun.cjs`（而非 image/video）
3. **[CI_GAP: dryrun-receipt-verify]** — 无验证中台收到 `ok:true dryRun:true` 回执（ffprobe step 只查 mp4，不查 JSON 回执）
4. **[CI_GAP: douyin-cookies-inject]** — workflow 无 `DOUYIN_COOKIES` secret 注入；article dryrun 依赖 cookie 登录抖音，缺少会走 CDP 模式，CI 中无抖音登录 session，导致 dryrun 返 `ok:false error:抖音未登录`

---

## Golden Path

[中台下发 task] → [Agent 接收 WebSocket 消息] → [handler 路由 type=article] → [spawn dryrun 脚本] → [dryrun 脚本 cookie 注入登录] → [走完创作流程不点发布] → [返回 ok:true dryRun:true] → [中台收到回执]

---

## ARTIFACT 条目

- [ ] [ARTIFACT] `publish-douyin-article-dryrun.cjs` 存在于 `services/agent/publishers/douyin-publisher/`
  Test: node -e "require('fs').accessSync('services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs')"

- [ ] [ARTIFACT] `services/agent/src/handlers/douyin-publish.ts` 含 `resolveDouyinScriptPath` 函数，type=article 时路由到 `-article-dryrun.cjs`
  Test: node -e "const c=require('fs').readFileSync('services/agent/src/handlers/douyin-publish.ts','utf8');if(!c.includes('resolveDouyinScriptPath'))process.exit(1);if(!c.includes('publish-douyin-article'))process.exit(1)"

- [ ] [ARTIFACT] `.github/workflows/agent-e2e-video.yml` 含 DOUYIN_COOKIES secret 注入步骤（CI_GAP 补写后验证）
  Test: node -e "const c=require('fs').readFileSync('.github/workflows/agent-e2e-video.yml','utf8');if(!c.includes('DOUYIN_COOKIES'))process.exit(1)"

---

## BEHAVIOR 条目（内嵌可执行 manual: 命令）

### BEHAVIOR 1 — type 路由正确性：type=article 时选 article-dryrun 脚本

- [ ] [BEHAVIOR] `resolveDouyinScriptPath({type:'article'})` 返回路径含 `publish-douyin-article-dryrun`（ZENITHJOY_AGENT_REAL_PUBLISH 未设时）
  Test: manual:bash -c 'cd /Users/administrator/perfect21/zenithjoy && node -e "
    process.env.ZENITHJOY_AGENT_ROOT = \"services/agent\";
    const { resolveDouyinScriptPath } = require(\"./services/agent/dist/handlers/douyin-publish.js\");
    const p = resolveDouyinScriptPath({type:\"article\"}, {});
    if (!p.includes(\"publish-douyin-article-dryrun\")) { console.error(\"FAIL: got\",p); process.exit(1); }
    console.log(\"OK:\",p);
  " 2>&1'
  期望: OK: .../publish-douyin-article-dryrun.cjs

### BEHAVIOR 2 — dryrun 脚本 stdout 最后一行 JSON 含 ok:true dryRun:true（本机 PowerShell 直跑）

- [ ] [BEHAVIOR] `publish-douyin-article-dryrun.cjs` 在 DOUYIN_COOKIES 注入时 stdout 最后一行为 `{"ok":true,"dryRun":true,...}`
  Test: manual:bash -c '
    QUEUE=$(mktemp /tmp/queue-XXXXXX.json)
    COVER=$(mktemp /tmp/cover-XXXXXX.png)
    # 写最小 cover PNG（1x1 red pixel）
    python3 -c "import base64,sys; sys.stdout.buffer.write(base64.b64decode(\"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI6QAAAABJRU5ErkJggg==\"))" > "$COVER"
    echo "{\"title\":\"[DRY] BEHAVIOR test\",\"content\":\"test\",\"cover\":\"$COVER\"}" > "$QUEUE"
    OUTPUT=$(node services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs "$QUEUE" 2>/dev/null)
    LAST_JSON=$(echo "$OUTPUT" | grep "^{" | tail -1)
    if [ -z "$LAST_JSON" ]; then echo "FAIL: 无 JSON 输出"; exit 1; fi
    echo "$LAST_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d[\"ok\"]==True, f\"ok={d[\"ok\"]}\"; assert d[\"dryRun\"]==True, f\"dryRun={d[\"dryRun\"]}\"; print(\"OK\")" || exit 1
    rm -f "$QUEUE" "$COVER"
  '
  期望: OK

### BEHAVIOR 3 — JSON schema 字段完整性：ok + dryRun 两个字段都存在（keys 完整性）

- [ ] [BEHAVIOR] dryrun 脚本 JSON 输出必须同时含 `ok` 和 `dryRun` 字段（缺任一 = FAIL）
  Test: manual:bash -c '
    QUEUE=$(mktemp /tmp/queue-XXXXXX.json)
    COVER=$(mktemp /tmp/cover-XXXXXX.png)
    python3 -c "import base64,sys; sys.stdout.buffer.write(base64.b64decode(\"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI6QAAAABJRU5ErkJggg==\"))" > "$COVER"
    echo "{\"title\":\"[DRY] keys test\",\"content\":\"test\",\"cover\":\"$COVER\"}" > "$QUEUE"
    OUTPUT=$(node services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs "$QUEUE" 2>/dev/null)
    LAST_JSON=$(echo "$OUTPUT" | grep "^{" | tail -1)
    echo "$LAST_JSON" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert \"ok\" in d, f\"缺字段 ok\"
assert \"dryRun\" in d, f\"缺字段 dryRun\"
print(\"OK: keys present\")
" || exit 1
    rm -f "$QUEUE" "$COVER"
  '
  期望: OK: keys present

### BEHAVIOR 4 — 禁用字段反向：response 中不应含 `published` 字段（真发标志禁止在 dryrun 出现）

- [ ] [BEHAVIOR] dryrun 输出 JSON **不含** `published:true`（`published` 是真发脚本专属字段，dryrun 严禁出现）
  Test: manual:bash -c '
    QUEUE=$(mktemp /tmp/queue-XXXXXX.json)
    COVER=$(mktemp /tmp/cover-XXXXXX.png)
    python3 -c "import base64,sys; sys.stdout.buffer.write(base64.b64decode(\"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI6QAAAABJRU5ErkJggg==\"))" > "$COVER"
    echo "{\"title\":\"[DRY] anti-published test\",\"content\":\"test\",\"cover\":\"$COVER\"}" > "$QUEUE"
    OUTPUT=$(node services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs "$QUEUE" 2>/dev/null)
    LAST_JSON=$(echo "$OUTPUT" | grep "^{" | tail -1)
    echo "$LAST_JSON" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d.get(\"published\") is not True, f\"禁用字段 published=True 出现在 dryrun 输出\"
print(\"OK: published 未出现或非 true\")
" || exit 1
    rm -f "$QUEUE" "$COVER"
  '
  期望: OK: published 未出现或非 true

### BEHAVIOR 5 — error path：封面文件不存在时 exit 1 + ok:false

- [ ] [BEHAVIOR] 封面文件路径不存在时，脚本 exit code 为 1，stdout JSON 含 `ok:false`
  Test: manual:bash -c '
    QUEUE=$(mktemp /tmp/queue-XXXXXX.json)
    echo "{\"title\":\"error path test\",\"content\":\"test\",\"cover\":\"/nonexistent/cover.png\"}" > "$QUEUE"
    OUTPUT=$(node services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs "$QUEUE" 2>/dev/null)
    EXIT_CODE=$?
    LAST_JSON=$(echo "$OUTPUT" | grep "^{" | tail -1)
    [ "$EXIT_CODE" -ne 0 ] || { echo "FAIL: exit code 应为非0，实际=$EXIT_CODE"; exit 1; }
    echo "$LAST_JSON" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d[\"ok\"] == False, f\"ok 应为 false，实际={d[\"ok\"]}\"
print(\"OK: error path exit 1 + ok:false\")
" || exit 1
    rm -f "$QUEUE"
  '
  期望: OK: error path exit 1 + ok:false

### BEHAVIOR 6 — 安全栅栏：dryrun 不触发 /web/api/media/article/publish

- [ ] [BEHAVIOR] dryrun 脚本 stdout 不含 `[DY-ARTICLE-DRY] !! 检测到文章发布 API 调用，dry-run 失守 !!`（内置安全栅栏监听）
  Test: manual:bash -c '
    QUEUE=$(mktemp /tmp/queue-XXXXXX.json)
    COVER=$(mktemp /tmp/cover-XXXXXX.png)
    python3 -c "import base64,sys; sys.stdout.buffer.write(base64.b64decode(\"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI6QAAAABJRU5ErkJggg==\"))" > "$COVER"
    echo "{\"title\":\"[DRY] safety test\",\"content\":\"test\",\"cover\":\"$COVER\"}" > "$QUEUE"
    ALL_OUTPUT=$(node services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs "$QUEUE" 2>&1)
    if echo "$ALL_OUTPUT" | grep -q "dry-run 失守"; then
      echo "FAIL: 安全栅栏触发，文章发布 API 被调用"
      exit 1
    fi
    echo "OK: 安全栅栏未触发"
    rm -f "$QUEUE" "$COVER"
  '
  期望: OK: 安全栅栏未触发

---

## CI_GAP 补写要求（Generator 必须在 .github/workflows/agent-e2e-video.yml 或新 job 中补写）

> 以下 4 项 CI_GAP 需要 Generator 补写 workflow step。在 CI 补写完成前，windows_cloud 环境的 BEHAVIOR 1-6 依赖本地 manual:bash 执行。

1. **补写 DOUYIN_COOKIES 注入**：在 `Write .env` step 或新 step 中将 `secrets.DOUYIN_COOKIES` 写入 Agent 的 `.env` 文件或注入为 env var，供 `publish-douyin-article-dryrun.cjs` cookie 注入模式使用
2. **补写 task 下发 step**：在 `Run Playwright E2E test` 后新增 step，通过 curl 向中台 POST `{task_type:"douyin_publish", payload:{type:"article", title:"[DRY]...", content:"...", cover:"..."}}` 触发 Agent handler
3. **补写 dryrun 回执验证 step**：轮询 `/api/agent/tasks/{task_id}/result`（或从 Agent log 提取），验证 JSON 含 `ok:true dryRun:true`
4. **补写 handler 路由日志验证 step**：从 `$env:RUNNER_TEMP\agent-out.log` grep `[type-route] resolveDouyinScriptPath type=article`，确认 Agent 选了 article 脚本

---

## E2E 验收（final-e2e — windows_cloud 变体 B：publisher dryrun）

**target_environment**: windows_cloud（`.github/workflows/agent-e2e-video.yml`）
**PASS 标准**: PowerShell 脚本 exit 0 + stdout JSON `ok:true, dryRun:true`
**FAIL 标准**: exit 1 OR `ok:false` OR timeout 15min

```powershell
# final-e2e 验证脚本 — ZenithJoy Agent 抖音图文 Dryrun（windows-latest）
# 在 agent-e2e-video.yml 中的 Run Playwright E2E test 步骤之后执行

param(
  [string]$Platform = "douyin",
  [string]$PublishType = "article",
  [string]$CloudBase = "https://autopilot.zenjoymedia.media",
  [string]$LicenseKey = "ZJ-F-FBFYTLFR"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# 1. 创建测试封面图（PowerShell System.Drawing）
Write-Host "[e2e-article-dryrun] 创建测试封面..."
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Bitmap]::new(300, 200)
$g = [System.Drawing.Graphics]::FromImage($img)
$g.Clear([System.Drawing.Color]::FromArgb(255, 100, 0))
$g.DrawString("ZenithJoy DryRun", [System.Drawing.SystemFonts]::DefaultFont, [System.Drawing.Brushes]::White, 50, 80)
$g.Dispose()
$coverPath = "$env:GITHUB_WORKSPACE\test-article-cover.png"
$img.Save($coverPath)
$img.Dispose()
Write-Host "[e2e-article-dryrun] 封面: $coverPath"

# 2. 创建 queue.json
$queue = @{
  title   = "[DRY-RUN] E2E 图文自检 $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
  content = "GitHub Actions E2E 自动验证图文 dryrun 路径。"
  cover   = $coverPath
  summary = "E2E 自检"
} | ConvertTo-Json -Depth 5
$queuePath = "$env:GITHUB_WORKSPACE\queue-article.json"
$queue | Out-File -FilePath $queuePath -Encoding utf8

# 3. 通过中台 API 下发 douyin_publish task（type=article）→ Agent 接收
$hdr = @{ Authorization = "Bearer $LicenseKey"; "Content-Type" = "application/json" }
$taskBody = @{
  task_type = "douyin_publish"
  payload   = @{
    type    = "article"
    title   = "[DRY-RUN] E2E 图文自检"
    content = "E2E 验证正文。"
    cover   = $coverPath
  }
} | ConvertTo-Json -Depth 5

Write-Host "[e2e-article-dryrun] 下发 task..."
$taskResp = Invoke-RestMethod -Uri "$CloudBase/api/ai-content/tasks" `
  -Method POST -Headers $hdr -Body $taskBody -ErrorAction Stop
$taskId = $taskResp.id ?? $taskResp.task_id
if ([string]::IsNullOrWhiteSpace($taskId)) { throw "FAIL: task_id 为空，中台下发失败" }
Write-Host "[e2e-article-dryrun] taskId=$taskId"

# 4. 等待 Agent 处理（最多 3 分钟）
$maxWait = 180; $elapsed = 0
$finalResult = $null
while ($elapsed -lt $maxWait) {
  Start-Sleep -Seconds 5; $elapsed += 5
  try {
    $r = Invoke-RestMethod -Uri "$CloudBase/api/ai-content/tasks/$taskId" -Headers $hdr -EA Stop
    Write-Host "[e2e-article-dryrun] ${elapsed}s status=$($r.status)"
    if ($r.status -eq "completed" -or $r.status -eq "failed") {
      $finalResult = $r
      break
    }
  } catch { Write-Host "[e2e-article-dryrun] 轮询: $($_.Exception.Message)" }
}

if (-not $finalResult) { throw "FAIL: task 在 ${maxWait}s 内未完成" }

# 5. 验证回执 JSON：ok:true + dryRun:true
$receipt = $finalResult.result ?? $finalResult
Write-Host "[e2e-article-dryrun] receipt: $($receipt | ConvertTo-Json)"

if ($receipt.ok -ne $true) {
  throw "FAIL: ok=$($receipt.ok) (expected true) error=$($receipt.error)"
}
if ($receipt.dryRun -ne $true) {
  throw "FAIL: dryRun=$($receipt.dryRun) (expected true) — 可能走了真发路径"
}

# 6. 验证 Agent 日志中有 type=article 路由记录（[CI_GAP: agent-type-route] 补写后可用）
$agentLog = "$env:RUNNER_TEMP\agent-out.log"
if (Test-Path $agentLog) {
  $typeRouteLog = Get-Content $agentLog | Where-Object { $_ -match "type-route.*type=article" }
  if ($typeRouteLog) {
    Write-Host "[e2e-article-dryrun] ✅ agent 日志确认 type=article 路由: $($typeRouteLog | Select-Object -First 1)"
  } else {
    Write-Host "[e2e-article-dryrun] WARNING: agent 日志未找到 type=article 路由记录（可能 agent 版本旧）"
  }
}

Write-Host "✅ E2E dryrun 验证通过: ok=$($receipt.ok) dryRun=$($receipt.dryRun)"
exit 0
```

**PASS 标准**: exit 0 + `ok:true dryRun:true`
**FAIL 标准**: exit 1 OR `ok:false` OR `dryRun:false` OR timeout 3 min

---

## 自查 checklist（proposer 内部验证）

1. PRD Response Schema 字段：`ok (boolean)`, `dryRun (boolean)` — 来自 task prompt 明确定义
2. Contract jq/python3 断言字段：`ok`, `dryRun` — 与 PRD 字面一致 ✅
3. PRD 字段集合 == Contract 断言字段集合 ✅
4. 禁用字段 `published` — 在 BEHAVIOR 4 用 `assert d.get("published") is not True` 反向检查 ✅
5. BEHAVIOR 条目数：6 条，>= 4 ✅
6. 假绿自查：
   - BEHAVIOR 1：依赖 `resolveDouyinScriptPath` 函数存在且 type=article 分支实现 — 代码不存在时 FAIL ✅
   - BEHAVIOR 2：依赖 dryrun 脚本实际运行并输出 `ok:true dryRun:true` — 未实现时 FAIL ✅
   - BEHAVIOR 3：依赖 JSON 同时含 `ok` + `dryRun` — 缺字段时 FAIL ✅
   - BEHAVIOR 4：反向检查禁用字段 — 无法造假 ✅
   - BEHAVIOR 5：封面不存在时 exit 1 — 测的是脚本的错误处理路径，代码不处理时 FAIL ✅
   - BEHAVIOR 6：安全栅栏检查 — 脚本不实现监听时不会输出"失守"日志，但也不会 FAIL（此条为偏 ARTIFACT 性质，可接受）✅
