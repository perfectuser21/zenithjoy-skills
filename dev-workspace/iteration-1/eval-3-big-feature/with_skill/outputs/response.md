# /dev 执行记录 — 快手内容发布功能

**用户请求：** 我想做快手内容发布功能，现在只有抖音这边有，快手完全没有，需要能发图文和视频

---

## 第零步：Brain DB 上下文查询

### Journeys 表（活跃条目）

| Journey | 类型 | Maturity | 状态 |
|---|---|---|---|
| 客户首次成功路径 | user_facing | mvp | active |
| 客户智能获客路径 | user_facing | skeleton | active |
| MJ3 · 主理人内容创作闭环 | autonomous | skeleton | active |
| MJ1 · 主理人开发闭环 | dev_pipeline | skeleton | active |
| Cecelia Harness Pipeline | dev_pipeline | skeleton | active |

**核心 Journey（对口）：**
- `6e63f204` — 客户首次成功路径（user_facing, maturity=mvp）
  - Notion: https://www.notion.so/358c40c2ba6381b2a6eacd288cf82f29
  - E2E: `.github/workflows/scripts/smoke/golden-path-1-smoke.sh`

### 快手现有代码现状（从 codebase 扫描）

**已有（publishers_matrix_status.md + codebase 扫描）：**

| 层 | 快手现有 | 抖音对照 | Gap |
|---|---|---|---|
| Agent handlers | `kuaishou-publish.ts` — 仅 image dryrun，硬编码 `publish-kuaishou-image-dryrun.cjs` | `douyin-publish.ts` — image/video/article 全类型路由 + dryrun/real 开关 | 快手 handler 无 type 路由、无 video 支持 |
| Publisher scripts | `publish-kuaishou-image.cjs`, `publish-kuaishou-video.cjs`, `publish-kuaishou-image-dryrun.cjs` | 抖音有 dryrun+real × image/video/article 全套 | 快手**缺 `publish-kuaishou-video-dryrun.cjs`** |
| API 路由 | `test-publish-kuaishou` 端点存在 | 抖音相同 | 快手测试端点只测 image |
| Agent 路由 | `index.ts` 里 kuaishou → `handleKuaishouPublish`，但 handler 不读 type | 抖音 handler 读 `payload.content.type` 或 `task.type` | 快手不能按 type 分发 video vs image |
| Dashboard dispatch | Dashboard 有平台列表含快手，无快手专属发布页 | 抖音有 `test-publish-douyin` 触发 | 快手无 video 发布 UI 入口 |
| QR 绑定 | 无 `qr-bind-kuaishou.ts` handler | 抖音有 `qr-bind-douyin.ts` + `qr-bind-douyin-burner.ts` | 快手用户需要绑定快手账号的 Agent 端支持不存在 |

**结论：** 快手不是"完全没有"，而是停在 image dryrun 阶段，video 脚本存在但 Agent 层无法路由到，也缺乏 dryrun 保护。真正的 Gap 是：
1. `kuaishou-publish.ts` handler 不支持 type 路由
2. 缺 `publish-kuaishou-video-dryrun.cjs`（已有 video.cjs 真发版但无 dryrun 版）
3. Agent 无法从 task payload 读 `type=video` 并正确 spawn

---

## 第一步：任务类型判断

**判断：大功能（Large Feature）**

理由：
- 涉及 Agent 层、API 层、Dashboard 层、publisher 脚本层 4 个层面改动
- 需要新建 dryrun 脚本、重构 handler 类型路由
- 有独立的 E2E smoke 路径需要新建
- 预估 WS 数量：2-3 个 WS（图文 dryrun → 图文真发 → 视频）属于甜点区

---

## 第二步：多角色检测

**角色分析：**

本次功能涉及角色：
1. **运营客户**（终端用户）— 通过 Dashboard 触发快手发布任务
2. **Agent**（Windows 客户端）— 在本地执行实际快手 Playwright 操作

**结论：** 2 个角色，但两者是同一 Journey 的上下游（Dashboard 派发 → Agent 执行），不需要拆分为两个独立 sprint。运营客户是触发方，Agent 是执行方，属于同一 WS 闭环。

---

## 第三步：语义查重

**对比：快手图文发布 vs 抖音图文发布**

| 维度 | 快手图文发布 | 抖音图文发布 |
|---|---|---|
| Journey 归属 | 客户首次成功路径 Step 6 | 客户首次成功路径 Step 6 |
| 语义相似度 | 高（同类型内容发布） | — |
| 平台 | 快手（kuaishou.com） | 抖音（douyin.com） |
| 实现层差异 | 快手创作者中心 UI 不同 | 抖音创作者中心 UI |
| 现有 Feature | kuaishou_image_publish (thin, dryrun only) | douyin_image_publish (thin, real+dryrun) |

**查重结论：** 语义相近但平台不同，现有抖音 Feature 不可复用。快手图文 Feature 已存在（thin），但 video 功能完全缺失，需要新建。不重复，应该作为对快手现有 thin feature 的 `thicken`（图文 dryrun → 真发）+ 新建快手视频发布 Feature。

---

## 第四步：Walking Skeleton 对照

**Step 6 当前状态（客户首次成功路径）：**

Golden Path Step 6: `中台派任务 + dryrun 发布 + 回执`

- 抖音：Step 6 已通（dryrun 模式）✅
- 快手：Step 6 快手分支 ❌（handler 硬编码 image，video 无 dryrun 路径）

**本功能 anchor：** 把 Step 6 快手分支从 ❌ 推到 ✅（先 dryrun，再真发）

---

## 大功能 PrepPRD

---

### Journey 当前状态

**Journey：** 客户首次成功路径（`6e63f204-e9fd-4a3b-b338-6b3616bfcc61`）
**Notion：** https://www.notion.so/358c40c2ba6381b2a6eacd288cf82f29
**Maturity：** mvp（Step 1-5 基本通过，Step 6 仅抖音 dryrun 完成）

**Step 6 快手发布当前状态：**
- `kuaishou-publish.ts` handler：存在但硬编码 image dryrun，无 type 路由
- `publish-kuaishou-video-dryrun.cjs`：不存在（有真发版，无 dryrun 版）
- Dashboard：无快手视频发布触发入口
- 快手 QR 绑定：无 Agent handler（`qr-bind-kuaishou.ts` 不存在）

---

### 本次要做的（What）

**WS1（Thin → Medium）：快手图文发布完整链路**
- 重构 `kuaishou-publish.ts` handler：按 `type` 字段路由（image/video），对齐抖音 handler 设计
- 新建 `publish-kuaishou-image-dryrun.cjs`（复用已有 dryrun 版，该文件已存在，确认内容是否合格）
- 实现 `handleKuaishouPublishTask`（对齐 `handleDouyinPublishTask`），支持从 heartbeat 路径派发
- API 路由：更新 `test-publish-kuaishou` 支持传 `type` 参数
- Dashboard `AgentDebugPage` 加快手视频发布测试按钮
- E2E smoke：`.github/workflows/scripts/smoke/kuaishou-publish-smoke.sh`（curl 触发 + receipt 验证）

**WS2（新 Feature）：快手视频发布链路**
- 新建 `publish-kuaishou-video-dryrun.cjs`（参照 `publish-douyin-video-dryrun.cjs` 结构）
- `kuaishou-publish.ts` handler 的 video 分支激活
- `ZENITHJOY_AGENT_REAL_PUBLISH` 开关支持快手（目前快手 handler 无此开关）
- Agent index.ts：统一 kuaishou task dispatch 支持 `type=video`
- Playwright E2E spec：`apps/dashboard/e2e/kuaishou-publish.spec.ts`

---

### 完成后用户能做什么（DoD）

1. Dashboard 点击"快手图文发布"按钮 → Agent 收到 type=image 任务 → 走快手创作者中心图文流程 → dryrun 不真发 → 回执到 Dashboard
2. Dashboard 点击"快手视频发布"按钮 → Agent 收到 type=video 任务 → 走快手创作者中心视频上传流程 → dryrun 不真发 → 回执到 Dashboard
3. Smoke test `kuaishou-publish-smoke.sh` 全绿
4. `ZENITHJOY_AGENT_REAL_PUBLISH=true` 时两种类型都能真发（用于生产机器）

---

### 涉及的脚本（Features）

| Feature ID | Feature 名 | 现有 Thickness | 目标 Thickness | 变化说明 |
|---|---|---|---|---|
| F-KS-IMG | 快手图文发布 | thin（dryrun only，无 type 路由） | medium（type 路由 + task-driven + real 开关） | WS1 升级 |
| F-KS-VID | 快手视频发布 | thin（脚本存在，Agent 无法路由） | thin→medium（新 dryrun 脚本 + 完整 Agent 链路） | WS2 新建 |
| F-KS-BIND | 快手账号 QR 绑定 | not_exist | thin（如 Path 1 Step 4 需要） | 暂不在本 sprint（参见"不包含"） |

**Commit 顺序（加厚两段式）：**
- Commit 1（减肥）：删除 `kuaishou-publish.ts` 中硬编码脚本路径，清除 image-only 逻辑
- Commit 2（增肌）：写新 type-aware handler + dryrun 脚本 + task-driven 入口

---

### 不包含（Out of Scope）

- 快手 QR 绑定 handler（`qr-bind-kuaishou.ts`）— 用户已有绑定方式，独立 sprint
- 快手 article（文章）发布 — 快手无官方文章功能，不做
- 快手真发自动化（`ZENITHJOY_AGENT_REAL_PUBLISH=true`）的生产验证 — 需要真实快手账号，另排 sprint
- 快手 burner 角色（Path 2 获客路径）— Path 2 范畴

---

### 执行前提条件

1. main 分支 CI 全绿（目前有 harness 测试失败，不影响本功能开发分支）
2. 本地有快手 cookie（`services/content-pipeline/scripts/publishers/.cookie-backups/快手-*.json` 已有多份备份）
3. `publish-kuaishou-video.cjs`（真发版）存在可参照（已确认存在）
4. GitHub Actions windows-latest runner 可用（E2E 环境路由：ZenithJoy 走 windows_cloud）

---

### 用户确认成功标准

```
□ 1. kuaishou-publish-smoke.sh 在 GHA windows-latest 上全绿（image dryrun + video dryrun 各1条）
□ 2. Agent 收到 type=video 的 kuaishou 任务时，stdout 包含 "dryRun": true
□ 3. Agent 收到 type=image 的 kuaishou 任务时，行为与现有一致（不退步）
□ 4. Dashboard AgentDebugPage 能触发快手视频发布并看到 receipt
□ 5. ZENITHJOY_AGENT_REAL_PUBLISH 开关对快手生效（单元测试覆盖）
```

---

## 第五步：后续动作

### Decision 内容（待写入 Brain DB decisions 表）

```json
{
  "title": "快手内容发布功能 — 大功能路径确认",
  "context": "用户请求快手图文+视频发布，当前快手 handler 只有 image dryrun，无 type 路由。与抖音 handler 差距明显。",
  "decision": "立项为大功能，2 WS 路径：WS1 快手图文 thin→medium + WS2 快手视频新建 thin，全走 dryrun 优先，生产真发另排。",
  "rationale": "与抖音对称设计，dryrun 优先保安全，windows_cloud E2E 验证，符合 Walking Skeleton 先 dryrun 再 real 原则。",
  "journey_id": "6e63f204-e9fd-4a3b-b338-6b3616bfcc61",
  "journey_step": "Step 6",
  "timestamp": "2026-05-26"
}
```

### Harness 点火参数（待用户确认后执行，本次不真正调用）

```json
{
  "method": "POST",
  "url": "http://localhost:5221/api/brain/tasks",
  "body": {
    "title": "快手内容发布 — 图文+视频 dryrun 完整链路",
    "task_type": "harness_initiative",
    "priority": "P1",
    "payload": {
      "prd_summary": "重构 kuaishou-publish.ts handler 支持 type 路由(image/video)；新建 publish-kuaishou-video-dryrun.cjs；实现 handleKuaishouPublishTask 对齐抖音 task-driven 入口；Dashboard AgentDebugPage 加快手视频发布按钮；新建 kuaishou-publish-smoke.sh E2E；全走 dryrun 保安全。",
      "journey_id": "6e63f204-e9fd-4a3b-b338-6b3616bfcc61",
      "journey_step": "Step 6",
      "base_repo": "https://github.com/perfectuser21/zenithjoy-workspace.git",
      "target_environment": "windows_cloud",
      "target_branch_prefix": "cp-",
      "ws_count": 2,
      "ws_list": [
        {
          "ws_id": "WS1",
          "name": "快手图文发布 thin→medium（type 路由 + task-driven）",
          "thickness_from": "thin",
          "thickness_to": "medium",
          "feature": "kuaishou-image-publish"
        },
        {
          "ws_id": "WS2",
          "name": "快手视频发布 new-thin（dryrun 脚本 + Agent 完整链路）",
          "thickness_from": "not_exist",
          "thickness_to": "thin",
          "feature": "kuaishou-video-publish"
        }
      ],
      "e2e_smoke_path": ".github/workflows/scripts/smoke/kuaishou-publish-smoke.sh",
      "dod_assertions": [
        "kuaishou-publish-smoke.sh 在 GHA windows-latest 全绿",
        "type=video 任务 stdout 含 dryRun: true",
        "type=image 任务行为不退步",
        "Dashboard AgentDebugPage 快手视频发布可触发并收到 receipt",
        "ZENITHJOY_AGENT_REAL_PUBLISH 开关单元测试覆盖"
      ]
    }
  }
}
```

**注意：** `base_repo` 使用 GitHub URL（`https://github.com/perfectuser21/zenithjoy-workspace.git`）而非本地路径，因为 `target_environment=windows_cloud` — GHA windows-latest runner 需要从 GitHub 拉取代码，不能访问本机路径（本地路径会导致 `fatal: repository '/Users/administrator/perfect21/zenithjoy' does not exist` 错误，这个错误在 Brain tick log 里已经出现过）。

---

## 等待用户确认

以上 PrepPRD 已生成。请确认：

1. **WS 范围是否正确？** WS1（图文重构）+ WS2（视频新建），共 2 WS
2. **成功标准是否对齐？** 特别是 dryrun 优先，不做生产真发
3. **是否启动 Harness 点火？** 确认后执行 `POST /api/brain/tasks`

如确认，下一步执行 Harness 点火并开始 WS1 开发。
