# Harness Evaluator — 评估结果

## 评估对象

- 文件路径：`/tmp/eval-evaluator-fixtures/hollow-workflow.yml`
- 评估时间：2026-05-30
- 评估模式：windows_cloud workflow 内容检查（pre-trigger 空壳检测）

## 判定结论

**FAIL — 空壳 workflow，禁止触发 Final E2E**

## 详细分析

### Workflow 基本信息

```
name: agent-hollow-check
触发器: workflow_dispatch（需 artifact_path 输入）
运行环境: windows-latest
步骤数: 2
```

### 业务逻辑验证步骤计数

按照 harness-evaluator 空壳检测规则，扫描以下关键词：

| 关键词类别 | 包含项 | 数量 |
|---|---|---|
| 业务行为验证（node/npx/npm/vitest/playwright/curl/Invoke-RestMethod/session/publish/cookies/DOUYIN） | 无 | **0** |
| 文件存在/大小检查（Test-Path / .Length / .Size / file exist） | `$file.Length`（文件大小检查） | **1** |

### 失败依据

根据 harness-evaluator 反作弊规则（windows_cloud 空壳检测）：

> 若 `BUSINESS_STEPS == 0` 且 `SHALLOW_ONLY > 0`，判定为空壳 workflow，直接 FAIL，禁止触发。

本 workflow 符合此判定条件：
- `BUSINESS_STEPS = 0`：workflow 中不含任何业务行为验证（无 node 调用、无 Playwright、无 curl/Invoke-RestMethod、无 session 验证、无发布行为检测）
- `SHALLOW_ONLY = 1`：仅包含 `$file.Length` 文件大小检查

### Workflow 实际做了什么

```
步骤1: 下载 artifact (zenithjoy-agent)
步骤2: 检查下载文件大小是否 >= 1MB
```

这两个步骤只验证"文件存在且够大"，**完全不验证以下任何业务行为**：

- Agent 是否能正常安装
- Agent 是否能成功连接中台
- 用户路径（Path 1/Path 2/Path 4）任何一步是否可通过
- 任何 API 端点是否正确响应
- 任何会话/认证流程是否正常
- 任何内容发布行为是否成功

### 合同 BEHAVIOR 覆盖性

此 workflow 无法覆盖任何合同 `[BEHAVIOR]` 条目，因为它不执行任何业务逻辑。即便合同中有断言，此 workflow 跑"成功"也只意味着"文件被下载且大小 >= 1MB"，与业务正确性零关联。

## 修复方向

需要将 workflow 改写为真实业务验证，包含以下至少一项：

1. **安装并启动 Agent**：`Start-Process` 静默安装，等待进程起来
2. **调用 Agent API**：`Invoke-RestMethod http://localhost:<port>/health` 验证服务响应
3. **验证连接中台**：检查 Agent 是否成功向中台注册（API 回调或 DB 状态）
4. **跑 Playwright E2E**：`npx playwright test` 模拟用户操作路径

## 结论

```json
{"verdict":"FAIL","failed_step":"workflow_content_check","log_excerpt":"workflow agent-hollow-check 只包含文件大小检查（$file.Length），不含任何业务逻辑验证（node/npx/vitest/playwright/curl/Invoke-RestMethod）。合同 BEHAVIOR 断言无法通过此 workflow 真实验证。BUSINESS_STEPS=0, SHALLOW_ONLY=1。请更新 workflow 加入业务行为测试（如 Agent 安装启动 + API 健康检查 + Playwright 路径验证）后重新提交。"}
```
