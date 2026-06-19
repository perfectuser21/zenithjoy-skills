# Dev Skill v20.1.0 执行记录

**执行时间**：2026-06-19  
**Skill 版本**：baseline v20.1.0  
**用户请求**：「我想在 ZenithJoy 里做一个「抖音定时发布」功能：用户在 Dashboard 设定发布时间，到时间自动把视频发到抖音，并把帖子链接写回 Brain DB。这个功能现在完全没有，需要从零开始。」

---

## Phase 1：听懂意图（不查 DB，纯解析）

**分析**：
- 用户说「想做一个」、「新功能」、「从零开始」
- 没有任何 bug/报错/崩溃关键词
- 不是小改动——是一条完整的新能力链路（Dashboard UI + 定时任务 + 发布执行 + DB 回写）

**判断** → **路径 C：大功能 / Harness**

---

## Phase 2：按路径查上下文（路径 C — 5 个源）

### 源 1：Journey 体系（journeys）

Brain API 返回结果中，与「抖音发布」最相关的 Journey：

| Journey 名 | ID | 成熟度 | 状态 |
|---|---|---|---|
| **智能发布** | `c019cdeb-d90b-4f8b-a658-ae333663ac35` | skeleton | active |
| ZenithJoy 运营中枢 | `636a918c-8b23-4df5-baec-b1eb3308fffb` | skeleton | active |
| 客户首次成功路径 | `6e63f204-e9fd-4a3b-b338-6b3616bfcc61` | mvp | active |

**确定本次 Journey**：**智能发布**（`c019cdeb-d90b-4f8b-a658-ae333663ac35`）  
描述印证：「8 平台自动发布能力（抖音/快手/小红书…）」——定时发布是智能发布 Journey 的核心 Ability。

### 源 2：已有 Journey Features（智能发布 Journey 相关条目）

从 `journey_features` 返回，过滤 `journey_id = c019cdeb-...`，提取状态：

| Feature/Ability 名 | kind | thickness | status |
|---|---|---|---|
| 抖音 OAuth 授权 | feature | thin | working |
| 全平台状态探测 | feature | thin | working |
| 掉线飞书告警 | feature | thin | working |
| 全平台心跳保活 | feature | thin | working |
| 抖音图文发布 | ability | thin | working |
| 抖音长文发布 | ability | thin | working |
| 小红书视频发布 | ability | thin | broken |
| 小红书图文发布 | ability | thin | broken |
| 快手图文发布 | ability | thin | working |
| 视频号视频发布 | ability | thin | planned |
| 头条微头条发布 | ability | thin | planned |

**关键发现**：
- 抖音即时发布能力（图文/长文）已有 thin 骨架，status=working
- **「抖音视频发布」** 在 journey_features 中**不存在**——需要新建
- **「定时发布」**（Dashboard 时间配置 + 调度器 + 发布触发 + 帖子链接回写）完全不存在——需要全新建设
- 「抖音 OAuth 授权」已有 thin，可复用作前置依赖（不用在本 sprint 做）

### 源 3：进行中任务

Brain API 返回 `tasks?status=in_progress` → **空数组**（无进行中任务）

本次功能无并发冲突风险。

### 源 4：Harness 历史 Run

最近 20 条 runs 均属其他 initiative（客户私域 AI 接管、Harness Pipeline 等），无与「抖音发布」直接相关的历史 run。

最近的 run 状态多为 failed（Final E2E FAIL 或 watchdog_overdue），说明当前 Harness 管道整体存在 E2E 稳定性挑战——本 Sprint 制定验收标准时需偏保守，聚焦核心路径。

### 源 5：历史决策匹配

`decisions/match` 返回 `{"matched":[], "missing":[]}`——无相关历史决策。

本次从零建设，没有需要遵守的历史约束。

---

## 步骤 0：比对已有 Abilities，展示 Golden Path 草稿

### 已有（智能发布 Journey，✅ 不动 / ⚠️ 旁依赖）：

- ✅ 抖音 OAuth 授权（thin, working）—— 本 sprint 直接复用，不重做
- ✅ 抖音图文发布（thin, working）—— 参考实现模式
- ✅ 抖音长文发布（thin, working）—— 参考实现模式
- ✅ 全平台心跳保活（thin, working）—— 保障发布时 session 有效
- ✅ 全平台状态探测（thin, working）—— 发布前健康检查可复用

### 本次新增/推进（➕ 本 sprint 范围）：

- ➕ **抖音视频发布**（新建，thin）—— 核心 Ability：把视频文件真实发到抖音，拿到帖子链接
- ➕ **定时发布调度器**（新建，thin）—— Feature：Brain DB 中存储定时任务，Brain tick 到时触发
- ➕ **Dashboard 定时配置 UI**（新建，thin）—— Feature：用户在 Dashboard 选视频+填时间+提交

### 建议 Golden Path（用户视角，单线性步骤序列）：

```
Step 1: 用户打开 ZenithJoy Dashboard，进入「定时发布」页面
        → 系统显示「新建定时任务」表单（视频上传区 + 发布时间选择器 + 提交按钮）
        → 状态：表单空白，等待输入

Step 2: 用户上传/选择一个视频文件（mp4），填写抖音标题/描述，设定发布时间（如 2 小时后）
        → 系统接受上传，预览缩略图，时间选择器显示所填时间
        → 状态：表单已填，等待提交

Step 3: 用户点击「提交定时任务」
        → 系统把任务写入 Brain DB（scheduled_publish 表），返回任务 ID 和「已计划：[时间]」确认提示
        → 状态：任务 ID 可见，任务出现在「我的定时任务」列表

Step 4: 到达设定时间，Brain tick 检测到待触发任务
        → 系统自动调用抖音视频发布脚本，使用已有 OAuth session 上传视频
        → 状态：发布执行中（用户无需操作）

Step 5: 发布成功，抖音返回帖子 URL
        → 系统把帖子 URL 写回 Brain DB（scheduled_publish 表的 result_url 字段）
        → Dashboard「我的定时任务」列表中，该任务状态变为「已发布」，并显示帖子链接

Step 6: 用户在 Dashboard 点击帖子链接
        → 浏览器打开抖音帖子页面，视频已真实发布可见
        → 出口：用户拿到可分享的抖音帖子链接

---
出错场景（掉线恢复）：
Step 4 发布时 OAuth session 过期 → 系统检测到 401 错误
        → 系统在 Brain DB 中把该任务状态标记为「session_expired」
        → 飞书推送告警：「定时发布失败：抖音 session 过期，请重新登录」
        → 用户在 Dashboard 重登抖音，触发「重试」按钮 → 系统重新执行发布
```

---

## 步骤 1：核对前置工作

从 Golden Path 推断本 sprint 所需前置依赖：

| 前置类型 | 具体项 | 状态 |
|---|---|---|
| API Key / 凭据 | 抖音 OAuth session（cookies）— 已有 `抖音 OAuth 授权` feature working | ✅ 可复用 |
| 抖音发布脚本 | `publishers/douyin-publisher/` 目录已有图文/长文发布脚本，视频发布需新写，可参考图文实现 | ✅ 有范本 |
| Dashboard 接入 | ZenithJoy Dashboard（GHA windows-latest E2E 环境）已有基础框架 | ✅ 已有框架 |
| Brain DB | Brain API localhost:5221 运行中，可新建 scheduled_publish 表（migration） | ✅ 运行中 |
| 测试 Fixture | 需要一个测试用 mp4 视频文件用于 E2E | ⚠️ 需明确路径 |
| E2E 环境 | ZenithJoy UI → windows_cloud（GHA windows-latest），符合 E2E 路由死规则 | ✅ 确认 |

**Fixture 说明**：根据 dev skill 规则，测试视频可用 `ffmpeg` 合成最小合法 mp4（无需用户提供真实视频）：
```bash
ffmpeg -f lavfi -i color=c=blue:size=1280x720:rate=30 -t 5 -c:v libx264 test-fixture.mp4
```
此方案可在 CI 中自动生成，无需用户干预 → 前置工作全部 ✅

**全部前置工作确认完毕，可进入 PrepPRD 写作。**

---

## PrepPRD 正文

---

# PrepPRD：智能发布 — 抖音定时发布（从零建 thin 骨架）

## 本次对话涵盖的所有事项（防信息丢失）
- [x] 本 PrepPRD 包含：Dashboard 定时配置 UI（选视频+填时间+提交）、Brain DB 新建 scheduled_publish 表（migration）、Brain tick 触发逻辑、抖音视频发布 Ability（thin）、发布结果 URL 回写 Brain DB
- [ ] 另立 Sprint（本次不做）：多平台同步定时发布（本次只做抖音）、定时任务编辑/取消、批量定时、发布数据回流统计、Dashboard 定时任务日历视图
- [ ] 待讨论：定时精度要求（Brain tick 默认 5min 周期，最大误差 5 分钟，用户是否接受）

## Journey 当前状态（智能发布 Journey）

- ✅ 抖音 OAuth 授权 — thin/working（本 sprint 复用）
- ✅ 抖音图文发布 — thin/working（参考实现）
- ✅ 抖音长文发布 — thin/working（参考实现）
- ✅ 全平台心跳保活 — thin/working（session 保活依赖）
- ✅ 全平台状态探测 — thin/working（发布前健康检查）
- 🔄 抖音视频发布 — **本 sprint 新建 thin**
- 🔄 定时发布调度器 — **本 sprint 新建 thin**
- 🔄 Dashboard 定时配置 UI — **本 sprint 新建 thin**
- ⬜ 小红书视频发布 — broken（另立 sprint）
- ⬜ 视频号视频发布 — planned（另立 sprint）
- ⬜ 头条微头条发布 — planned（另立 sprint）

## 本次要做的

用户在 ZenithJoy Dashboard 里填写「视频文件 + 发布时间 + 标题描述」，点提交后系统把任务存到 Brain DB。到设定时间，Brain tick 自动触发把视频发到抖音，拿到帖子链接后写回 Brain DB，Dashboard 上可看到「已发布」状态和帖子链接。

## Golden Path（用户操作流程，单线性步骤序列）

> 这是唯一决定"做什么"的锚点。合同、E2E 全部从这里派生。

1. 用户打开 ZenithJoy Dashboard，点击侧栏「定时发布」→ 系统显示「新建定时任务」表单（视频上传输入框、标题文本框、描述文本框、发布时间选择器、提交按钮）→ 表单空白等待输入
2. 用户选择视频文件（mp4）、填写标题和描述、设定未来的发布时间（至少 1 分钟后）→ 系统接受文件并显示文件名，时间选择器回显所填时间 → 表单验证通过，提交按钮可点
3. 用户点击「提交定时任务」→ 系统调用 Brain API 创建 scheduled_publish 记录，返回任务 ID，页面显示「✅ 已计划发布：[时间]，任务 ID: [id]」→ 该任务出现在「我的定时任务」列表，状态为「待发布」
4. 系统到达设定时间（Brain tick 检测 scheduled_publish 表中 `scheduled_at <= now AND status = 'pending'`）→ Brain 自动调用抖音视频发布脚本，上传视频文件，等待抖音返回帖子 URL → 发布执行中（用户无需操作）
5. 抖音返回帖子 URL → 系统把 `result_url` 写回 Brain DB scheduled_publish 表，更新 `status = 'published'` → Dashboard「我的定时任务」列表中该任务状态变为「✅ 已发布」，显示可点击的帖子链接
6. 用户在 Dashboard 点击帖子链接 → 浏览器打开抖音帖子页面，视频真实可见 → 出口：用户拿到可分享的抖音帖子 URL

> **出错场景（必须覆盖）**：Step 4 发布时 OAuth session 过期 → 系统捕获 401/403 错误 → Brain DB 中该任务状态标记为 `session_expired` → 飞书推送告警「定时发布失败：抖音 session 过期，请重新登录」→ 用户在 Dashboard 重登抖音 → 点「重试」→ 系统重新执行 Step 4-5

## 客户视角（用户打开产品能感知到什么）

打开 ZenithJoy Dashboard 后，侧栏出现「定时发布」入口。填表、选时间、提交——就能看到计划中的任务列表。到时间后，任务自动变成「已发布」，旁边出现抖音帖子链接，点开就是真实发布的视频。全程不用手动操作抖音 App。

## 完成后用户能

- 在 Dashboard 提前排好抖音视频发布计划，不用盯着时间手动发
- 发布完成后在 Dashboard 直接拿到抖音帖子链接
- 出了问题（session 过期）第一时间收到飞书提醒

## 涉及的 Ability / Feature

- **抖音视频发布**（新建，thin）— kind: ability，Journey: 智能发布
- **定时发布调度器**（新建，thin）— kind: feature，Journey: 智能发布（Brain tick 扩展模块）
- **Dashboard 定时配置 UI**（新建，thin）— kind: feature，Journey: 智能发布

## 不包含

- 多平台定时发布（非抖音平台）
- 定时任务的编辑、取消、复制
- 发布数据回流统计（播放量/点赞等）
- 批量排期（日历视图）
- 定时精度低于 5 分钟（Brain tick 最小粒度 5 分钟）

## 前置工作（已逐项确认，无 TBD）

### 账号与登录
- [x] 抖音账号 OAuth session — 已有 `抖音 OAuth 授权` feature (thin/working)，cookies 存于 ZenithJoy Agent profile

### API 与凭据
- [x] 抖音发布鉴权 — 复用现有 session cookies（`publishers/douyin-publisher/` 同目录机制），无需额外 API Key

### E2E 测试账号
- [x] ZenithJoy Dashboard 访问 — GHA windows-latest runner，windows_cloud 环境
- [x] 抖音发布账号 — 复用现有智能发布 CI 已配置账号（`publisher-smoke.sh` 已在 CI 跑通）

### 测试 Fixture
- [x] 测试视频 — CI 中用 ffmpeg 合成最小合法 mp4（5 秒蓝色画面，1280x720）：
  ```bash
  ffmpeg -f lavfi -i color=c=blue:size=1280x720:rate=30 -t 5 -c:v libx264 test-douyin-video.mp4
  ```
  无需用户提供真实视频

### 基础设施
- [x] Brain API — localhost:5221 运行中，DB migration 新增 scheduled_publish 表
- [x] Brain tick — 5 分钟周期，扩展 tick executor 检测 scheduled_publish 待发布任务
- [x] ZenithJoy Dashboard — GHA windows-latest E2E 已有基础，新增路由 `/scheduled-publish`

## 验收标准（Final E2E）

**逻辑断言（CI/单测验）**：
- [ ] `scheduled_publish` 表 migration 跑通，`status` 字段枚举 (`pending`/`publishing`/`published`/`session_expired`/`failed`) 校验正确
- [ ] `POST /api/scheduled-publish` 创建记录，返回包含 `id`、`scheduled_at`、`status: "pending"` 的 JSON，单测绿
- [ ] Brain tick executor 函数：输入一条 `scheduled_at = now - 10s, status = pending` 的记录，正确触发发布调用（mock 发布脚本），单测绿
- [ ] 发布成功回调：`result_url` 写回 DB，`status` 变为 `published`，单测绿

**接缝断言（真目标验证，logic-done-pending 前不能标 done）**：

> 接缝清单（3 个碰真实世界的点）：
> 1. **抖音视频上传接缝**：`publish-douyin-video.js` 真实调用抖音上传接口，返回非空 `post_url`（真机 GHA windows-latest runner，真实抖音 session）
> 2. **Brain DB 回写接缝**：`result_url` 真实写入生产 Brain DB（`hk-vps` postgres），`GET /api/scheduled-publish/:id` 能读到该 URL
> 3. **Dashboard UI 接缝**：GHA windows-latest Playwright E2E，截图确认「已发布」标签和帖子链接文字出现在页面

- [ ] [接缝 1] E2E smoke：ffmpeg 合成视频 → Dashboard 提交定时任务（定时 1 分钟后）→ Brain tick 触发 → 抖音返回真实帖子 URL（非空，格式为 `https://www.douyin.com/video/...`）
- [ ] [接缝 2] Brain DB 回写验证：`psql cecelia -c "SELECT result_url, status FROM scheduled_publish WHERE status='published' LIMIT 1"` 返回非空 URL
- [ ] [接缝 3] Dashboard Playwright 截图：页面出现「✅ 已发布」文字 + 帖子链接，截图存为 `douyin-scheduled-publish-result.png`
- [ ] CI 全绿（GHA windows-latest smoke job pass）

---

## 技术实现草图（供 Planner/Proposer 参考，非 PrepPRD 必须部分）

### 新增文件清单（thin 骨架）

```
publishers/douyin-publisher/publish-douyin-video.js     # 新建（参考图文/长文发布脚本）
services/scheduled-publish/
  ├── scheduler.js                                       # Brain tick 扩展：查 DB + 触发发布
  ├── migrations/001_create_scheduled_publish.sql        # DB migration
  └── __tests__/scheduler.test.js                        # 单元测试
apps/dashboard/src/pages/ScheduledPublish/
  ├── index.tsx                                          # 页面入口（路由 /scheduled-publish）
  ├── NewTaskForm.tsx                                    # 新建定时任务表单
  └── TaskList.tsx                                       # 任务列表（状态 + 帖子链接）
.github/workflows/scripts/smoke/douyin-scheduled-publish-smoke.sh  # CI smoke
```

### DB Schema（scheduled_publish 表）

```sql
CREATE TABLE scheduled_publish (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform      TEXT NOT NULL DEFAULT 'douyin',
  video_path    TEXT NOT NULL,
  title         TEXT NOT NULL,
  description   TEXT,
  scheduled_at  TIMESTAMPTZ NOT NULL,
  status        TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','publishing','published','session_expired','failed')),
  result_url    TEXT,
  error_message TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_scheduled_publish_status_scheduled_at ON scheduled_publish(status, scheduled_at);
```

### Harness 点火参数（路径 C 点火）

```json
{
  "task_type": "harness_initiative",
  "title": "抖音定时发布",
  "description": "用户在 Dashboard 设定发布时间，到时间自动把视频发到抖音，帖子链接写回 Brain DB。从零建 thin 骨架，含 Dashboard UI + Brain tick 调度 + 抖音视频发布 Ability + DB 回写。",
  "priority": "P1",
  "payload": {
    "sprint_dir": "sprints/MMDDHHNN-douyin-scheduled-publish",
    "journey_id": "c019cdeb-d90b-4f8b-a658-ae333663ac35",
    "base_repo": "https://github.com/perfectuser21/zenithjoy-workspace.git",
    "target_environment": "windows_cloud"
  }
}
```

---

## 执行流程摘要（dev skill v20.1.0 视角）

| 阶段 | 内容 | 结果 |
|---|---|---|
| Phase 1 意图解析 | 「想做」+「新功能」+「从零开始」 | → 路径 C 大功能/Harness |
| Phase 2 源 1 Journey | 语义匹配「智能发布」Journey | ✅ 确认归属 |
| Phase 2 源 2 Features | 抖音视频发布、定时调度器、Dashboard UI 均不存在 | ✅ 全新建 |
| Phase 2 源 3 任务 | 无进行中任务，无并发冲突 | ✅ 可启动 |
| Phase 2 源 4 Runs | 近期多个 Final E2E FAIL，验收标准需保守聚焦 | ⚠️ 注意 |
| Phase 2 源 5 决策 | 无历史决策匹配，从零建设 | ✅ 无约束 |
| 步骤 0 Golden Path 草稿 | 提炼 6 步主线 + 1 条出错恢复 | ✅ 完成 |
| 步骤 1 前置工作核对 | 全部 ✅，ffmpeg 合成 fixture | ✅ 全部到位 |
| PrepPRD 生成 | 含 Golden Path 6 步 + 接缝清单 3 条 | ✅ 完成 |
| 路由 | → 路径 C Harness 点火 | 待用户确认后执行 |
