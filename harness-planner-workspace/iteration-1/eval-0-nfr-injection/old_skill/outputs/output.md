# Sprint PRD — 抖音定时发布（thin 骨架）

## OKR 对齐

- **对应 KR**：KR-智能发布（Line 01 — 智能发布）
- **当前进度**：待查
- **本次推进预期**：完成定时发布骨架，打通"设定时间 → 到时自动发布 → 链接写回"核心链路

## 背景

用户需要在 Dashboard 预排发布计划，而非手动实时触发。本 sprint 实现最小可验证骨架：用户在 Dashboard 填写发布时间，Brain 到点调用抖音发布，帖子链接写回 DB。

## Golden Path（核心场景）

用户从 [Dashboard 定时发布表单] → 经过 [设置发布时间并提交 → Brain tick 到点触发发布 → 抖音发布成功] → 到达 [帖子链接可在 Dashboard 查看]

具体：

1. 用户在 Dashboard「定时发布」页面选择视频、填写计划发布时间，点击「提交」
2. Brain DB 写入一条 scheduled_publish 记录（video_path、platform=douyin、scheduled_at、status=pending）
3. Brain tick 检测到 scheduled_at <= now 且 status=pending，调用抖音发布接口
4. 发布成功后，Brain 将帖子链接写回该记录（post_url、status=done）
5. Dashboard 刷新后，用户在列表中看到帖子链接（可点击跳转抖音）

<!-- Response Schema 由 Proposer 在 Step 1.1 读 api_registry 后推导，Planner 不负责定义技术规范。 -->

## 边界情况

- scheduled_at 已过期（过去时间提交）→ 拒绝写入，返回错误提示
- 发布失败（抖音接口报错）→ 记录 status=failed，error_msg 写回 DB，Dashboard 展示失败状态
- 重复提交同一视频 → 暂不去重（thin 骨架范围外，列入不在范围内）

## 范围限定

**在范围内**：
- Dashboard 定时发布表单（选视频 + 选时间 + 提交）
- Brain DB 新增 scheduled_publish 表（id / video_path / platform / scheduled_at / status / post_url / error_msg）
- Brain tick 到点触发发布逻辑（thin 骨架：调用现有抖音发布 skill 或 stub）
- 帖子链接写回 DB + Dashboard 列表展示

**不在范围内**：
- 发布重试机制
- 多平台同步发布
- 视频上传（假设视频已在服务器本地路径可访问）
- 通知/提醒（飞书、邮件等）
- 定时任务管理 UI（取消、编辑）

## 假设

- [ASSUMPTION: 抖音发布接口（或 stub）已存在，thin 骨架允许用 stub 模拟返回帖子链接]
- [ASSUMPTION: Dashboard 已有视频列表数据源，用户可从中选取视频路径]
- [ASSUMPTION: Brain tick 间隔足够精确（≤ 1 分钟），可用于触发定时发布]
- [ASSUMPTION: scheduled_publish 表由本 sprint 新建 migration 创建]

## 预期受影响文件

- `apps/dashboard/src/pages/ScheduledPublish.tsx`（或同等路由页）：新建定时发布表单页
- `apps/dashboard/src/components/ScheduledPublishList.tsx`：帖子链接列表展示组件
- `packages/brain/src/routes/scheduled-publish.js`：POST /api/brain/scheduled-publish 写入记录；GET 查询列表
- `packages/brain/src/tick.js`（或新建 scheduled-publish-tick.js）：tick 中检测 pending 记录并触发发布
- `packages/brain/migrations/xxxx_create_scheduled_publish.sql`：新建表 migration

## E2E 验收

> Planner 初稿此区块可留空（只写占位 + 期望验收点的自然语言描述）。最终可执行的 E2E 脚本由 proposer 在 GAN 阶段产出（按 target_environment 选 bash/.ps1 模板，写进 contract-draft.md 的 `## E2E 验收` 区块）。Planner 在此先框定"端到端要验到什么"，供 proposer 翻译成命令。

```bash
# 占位：proposer 将按 target_environment=mac_web 填入真实脚本（Playwright）
# 期望验收点（自然语言）：
# 1. 在 Dashboard 定时发布页面填写视频路径 + 未来 1 分钟的发布时间，提交后 DB 出现 status=pending 记录
# 2. 等待 Brain tick 触发（或 mock tick 直接调用），DB 记录更新为 status=done，post_url 非空
# 3. Dashboard 列表刷新后可见帖子链接（非空字符串，可点击）
```

## journey_type: user_facing
## journey_type_reason: 任务涉及 apps/dashboard/（用户在 Dashboard 设置发布时间），属于前端用户可见交互，命中 user_facing 第一条规则
## target_environment: mac_web
## target_environment_reason: Cecelia Dashboard 为内网 Web 产品，E2E 走本机 Playwright（localhost:5174），命中 mac_web 规则
## journey_id: <来源 = task.payload.journey_id，对应 Line 01 — 智能发布 Journey UUID>
## step_id: <来源 = PrepPRD Golden Path 锚定结果，对应「定时发布」step>
