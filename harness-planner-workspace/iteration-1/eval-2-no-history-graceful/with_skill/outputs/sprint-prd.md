# Sprint PRD — Brain /api/brain/status 新增 uptime_seconds 字段

## OKR 对齐

- **对应 KR**：未能获取（/api/brain/context 当前不可达，返回空）
- **当前进度**：未知
- **本次推进预期**：Brain 可观测性小步增强（Proposer 阶段可补锚定）

## 背景

用户希望在 status 接口直接看到 Brain 已运行多久（秒）。当前 `/api/brain/status` 响应中没有运行时长信息，排查"Brain 是否刚重启过"需要翻日志。本 sprint 只加一个字段：`uptime_seconds`。

## Golden Path（核心场景）

用户/系统从 [请求 status 接口] → 经过 [Brain 返回状态 JSON] → 到达 [看到 uptime_seconds 字段]

具体：
1. [触发条件] 客户端请求 `GET /api/brain/status`（Brain 进程已启动运行中）
2. [系统处理] Brain 在原有 status 响应 JSON 中附带 `uptime_seconds` 字段，值 = 进程启动至今的秒数
3. [可观测结果] 响应 JSON 含 `uptime_seconds`，为非负数值；间隔数秒再次请求，该值单调增大（增量 ≈ 间隔秒数）

<!-- Response Schema由Proposer在Step 1.1读api_registry后推导，Planner不负责定义技术规范。 -->

## 边界情况

- Brain 刚启动即被请求：`uptime_seconds` 应为很小的非负值（如 0 或 1），不得为负数/缺失
- 原 status 响应的既有字段不得因新增字段而丢失或改名
- 并发多次请求：各自返回请求时刻的运行秒数，不要求完全相等，但均须非负且不回退

## 范围限定

**在范围内**：`GET /api/brain/status` 响应新增 `uptime_seconds` 一个字段（进程启动至今秒数）
**不在范围内**：其他端点改动、历史 uptime 持久化/统计、Dashboard 展示、重启告警、格式化人类可读时长

## 假设

- [ASSUMPTION: `/api/brain/status` 端点已存在，本 sprint 只在其响应中增字段，不新建端点]
- [ASSUMPTION: uptime_seconds 为非负数值（秒），整数或带小数均可接受，以整数秒为默认预期]
- [ASSUMPTION: "启动"指 Brain 进程本次启动时刻；容器/宿主机重启即重新计数，无需跨重启累计]

## 预期受影响文件

- `packages/brain/src/`（status 路由/响应组装处）: 在 status 响应中加入 uptime_seconds 字段（thin_prd 位置词 "Brain" → packages/brain/src/）

## NFR 约束

<!-- 来源: decisions 表 category=nfr，PrepPRD 显式值优先；本次 step/journey_feature 双源均为空数组 -->
- 超时/延迟: 待定（PrepPRD 未指定，decisions 无沉淀）
- 频控: 待定（PrepPRD 未指定，decisions 无沉淀）
- 版本要求: 空
- 可观测: 空

## Invariant 约束（铁律，proposer/evaluator 不得违反）

<!-- 来源: decisions category=invariant，step + journey_feature + area 三源合并去重；本次三源均为空 -->
（本 line 暂无历史）

## 累积 FR（本 line 已验收行为，本 sprint 不得回退/重复）

<!-- 来源: 本 line 已完成 ability 的 golden_path；本任务 payload 无 journey_id（非路径 C 点火），优雅降级为无累积 FR -->
（本 line 暂无历史）

## E2E 验收

> Planner 初稿此区块**可留空**（只写占位 + 期望验收点的自然语言描述）。**最终可执行的 E2E 脚本由 proposer 在 GAN 阶段产出**（按 target_environment 选 bash/.ps1 模板，写进 contract-draft.md 的 `## E2E 验收` 区块）。Planner 在此先框定"端到端要验到什么"，供 proposer 翻译成命令。

```bash
# 占位：proposer 将按 target_environment=local_api 填入真实脚本（curl localhost:5221 + jq 断言）
# 期望验收点（自然语言）：
# 1. GET /api/brain/status 响应 JSON 含 uptime_seconds 字段，值为非负数值
# 2. 间隔 N 秒二次请求，uptime_seconds 增大约 N 秒（单调不回退）
# 3. status 响应原有字段全部保留
```

## journey_type: autonomous
## journey_type_reason: 改动仅涉及 packages/brain/（纯后端 API 字段），无 UI/agent 协议/engine 路径线索
## target_environment: local_api
## target_environment_reason: 仅 packages/brain/ 纯 API 改动，本地 evaluator 用 curl localhost:5221 即可验证
## journey_id: 无（task.payload 无 journey_id——非路径 C 点火；PrepPRD 亦无 Journey 锚定，优雅降级）
## step_id: 无（无 Journey/Golden Path 锚定来源，优雅降级）
