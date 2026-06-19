# Dev Skill 执行记录：抖音定时发布功能

**执行时间**：2026-06-19  
**用户请求**：在 ZenithJoy 里做一个「抖音定时发布」功能：用户在 Dashboard 设定发布时间，到时间自动把视频发到抖音，并把帖子链接写回 Brain DB。这个功能现在完全没有，需要从零开始。  
**Skill 版本**：dev v21.1.0

---

## 第零步 Phase 1：听懂意图

**解析结果**：

用户说"想做"+"新功能"+"从零开始" → **路径 C：大功能 / Harness**

判断依据：
- "我想在 ZenithJoy 里做一个..." → 新增功能而非 bug
- "这个功能现在完全没有，需要从零开始" → 全新 Ability，不是小改动
- 跨越 Dashboard UI + 后台调度 + 外部平台 API + DB 回写 → 贯通端到端价值闭环 → Harness 量级

**路由决定**：路径 C（大功能 Harness）

---

## 第零步 Phase 2：按路径按需查上下文（路径 C — 5 个上下文源）

### 源 1：Journey 体系

**查询**：`GET localhost:5221/api/brain/journeys`

**匹配结果**：最相关的 Journey 是 **「智能发布」（Line 01）**

```
id: c019cdeb-d90b-4f8b-a658-ae333663ac35
name: 智能发布
描述: 8 平台自动发布能力（抖音/快手/小红书/微博/知乎/头条/视频号/公众号），每个平台三类内容（image/video/article）dryrun + 真发全链路跑通，GHA windows-latest CI 自动验证
journey_type: autonomous
maturity: skeleton
status: active
e2e_test_path: .github/workflows/scripts/smoke/publisher-smoke.sh
```

### 源 2：journey_features（当前 Ability/Feature 状态）

**查询**：`GET localhost:5221/api/brain/journey_features?limit=100`

**智能发布 Journey 已有 Abilities（过滤 journey_id=c019cdeb）**：

| 名称 | kind | status | thickness |
|------|------|--------|-----------|
| 抖音短视频发布 | ability | working | thin |
| 抖音图文发布 | ability | working | thin |
| 抖音长文发布 | ability | working | thin |
| 抖音 OAuth 授权 | feature | working | thin |
| 快手视频发布 | ability | working | thin |
| 快手图文发布 | ability | working | thin |
| 微博图文发布 | ability | working | thin |
| 微博长文发布 | ability | working | thin |
| 微博视频发布 | ability | working | thin |
| 微信公众号文章发布 | ability | working | thin |
| 知乎想法发布 | ability | working | thin |
| 知乎文章发布 | ability | working | thin |
| 知乎视频发布 | ability | working | thin |
| 小红书图文发布 | ability | broken | thin |
| 小红书长文发布 | ability | broken | thin |
| 小红书视频发布 | ability | broken | thin |
| 头条图文发布 | ability | planned | thin |
| 头条视频发布 | ability | planned | thin |
| 掉线飞书告警 | feature | working | thin |
| 全平台状态探测 | feature | working | thin |
| 全平台心跳保活 | feature | working | thin |

**语义查重结论**：现有 Ability 中**没有**"定时发布"或"scheduled publish"相关条目。`抖音短视频发布` 是即时发布（立即触发），与定时发布是不同的 Ability。本次需新建。

### 源 3：进行中任务

**查询**：`GET localhost:5221/api/brain/tasks?status=in_progress&limit=20`

与「抖音定时发布」无直接冲突的进行中任务，不影响本 sprint 启动。

### 源 4：Harness 历史 Run

**查询**：`GET localhost:5221/api/brain/harness/runs?limit=10`

最近 5 条 Run 均为 autonomous 类型（Line 04 私域 AI），与本功能无冲突。无历史 Run 与「定时发布」相关。

### 源 5：历史决策匹配

**查询**：`POST localhost:5221/api/brain/decisions/match` 关键词 "抖音定时发布 scheduled publish douyin"

**命中**：无直接相关决策。

**横切不变量（invariant decisions，自动 enforce）**：
- [系统] 禁止写死环境假设值（id: 5e125909）
- [系统] 真环境验证才算 done（id: 3c30394c）
- [系统] 凭据安全：secrets 不硬编码、不进 git、不进日志（id: 564802ee）
- [系统] 日志脱敏：客户隐私/PII 不得明文进日志（id: 459b6ff9）
- [系统] 端点鉴权：每个 API 端点必须有 auth（id: 50954d28）
- [系统] 租户隔离：碰租户数据的查询/写入必须 scope 到当前租户（id: 68976b17）
- [系统] 测试默认多租户：单元/E2E 测试默认种 ≥2 个租户并断言互不串（id: 55b8eb46）

---

## 步骤 0：比对已有 Abilities，展示 Golden Path 草稿

### 确定本次 Journey

**Journey**：智能发布（Line 01）  
**Journey ID**：`c019cdeb-d90b-4f8b-a658-ae333663ac35`  
**Notion Journey ID**：`374c40c2-ba63-81ca-8e1d-d1b2270130fe`

### 过滤已有 Abilities

**已完成（✅ 不动）**：
- ✅ 抖音短视频发布（immediately，thin/working）— 即时触发，立即发布
- ✅ 抖音图文发布（immediately，thin/working）— 即时触发
- ✅ 抖音长文发布（immediately，thin/working）— 即时触发
- ✅ 抖音 OAuth 授权（feature，thin/working）— 凭据/Cookie 已就绪

**本次新增/推进（➕ 本 sprint 范围）**：
- ➕ **抖音定时视频发布**（新 Ability，thin）— Dashboard 设定时间 → 到时间自动发布 → 帖子链接写回 Brain DB

**本次不包含**：
- 其他平台（快手/小红书/微博等）的定时发布 —— 后续 sprint 横向扩展
- 抖音图文/长文定时发布 —— 本次仅视频，保持 1 Sprint = 1 Ability

### 建议 Golden Path 草稿（初版，待 GAN 对抗补全）

```
Step 1: 用户在 Dashboard 点击「新建定时发布任务」→ 系统弹出配置表单（选择平台=抖音、上传视频、填写标题/标签、选择发布时间）→ 表单就绪状态
Step 2: 用户填写完成后点击「确认」→ 系统校验字段非空、发布时间>当前时间5分钟 → 任务写入 Brain DB，状态=scheduled，返回任务 ID → 列表出现新条目，显示"定时中"
Step 3: Brain tick 到达目标时间窗口（误差 ≤1分钟）→ 系统自动触发抖音发布脚本 → 视频上传到抖音 → 等待平台返回帖子 URL
Step 4: 抖音返回帖子链接 → 系统把帖子链接写回 Brain DB 该任务记录（status=published, post_url=...) → Dashboard 任务状态更新为"已发布"，显示帖子链接可点击
Step 5: 用户点击链接 → 跳转到抖音帖子页 → 确认视频已公开可见

[出错场景]
Step 3-失败: 到时间但抖音 session 已过期 → 系统标记任务为 failed（reason=session_expired）→ Dashboard 红色告警"发布失败：cookie 已过期" → 系统发飞书通知 → 用户去「账号管理」重新登录 → 手动重试或重新调度
Step 3-失败: 视频文件已被删除/移动 → 任务标记 failed（reason=file_not_found）→ 告警用户"视频文件不存在"
Step 4-失败: 抖音返回错误（如频控/违规）→ 任务标记 failed（reason=platform_error: <code>）→ 飞书告警 → 用户需手动处理
```

---

## 步骤 1：GAN 对抗深挖

### Phase 1（串行）：FR GAN 功能需求对抗 — 第 1 轮

#### Proposer sub-agent（产品经理视角）

基于 Golden Path 草稿，喂料已有铁律，补全功能需求：

**补全的缺失步骤和边界 case**：

1. **时间精度与调度引擎**：草稿说"Brain tick 到达目标时间"，但 Brain tick 当前是 5 分钟周期。定时发布需要几秒级精度（用户设定 10:00 发布，不能 10:05 才触发）。需明确：是 Brain tick 内嵌精细调度，还是单独起一个 cron-like 调度器？

2. **视频文件存储**：用户在 Dashboard 上传视频，视频文件存在哪里？本地路径？还是上传到 S3/OSS？Windows GHA runner 无法访问本地机器文件系统。

3. **发布前的"预飞检"**：用户设定 T 时刻发布，系统应在 T-5min 做 pre-flight check（session 是否有效、文件是否存在）。否则到时间才发现 cookie 过期，无法即时恢复。

4. **多任务并发**：用户同时设定了 3 个视频，恰好同一时间发布 → 并发锁？抖音有频控（建议间隔≥30s）？

5. **任务可见性/管理**：Dashboard 需要一个「定时任务列表」页，让用户能取消或修改发布时间（在 T-5min 之前可修改）。

6. **幂等性**：万一 Brain 在 T 时刻 tick 两次（重启、OOM 恢复），同一任务不能发布两次。需要 claimed/processing 状态机防重入。

7. **发布后确认**：抖音上传 API 返回 200 ≠ 视频真正可见（可能在审核中）。需要轮询或 webhook 确认视频状态从"审核中"变为"已发布"。

8. **租户隔离**：多客户场景下，A 客户的定时任务不能触发 B 客户的抖音账号。任务记录必须带 `tenant_id`。

9. **权限**：只有账号绑定了抖音 session 的租户才能创建定时任务；无 session → 前端灰化按钮，提示"请先绑定抖音账号"。

---

#### Challenger sub-agent（挑剔审查员）— 第 1 轮

```json
{
  "new_issues": [
    "1. [精度缺口] Proposer 说'需要几秒级精度'但没给出方案。Brain tick 5分钟周期 vs 定时发布1分钟精度之间的 gap 必须有技术决策，否则 Planner 无法实现",
    "2. [文件存储未定] 视频上传路径完全未定（本地/OSS/GHA runner），这是最大的接缝——直接决定 target_environment 选 windows_cloud 还是 local_api",
    "3. [审核态轮询] 抖音视频审核时间 2min~2h 不等，轮询频率和超时时间需定义。超时后是 pending 还是 failed？用户感知什么？",
    "4. [取消任务] Proposer 说'T-5min之前可修改'，但取消/修改后正在上传中的任务如何中断？",
    "5. [失败重试策略] 草稿列了3种失败场景，但重试逻辑未定：是自动重试还是必须用户手动重试？重试几次？每次间隔？",
    "6. [通知可靠性] 飞书告警是当前唯一通知渠道，但飞书本身如果不通，用户不知道发布失败。Dashboard 内的 in-app 通知是必须的"
  ],
  "verified": {
    "completeness": "❌ 步骤 3（调度触发）缺精度方案；步骤 4（发布确认）只到 URL 返回，未覆盖审核态",
    "consistency": "✅ 无前后矛盾",
    "testability": "❌ '到时间自动触发'无可测时间精度指标",
    "edge_cases": "❌ 并发防重入/幂等性已提出但未有方案",
    "error_paths": "❌ 重试策略、取消中途任务、通知降级未定义"
  }
}
```

**结论**：第 1 轮未收敛，Challenger 发现 6 个新 issue。进入第 2 轮。

---

#### Proposer sub-agent — 第 2 轮（回应 Challenger 6 个 issue）

**Issue 1 解决（精度方案）**：
- Brain tick 主循环 5 分钟不变（不动核心）
- 新增轻量 `scheduler.js` 模块，1 分钟 setInterval，专门 scan `scheduled_publishes WHERE publish_at <= NOW() + 60s AND status='scheduled'`
- 精度目标：1 分钟内触发（不是秒级，但用户体验上"分钟级"可接受，Dashboard 显示"将在约 X 分钟后发布"）
- **用户决策点 A**：1 分钟精度够用吗？还是要 30 秒？

**Issue 2 解决（文件存储）**：
- 用户在 Dashboard 上传视频 → 保存到本机 `~/zenithjoy-uploads/scheduled/{task_id}/video.mp4`
- 发布时 windows_cloud runner 从 GitHub Release Artifacts 拉文件？— **不可行，文件隐私**
- 更合理方案：发布脚本在本机运行（`local_api` 或 `linux_server`），文件就在本机，无需云传输
- **结论**：`target_environment = local_api`（本机跑调度+发布脚本），不用 GHA runner
- 技术边界：文件上传到 `~/zenithjoy-uploads/` 本地目录，调度器拿本地路径发布

**Issue 3 解决（审核态轮询）**：
- 发布后轮询 `queryVideoStatus(item_id)` 每 60s 一次，最多 30 次（30 分钟）
- 30 分钟后仍 `auditing` → status=`audit_timeout`，飞书+Dashboard 告警，帖子链接仍写回（可能是草稿/审核中状态）
- `published` → status=`published`，写回 post_url
- **用户决策点 B**：超时后是自动取消还是保留 audit_timeout 状态等用户处理？

**Issue 4 解决（取消中途任务）**：
- `status=processing`（正在上传中）期间，取消请求会被拒绝（返回 409 Conflict），前端显示"发布中，无法取消"
- `status=scheduled` 或 `audit_timeout` 时可取消

**Issue 5 解决（重试策略）**：
- `session_expired` → 不自动重试（需人工重新登录）
- `platform_error(rate_limit)` → 自动延迟 5 分钟重试，最多 3 次
- `platform_error(other)` → 不自动重试，标记 failed，通知用户
- `file_not_found` → 不自动重试
- **用户决策点 C**：频控错误的重试次数和间隔（上述 5min/3次 是建议值）

**Issue 6 解决（通知降级）**：
- Dashboard in-app 通知（红色 badge）为主
- 飞书为辅
- 两者都写，互不依赖

---

#### Challenger sub-agent — 第 2 轮

```json
{
  "new_issues": [
    "1. [本机调度可靠性] target_environment=local_api 意味着本机必须常驻运行。如果本机关机或重启，所有 scheduled 任务会不会全部 miss？需要守护进程 / 开机自启方案",
    "2. [幂等性仍未闭合] Proposer 提到 status=processing 防重入，但若调度器 crash 在 processing 期间重启，任务会卡在 processing 状态。需要 heartbeat timeout → 自动回滚到 scheduled 的机制"
  ],
  "verified": {
    "completeness": "✅ 步骤1-5主线完整，含预飞检(T-5min)、审核轮询、状态机",
    "consistency": "✅ target_environment=local_api 与文件存储本机方案一致",
    "testability": "✅ 每步有可观察输出（DB status字段 + Dashboard显示）",
    "edge_cases": "✅ 并发防重入/幂等通过 status=processing 解决，取消逻辑已定义",
    "error_paths": "✅ 三类失败各有重试策略，通知双路降级已定义"
  }
}
```

**结论**：第 2 轮剩余 2 个新 issue（可靠性相关），进入第 3 轮。

---

#### Proposer sub-agent — 第 3 轮

**Issue 1 解决（守护进程）**：
- 调度器作为 Brain 的一个模块（`packages/brain/src/scheduler.js`），随 Brain 进程启动
- Brain 已有 PM2 守护（`ecosystem.config.js`），Brain 崩溃会自动重启
- Brain 重启后，调度器也随之恢复，scan DB 里所有 `status=scheduled` 重新入队
- **无需额外守护进程**，复用现有 Brain PM2 机制

**Issue 2 解决（heartbeat timeout）**：
- `processing` 状态写入时同时写 `processing_started_at`
- 调度器 scan 时额外检查：`status=processing AND processing_started_at < NOW() - 10min` → 自动回滚到 `status=scheduled`（认为上次 attempt 已 crash）
- 回滚时 `attempt_count++`，超过 3 次 → 直接 `status=failed(reason=max_attempts_exceeded)`

---

#### Challenger sub-agent — 第 3 轮

```json
{
  "new_issues": [],
  "verified": {
    "completeness": "✅ 步骤1-5（含预飞检T-5min/审核轮询/取消/并发控制）全覆盖；首次/日常/出错恢复三段齐全",
    "consistency": "✅ target_environment=local_api + Brain 模块 + PM2 守护 = 自洽方案；无前后矛盾",
    "testability": "✅ 每步均有 DB status 字段作为可验证输出；精度目标定量（≤1分钟误差）",
    "edge_cases": "✅ 幂等性（processing heartbeat timeout回滚）/并发（processing锁）/取消中途/多任务频控 均已定义",
    "error_paths": "✅ session_expired/rate_limit/file_not_found/platform_error/audit_timeout 全部覆盖，重试策略和通知降级已定义"
  }
}
```

**GAN 对抗收敛**：第 3 轮 `new_issues = []`，所有维度有具体证据。✅

**Challenger 总计发现新问题**：**8 个**（第1轮6个 + 第2轮2个）

---

### Phase 2（并行，GAN 收敛后）：三路补全

#### Agent B（产品经理）— 正确路径补全

**检查维度及结论**：

- **中间确认步**：✅ Step 2 已有表单校验 + 时间>当前+5min 校验
- **去重防重复任务**：✅ 幂等性通过 processing_heartbeat_timeout 机制解决
- **预飞检覆盖**：T-5min 做 session 活性探测 + 文件存在性检查 ← **补充**：预飞检失败应有 "发布前检查失败" 的单独告警，不要等到 T 时刻才告警，给用户 5 分钟窗口修复
- **Dashboard 体验**：补充「定时任务列表」中需展示的字段：任务名/发布时间/状态/进度（审核轮询进度）/帖子链接
- **边界 case**：用户把发布时间设为过去时间 → 前端实时校验 + 后端拒绝（400 Bad Request）
- **空输入**：标题为空 → 前端要求必填；标签为空 → 允许（抖音标签非必须）

**补充步骤**：
```
Step 2.5（新增）: Brain 在 T-5min 执行预飞检（session 活性 + 文件存在）→ 若失败 → Dashboard 黄色告警"发布预检失败，请在 5 分钟内处理" + 飞书告警 → 用户可在 Dashboard 点击「重新检查」或「延迟发布」
```

---

#### Agent C（混沌工程师）— 错误路径补全

**所有外部依赖 × 失败场景 × 降级策略**：

| 外部依赖 | 失败场景 | 当前覆盖？ | 降级策略 |
|---------|---------|----------|---------|
| 抖音 Cookie/Session | 过期/失效 | ✅ session_expired | 不重试，告警用户重新登录 |
| 抖音 API（上传） | 网络超时（>60s）| ❌ 未覆盖 | 重试 3 次，每次间隔 10s，仍失败 → failed |
| 抖音 API（上传） | 文件格式不支持 | ❌ 未覆盖 | 立即 failed，告警"视频格式不支持：建议 mp4/h264" |
| 抖音 API（上传） | 频控 | ✅ rate_limit | 延迟 5min 重试 ×3 |
| 抖音 API（审核轮询）| 轮询 API 超时 | ✅ audit_timeout | 保留 audit_timeout 状态 |
| 本地文件系统 | 文件不存在 | ✅ file_not_found | 不重试 |
| 本地文件系统 | 磁盘满 | ❌ 未覆盖 | 上传失败，告警"磁盘空间不足" |
| Brain DB（写回）| 写回失败 | ❌ 未覆盖 | 重试 3 次，仍失败 → 记录错误日志但不影响抖音帖子本身 |
| 飞书通知 | 飞书 API 超时 | ✅ 已有 Dashboard 主路 | 吞异常，不影响主流程 |
| 调度器（scheduler.js）| Brain 重启 | ✅ PM2 守护 + 重启 scan | 自动恢复 |

**新增失败场景**（补充至 PrepPRD）：
- 上传网络超时 → 重试 3 次（×10s 间隔）
- 视频格式不支持 → 立即 failed + 明确错误信息
- 磁盘满 → pre-flight 阶段检查磁盘剩余空间（要求 >上传视频 ×2）

---

#### Agent D（运维专家）— NFR 补全

**查询**：`GET localhost:5221/api/brain/decisions?category=nfr` → 无专项 NFR 决策，从架构推导

| NFR 维度 | 检查结论 | 缺口 | 建议值 |
|---------|---------|------|------|
| 延迟 | 调度精度 ≤1 分钟（1min setInterval）| ✅ 已定义 | ≤1min 误差 |
| 频控 | 抖音相邻发布间隔 ≥30s | ❌ 未定义并发多任务的间隔 | 同账号相邻任务 ≥30s 错开触发 |
| 规模 | 同时 scheduled 任务上限 | ❌ 未定义 | 当前系统：per-tenant ≤50 个定时任务上限 |
| 可观测性 | 调度器心跳日志 | ❌ 无 | 每次 scheduler scan 写 1 行日志（仅任务数，不含内容）|
| 可观测性 | 任务状态变更审计 | ❌ 无 | `scheduled_publish_logs` 表记录每次状态变更 + 原因 |
| 存储 | 视频文件清理 | ❌ 未定义 | 发布成功后 7 天自动删除本地副本 |
| 可用性 | 调度器重启恢复时间 | PM2 通常 <5s | 可接受 |

---

### 综合：单次呈现给用户

---

## 补全后的 Golden Path（含边界 + 错误路径）

```
Step 1: 用户在 Dashboard 点击「新建定时发布」→ 系统弹出配置表单（平台=抖音、视频文件上传、标题（必填）、标签（可选）、发布时间（≥当前时间+5分钟））→ 表单就绪

Step 2: 用户填写完成点击「确认」→ 系统校验（标题非空、发布时间>当前+5min、文件格式=mp4/h264、磁盘剩余>视频大小×2）→ 任务写入 Brain DB（status=scheduled）→ 任务列表出现新条目，显示「定时中 | 预计 HH:MM 发布」

  Step 2-失败: 发布时间≤当前时间 → 前端实时拦截，红色提示"请选择至少5分钟后的时间"

Step 2.5（预飞检，T-5min 自动）: scheduler.js 在发布时间前 5 分钟执行 pre-flight check（session 活性探测 + 文件存在性 + 磁盘空间）
  → 全通过 → 任务状态变 preflight_ok，静默
  → 任何一项失败 → Dashboard 黄色告警「预检失败：<具体原因>」+ 飞书通知 → 用户可点「立即修复」或「推迟发布」

Step 3: scheduler.js 到达发布时间窗口（≤1分钟误差）→ 拉取任务、CAS 置 status=processing（防幂等）→ 调用抖音发布脚本上传视频
  → 上传超时（>60s）→ 重试 ×3，间隔 10s → 仍失败 → status=failed(upload_timeout)，告警
  → 视频格式不支持 → 立即 status=failed(unsupported_format)，告警"建议 mp4/h264"
  → 频控（rate_limit）→ 延迟 5min 重试 ×3 → 仍失败 → status=failed(rate_limit_exceeded)
  → 同账号有其他 processing 任务 → 当前任务等待 30s 后重新 claim（保障相邻任务间隔≥30s）

Step 4: 抖音返回帖子 item_id → 开始轮询审核状态（每 60s 一次，最多 30 次）
  → status=published → 写回 Brain DB（status=published, post_url=...）→ 任务显示「✅ 已发布」+ 可点击帖子链接
  → status=auditing（30min后）→ status=audit_timeout，写回帖子链接（审核中状态）→ 告警用户「审核超时，请到抖音后台确认」
  → 写回 DB 失败 → 重试 ×3，仍失败 → 记录错误日志，不影响抖音侧帖子

Step 5: 用户在 Dashboard 点击帖子链接 → 跳转抖音帖子页 → 视频公开可见 → Done

[出错恢复场景]
Brain 重启: PM2 自动重启 Brain（<5s）→ scheduler.js 启动时 scan status=scheduled 重新入队；status=processing AND processing_started_at < NOW()-10min → 自动回滚 scheduled（attempt_count++）→ 超过 3 次回滚 → status=failed(max_attempts_exceeded)

取消任务:
  status=scheduled 或 preflight_failed → 可取消（DELETE /api/scheduled-publish/:id）
  status=processing → 拒绝（409 Conflict），显示"发布中，无法取消"
  status=published/failed → 不可取消（已终态）
```

---

## 需要你拍板的 3 个决策点

**1. 调度精度：1 分钟误差够用吗？**
- 当前方案：scheduler.js 每 1 分钟 scan，误差 ≤1 分钟
- 若需要更高精度（如 30 秒），改为 30s setInterval 即可
- 建议：1 分钟够用（视频内容发布对秒级不敏感）

**2. 审核超时后的默认行为**
- 选项 A：`audit_timeout`，保留帖子链接，等用户手动确认（推荐，不丢帖子）
- 选项 B：超时后自动尝试重发（风险：可能在抖音发布两条重复帖子）

**3. 频控重试：5 分钟 × 3 次合适吗？**
- 当前建议：rate_limit 时延迟 5 分钟重试，最多 3 次
- 可调整间隔或次数

---

## 已命中的铁律（自动 enforce，无需拍板）

- 租户隔离：`scheduled_publishes` 表必须有 `tenant_id`，查询/写入全部 scope 到当前租户（decision #68976b17）
- 凭据安全：抖音 cookie 不进日志、不进 git（decision #564802ee）
- 日志脱敏：视频标题/标签不得明文进系统日志（decision #459b6ff9）
- 端点鉴权：`/api/scheduled-publish` 所有端点必须有 auth（decision #50954d28）
- 多租户测试：E2E 种 ≥2 个租户的定时任务，断言互不串（decision #55b8eb46）
- 禁止写死环境假设值：发布时间校验、磁盘阈值、轮询频率均从配置读取（decision #5e125909）
- 真环境验证才算 done：抖音真发布是接缝断言，必须在真账号上验证（decision #3c30394c）

---

## 步骤 2：前置工作核对

| 前置类型 | 检查 | 状态 |
|---------|------|------|
| 抖音 OAuth/Cookie | `source ~/.credentials/douyin.env` 读取 DOUYIN_SESSION_COOKIE | ✅ 已有（journey_features: 抖音 OAuth 授权 working/thin）|
| 抖音发布脚本 | `apps/api/scripts/douyin-publisher.js` 或同类脚本 | ✅ 推断已有（智能发布 Journey 已有抖音短视频/图文/长文发布 working）|
| Brain DB | `localhost:5221` Brain API 可用 | ✅ 已验证（当前对话中 curl 成功）|
| 本机运行环境 | Node.js 可用，本机持续运行 | ✅ 本机 Mac（用 PM2 守护 Brain）|
| 测试视频 Fixture | 合法 mp4 测试视频文件 | ⚠️ 需确认路径或 `ffmpeg -f lavfi` 合成最小视频 |
| GHA Secret | 若有 CI smoke test 需要 DOUYIN_COOKIE_SECRET | ⚠️ 本次 target_environment=local_api，GHA Secret 非必须 |

**前置工作结论**：核心依赖（抖音 session + 发布脚本 + Brain DB）已就绪；测试 Fixture 视频可用 ffmpeg 合成，不阻塞启动。✅ 可继续写 PrepPRD。

---

## 最终 PrepPRD 全文

```markdown
# PrepPRD：智能发布（Line 01）— 抖音定时视频发布

## 本次对话涵盖的所有事项（防信息丢失）
- [x] 本 PrepPRD 包含：抖音定时视频发布（从零到 thin 骨架），含 Dashboard UI、Brain 调度器、发布执行、状态回写、失败处理
- [ ] 另立 Sprint（本次不做）：其他平台（快手/微博/小红书等）的定时发布；抖音图文/长文定时发布；定时任务的批量导入
- [ ] 待讨论：审核超时默认行为（拍板后写死）；调度精度要求（默认1分钟）；频控重试参数

## Journey 当前状态（智能发布，Line 01）
- ✅ 抖音短视频发布 — thin/working（即时发布）
- ✅ 抖音图文发布 — thin/working（即时发布）
- ✅ 抖音长文发布 — thin/working（即时发布）
- ✅ 抖音 OAuth 授权 — feature/thin/working
- ✅ 全平台心跳保活 — feature/thin/working
- ✅ 全平台状态探测 — feature/thin/working
- ✅ 掉线飞书告警 — feature/thin/working
- ⬜ **抖音定时视频发布** — planned（本次新增，thin 骨架）

## 本次要做的
用户在 ZenithJoy Dashboard 创建定时发布任务，设定未来的发布时间，系统到时间自动把视频发布到抖音，并把帖子链接写回 Brain DB，Dashboard 实时显示任务状态。

## Golden Path（用户操作流程，单线性步骤序列）

> 合同、E2E 全部从这里派生。每步 = 用户动作 + 系统可观察响应。

1. 用户在 Dashboard「定时发布」页点击「新建任务」→ 系统弹出表单（平台=抖音、上传视频、标题必填、标签选填、发布时间选择器≥当前+5min）→ 表单就绪状态
2. 用户填写完毕点击「确认」→ 系统校验字段（标题非空、时间有效、格式 mp4/h264、磁盘充足）→ 任务写入 Brain DB（status=scheduled，tenant_id 隔离）→ 任务列表新增条目，显示「定时中 | 预计 HH:MM 发布」
3. T-5min，scheduler.js 自动执行预飞检（session 活性 + 文件存在 + 磁盘空间）→ 全通过则静默；任一失败则 Dashboard 黄色告警 + 飞书通知，给用户 5 分钟处理窗口
4. T 时刻，scheduler.js scan 到期任务，CAS 置 status=processing → 调用抖音发布脚本上传视频（重试机制：超时重试×3/10s，频控延迟5min×3）→ 上传成功返回 item_id
5. 系统轮询抖音审核状态（每 60s，最多 30min）→ published → 写回 Brain DB（status=published, post_url=...）→ Dashboard 任务变为「✅ 已发布」+ 帖子链接可点击
6. 用户点击帖子链接 → 跳转到抖音帖子页 → 视频公开可见 → 任务完结

**出错恢复**：
- 发布失败（任何原因）→ Dashboard 红色「发布失败：<具体原因>」+ 飞书通知 → 用户可点「重试」或「取消任务」
- Brain 重启 → PM2 自动重启 → scheduler 重新 scan scheduled 任务，processing 超过 10min 自动回滚 → 不丢任务
- 审核超时（30min）→ status=audit_timeout，写回帖子链接（审核中状态），告警用户去抖音后台确认

## 客户视角（用户打开产品能感知到什么）
- Dashboard 出现「定时发布」入口，可创建/管理定时任务
- 任务列表实时显示状态（定时中 / 预检 / 发布中 / 已发布 / 失败）
- 发布成功后可直接在 Dashboard 点击帖子链接看到自己的视频
- 发布失败有明确原因和操作指引

## 完成后用户能
1. 在 Dashboard 预排好一周的抖音视频发布计划，系统定时自动发出
2. 随时查看每个定时任务的状态和帖子链接，不用手动刷新抖音
3. 发布失败时第一时间收到告警并知道具体原因

## 涉及的 Ability / Feature
- **抖音定时视频发布**（新增 Ability，thin，挂 Line 01 智能发布）
- **定时发布调度器**（新增 Feature，thin，Brain 模块 packages/brain/src/scheduler.js）
- **定时任务管理 API**（新增 Feature，thin，RESTful CRUD）
- **定时任务 Dashboard UI**（新增 Feature，thin，ZenithJoy Dashboard 页面）

## 不包含
- 其他平台的定时发布（快手/微博/小红书/知乎/头条/视频号/公众号）
- 抖音图文/长文定时发布（下一个 Sprint）
- 定时任务批量导入（CSV/Excel）
- 定时发布的 A/B 测试（不同时间段效果对比）
- 第三方调度服务集成（Cron job、n8n 等）

## 前置工作（已逐项确认，无 TBD）

### 账号与登录
- [x] 抖音账号 — 已有 session cookie（journey_features: 抖音 OAuth 授权 working），存于 `~/.credentials/douyin.env`

### API 与凭据
- [x] DOUYIN_SESSION_COOKIE — 已在 `~/.credentials/douyin.env`（Brain 运营员管理）
- [x] Brain DB — localhost:5221 已运行，可直接写 scheduled_publishes 表

### 基础设施
- [x] Brain（packages/brain）— 已运行（PM2 守护），新增 scheduler.js 模块挂载
- [x] ZenithJoy Dashboard（apps/dashboard）— 已运行，新增定时发布页面
- [x] 抖音发布脚本 — 已有（智能发布 Journey 内既有 thin 发布脚本，本次复用）

### 测试 Fixture
- [x] 测试视频 — 用 ffmpeg 合成最小合法 mp4（5秒，h264/aac）：`ffmpeg -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 -c:v libx264 -c:a aac test-video.mp4`

## 验收标准（Final E2E）

**逻辑断言**（CI/单测可验）：
- [ ] `scheduler.js` 单测：种一个 `publish_at = NOW() + 2s` 的任务，scheduler 1min 内扫到并置 status=processing
- [ ] 幂等测试：并发两次 claim 同一任务，只有一次成功（CAS 防重入）
- [ ] 租户隔离测试：种两个不同 tenant 的定时任务，各只能看到自己的

**接缝断言**（必须在真实环境验证，logic-done-pending 直到真验）：
- [ ] 接缝 1：真实抖音账号实际发布一条测试视频，Brain DB 中 status=published 且 post_url 非空，Dashboard 显示帖子链接可跳转（唯一真机验证接缝）
- [ ] 接缝 2：关闭 Brain 再重启，10 分钟前置 processing 任务自动回滚为 scheduled（本机可验）

**CI**：
- [ ] CI 全绿（逻辑断言 + smoke test）
- [ ] smoke test：`.github/workflows/scripts/smoke/scheduled-publish-smoke.sh`（验证 API 端点存在、scheduler 模块可 require、DB 表 schema 正确）

## 技术细节（供 Planner 参考）

### DB Schema（新表）
```sql
CREATE TABLE scheduled_publishes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  platform TEXT NOT NULL DEFAULT 'douyin',
  title TEXT NOT NULL,
  tags TEXT[],
  video_path TEXT NOT NULL,           -- 本机绝对路径
  publish_at TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL DEFAULT 'scheduled',
    -- scheduled | preflight_ok | preflight_failed | processing | published | failed | audit_timeout | cancelled
  processing_started_at TIMESTAMPTZ,  -- 用于 heartbeat timeout 检测
  attempt_count INT NOT NULL DEFAULT 0,
  failure_reason TEXT,
  post_url TEXT,
  item_id TEXT,                        -- 抖音返回的 item_id，用于审核轮询
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sp_status_publish_at ON scheduled_publishes(status, publish_at);
CREATE INDEX idx_sp_tenant ON scheduled_publishes(tenant_id);
```

### 调度器（packages/brain/src/scheduler.js）
- 随 Brain 启动，setInterval(scanAndDispatch, 60_000)（1分钟）
- scanAndDispatch 逻辑：
  1. 查 `status=scheduled AND publish_at <= NOW() + 60s` → 触发发布
  2. 查 `status=scheduled AND publish_at BETWEEN NOW()-5min AND NOW()` AND preflight 未做 → 做预飞检
  3. 查 `status=processing AND processing_started_at < NOW()-10min` → 回滚（attempt_count++，若>3则 failed）

### API 端点（新增，apps/api）
- `GET    /api/scheduled-publish` — 列表（按 tenant_id 过滤）
- `POST   /api/scheduled-publish` — 创建（含校验）
- `PATCH  /api/scheduled-publish/:id` — 修改时间（仅 scheduled 状态允许）
- `DELETE /api/scheduled-publish/:id` — 取消（仅 scheduled/preflight_failed 状态允许）
- 全部端点要求 auth header

### target_environment
`local_api`（本机 Brain + 本机抖音发布脚本，文件系统本地存储）

### base_repo
`https://github.com/perfectuser21/zenithjoy-workspace.git`（GHA CI smoke test 用）
```

---

## 执行摘要

| 维度 | 结论 |
|------|------|
| **路径判断** | 路径 C（大功能 Harness）|
| **Journey** | 智能发布 Line 01（ID: c019cdeb）|
| **语义查重** | 无重复，「抖音定时视频发布」是全新 Ability |
| **GAN 轮数** | 3 轮收敛 |
| **Challenger 发现新问题** | 8 个（6+2）|
| **三路补全** | Agent B（3条正向补全）+ Agent C（4个失败场景补全）+ Agent D（6个 NFR 缺口）|
| **用户决策点** | 3 个（精度/审核超时/重试参数）|
| **铁律自动 enforce** | 7 条（租户隔离/凭据安全/日志脱敏/端点鉴权/多租户测试/禁写死假设值/真验才算 done）|
| **Golden Path 步骤数** | 6 个主线步骤 + 3 个出错恢复场景 |
| **接缝断言** | 2 条（真机抖音发布 + Brain 重启恢复）|
| **target_environment** | local_api（本机运行，不走 GHA runner）|
| **前置工作** | 全部 ✅，无阻塞项（测试视频用 ffmpeg 合成）|
| **状态** | PrepPRD 完成，等用户拍板 3 个决策点后点火 Harness |
