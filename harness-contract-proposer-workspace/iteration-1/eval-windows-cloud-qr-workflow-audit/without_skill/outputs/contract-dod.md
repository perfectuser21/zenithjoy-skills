# Sprint Contract — DoD
## 功能：ZenithJoy Agent 抖音 QR 扫码绑定

**Sprint ID**: agent-qr-douyin-bind-v1
**Target Environment**: windows_cloud (GitHub Actions windows-latest)
**Workflow**: `.github/workflows/agent-qr-windows-verify.yml`
**生成方式**: baseline（无 skill）
**日期**: 2026-05-30

---

## 一、用户路径（Golden Path）

```
用户启动 Agent → Agent 打开抖音创作者后台弹出 QR 码
→ 用户用手机扫码登录
→ Agent 检测到 sessionid/sessionid_ss/sid_tt cookie 出现在 .douyin.com 域
→ storageState 序列化写入 ~/.zenithjoy-agent/sessions/douyin/default.json
→ 发布 handler 读取该文件，注入 DOUYIN_COOKIES env var 到 publisher 子进程
→ publisher 进程使用 cookie 完成发布（dryrun 模式下不真实点击发布按钮）
```

---

## 二、[BEHAVIOR] 断言列表

### B-1：Session 文件路径符合约定
[BEHAVIOR]
- **断言**：扫码成功后，session 文件必须写入 `%USERPROFILE%\.zenithjoy-agent\sessions\douyin\default.json`（Windows 路径，对应 `os.homedir()` + `.zenithjoy-agent/sessions/douyin/default.json`）
- **验证方式**：`Test-Path "$env:USERPROFILE\.zenithjoy-agent\sessions\douyin\default.json"` 返回 `True`
- **失败条件**：文件不存在，或路径组件不完整（如缺少 `sessions/douyin/` 子目录层级）

### B-2：Session 文件包含有效抖音 cookie
[BEHAVIOR]
- **断言**：`default.json` 内容为合法 JSON，`cookies` 数组中至少存在一条满足：`name` 为 `sessionid_ss`、`sessionid` 或 `sid_tt` 之一，且 `domain` 以 `.douyin.com` 结尾，且 `value` 非空字符串
- **验证方式**：PowerShell `Get-Content | ConvertFrom-Json` 读取文件，断言 `cookies` 数组长度 ≥ 1，且至少一条 cookie 满足上述条件
- **失败条件**：文件内容非 JSON / cookies 为空数组 / 无满足条件的 session cookie

### B-3：Handler 能读取本地 session 文件
[BEHAVIOR]
- **断言**：`douyin-publish.ts` 中的 `readLocalDouyinSession()` 调用时，若 `DOUYIN_COOKIES` 未设，必须成功读取 `~/.zenithjoy-agent/sessions/douyin/default.json` 并返回非空字符串
- **验证方式**：单元测试中写入临时 session 文件，调用 `handleDouyinPublish` 或 `handleDouyinPublishTask`，断言 spawn 子进程的 env 中 `DOUYIN_COOKIES` 等于写入的内容（通过 `spawnImpl` mock 捕获）
- **失败条件**：`DOUYIN_COOKIES` 未注入到 spawn env / 读取抛异常未被 catch / 返回 undefined

### B-4：DOUYIN_COOKIES 正确注入到 publisher 子进程
[BEHAVIOR]
- **断言**：`handleDouyinPublishTask` spawn publisher 子进程时，`spawnEnv.DOUYIN_COOKIES` 必须等于 session 文件内容（完整 JSON 字符串，含 cookies + origins 字段）
- **验证方式**：mock `spawnImpl`，捕获传入的 `env` 参数，断言 `env.DOUYIN_COOKIES` 为有效 JSON 且 `JSON.parse(env.DOUYIN_COOKIES).cookies` 数组非空
- **失败条件**：env 中 DOUYIN_COOKIES 为 undefined / 为空字符串 / 不是合法 JSON

### B-5：QR 绑定超时返回标准错误结构
[BEHAVIOR]
- **断言**：用户未在 `timeoutMs` 内完成扫码，handler 必须返回 `{ ok: false, qr_login: 'timeout', error: <含 timeout 字样的字符串> }`
- **验证方式**：单元测试中注入返回空 cookies 的 mock storageState，设置极短 timeoutMs（如 50ms），断言返回值符合上述结构
- **失败条件**：返回 `ok: true` / 不含 `qr_login: 'timeout'` / error 字段为空

### B-6：Windows 路径分隔符兼容性
[BEHAVIOR]
- **断言**：`getSessionPath('douyin', 'default')` 在 Windows 环境（`os.homedir()` 返回 `C:\Users\<user>`）下，返回路径使用 `\` 分隔符，且路径结构正确（`<homedir>\.zenithjoy-agent\sessions\douyin\default.json`）
- **验证方式**：在 windows-latest runner 的 unit test job 中，`path.join` 自动处理分隔符，断言 `res.sessionPath.endsWith('sessions\\douyin\\default.json')` 或 `sessions/douyin/default.json`（`path.join` 在不同平台各自正确）
- **失败条件**：路径硬编码 `/` 导致 Windows 下文件写入失败 / `fs.mkdirSync` 目录创建失败

### B-7：`qr_login: 'success'` 与文件写入原子性
[BEHAVIOR]
- **断言**：返回 `{ ok: true, qr_login: 'success' }` 时，session 文件必须已经成功落盘（`fs.existsSync(sessionPath)` 为 true），不允许返回 ok:true 但文件未写入
- **验证方式**：单元测试在调用结束后立即读取 `res.sessionPath`，断言文件存在且内容与 mock storageState 一致
- **失败条件**：返回 ok:true 但 sessionPath 文件不存在 / 文件内容与 storageState 不一致

---

## 三、CI 覆盖分析

### 当前 workflow 覆盖情况（`agent-qr-windows-verify.yml`）

| Job | 覆盖内容 | 状态 |
|-----|---------|------|
| `unit-tests-windows` | 运行 `services/agent` 所有单元测试，含 `qr-bind-douyin.test.ts`，验证 B-2/B-3/B-5/B-7 | ✅ 已覆盖 |
| `sandbox-install` | 下载 COS install pack，验证 exe 存在且 >1MB | ⚠️ 部分覆盖（只验证打包，不验证 QR 绑定行为）|

### [CI_GAP] 缺失的 E2E 验证

**[CI_GAP] GAP-1：无端到端 QR 扫码 → session 文件写入验证**
- 当前 CI 仅有 unit test（mock launcher），没有在 windows-latest runner 上真实运行 Agent exe + 模拟扫码 + 验证文件写入的 E2E job
- **修复建议**：在 `sandbox-install` job 之后增加 `e2e-session-flow` job：启动 Agent exe，发送 `qr_bind_douyin` task，提供预录制的 mock storageState（或 playwright codegen 录制）验证文件落地

**[CI_GAP] GAP-2：`sandbox-install` job 不验证 DOUYIN_COOKIES 注入行为（B-4）**
- exe 大小校验通过不代表 session → DOUYIN_COOKIES 链路正确
- **修复建议**：在 install smoke 中增加一步：写入 fixture session 文件，调用 Agent 触发 publish task（dryrun 模式），捕获 spawn 的子进程 env 或日志中 `[handler:douyin] 使用本地 QR session 注入 DOUYIN_COOKIES` 字样

**[CI_GAP] GAP-3：workflow 只支持 `workflow_dispatch`，无 PR trigger**
- QR 绑定代码改动不会自动触发验证，存在回归风险
- **修复建议**：添加 `on: pull_request: paths: ['services/agent/**']` trigger

**[CI_GAP] GAP-4：`sandbox-install` 不验证打包产物内是否包含 `qr-bind-douyin.cjs` 和 `publishers/` 目录**
- exe 打包可能遗漏 publishers 目录，导致 `resolveQrBindDouyinScript()` fallback 到 dev 路径失败
- **修复建议**：在 Extract 步骤后增加 `Test-Path "pack\publishers\qr-bind-douyin.cjs"` 校验

---

## 四、DoD 验收检查清单

```
□ B-1: session 文件路径 %USERPROFILE%\.zenithjoy-agent\sessions\douyin\default.json 存在
□ B-2: session 文件 JSON 合法，包含 .douyin.com session cookie
□ B-3: handler readLocalDouyinSession() 成功读取并返回非空字符串
□ B-4: DOUYIN_COOKIES env var 正确注入 publisher spawn 进程
□ B-5: 超时场景返回 { ok: false, qr_login: 'timeout' }
□ B-6: Windows 路径分隔符下 getSessionPath 返回正确路径
□ B-7: ok:true 时 sessionPath 文件已落盘且内容正确
□ CI: unit-tests-windows job 全部通过
□ CI: sandbox-install job 通过（exe 存在且 >1MB）
□ CI GAP（待修复）: 无端到端 QR session 文件写入 E2E
□ CI GAP（待修复）: 无 PR trigger 自动触发
```

---

## 五、技术参考

- **session 写入逻辑**：`services/agent/src/handlers/qr-bind-douyin.ts` L182-183（`fs.mkdirSync` + `fs.writeFileSync`）
- **session 读取注入逻辑**：`services/agent/src/handlers/douyin-publish.ts` L111-129（`readLocalDouyinSession()`）、L190-198（注入到 spawnEnv）
- **cookie 识别规则**：sessionid_ss / sessionid / sid_tt，domain 必须 endsWith `.douyin.com`
- **Windows runner**：`windows-latest`，Node 20，`services/agent` working-directory
