# Contract Draft — gear=hotfix 短流程示例

> 本文件由 harness-controller gear=hotfix 路径自动生成，跳过 GAN（proposer/reviewer）直接从 thin_prd 锚定声明组装。

## 任务概要

- **Task ID**: `example-hotfix-task-0000`
- **Sprint**: `sprints/YYYYMMDD-hotfix-<slug>/`
- **Gear**: hotfix（短流程，跳过 GAN）
- **锚定来源**: `sprint-prd.md ## 锚定声明` 段

## 功能描述

> 示例：修复 API 响应缺少 `X-Request-Id` header 的问题。

hotfix 档合同聚焦单一确定性断言——目标行为已在 thin_prd 的「锚定声明」段明确描述，无须经过 GAN 对抗精化。

## E2E 验收

| 验收项 | 验收方式 | 通过条件 |
|--------|----------|----------|
| API 响应含 X-Request-Id header | `curl -I <endpoint>` 检查响应头 | header 存在且值为 UUID 格式 |
| 非 hotfix 路径不受影响 | 全套回归测试通过 | CI 绿 |

```bash
# E2E 验收命令（手动执行或 CI 自动）
curl -s -I https://api.example.com/health | grep -i "X-Request-Id"
```

## 未覆盖真实链路清单

N/A（hotfix 档不引入新 mock，覆盖线上真实路径）

## 合规说明

- 本合同由 gear=hotfix 短流程生成，**不经过 GAN 对抗**
- 锚定断言来自 `sprint-prd.md ## 锚定声明`，内容只读，禁止 generator 顺手改
- 若实现过程发现需修改锚定断言，必须升档为全流程 sprint（FATAL 报错）
