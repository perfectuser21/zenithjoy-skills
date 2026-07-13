# Sprint PRD — 抖音定时发布 thin 骨架

## OKR 对齐

- **对应 KR**：KR-L01（智能发布 — 抖音自动发布链路）
- **当前进度**：0%（本 ability 首个 Run）
- **本次推进预期**：+20%（thin 骨架跑通定时发布最小闭环）

## 背景

用户希望在 Dashboard 设置发布时间后，系统在指定时间自动把视频发布到抖音，并将帖子链接写回 Brain DB。本 Sprint 只做 thin 骨架：设置时间 → 定时触发 → 发布 → 链接回写，不做批量排期、失败重试策略等厚功能。

## Golden Path（核心场景）

用户/系统从 [Dashboard 设置发布时间] → 经过 [定时触发 → 自动发布视频到抖音] → 到达 [帖子链接写回 Brain DB]

具体：
1. 用户在 Dashboard 为一个待发视频设置**发布时间**并保存，页面显示"已排期"状态
2. 系统在指定时间到达时自动触发发布流程，把该视频**发布到抖音**（允许最多 5 秒延迟，见 NFR）
3. 发布成功后，系统把抖音**帖子链接写回 Brain DB**，Dashboard 状态更新为"已发布"并展示帖子链接

<!-- Response Schema由Proposer在Step 1.1读api_registry后推导，Planner不负责定义技术规范。 -->

## 边界情况

- 发布时间已过期（用户设了过去的时间）→ 系统拒绝保存或立即标记异常，不静默吞掉
- 定时触发时抖音发布失败 → 任务标记 failed，不写入假的帖子链接
- 同一分钟内多个排期任务 → 受抖音 API 频控约束（见 NFR），排队串行调用

## 范围限定

**在范围内**：单条视频的定时发布设置、到点自动发布抖音、帖子链接写回 Brain DB、Dashboard 状态可见
**不在范围内**：批量排期、失败自动重试、多平台分发、发布内容编辑/审核流

## 假设

- [ASSUMPTION: 抖音账号已登录且 cookie 有效，登录/保活由既有 Feature 承担，不在本 Sprint 范围]
- [ASSUMPTION: 待发视频文件已存在于系统中，本 Sprint 不做视频上传/剪辑]

## NFR 约束

<!-- 来源: decisions 表 category=nfr，PrepPRD 显式值优先 -->
- 超时/延迟: 发布触发允许最多 5 秒延迟（来源: decisions nfr-002「发布延迟容忍」；PrepPRD 未显式指定数值，采用 decisions 值）
- 频控: 抖音 API 每 60 秒最多调用 3 次（来源: decisions nfr-001「抖音 API 频控」；PrepPRD 未显式指定，采用 decisions 值）
- 版本要求: 空（PrepPRD 与 decisions 均未指定）
- 可观测: 发布结果（成功帖子链接 / 失败原因）必须写回 Brain DB，Dashboard 可见状态变化

## 预期受影响文件

- `apps/dashboard/`: 发布时间设置入口与"已排期/已发布"状态展示
- `packages/brain/`: 定时触发调度 + 帖子链接写回 Brain DB 的任务记录

## E2E 验收

> Planner 初稿此区块**可留空**（只写占位 + 期望验收点的自然语言描述）。**最终可执行的 E2E 脚本由 proposer 在 GAN 阶段产出**（按 target_environment 选 bash/.ps1 模板，写进 contract-draft.md 的 `## E2E 验收` 区块）。Planner 在此先框定"端到端要验到什么"，供 proposer 翻译成命令。

```bash
# 占位：proposer 将按 target_environment 填入真实脚本（mac_web→Playwright + 查 Brain DB）
# 期望验收点（自然语言）：
# 1. Dashboard 上为一条视频设置发布时间并保存，页面出现"已排期"状态
# 2. 到达指定时间后（容忍 ≤5 秒延迟），系统自动发布视频到抖音，帖子真实出现（平台确认/截图）
# 3. 查 Brain DB 确认该任务记录存在且帖子链接字段非空、状态=已发布，Dashboard 展示该链接
```

## journey_type: user_facing
## journey_type_reason: 入口是 Dashboard 前端设置发布时间，用户可见状态变化，命中 if-elif 链第一条（涉及 apps/dashboard/）
## target_environment: mac_web
## target_environment_reason: 涉及 Dashboard 前端页面交互（本机 Playwright，localhost:5174），命中优先级链"涉及 apps/dashboard/ 或前端页面"
## journey_id: Line 01（智能发布；task.payload.journey_id 未提供，取 PrepPRD 锚定结果）
## step_id: L01-S1（抖音定时发布 ability 的 Golden Path 首步，来源 = PrepPRD 锚定）
