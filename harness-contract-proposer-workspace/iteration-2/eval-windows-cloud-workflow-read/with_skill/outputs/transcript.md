# Harness Contract Proposer — 推理过程记录

**Eval**: eval-windows-cloud-workflow-read / with_skill
**Sprint**: ZenithJoy Agent 抖音 QR 扫码绑定
**执行日期**: 2026-05-30

---

## Step 1: 读取 Skill 文件

读取 `/Users/administrator/perfect21/zenithjoy-skills/harness-contract-proposer/SKILL.md`（v8.2.0）。

关键规则确认：
- **v8.1.0 规则**：windows_cloud workflow 内容审查强制 — 写任何 windows_cloud BEHAVIOR 引用 GHA workflow 之前，必须用 Bash cat 读取 workflow 实际内容，做用户路径 1:1 映射检查，缺失步骤标注 `[CI_GAP]`，禁止将文件存在/大小/版本号检查算作业务行为验证
- **v7.12.0 规则**：假绿反模式禁止（新端点 404-acceptable 旁路 + 环境操作当 BEHAVIOR）
- **v7.6.0 规则**：BEHAVIOR 数量 ≥ 4 条
- **v7.4.0 规则**：BEHAVIOR 必须内嵌 manual:bash 命令，不能只写 vitest 索引
- **v7.5.0 规则**：PRD 是法律，不许改字段名
- **两层验证架构**：模式 A（evaluator 逐 ws）+ 模式 B（final-e2e）

---

## Step 2: 读取 workflow 文件

执行 `cat .github/workflows/agent-qr-windows-verify.yml`。

**workflow 实际内容**：
- `job: unit-tests-windows` — 跑 `npm test -- --reporter=verbose`（qr-bind-operator 单元测试）
- `job: sandbox-install` — 从 COS 下载 zenithjoy-agent-v{version}.tar.gz，解压验证 exe 存在且大小 ≥ 1MB

**用户路径 1:1 映射分析**：

任务要求验证的用户路径：
1. 用户扫码后 session 写入 `~/.zenithjoy-agent/sessions/douyin/default.json`
2. handler 能读到 session 文件（`readLocalDouyinSession`）
3. DOUYIN_COOKIES 能注入发布进程（`spawnEnv.DOUYIN_COOKIES = localSession`）

workflow 覆盖情况：
- session 写入验证：**缺失** → `[CI_GAP: QR_SESSION_WRITE]`
- handler 读取验证：**缺失** → `[CI_GAP: SESSION_READ_BY_HANDLER]`
- DOUYIN_COOKIES 注入验证：**缺失** → `[CI_GAP: DOUYIN_COOKIES_INJECT]`

注意：`sandbox-install` job 里的文件大小检查不算业务行为验证（根据 v8.1.0 规则）。

---

## Step 3: 读取相关源码

读取以下文件以理解实现细节：

**`services/agent/src/handlers/qr-bind-douyin.ts`**：
- `getSessionPath(platform, accountLabel, sessionDir?)` — 计算 `~/.zenithjoy-agent/sessions/{platform}/{accountLabel}.json`
- `handleQrBindDouyin` — 扫码完成后 `fs.writeFileSync(sessionPath, JSON.stringify(storageState, null, 2))`
- 检测 session cookie 名：`['sessionid_ss', 'sessionid', 'sid_tt']`

**`services/agent/src/handlers/douyin-publish.ts`**：
- `readLocalDouyinSession(accountLabel = 'default')` — 读取 `~/.zenithjoy-agent/sessions/douyin/{accountLabel}.json`
- `spawnEnv.DOUYIN_COOKIES = localSession` — session 注入到 publisher 子进程 env
- 有 `fs.existsSync(sessionPath)` 保护，文件不存在时不抛异常，降级 CDP 模式

**`services/agent/src/handlers/__tests__/qr-bind-douyin.test.ts`**：
- 包含 `writes storageState to sessionPath` 测试用例
- 包含 `ok:false when launch fails` 和 `times out if user never logs in` error path 测试

---

## Step 4: 合同设计决策

### journey_type 选择

本 sprint 是 Agent 远程行为验证（Windows Agent + 扫码绑定），无标准 web UI，用 `agent_remote`。target_environment = `windows_cloud`。

### BEHAVIOR 设计原则

由于 target_environment = windows_cloud，BEHAVIOR 命令以 PowerShell/node -e 形式写，确保在 GitHub Actions windows-latest 上可直接执行。

为避免假绿，每条 BEHAVIOR 的设计原则：
- "如果对应代码一行都没写，这条命令会 FAIL 吗？" → 答案必须是 YES

各条 BEHAVIOR 真红分析：
1. **session 文件内容验证**：扫码成功 → 文件写入，文件不存在时 `Test-Path` 或 `fs.existsSync` 返回 false → exit 1
2. **handler 读取验证**：handler 读取逻辑依赖文件存在，用 node -e 验证读取链路完整
3. **DOUYIN_COOKIES 注入验证**：通过 grep 源码中 `spawnEnv.DOUYIN_COOKIES = localSession` 精确匹配，代码未实现时 grep 失败
4. **路径计算验证**：`getSessionPath` 实现错误时路径不匹配
5. **unit tests 完整性**：测试用例缺失时 `includes` 检查失败
6. **error path 保护**：源码中 `fs.existsSync` 和 CDP 降级 warn 日志缺失时失败

### CI_GAP 补写策略

按 v8.1.0 规则，workflow 缺失 3 个用户路径验证 step，必须：
1. 在 contract-dod.md 中标注 `[CI_GAP]`
2. 在 E2E 验收脚本中补写对应 step
3. 要求 Generator 将脚本作为新 job `qr-session-e2e` 补入 workflow

### windows_cloud E2E 脚本模板选择

本 sprint 不是安装包交付（变体 A），不是 publisher dryrun（变体 B），不是 Dashboard/Web App（变体 C）。
选用基础 windows_cloud 模板，自定义为 Agent session 验证场景。

**4 条 Windows PS1 强制规则遵守**：
- npm/npx 调用使用 `cmd.exe /c npm.cmd ...` 形式 ✅
- 指定 `-WorkingDirectory $repoRoot\services\agent` ✅
- 不涉及 Vite 端口（非 Dashboard sprint），跳过端口检测 ✅
- 无 localhost 服务（Agent session 验证不需要），跳过 `Test-NetConnection` ✅

---

## Step 5: 自查 Checklist 执行

1. PRD Response Schema 字段 → 本 sprint 无标准 REST API response，不适用
2. contract jq -e 字段名 → 使用 node -e 代替 jq（PowerShell 环境），字段名从任务描述字面取
3. schema 断言 → 不适用
4. 禁用字段反向检查 → 不适用
5. **BEHAVIOR 数量**: 6 条 ≥ 4 ✅
6. **假绿自查**: 全部 6 条均为真红（分析见 contract-dod.md）

---

## Step 6: 产出物列表

1. `contract-dod.md` — 包含 4 个 [ARTIFACT] + 6 个 [BEHAVIOR] + E2E 验收脚本 + CI_GAP 分析
2. `transcript.md` — 本文件

**未产出**（eval 约束）：
- `contract-draft.md` — GAN Round 1 草案（可由此 DoD 倒推）
- `tests/*.test.ts` — TDD Red 测试文件（已有现存测试，新 sprint 补充测试需 Generator 写）
- `task-plan.json` — GAN 收敛后产出
- git commit/push — eval 禁止

---

## 关键发现

1. **workflow 有 3 个 CI_GAP**：现有 workflow 只验证安装包完整性和 unit tests，完全没有验证核心用户路径（扫码→session写入→handler读取→DOUYIN_COOKIES注入）。这是真实的测试盲区。

2. **源码实现完整**：`qr-bind-douyin.ts` 和 `douyin-publish.ts` 的实现逻辑完整，包含 error path 保护（`existsSync` + try/catch + CDP 降级），合同 BEHAVIOR 可直接对应源码验证。

3. **BEHAVIOR 设计选择 node -e 而非 jq**：windows_cloud target 下，PowerShell 脚本中 `node -e` 比 `jq` 更可靠（避免 jq 未安装问题），且 node 在 windows-latest 可直接使用。

4. **walking skeleton thin 原则**：CI 中用 mock session 模拟扫码成功后的写入，而非真实 Playwright QR 扫码（真实扫码需要用户交互）。加厚阶段再接真实 Playwright QR 流程。
