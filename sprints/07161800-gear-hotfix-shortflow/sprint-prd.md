# Sprint PRD — harness-controller/SKILL.md 支持 gear=hotfix 短流程直通

## OKR 对齐

- **对应 KR**：harness 流程效率（修层短流程落地）
- **当前进度**：建制 W4
- **本次推进预期**：gear=hotfix 档落地，controller 可免 GAN 直通交付合同

## 背景

决策 145014a4：hotfix 类任务（图不变、仅修已有断言对应行为）反复走 proposer/reviewer 两棒 GAN 浪费循环。本 sprint 在 harness-controller/SKILL.md 中添加 gear=hotfix 短流程，让 controller 直接组装合同，generator/evaluator/judge 零感知。

## Golden Path（核心场景）

系统从 [controller 读取 task payload.gear=hotfix] → 经过 [跳过 proposer/reviewer GAN，controller 直接组装 contract-draft.md 与 contract-dod.md] → 到达 [generator 收到格式与全流程一致的合同文件，evaluator/judge 无感知正常执行]

具体：

1. controller 在 Relay 入口段变量表中读取 `HARNESS_GEAR`（来源 `task payload.gear`）
2. 检测 `HARNESS_GEAR=hotfix`：跳过 proposer/reviewer 两棒，controller 直接从 thin_prd 的锚定断言 + "必须先写复现 failing test" 要求组装 contract-draft.md 与 contract-dod.md；`[BEHAVIOR]` 条目 = 锚定步骤的既有断言原文 + 新 failing test
3. 合同文件结构与全流程产物完全一致（下游 generator/evaluator/judge 零改动、无感知）
4. 安全阀①：generator 发现需要改动 sprint-prd Golden Path 步骤定义/断言文本 → FATAL 报错升档，禁止顺手改
5. 安全阀②：thin_prd 缺锚定声明（未写覆盖父路第 N 步或独立小路）→ 拒绝 hotfix 档，回退全流程
6. 验收：SKILL.md 新段落 grep 断言通过 + 用例文档给出一次完整 hotfix 档产物示例；版本 bump + changelog

## 边界情况

- `gear` 字段缺失或非 `hotfix`：走现行全流程，零回归
- thin_prd 有锚定声明但锚定步骤在 sprint-prd 中不存在：FATAL 报错，不生成合同
- generator 修改 Golden Path 断言文本：FATAL 报错，禁止继续

## 范围限定

**在范围内**：
- `harness-controller/SKILL.md` 新增 gear=hotfix 识别段与 HARNESS_GEAR 变量表行
- controller 直接组装 contract-draft.md / contract-dod.md 的逻辑
- 两条安全阀铁律写入 SKILL.md
- 用例文档（hotfix 档完整产物示例，合同文件结构示例）
- 版本 bump + changelog

**不在范围内**：
- generator/evaluator/judge SKILL.md 改动（零感知）
- 新增 task_type 或 DB schema 变更
- UI/Dashboard 变更

## 假设

- [ASSUMPTION: 现有 sprint-prd 的 Golden Path 段已包含可锚定的步骤断言，hotfix 任务的 thin_prd 需显式写明"覆盖父路第 N 步"或"独立小路"字样]
- [ASSUMPTION: contract-draft.md / contract-dod.md 的格式以现行全流程产物为准，controller 按固定模板组装]

## 预期受影响文件

- `harness-controller/SKILL.md`: 新增 gear=hotfix 识别段、HARNESS_GEAR 变量表行、两条安全阀铁律、版本 bump + changelog
- `harness-controller/examples/` 或同仓用例目录: hotfix 档一次完整产物示例（contract-draft.md + contract-dod.md 结构示例）

## NFR 约束

<!-- 来源: decisions 表 category=nfr，PrepPRD 显式值优先 -->
- 超时/延迟: 待定（PrepPRD 未指定）
- 频控: 不适用
- 版本要求: harness-controller SKILL.md 需版本 bump（changelog 同步）
- 可观测: gear=hotfix 跳过 GAN 时须在 controller 日志输出 `[gear=hotfix] skip proposer/reviewer GAN`

## Invariant 约束（铁律，proposer/evaluator 不得违反）

<!-- 来源: decisions category=invariant，step + journey_feature + area 三源合并去重 -->
- [tmux子shell] headed relay 的 tmux innerCmd 启动的子 shell 不自动继承父进程环境变量；凡需要在 Claude session 内部感知 harness 上下文的变量必须在 innerCmd 字符串中显式 export（来源: area）
- [复用历史合同] Proposer 复用历史合同模板时必须先核对本次任务的真实派发/执行历史，不能假设与先例路径相同（来源: area）
- [CI共享文件禁区] .github/workflows/*.yml、smoke-allowlist.txt 等跨 sprint 共享文件未经合同显式授权不可修改（来源: area）
- [SHA锚定核验] PR 合并前须用 PR head SHA 核对 evaluator/judge verdict 文件锚定的 sha 与实际合并 sha 一致（来源: area）
- [单slot串行] 一个 slot/会话内严格串行执行任务（来源: area）
- [禁写死环境假设值] 环境假设值禁止写死，要么从环境推导要么真机校准（来源: area）
- [真环境验证] 接缝断言必须在真目标上验证过才算 done（来源: area）
- [凭据安全] secrets 不硬编码、不进 git、不进日志（来源: area）
- [租户隔离] 碰租户数据的查询/写入必须 scope 到当前租户（来源: area）

## 累积 FR（本 line 已验收行为，本 sprint 不得回退/重复）

<!-- 来源: 本 line 已完成 ability 的 golden_path，无 journey_id，优雅降级 -->
（本 line 暂无历史——无 journey_id，累积 FR 降级为空）

## E2E 验收

> 最终可执行 E2E 脚本由 proposer 在 GAN 阶段产出。

```bash
# 期望验收点（自然语言）：
# 1. grep harness-controller/SKILL.md 含 "HARNESS_GEAR" 行和 "gear=hotfix" 段
# 2. grep 安全阀铁律：(a) 禁改 Golden Path 断言 → FATAL；(b) 缺锚定声明 → 拒绝 hotfix 回退全流程
# 3. 用例文档存在：展示 hotfix 档 contract-draft.md + contract-dod.md 结构，与全流程产物一致
# 4. SKILL.md 版本号已 bump，changelog 含本次变更描述
# 5. 无 gear 字段时流程路径不变（零回归验证：grep 默认档条件分支存在）
```

## journey_type: dev_pipeline
## journey_type_reason: 改动目标为 harness-controller/SKILL.md（harness pipeline 技能文件），属于开发流水线配置变更
## target_environment: local_api
## target_environment_reason: payload 显式指定 local_api；zenithjoy-skills 仓纯 SKILL.md 文本变更，验收通过 grep 断言本地执行
## journey_id: none
## step_id: none（PrepPRD 未锚定）
