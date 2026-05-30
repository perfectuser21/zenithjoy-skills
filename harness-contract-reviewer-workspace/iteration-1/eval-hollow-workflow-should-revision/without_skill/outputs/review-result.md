# Contract 审查结论

## 被审查的 Contract

- **target_environment**: windows_cloud
- **workflow**: `.github/workflows/agent-qr-windows-verify.yml`

### Contract 声明

- [ARTIFACT] session 文件写入路径
- [BEHAVIOR] CI 验证: 运行 agent-qr-windows-verify workflow，PASS = 文件存在且大小 > 1KB
- [BEHAVIOR] session 格式验证: 文件包含 cookies 字段

---

## 审查结论：**需要修改（REVISION REQUIRED）**

### 问题 1：BEHAVIOR 断言与 workflow 实际内容完全不匹配（严重）

Contract 声明的 BEHAVIOR：
- "文件存在且大小 > 1KB"（指 session 文件）
- "文件包含 cookies 字段"

实际 workflow 做的事：
1. `unit-tests-windows` job：运行 `npm test` 跑 qr-bind-operator 单元测试
2. `sandbox-install` job：从 COS 下载 `zenithjoy-agent-v{version}.tar.gz`，解压后验证 `zenithjoy-agent.exe` 存在且 > 1MB

**两个 job 都没有**：
- 写入任何 session 文件
- 检查 session 文件是否存在
- 验证 cookies 字段

Contract 断言的是一个在 workflow 里完全不存在的行为。BEHAVIOR 描述的是假想的验收条件，不是实际 workflow 执行的检查。

### 问题 2：ARTIFACT 描述模糊（中等）

"session 文件写入路径" 没有写出具体路径。Contract 应该明确写出：
- 路径（如 `%APPDATA%\zenithjoy\session.json` 或 `C:\Users\runner\.zenithjoy\session.json`）
- 由哪个步骤写入
- 在 workflow 的哪个 job/step 产生

### 问题 3：BEHAVIOR 未验证业务逻辑核心（严重）

Contract 意图似乎是验证"QR 扫码绑定 → session 文件被正确写入"。但 workflow 实际只验证：
1. 安装包能下载（网络/COS 可达性）
2. exe 文件存在且 >1MB（安装包完整性）

这两个断言**都不能证明 session 文件写入功能正常**。workflow 里根本没有触发任何扫码/绑定动作，也没有 Agent 运行的步骤。

### 问题 4：contract 断言无法通过 workflow 被验证

当前 workflow 没有任何步骤会：
- 启动 zenithjoy-agent.exe 并让它实际运行
- 模拟 QR 扫码流程
- 检查 session 文件存在性
- 解析 session 文件 JSON 并验证 cookies 字段

因此这个 contract 是"空洞的"（hollow）— BEHAVIOR 断言看起来有具体标准（文件大小、字段名），但背后的 workflow 完全没有执行对应验证逻辑。

---

## 需要的修改方向

### 方案 A：修改 workflow 使其真正验证 session 写入

在 `sandbox-install` job 里增加步骤：
1. 以 `--headless` 或测试模式启动 `zenithjoy-agent.exe`
2. 注入 mock session（或跳过 QR 步骤）让 Agent 写入 session 文件
3. 用 PowerShell 检查文件存在：`Test-Path "$env:APPDATA\zenithjoy\session.json"`
4. 用 PowerShell 解析并验证 cookies 字段：`(Get-Content session.json | ConvertFrom-Json).cookies`

### 方案 B：修改 contract 使其与 workflow 实际行为匹配

如果 workflow 的目的只是验证安装包完整性，则 contract 应该改为：

```
[ARTIFACT] zenithjoy-agent.exe 安装包
[BEHAVIOR] CI 验证: sandbox-install job PASS = agent.tar.gz 下载成功 + exe 解压存在 + 大小 > 1MB
[BEHAVIOR] 单元测试: unit-tests-windows job PASS = qr-bind-operator 所有单元测试通过
```

---

## 评分

| 维度 | 评分 | 说明 |
|------|------|------|
| ARTIFACT 明确性 | 2/5 | 路径未写明 |
| BEHAVIOR 可验证性 | 1/5 | 断言在 workflow 里完全没有对应实现 |
| BEHAVIOR 与业务逻辑对齐 | 1/5 | 没有验证 session 写入这个核心业务动作 |
| Contract 与实现一致性 | 0/5 | 严重不匹配，属于"空洞 contract" |
| 整体质量 | **不合格** | 需要修改后重新审查 |

---

*审查时间：2026-05-30*
*审查方式：without_skill（无 harness-contract-reviewer skill，直接判断）*
