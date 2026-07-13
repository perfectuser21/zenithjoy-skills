# Sprint PRD — 抖音定时发布 thin 骨架

## OKR 对齐

- **对应 KR**：KR-（mock 测试，未接 Brain context，待 Proposer 阶段回填）
- **当前进度**：0%
- **本次推进预期**：thin 骨架跑通定时发布最小闭环

## 背景

用户需要在 Dashboard 设置发布时间，让系统在指定时间自动把视频发布到抖音，并把帖子链接写回 Brain DB。本 sprint 只做 thin 骨架：单视频、单账号、一次定时发布闭环。

## Golden Path（核心场景）

用户/系统从 [Dashboard 设置发布时间] → 经过 [到点触发 → 自动发布到抖音] → 到达 [帖子链接写回 Brain DB]

具体：
1. 用户在 Dashboard 为一个已就绪的视频设置发布时间并保存 → 界面显示"已排期 + 目标时间"
2. 系统在指定时间触发发布流程，调用抖音发布链路上传该视频
3. 发布成功后，系统将抖音帖子链接写回 Brain DB 对应记录，Dashboard 状态变为"已发布 + 链接可点"

<!-- Response Schema由Proposer在Step 1.1读api_registry后推导，Planner不负责定义技术规范。 -->

## 边界情况

- 到点时视频文件缺失/不可读 → 标记失败，不重复重试超频控
- 发布调用失败（登录态失效/网络）→ 记录失败原因，状态置 failed，不静默吞掉
- 同一视频被重复排期 → 后一次覆盖前一次，只发一次

## 范围限定

**在范围内**：单视频单账号的定时发布闭环（设置时间 → 到点发布 → 链接回写 DB）
**不在范围内**：批量排期、多账号轮换、失败自动重试策略、发布内容生成

## 假设

- [ASSUMPTION: 抖音登录态已就绪（cookie/CDP 环境可用），本 sprint 不做登录流程]
- [ASSUMPTION: "写回 Brain DB"指更新已存在的发布任务记录，不新建表]

## NFR 约束

<!-- 来源: decisions 表 category=nfr（mock: nfr-001/nfr-002），PrepPRD 显式值优先 -->
- 频控: 抖音 API 每 60 秒最多调用 3 次（来源: decisions nfr-001「抖音 API 频控」，PrepPRD 未显式指定）
- 超时/延迟: 实际发布时间相对用户设定时间允许最多 5 秒延迟（来源: decisions nfr-002「发布延迟容忍」；PrepPRD 提出"在指定时间自动发布"的准点要求但未给具体容忍值，故取 decisions 值）
- 规模: 待定（PrepPRD 未指定，decisions 无值 → Proposer 阶段对用户提问）
- 版本要求: 无
- 可观测: 发布成功/失败结果必须落 Brain DB（帖子链接或失败原因），Dashboard 可见

## Invariant 约束（铁律，proposer/evaluator 不得违反）

<!-- 来源: decisions category=invariant，step + journey_feature + area 三源合并去重 -->
- （本 line 暂无历史）

## 累积 FR（本 line 已验收行为，本 sprint 不得回退/重复）

<!-- 来源: 本 line 已完成 ability 的 golden_path，按 ability 分组、order_no 排序 -->
- （本 line 暂无历史）

## E2E 验收

```bash
# 占位：proposer 将按 target_environment 填入真实脚本（windows_cloud → .ps1 / GitHub Actions windows-latest）
# 期望验收点（自然语言）：
# 1. Dashboard 上设置某视频发布时间后，界面显示"已排期"
# 2. 到达设定时间后 ≤5 秒内发布动作被触发（NFR: 延迟容忍 5 秒）
# 3. 抖音侧帖子真实出现，帖子链接被写回 Brain DB 对应记录且字段正确
# 4. 发布链路调用频率不超过每 60 秒 3 次（NFR: 频控）
```

## journey_type: user_facing
## journey_type_reason: 用户在 Dashboard 设置发布时间并观察发布状态，核心交互发生在前端界面
## target_environment: windows_cloud
## target_environment_reason: 抖音发布属 ZenithJoy 产品线，ZenithJoy UI/Dashboard 的 E2E 一律走 GitHub Actions windows-latest 干净 runner（死规则，不按路径判断）
## journey_id: <mock 测试未注入 task.payload.journey_id，待 /dev 路径 C 点火写入>
## step_id: <mock 测试未提供 PrepPRD Golden Path 锚定结果，待锚定>
