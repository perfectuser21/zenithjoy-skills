# /dev 技能执行记录 — 快手内容发布功能

> 任务：我想做快手内容发布功能，现在只有抖音这边有，快手完全没有，需要能发图文和视频

---

## Phase 1：听懂意图（路径判断）

**判断结果：路径 C — 大功能 / Harness**

用户说"我想做 X 功能"，这是新功能立项诉求，不是 bug 修复也不是小改动。直接进路径 C。

---

## Phase 2：按路径查上下文（路径 C — 5 个上下文源）

会执行以下 5 条查询（Brain API 在此 sandbox 不可用，列出应执行的 endpoint，注明已废弃的避开项）：

### 查询 1 & 2：Journey 体系

```bash
# 查所有 Journey
curl -s "localhost:5221/api/brain/journeys"

# 查所有 Abilities（journey_steps / journey_features 已废弃，禁止查）
curl -s "localhost:5221/api/brain/abilities?limit=50"
```

> 注意：`journey_steps` 和 `journey_features` 表已废弃，不查。

### 查询 3：进行中任务

```bash
curl -s "localhost:5221/api/brain/tasks?status=in_progress&limit=20"
```

### 查询 4：Harness 历史 Run

```bash
curl -s "localhost:5221/api/brain/harness/runs?limit=20"
```

### 查询 5：历史决策匹配

```bash
curl -s -X POST "localhost:5221/api/brain/decisions/match" \
  -H "Content-Type: application/json" \
  -d "{\"prd\": \"快手发布 图文 视频 kuaishou publisher\"}"
```

---

## 步骤 0：Golden Path 草稿（基于实际代码库扫描结果）

### 代码库现状扫描

通过实际查看代码库，发现以下**重要现有实现**：

**已有（意料之外，代码库已存在快手相关代码）：**
- `services/agent/src/handlers/kuaishou-publish.ts` — Handler 已写完，支持 image / video 两种 type，dryrun/真发双模式
- `services/agent/publishers/kuaishou-publisher/publish-kuaishou-image-dryrun.cjs` — 图文 dryrun 脚本（WS1 已完成，PR #493 已合并）
- `services/agent/publishers/kuaishou-publisher/publish-kuaishou-image.cjs` — 图文真发脚本
- `services/agent/publishers/kuaishou-publisher/publish-kuaishou-video-dryrun.cjs` — 视频 dryrun 脚本（已存在文件）
- `services/agent/publishers/kuaishou-publisher/publish-kuaishou-video.cjs` — 视频真发脚本
- `sprints/zj-kuaishou-three-mode/` — 已有进行中 sprint，WS2 + WS3 续跑（video-dryrun + GHA workflow）

**从 abilities API 预期找到（Line 01 智能发布 Journey 下）：**
- ✅ 抖音视频发布（done）
- ✅ 抖音图文发布（done）
- 🔄 快手图文发布（working / thin，WS1 已完成）
- ⬜ 快手视频发布（计划中 / thin 进行中）

### Golden Path 草稿

```
已有（✅ 不动）：
- ✅ 抖音视频发布 — done（多端真发 + dryrun）
- ✅ 抖音图文发布 — done
- ✅ 快手图文 dryrun（publish-kuaishou-image-dryrun.cjs）— WS1 PR #493 已合并
- ✅ kuaishou-publish.ts handler — 已完整，image/video 双路由

本次新增/推进（➕ 本 sprint 范围）：
- ➕ 快手视频 dryrun（publish-kuaishou-video-dryrun.cjs）— thin，WS2
- ➕ GHA kuaishou-e2e.yml — windows-latest runner CI 验证，WS3
- ➕（可选）快手图文真发（publish-kuaishou-image.cjs 是否完整）

建议 Golden Path（用户视角，不写系统组件）：

[首次使用（运营人员）]
Step 1: 运营人员在中台选择"快手"平台 → 填写图文标题 + 正文 + 上传图片
Step 2: 点击"发布" → 系统发送任务给 Agent → Agent 验证快手 cookie 有效
Step 3: Agent 导航到快手创作者后台图文发布页 → 填入标题/正文/图片 → 提交发布
Step 4: 中台收到发布回执（成功 URL / 帖子链接）→ 运营人员看到"发布成功"

[发布视频]
Step 1: 运营人员选择"快手"平台 + 内容类型"视频" → 上传视频文件 + 填标题
Step 2: 点击"发布" → Agent 导航到快手视频发布页 → 上传视频 → 提交
Step 3: 中台收到发布回执（视频 URL）

[出错 / cookie 过期]
Step 1: 发布失败，中台显示"快手登录状态失效"
Step 2: 运营人员在 Agent 客户端触发"重新扫码绑定快手账号"
Step 3: 扫码成功 → 新 cookie 写入 → 重新触发上次失败任务
```

---

## 步骤 1：前置工作核对（硬门槛）

从 Golden Path 推断本次 sprint 需要的外部依赖，逐条核对：

### 核对结果 — 存在缺失项 ❌

| 前置类型 | 具体内容 | 状态 | 说明 |
|---|---|---|---|
| **快手账号 Cookie** | `KUAISHOU_COOKIES` GHA Secret | ❌ **未确认** | sprints/zj-kuaishou-three-mode/sprint-prd.md 中标注为 `[ASSUMPTION: KUAISHOU_COOKIES 已作为 GHA Secret 上传]`，但未有用户确认 |
| **快手测试账号** | 能登录快手创作者中心的账号 | ❌ **未提供** | E2E 必须用真实 cookie 验证登录状态，用户没有告知账号情况 |
| **视频测试素材** | 用于视频发布 E2E 的视频文件 | ❌ **未提供** | 视频真发需要真实视频文件；dryrun 只需导航可不上传，但需确认范围 |
| **发布页 URL** | 快手视频发布页 URL | ✅ 已知 | `https://cp.kuaishou.com/article/publish/video`（sprint-prd.md 有记录） |
| **CDP 端口** | 快手 CDP 端口 19223 | ✅ 已知 | handler 中有明确定义，与抖音 19222 隔离 |
| **GHA Secret 配置权限** | 能向 zenithjoy-workspace repo 写入 Secret | ❌ **未确认** | 需要 PAT 含 secrets write scope 或用户手动在 GitHub UI 配置 |

---

## 停止点：需要用户提供前置信息

**根据 SKILL.md 步骤 1 规则："有任何一项 ❌ → 停下来明确告诉用户缺什么，拿到后再继续。"**

### 必须向用户确认以下内容，才能继续写 PrepPRD 并点火 Harness：

---

**问题 1：快手账号 Cookie 状态**

现有的 `KUAISHOU_COOKIES` GHA Secret 是否已经配置好？
- 如果**已配置**：请确认 Secret 名称（`KUAISHOU_COOKIES`），以及 cookie 是否仍有效（上次使用时间）
- 如果**未配置**：需要你先在快手创作者中心（https://cp.kuaishou.com）登录一个测试账号，导出 cookie，然后我来帮你配置到 GHA Secret

---

**问题 2：本次 sprint 的范围**

代码库中已有 `publish-kuaishou-video-dryrun.cjs` 文件存在（sprints/zj-kuaishou-three-mode 中有记录），但根据 sprint-prd.md，WS2 和 WS3 尚未完成。

你说的"快手完全没有"——是指：
- A. 现有的快手 dryrun 脚本没有真正跑通 E2E（CI 上没验证过）？
- B. 快手真发（真实发布到快手）还没做好？
- C. 中台 Dashboard 层面没有快手发布入口？

这影响到本次 sprint 的目标定义。

---

**问题 3（仅当范围包含视频真发时）：视频测试素材**

如果需要验证视频真实发布，需要一个测试视频文件：
- 已有现成的测试视频路径？（如 `tests/fixtures/*.mp4`）
- 或者我用 `ffmpeg` 合成一个 5 秒最小合法 MP4？

---

**⛔ 在以上问题得到答复之前，不写 PrepPRD，不点火 Harness。**

---

## 附：已知架构信息（无需用户提供）

以下信息已从代码库确认，PrepPRD 写作时直接引用：

- **目标 Journey**：Line 01 智能发布（`user_facing`）
- **目标环境**：`windows_cloud`（GHA windows-latest runner，快手 publisher 需要 Windows Playwright + Chromium）
- **base_repo**：必须用 GitHub URL（windows_cloud 环境要求），不能用本地路径
- **CDP 端口**：快手 19223（严格区分于抖音 19222）
- **dryrun 默认**：`ZENITHJOY_AGENT_REAL_PUBLISH` 未设时走 dryrun，安全优先
- **handler 已完整**：`kuaishou-publish.ts` 支持 image/video 路由，不需要改 handler
