# Transcript：without_skill baseline eval

**场景**：hollow-workflow BEHAVIOR 断言覆盖判断  
**模式**：without_skill（不加载 harness-evaluator skill）  
**执行时间**：2026-05-30

---

## 推理过程

### 第一步：理解任务

收到请求：判断一个 windows_cloud Sprint 的 Final E2E workflow 是否能验证 contract-dod.md 里的 3 条 [BEHAVIOR] 断言。

### 第二步：解析 workflow 结构

workflow 共 2 个步骤：
1. `Invoke-WebRequest` 下载 installpack（tar.gz）
2. 检查 `zenithjoy-agent.exe` 是否存在 + 文件大小是否 ≥ 1MB

这是标准的 artifact sanity check 模式。

### 第三步：对比 BEHAVIOR 断言要求

contract-dod.md 要求验证 3 条 BEHAVIOR：
- session 写入路径
- DOUYIN_COOKIES 注入  
- vitest 回归测试

逐条检查：
- session 写入：workflow 没有启动 Agent → 不可能有 session 写入 → **未覆盖**
- DOUYIN_COOKIES：workflow 没有注入 env var，没有启动进程 → **未覆盖**
- vitest：workflow 没有任何 test runner 调用 → **未覆盖**

### 第四步：判断是否值得触发 run

触发条件：workflow 至少有可能验证部分 BEHAVIOR 断言。

当前情况：0 条断言有任何覆盖可能。触发 run 的 CI 结果（green/red）与 BEHAVIOR 验证毫无关系。

结论：**不触发，直接 FAIL**。

### 第五步：生成结果

写入 eval-result.md，包含：
- 逐条断言分析
- 现有 workflow 实际验证内容对比
- 修复方向建议
- 最终判断表

---

## 与 with_skill 的差异预期

without_skill 版本（本次）：
- 纯推理，无结构化 rubric
- 没有自动加载 contract-dod.md 内容（通过描述推断）
- 输出格式由 agent 自行决定
- 判断路径：workflow 内容 → BEHAVIOR 对比 → 结论

with_skill 版本（对照组）：
- harness-evaluator skill 会提供结构化评估框架
- 可能自动读取 contract-dod.md 文件内容
- 有标准化 rubric（覆盖率阈值/分级等）
- 输出格式更标准化

---

## 原始输入摘要

```yaml
# workflow 关键步骤
- Invoke-WebRequest 下载 agent.tar.gz
- Test-Path zenithjoy-agent.exe → exit 1 if missing
- Get-Item .Length < 1000000 → exit 1 if too small
```

BEHAVIOR 断言（来自描述）：
- session 写入路径
- DOUYIN_COOKIES 注入
- vitest 回归测试

---

## 最终结论

**FAIL**（不触发 workflow run）  
**理由**：workflow 是空壳 artifact check，BEHAVIOR 覆盖率 0/3
