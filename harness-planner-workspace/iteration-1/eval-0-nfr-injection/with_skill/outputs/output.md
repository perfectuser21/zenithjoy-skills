# Sprint PRD — 抖音定时发布（thin 骨架）

## OKR 对齐

- **对应 KR**：KR-L01（智能发布 · 多平台自动发布能力）
- **当前进度**：30%
- **本次推进预期**：+15%

## 背景

用户需要在 Dashboard 提前配置抖音视频的发布时间，由系统在指定时刻自动触发发布，并将生成的帖子链接回写到 Brain DB，实现无人值守的定时发布闭环。

## NFR 约束

<!-- 来源: decisions 表 category=nfr，PrepPRD 显式值优先 -->
- 频控: 每60秒最多调用抖音 API 3次（来源: decisions nfr-001）
- 超时/延迟: 允许最多5秒发布延迟（来源: decisions nfr-002）
- 版本要求: 无特殊版本约束
- 可观测: 发布成功/失败结果必须写回 Brain DB（帖子链接或失败原因）

## Golden Path（核心场景）

用户从 [Dashboard 定时发布配置界面] → 经过 [设置时间保存 → 到时自动发布 → 链接回写] → 到达 [Brain DB 中可查到帖子链接]

具体：
1. 用户在 Dashboard「抖音发布」页面选择视频，填写发布时间，点击「定时发布」保存
2. 系统到达指定时间时，调用抖音发布 API 提交视频（遵守频控：每60秒≤3次调用，容忍≤5秒延迟）
3. 发布成功后，系统将返回的帖子链接写入 Brain DB 对应记录；用户在 Dashboard 可看到状态从「待发布」变为「已发布」并附帖子链接

<!-- Response Schema由Proposer在Step 1.1读api_registry后推导，Planner不负责定义技术规范。 -->

## 边界情况

- 到达发布时间但抖音 API 频控已触发（本分钟已达3次）→ 推迟至下一可用时间窗口重试
- 发布 API 超时（>5秒）→ 标记为发布失败，写 Brain DB failure_reason，不重复发布
- 视频文件已删除或不可访问 → 发布任务标记 terminal 失败
- 用户取消定时任务（发布时间前）→ 从调度队列移除，DB 状态改为「已取消」
- 重复触发（系统重启后）→ 检查 DB 状态，已发布的不再重复调用 API

## 范围限定

**在范围内**：
- Dashboard UI 设置发布时间（选择日期时间 + 保存）
- 后端调度器按时触发抖音发布 API
- 发布结果（帖子链接或失败原因）写回 Brain DB
- Dashboard 展示发布状态（待发布/已发布/失败）

**不在范围内**：
- 视频内容创建/编辑
- 抖音账号登录/Cookie 管理（依赖已有登录态）
- 批量定时发布（本 sprint 只做单条）
- 发布失败自动重试（标记失败即止，重试是下一个 sprint）

## 假设

- [ASSUMPTION: 抖音登录态（Cookie）由现有发布系统维护，本 sprint 复用，不重新实现]
- [ASSUMPTION: Brain DB 已有 tasks/publish_records 表可存储帖子链接字段，无需新建表]
- [ASSUMPTION: Dashboard 后端已有定时任务调度能力（如 node-cron 或 Brain tick），只需接入]

## 预期受影响文件

- `apps/dashboard/src/pages/douyin-publish.tsx`（或等效页面）: 新增时间选择控件 + 定时发布按钮
- `apps/dashboard/src/api/publish.ts`: 新增 schedulePublish API 调用
- `packages/brain/src/routes/publish.js`（或调度模块）: 新增定时任务注册 + 抖音 API 触发逻辑
- `packages/brain/src/tick.js`（或调度器）: 接入定时发布检查逻辑

## E2E 验收

> Planner 初稿此区块留占位。最终可执行的 E2E 脚本由 proposer 在 GAN 阶段产出（按 target_environment=mac_web 选 Playwright 模板，写进 contract-draft.md 的 `## E2E 验收` 区块）。

```bash
# 占位：proposer 将按 target_environment=mac_web 填入真实 Playwright 脚本
# 期望验收点（自然语言）：
# 1. 在 Dashboard localhost:5174 打开抖音发布页，设置1分钟后的发布时间，保存成功
# 2. 等待时间到达后，系统自动触发发布（不需用户操作）
# 3. Brain DB 中对应记录的帖子链接字段非空（curl localhost:5221 + psql 查询确认）
# 4. Dashboard 页面状态显示「已发布」并可点击帖子链接
```

## journey_type: user_facing
## journey_type_reason: 功能入口在 apps/dashboard/ UI（用户在页面设置时间），命中第一条优先级规则
## target_environment: mac_web
## target_environment_reason: Cecelia Dashboard 内网产品，走本机 Playwright，localhost:5174
## journey_id: <来源 = task.payload.journey_id，eval 模式未注入，待 Brain 点火时填入>
## step_id: <来源 = PrepPRD Golden Path 锚定结果，eval 模式待 Proposer 阶段确认>
