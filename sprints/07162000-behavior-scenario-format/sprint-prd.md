# Sprint PRD — [BEHAVIOR] 三段式剧本格式升级（proposer + evaluator SKILL.md）

## OKR 对齐

- **对应 KR**：Cecelia 基础稳固 — 系统可信赖、算力全开、管家闭环（82%）
- **本次推进预期**：83%（harness 验收从命令行长相升级为可读剧本）

## 背景

合同 [BEHAVIOR] 现为命令行长相，异步预期无标准写法。Alex 07-16 拍板：evaluator 应像人一步步操作验收（"点设置 → 应该收到消息"），不是跑命令看退出码。本 sprint 升级 harness-contract-proposer/SKILL.md 与 harness-evaluator/SKILL.md 两个文本。

## Golden Path（核心场景）

用户从【proposer 写新合同】→【三段式 [BEHAVIOR]：动作/预期观察/验证命令】→【evaluator 按步执行并在 .brain-result.json 留 action/expected 证据】

1. proposer 读新模板，写出三段式 [BEHAVIOR]（含 until-loop 等待预算）
2. evaluator 按剧本逐步：执行动作 → 轮询预期观察（within 预算）→ 跑验证命令
3. .brain-result.json behavior_tests 条目新增 action/expected 字段（与 command/exit_code/log_tail 共存）

## 范围限定

**在范围内**：harness-contract-proposer/SKILL.md、harness-evaluator/SKILL.md（各自 version bump + changelog）；存量纯命令写法标 legacy 兼容不回改；样例剧本"点设置 → within 60s 收到消息"

**不在范围内**：cecelia 仓代码（harness-judge.js 只读核对不修改）；其他 harness skill 文件；存量 contract-draft.md 回改

## 假设

- [ASSUMPTION: 需 rebase 在 W3/b6b6cca5 main 之上，同文件改动冲突由 generator 解决]
- [ASSUMPTION: harness-judge.js behavior_tests[i] 现有字段为 command/exit_code/log_tail，新增 action/expected 字段向后兼容]

## 预期受影响文件

- `harness-contract-proposer/SKILL.md`：三段式模板、until-loop 范式、legacy 标记、样例剧本、version bump
- `harness-evaluator/SKILL.md`：按剧本逐步执行流程、behavior_tests action/expected 字段、version bump

## E2E 验收

> 产物为纯文本 SKILL.md，E2E 为 grep 机检格式合规性。

```bash
#!/usr/bin/env bash
set -euo pipefail
P="/workspace/harness-contract-proposer/SKILL.md"
E="/workspace/harness-evaluator/SKILL.md"
grep -q "动作" "$P" && grep -q "预期观察" "$P" && grep -q "验证命令" "$P" || { echo "FAIL: proposer 缺三段式关键词"; exit 1; }
grep -q "until" "$P" || { echo "FAIL: proposer 缺 until-loop 范式"; exit 1; }
grep -q "legacy" "$P" || { echo "FAIL: proposer 缺 legacy 兼容标记"; exit 1; }
grep -q "action" "$E" && grep -q "expected" "$E" || { echo "FAIL: evaluator 缺 action/expected 字段"; exit 1; }
grep -qE "within|60s" "$P" || { echo "FAIL: proposer 缺样例等待预算"; exit 1; }
echo "PASS"
```

## NFR 约束

<!-- 来源: decisions 表 category=nfr，PrepPRD 显式值优先 -->
- 超时/延迟: 样例剧本等待预算 within 60s（PrepPRD 显式）
- 其余: 待定（PrepPRD 未指定）

## Invariant 约束（铁律，proposer/evaluator 不得违反）

<!-- 来源: decisions category=invariant，step + journey_feature + area 三源合并去重 -->
- [generator 不得自 merge] generator 只推 branch，merge 权归 controller（来源: area）
- [共享 CI 文件禁区] .github/workflows/*.yml 等未经合同显式授权不可修改（来源: area）
- [proposer 核查派发历史] 复用历史合同模板前必须核对真实执行历史（来源: area）
- [单 slot 串行] 一个 slot 同时只允许一个任务在跑（来源: area）
- [真环境验证才算 done] 接缝断言必须在真目标上验证过才算 done（来源: area）
- [凭据安全] secrets 不硬编码、不进 git、不进日志（来源: area）

## 累积 FR（本 line 已验收行为，本 sprint 不得回退/重复）

（本 line 暂无历史——journey_id 未绑定，无法查询已验收 golden_path）

## journey_type: autonomous
## journey_type_reason: 修改 harness skill 文本文件（工具链变更），无前端 UI/Windows App/微信 RPA
## target_environment: local_api
## target_environment_reason: payload 显式指定 local_api；zenithjoy-skills repo，E2E 为本地 grep 命令
## journey_id: none
## step_id: none（PrepPRD 未锚定具体 Golden Path step）
