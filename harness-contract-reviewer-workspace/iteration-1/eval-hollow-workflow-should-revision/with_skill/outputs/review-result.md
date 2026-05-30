# Harness Contract Reviewer — 审查结果

## 元信息

- **审查时间**: 2026-05-30
- **Reviewer Skill 版本**: 8.0.0
- **target_environment**: windows_cloud
- **引用 workflow**: `.github/workflows/agent-qr-windows-verify.yml`
- **是否读取 workflow 文件**: 是（已通过 Bash 工具执行 `cat` 命令读取完整内容）

---

## Step 1: 读取合同内容

**待审查 contract-dod.md：**

```
target_environment: windows_cloud
workflow: .github/workflows/agent-qr-windows-verify.yml

[ARTIFACT] session 文件写入路径
[BEHAVIOR] CI 验证: 运行 agent-qr-windows-verify workflow，PASS = 文件存在且大小 > 1KB
[BEHAVIOR] session 格式验证: 文件包含 cookies 字段
```

**workflow 文件真实内容（已读取）：**

workflow `agent-qr-windows-verify.yml` 包含两个 job：

1. **unit-tests-windows**: 运行 `npm test -- --reporter=verbose`（qr-bind-operator unit tests）
2. **sandbox-install**: 从 COS 下载 zenithjoy-agent-v{version}.tar.gz → 解压 → 检查 `zenithjoy-agent.exe` 存在且大小 > 1MB

**关键发现**：workflow 文件里完全没有以下任何步骤：
- QR 码显示 / 扫码流程
- session 文件写入
- handler 读取 session
- DOUYIN_COOKIES 注入
- 任何抖音平台 session 相关的业务链路验证

---

## Step 2: 7 维 Rubric 评分

## RUBRIC SCORES

```json
{
  "dod_machineability": 3,
  "scope_match_prd": 2,
  "test_is_red": 2,
  "internal_consistency": 2,
  "risk_registered": 0,
  "verification_oracle_completeness": 1,
  "ci_workflow_alignment": 0
}
```

### 逐维证据

**DoD 机检性 = 3**
合同只有 `[BEHAVIOR] PASS = 文件存在且大小 > 1KB` 这个伪机检条件——它把文件大小 check 当成业务验证。没有任何 `node -e`、`curl`、`psql`、`npx vitest run` 等真正可执行的 exit-code 命令。`[ARTIFACT] session 文件写入路径` 甚至连具体路径都没给，无法写成可执行断言。得分极低但非 0，因为"文件存在且大小 > 1KB"在技术上是可用 PowerShell `Test-Path` + `Get-Item` 执行的，只是它验证的是错误的东西。

**Scope 匹配 PRD = 2**
task prompt 里描述的用户需求是"QR 扫码 → session 写入 → handler 读取 → DOUYIN_COOKIES 注入"的完整链路。合同只有 session 文件存在性和 cookies 字段两条，完全漏掉了：
- QR 扫码触发事件
- handler 读取 session 的逻辑
- DOUYIN_COOKIES 注入到后续流程
- 链路的任何中间验证点
PRD 描述的 4 个核心环节只覆盖了不到 1 个。

**Test 真红 = 2**
合同未列出任何测试文件路径。`[BEHAVIOR] session 格式验证: 文件包含 cookies 字段` 没有说明该验证在哪个测试文件里，也没有说明"不动代码时会 FAIL（因为什么原因 FAIL）"。workflow 里的 `npm test` 是 unit tests，但与 session 格式验证无直接关联。无法判断测试是否真红。

**内部一致 = 2**
`[ARTIFACT] session 文件写入路径` 声明了一个 artifact，但 `[BEHAVIOR]` 中验证"文件存在且大小 > 1KB"没有引用这个 artifact 的具体路径，形成悬空引用。两条 `[BEHAVIOR]` 之间没有数据流关系说明（第一条验证文件存在 → 第二条验证字段存在，但没说是同一个文件的同一次写入）。合同隐含假设 CI workflow 会生成 session 文件，但 workflow 文件里完全没有这个步骤。

**风险登记 = 0**
合同没有任何 Risks 栏。QR 扫码链路是高风险业务（二维码过期、网络超时、session 格式变更、DOUYIN_COOKIES 失效等），完全没有登记。

**Verification Oracle 完整性 = 1**
合同没有任何 `jq -e` 命令。`session 格式验证: 文件包含 cookies 字段` 是自然语言描述，没有具体的：
- `jq -e '.cookies | length > 0'`
- `jq -e 'keys | contains(["cookies"])'`
- session 文件 schema 的完整字段清单
- 禁用字段的反向检查
得 1 分（非 0）因为至少指出了需要验证 `cookies` 字段名，有一个概念上的 oracle 意图。

**CI Workflow 内容对齐 = 0**（关键维度）
Reviewer 已读取 workflow 文件。**致命不对齐发现**：

合同声称：`[BEHAVIOR] CI 验证: 运行 agent-qr-windows-verify workflow，PASS = 文件存在且大小 > 1KB`

但 `agent-qr-windows-verify.yml` 的实际内容是：
1. `unit-tests-windows` job → 运行 `npm test`（unit tests，无 session 文件生成）
2. `sandbox-install` job → 下载安装包、解压、验证 `zenithjoy-agent.exe` 存在且大小 > 1MB

**workflow 里没有任何步骤生成或验证 session 文件**。合同把"运行这个 workflow PASS"等同于"QR 扫码 session 链路验证通过"，但这两者根本不等价。这是 Specification 级别的严重错误：CI PASS 证明的是"安装包下载正常 + unit tests 通过"，完全不能证明"session 写入链路正常工作"。

---

## VERDICT: REVISION

**Round 1，target_environment = windows_cloud，阈值：7 维全部 ≥ 7 → APPROVED。**

当前各维度：
- dod_machineability: 3 < 7 → **BLOCK**
- scope_match_prd: 2 < 7 → **BLOCK**
- test_is_red: 2 < 7 → **BLOCK**
- internal_consistency: 2 < 7 → **BLOCK**
- risk_registered: 0 < 7 → **BLOCK**
- verification_oracle_completeness: 1 < 7 → **BLOCK**
- ci_workflow_alignment: 0 < 7 → **BLOCK（最严重）**

**总分: 10/70（目标 49/70+）**

所有 7 维均低于阈值，verdict = **REVISION**。

---

### 需要 Proposer 修的（block 项）

**问题 1**（维度：ci_workflow_alignment，当前 0 分，目标 ≥ 7）
**描述**：合同引用 `agent-qr-windows-verify.yml` 作为业务验证依据，但该 workflow 实际只测试安装包完整性 + unit tests，完全不涉及 QR 扫码/session 写入/DOUYIN_COOKIES 注入链路。用"workflow PASS"来声称"链路验证通过"是虚假对齐。
**修复**：要么新建一个真正执行 QR-session 链路的 workflow（包含启动 agent、触发 QR 流程、等待 session 文件写入、验证内容的步骤），要么把 BEHAVIOR 改为使用真实可执行的断言命令（不依赖这个 workflow）。

**问题 2**（维度：dod_machineability，当前 3 分，目标 ≥ 7）
**描述**：合同没有任何可直接执行的断言命令。`[ARTIFACT] session 文件写入路径` 连具体路径都没给（是 `%APPDATA%\zenithjoy\session.json`？还是别的？），无法写成 `Test-Path` 断言。
**修复**：每条 `[BEHAVIOR]` 必须有具体的可执行命令，如：
```powershell
# 验证文件存在且大小 > 1KB
$size = (Get-Item "$env:APPDATA\zenithjoy\qr-session.json").Length
if ($size -lt 1024) { exit 1 }

# 验证 cookies 字段
$session = Get-Content "$env:APPDATA\zenithjoy\qr-session.json" | ConvertFrom-Json
if (-not $session.cookies) { exit 1 }
```

**问题 3**（维度：scope_match_prd，当前 2 分，目标 ≥ 7）
**描述**：QR 扫码 → session 写入 → handler 读取 → DOUYIN_COOKIES 注入是 4 个关键环节，合同只覆盖了 session 文件写入后的格式检查，漏掉了 3 个环节的验证。
**修复**：补充以下 BEHAVIOR：
- QR 码触发事件（agent 收到 qr-bind 请求后生成 QR 图片/链接）
- handler 读取 session 的验证（session 文件被读取后返回正确的 cookies 数据结构）
- DOUYIN_COOKIES 注入验证（注入后发布接口能正常调用抖音 API）

**问题 4**（维度：risk_registered，当前 0 分，目标 ≥ 7）
**描述**：完全没有 Risks 栏。
**修复**：至少添加：
- Risk 1: QR 码 180 秒过期，CI runner 扫码窗口太小 → mitigation: mock QR 扫码事件，注入预生成 session 文件
- Risk 2: DOUYIN_COOKIES 格式随抖音版本变更 → mitigation: session schema 版本化，加 `schema_version` 字段验证

**问题 5**（维度：verification_oracle_completeness，当前 1 分，目标 ≥ 7）
**描述**：session 格式验证只说"包含 cookies 字段"，没有 schema 完整性验证。
**修复**：补充：
```powershell
# Windows PowerShell jq 等价
$session = Get-Content $sessionPath | ConvertFrom-Json
# schema 完整性
$required = @('cookies', 'user_id', 'expires_at')
$required | ForEach-Object { if (-not $session.$_) { Write-Error "Missing field: $_"; exit 1 } }
# cookies 非空
if ($session.cookies.Count -eq 0) { exit 1 }
```
