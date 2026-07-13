# Sprint PRD — Brain /api/brain/status 新增 uptime_seconds 字段

## OKR 对齐

- **对应 KR**：待定（Brain API `/api/brain/context` 不可达，无法读取当前活跃 KR）
- **当前进度**：未知（上下文源不可用）
- **本次推进预期**：Brain 可观测性小步推进（status 端点信息增强）

## 背景

用户需要在 status 接口直接看到 Brain 进程已运行多久（秒），用于快速判断 Brain 是否近期重启过、运行是否稳定。PrepPRD：用户在 status 接口能看到 Brain 已运行多久（秒），字段名 `uptime_seconds`。

> 上下文采集降级说明：本次规划时 Brain API（localhost:5221）不可达，`/api/brain/context`、`/api/brain/harness/runs`、`/api/brain/decisions?category=nfr` 均连接失败。无 Run 历史与 NFR 决策可参考，PRD 仅以 PrepPRD 为主源锚定，不臆测历史范围。

## Golden Path（核心场景）

用户/系统从 [请求 status 接口] → 经过 [Brain 计算进程启动至今秒数] → 到达 [响应中看到 uptime_seconds 字段]

具体：
1. 用户执行 `curl localhost:5221/api/brain/status`
2. Brain 在原有 status 响应基础上计算进程启动至今的秒数
3. 响应 JSON 中出现 `uptime_seconds` 字段，值为非负数，且随时间推移单调递增（两次间隔请求，第二次的值更大）

<!-- Response Schema由Proposer在Step 1.1读api_registry后推导，Planner不负责定义技术规范。 -->

## 边界情况

- 进程刚启动时请求：`uptime_seconds` 接近 0（允许为 0），不得为负数或缺失
- 原有 status 字段不受影响：新增字段是纯增量，已有字段一个不少、含义不变
- 进程重启后：`uptime_seconds` 归零重新计数（以进程启动时刻为基准，不是机器开机时间）

## 范围限定

**在范围内**：`/api/brain/status` 响应新增 `uptime_seconds` 字段（进程启动至今秒数）。
**不在范围内**：其他端点改动；uptime 的持久化/历史记录；Dashboard 展示；机器级 uptime；重启告警。

## 假设

- [ASSUMPTION: `uptime_seconds` 为数值型（整数秒即可满足"秒"粒度需求），不要求小数精度]
- [ASSUMPTION: 以 Brain Node.js 进程启动时刻为基准（进程级 uptime），非容器/宿主机 uptime]
- [ASSUMPTION: journey_id 缺失 — Brain API 不可达且 PrepPRD 未提供 Journey 锚定，留待 Proposer/上游补充]

## 预期受影响文件

- `packages/brain/src/server.js`（或 status 路由所在模块）: `/api/brain/status` 响应组装处新增 `uptime_seconds` 计算与输出（位置词死规则：thin_prd 含 "Brain" → 实现必须落在 `packages/brain/src/`）

## NFR 约束

<!-- 来源: decisions 表 category=nfr，PrepPRD 显式值优先；本次 decisions 源不可达（连接失败，回退空数组），PrepPRD 亦未指定 NFR -->
- 超时/延迟: 待定（PrepPRD 未指定）
- 频控: 待定（PrepPRD 未指定）
- 版本要求: 空
- 可观测: 空

## E2E 验收

> Planner 初稿此区块可留空（只写占位 + 期望验收点的自然语言描述）。最终可执行的 E2E 脚本由 proposer 在 GAN 阶段产出（按 target_environment 选 bash 模板，写进 contract-draft.md 的 `## E2E 验收` 区块）。

```bash
# 占位：proposer 将按 target_environment=local_api 填入真实脚本（curl localhost:5221 + jq 断言）
# 期望验收点（自然语言）：
# 1. curl localhost:5221/api/brain/status 的响应 JSON 含 uptime_seconds 字段
# 2. uptime_seconds 为非负数值（进程启动至今秒数）
# 3. 间隔 2 秒再次请求，uptime_seconds 值增大（证明是活的计时，不是硬编码）
# 4. status 原有字段全部保留，无回归
```

## journey_type: autonomous
## journey_type_reason: 改动仅涉及 packages/brain/ 纯后端 API 字段，无 UI/engine/远端 agent 协议。
## target_environment: local_api
## target_environment_reason: 仅 packages/brain/ 纯 API 改动，本地 evaluator 用 curl localhost:5221 即可验收。
## journey_id: 待定（Brain API 不可达，task.payload.journey_id 无法读取；PrepPRD 无 Journey 锚定信息）
## step_id: 待定（PrepPRD 未提供 Golden Path Step 锚定结果）
