# Contract DoD — gear=hotfix 短流程示例

> 本文件由 harness-controller gear=hotfix 路径自动生成。
> 格式与全流程 GAN 产物一致（[BEHAVIOR] 条目 ≥4，manual:bash 可执行验收命令）。

## DoD 条目

[BEHAVIOR] API 响应头含 X-Request-Id
- 描述：所有 API 端点的响应必须包含 `X-Request-Id` header，值为 UUID v4 格式
- 验收层级：[L1] manual:bash
- 验收命令：`curl -s -I https://api.example.com/health | grep -i 'x-request-id' | grep -Eo '[0-9a-f-]{36}'`
- 通过条件：输出非空（匹配到 UUID）

[BEHAVIOR] X-Request-Id 在 POST 请求中同样存在
- 描述：POST/PUT/PATCH/DELETE 请求的响应同样需要返回 X-Request-Id header
- 验收层级：[L1] manual:bash
- 验收命令：`curl -s -I -X POST https://api.example.com/items | grep -i 'x-request-id'`
- 通过条件：header 存在

[BEHAVIOR] X-Request-Id 值在同一请求链路中保持一致
- 描述：同一请求（含 upstream 传入的 Request-Id）不得产生新的随机值，应透传或生成后固定
- 验收层级：[L1] manual:bash
- 验收命令：`R1=$(curl -s -I -H 'X-Request-Id: test-uuid-1234' https://api.example.com/health | grep -i 'x-request-id' | awk '{print $2}' | tr -d '\r'); [ "$R1" = "test-uuid-1234" ] && echo PASS || echo FAIL`
- 通过条件：输出 PASS

[BEHAVIOR] 原有 API 行为零回归（hotfix 不引入新 side-effect）
- 描述：除 X-Request-Id header 新增外，API 响应体/状态码/其他 header 不得有任何变化
- 验收层级：[L1] manual:bash
- 验收命令：`bash sprints/YYYYMMDD-hotfix-<slug>/tests/contract-tests.sh`
- 通过条件：所有测试 exit 0

## 安全阀检查（gear=hotfix 专属）

- [ ] sprint-prd.md 含 `## 锚定声明` 段（缺则拒绝 hotfix，回退全流程）
- [ ] generator 未修改任何 Golden Path 断言（违者 FATAL 升档）
- [ ] 所有 [BEHAVIOR] 条目均来自 thin_prd 锚定声明，无 GAN 扩展条目

## 元数据

```
gear: hotfix
generated_by: harness-controller v2.8.0
shortflow: true (skip proposer/reviewer GAN)
```
