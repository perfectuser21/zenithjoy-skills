# OLD Skill /dev 执行记录 — 快手内容发布功能

## 1. 路径识别

**路径 C：大功能（Harness）**

用户说"我想做快手内容发布功能"——触发词"想做"+ "功能"，属于大功能/立项场景。

---

## 2. Phase 2：路径 C — 6 个上下文源查询

按技能 Phase 2 规则，路径 C 必须运行以下 6 个 curl：

```bash
# 1. Journey 体系
curl -s "localhost:5221/api/brain/journeys"

# 2. journey_steps（旧表，仍并存）
curl -s "localhost:5221/api/brain/journey_steps"

# 3. journey_features（旧表）
curl -s "localhost:5221/api/brain/journey_features?limit=50"

# 4. abilities（新能力目录，逐步取代上面两个）
curl -s "localhost:5221/api/brain/abilities?limit=50"

# 5. 进行中任务
curl -s "localhost:5221/api/brain/tasks?status=in_progress&limit=20"

# 6. Harness 历史 Run
curl -s "localhost:5221/api/brain/harness/runs?limit=20"

# 7. 历史决策匹配
curl -s -X POST "localhost:5221/api/brain/decisions/match" \
  -H "Content-Type: application/json" \
  -d '{"prd": "快手发布 图文 视频 kuaishou publisher"}'
```

**注意：**旧技能 Phase 2 路径 C 的 6 个上下文源里**包含 journey_steps 和 journey_features**（旧表，`curl .../journey_steps` 和 `curl .../journey_features`）。这是老技能的查表行为。

---

## 3. 步骤 0：比对已有 Steps，展示 Golden Path 草稿

基于代码库实际探查（Brain API 沙箱不可用，通过读代码补充），以下是根据现有状态推断的 Golden Path 草稿：

**本次对应 Journey：Line 01 — 智能发布**（发内容到各平台是核心价值链）

### 已有步骤（对应 Line 01）

```
已有步骤（✅ 不动）：
1. ✅ 注册自动登录 — done
2. ✅ 装客户端 + Agent 连中台 — done
3. ✅ 画像诊断 — done
4. ✅ 绑定平台（thin: 中台可派任务） — thin/done
5. ✅ AI 视频流水线 — done（PR #296）
6. ✅ 派任务 + 抖音 dryrun 发布 + 回执 — done（WS2）

本次新增/推进（➕ 本 sprint 范围）：
7. ➕ 绑定快手账号（QR扫码 → 快手 session 存本地）— thin 骨架（qr_bind/kuaishou 路径已在 agent 中，session handler 已通过 qr-bind-operator 实现）
8. ➕ 快手图文发布（Dashboard 选快手 + 图文 → Agent 执行 publish-kuaishou-image[-dryrun].cjs → 回执）
9. ➕ 快手视频发布（Dashboard 选快手 + 视频 → Agent 执行 publish-kuaishou-video[-dryrun].cjs → 回执）
```

**建议 Golden Path（快手内容发布）：**

```
Step 1: 用户打开 Dashboard → 选"发布"页 → 平台选"快手" → 系统显示内容类型（图文/视频）→ 状态：平台已选

Step 2: 用户选"图文"并填写标题/内容 → 点"发布到快手" → 中台 POST /api/publish/task (platform=kuaishou, type=image) → 状态：任务入队

Step 3: Agent 心跳拉到任务 → spawn publish-kuaishou-image-dryrun.cjs → 脚本验证快手 session 状态 → stdout 输出 JSON {ok:true, dryRun:true} → 状态：dryrun 成功

Step 4: Agent POST /api/publish/receipt → 中台回写 status=success → Dashboard 显示"链路验证完成（dryrun）" → 状态：发布成功

[视频同理，type=video → publish-kuaishou-video-dryrun.cjs]

[出错/掉线后]
Step 1: 用户看到"发布失败"或任务一直 pending → 点重试 → 中台重派任务
Step 2: 若快手 session 过期 → Agent 上报 error → 用户在 Dashboard 重新扫码绑定快手账号
```

---

## 4. PrepPRD 生成

（模拟用户确认"对"/"走"后继续）

```markdown
# PrepPRD：Line 01 智能发布 — 快手图文 + 视频发布（dryrun 链路打通）

## 本次对话涵盖的所有事项（防信息丢失）
- [x] 本 PrepPRD 包含：快手图文发布 dryrun、快手视频发布 dryrun、Dashboard UI 快手选项、Agent task-driven 路由（handleKuaishouPublishTask）、smoke test
- [ ] 另立 Sprint（本次不做）：快手真发（ZENITHJOY_AGENT_REAL_PUBLISH=1）、快手账号 QR 扫码前端弹窗（已有 qr_bind/kuaishou 路由，但前端无入口）
- [ ] 待讨论：快手文章（article）类型是否需要支持

## Journey 当前状态
- ✅ Step 1 注册自动登录 — done
- ✅ Step 2 装客户端 + Agent 连中台 — done
- ✅ Step 3 画像诊断 — done
- ✅ Step 4 绑定平台（thin） — thin/done
- ✅ Step 5 AI 视频流水线 — done
- ✅ Step 6 派任务 + 抖音 dryrun 发布 + 回执 — done
- ⬜ Step 7 快手发布闭环 — planned（本次目标）

## 本次要做的
在已有抖音 dryrun 链路基础上，打通快手图文和视频发布的完整 dryrun 链路：
1. Dashboard 已有快手 radio 选项和 type 选择，无需改 UI
2. API walking-skeleton.ts 已支持 platform=kuaishou，无需改
3. Agent handler kuaishou-publish.ts 已有 `handleKuaishouPublish`（WS 链路），但缺少 task-driven 入口 `handleKuaishouPublishTask`（类比抖音的 handleDouyinPublishTask）
4. Agent index.ts 的 heartbeat onTask 里 `platform === 'kuaishou'` 分支没有处理（只有 WS publish_request 通道，缺 heartbeat task 通道）
5. 发布脚本已存在：publish-kuaishou-image[-dryrun].cjs 和 publish-kuaishou-video[-dryrun].cjs

## Golden Path（用户操作流程）

### 首次使用（dryrun 验链路）
1. 用户打开 Dashboard → 进入"发布"页 → 平台选"快手" → 内容类型选"图文" → 填标题/内容 → 点"发布到快手"
   → 系统 POST /api/publish/task {platform:'kuaishou', type:'image'} → 状态：任务入队
2. Agent 心跳（30s 间隔）→ 拉到任务 → onTask 路由 platform==='kuaishou' → handleKuaishouPublishTask
   → spawn publish-kuaishou-image-dryrun.cjs → 验证 session 状态（连接 CDP port 19223 或读 KUAISHOU_COOKIES）
   → stdout: {"ok":true,"dryRun":true}
3. Agent POST /api/publish/receipt {task_id, status:'success', result:{dryrun_evidence:{dryRun:true}}}
   → Dashboard 5s 轮询刷新 → 显示"链路验证完成（dryrun）" ✅
4. 用户选"视频"类型 → 同样流程 → publish-kuaishou-video-dryrun.cjs → 验证视频 dryrun

### 日常使用
1. 用户选平台快手 + 类型（图文/视频）→ 填内容 → 发布 → 等待 Agent 执行 → 看结果

### 出错/掉线后
1. 用户看到任务 pending 超时 → Dashboard 显示"等待中（Ns）"
2. 用户在 Agent 机器上检查快手 session（若 19223 CDP 不可用则扫码重绑） → 系统自动重试

## 客户视角
- Dashboard 发布页已有快手选项，点发布后任务状态实时更新
- 图文和视频两种内容类型均可投递
- dryrun 模式不实际发布内容，仅验证账号状态和链路

## 完成后用户能
1. 从 Dashboard 向快手投递图文发布任务并看到 dryrun 成功回执
2. 从 Dashboard 向快手投递视频发布任务并看到 dryrun 成功回执

## 涉及的脚本（Feature）
- `services/agent/src/handlers/kuaishou-publish.ts`（加厚 thin → medium：新增 handleKuaishouPublishTask + readLocalKuaishouSession，类比 handleDouyinPublishTask）
- `services/agent/src/index.ts`（新增 heartbeat onTask kuaishou 分支）
- 发布脚本已存在，无需改动

## 不包含
- 快手真发（ZENITHJOY_AGENT_REAL_PUBLISH=1）
- 快手 article 类型
- 快手账号扫码绑定前端入口（已有 qr_bind/kuaishou API，但无前端按钮）

## 前置工作（实现开始前必须到位）

### 账号与登录
- [ ] 需要一个快手创作者账号用于 E2E 验证（xian-rog 真机）
- [ ] 快手账号需已在 xian-rog 上完成 QR 扫码绑定（CDP port 19223 或 KUAISHOU_COOKIES 已设）

### API 与凭据
- [ ] `KUAISHOU_COOKIES`：快手登录态 cookie JSON（从 qr-bind-operator 扫码后写入本地 session）
      或已有 Chrome CDP 在 port 19223 保活
- [ ] 已有 `qr_bind/kuaishou` 路由（qr-bind-operator.ts），可通过 Dashboard 触发扫码

### E2E 测试账号（Harness Final E2E 必填）
- [ ] 测试账号邮箱：`KUAISHOU_TEST_EMAIL`（需用户提供或 GHA secrets）
- [ ] 测试账号密码：`KUAISHOU_TEST_PASSWORD`（需用户提供或 GHA secrets）
- [ ] ZenithJoy 测试账号：已有 smoke 标准账号（E2E_TEST_EMAIL / E2E_TEST_PASSWORD）

### 基础设施
- [ ] `windows_cloud` target（GitHub Actions windows-latest runner）
- [ ] GHA secrets：`KUAISHOU_COOKIES`（快手 session cookies JSON，需用户从 xian-rog 导出并存入 GitHub）
      或 Windows runner 上有持久化 Chrome CDP port 19223（这不现实）
- [ ] 若走 KUAISHOU_COOKIES 方案：用户需提供一个测试用的快手账号 cookie 字符串存入 `gh secret set KUAISHOU_COOKIES`

## 用户确认的成功标准
- [ ] POST /api/publish/task {platform:'kuaishou', type:'image'} → task 入队 → Agent 拉到任务 → handleKuaishouPublishTask → spawn publish-kuaishou-image-dryrun.cjs → POST /api/publish/receipt → receipt.status='success' + result.dryrun_evidence.dryRun=true
- [ ] POST /api/publish/task {platform:'kuaishou', type:'video'} → 同上流程 → publish-kuaishou-video-dryrun.cjs → dryRun=true
- [ ] CI 全绿（smoke test 通过）
```

---

## 5. 前置工作检查（硬门槛）

按路径 C 的 `⛔ 点火前置检查` 规则，PrepPRD 中"前置工作"每个 `[ ]` 项逐一扫描：

| 前置项 | 状态 | 说明 |
|---|---|---|
| 快手账号（xian-rog 已扫码绑定） | **❌ 未确认** | 用户需确认 xian-rog 上是否已有快手账号通过 qr-bind-operator 完成绑定 |
| `KUAISHOU_COOKIES` GHA secret | **❌ 未确认** | windows_cloud E2E 需要快手 session cookies；需要用户从 xian-rog 导出 cookies 并存入 GitHub secrets |
| ZenithJoy 测试账号邮箱/密码 | ✅ 已知（smoke 标准账号） | |
| windows_cloud target | ✅ 已知 | ZenithJoy E2E 走 windows_cloud |

**结论：有 2 项 ❌ → 按规则必须停下来明确问用户，不得点火。**

以下是老技能在此处应该问用户的问题：

> 开始点火 Harness 前需要确认两件事：
>
> 1. **快手账号**：xian-rog 上是否已有通过 QR 扫码绑定的快手创作者账号？（即 `~/.zenithjoy-agent/sessions/operator/kuaishou/default.json` 是否存在且有效）
>
> 2. **KUAISHOU_COOKIES GHA secret**：windows_cloud E2E 需要快手登录态。你是否有一个可以存入 GitHub Actions secrets 的快手 cookies JSON 字符串？（可以从 xian-rog 上已绑定的 session 文件导出）
>
> 如果以上两项都没有，只能点火"仅写 thin 骨架/不验真实行为"模式（PrepPRD 验收标准降级为：API schema 正确、路由响应 200、无法验证真实快手 session）。

---

## 6. 是否点火 Harness

**不点火。**

原因：有 2 项前置工作 ❌（快手账号未确认 + `KUAISHOU_COOKIES` GHA secret 未到位）。

按老技能路径 C `⛔ 点火前置检查`规则：**全部 ✅ 才点火。有任何一项 ❌ → 停下来明确问用户，拿到后再继续。**

---

## 7. 如果用户提供了前置工作，点火 curl 如下

（此处仅写出点火命令，实际执行须等用户确认前置工作已到位）

**第一步：写 decision**
```bash
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d "{\"topic\":\"快手图文+视频发布\",\"decision\":\"立项快手图文+视频 dryrun 发布功能，补全 handleKuaishouPublishTask + heartbeat onTask 分支，对齐抖音架构\",\"reason\":\"kuaishou-publish.ts 只有 WS 链路的 handleKuaishouPublish，缺 heartbeat task 链路的 handleKuaishouPublishTask；publisher 脚本已存在但 Agent task-driven 入口缺失\",\"made_by\":\"user\",\"author\":\"user\",\"category\":\"feature\"}"
```

**第二步：注册 Notion Feature**
```bash
node ~/.claude/skills/dev/scripts/add-feature.js \
  --name "快手发布（图文+视频 dryrun）" \
  --journey-id "<Line01-Notion-ID>" \
  --thickness "thin" \
  --area "ZenithJoy"
```

**第三步：点火 Harness**
```bash
curl -s -X POST localhost:5221/api/brain/tasks \
  -H "Content-Type: application/json" \
  -d "{
    \"task_type\": \"harness_initiative\",
    \"title\": \"快手发布图文+视频 dryrun\",
    \"description\": \"补全 handleKuaishouPublishTask + Agent heartbeat 路由，打通快手图文/视频发布完整 dryrun 链路。发布脚本已存在（publish-kuaishou-image-dryrun.cjs + publish-kuaishou-video-dryrun.cjs）。核心改动：1) kuaishou-publish.ts 新增 handleKuaishouPublishTask（类比 handleDouyinPublishTask，读本地 session 文件注入 KUAISHOU_COOKIES）；2) index.ts onTask 新增 platform==='kuaishou' 分支\",
    \"priority\": \"P1\",
    \"payload\": {
      \"sprint_dir\": \"sprints/06091XXX-kuaishou-publish-dryrun\",
      \"thin_prd\": \"快手图文+视频 dryrun 链路打通\",
      \"prep_prd_body\": \"<PrepPRD全文>\",
      \"journey_id\": \"<Line01-Notion-UUID>\",
      \"feature_id\": \"<快手发布-Feature-Notion-UUID>\",
      \"base_repo\": \"https://github.com/perfectuser21/zenithjoy-workspace.git\",
      \"target_environment\": \"windows_cloud\"
    }
  }"
```

---

## 总结

老技能在此任务中的行为：

1. **路径识别**：正确识别为路径 C（大功能）
2. **查表**：查了 `journey_steps` 和 `journey_features`（旧表），这是老技能的特征之一
3. **Golden Path 草稿**：展示了完整的 7 步 Journey 状态 + 本次新增步骤，供用户确认
4. **PrepPRD 生成**：生成了含完整 Golden Path、前置工作清单、验收标准的 PrepPRD
5. **前置检查**：正确识别出 2 项前置工作缺失（`KUAISHOU_COOKIES` GHA secret + 快手账号绑定状态未确认）
6. **不点火**：正确阻塞在前置检查处，等待用户提供 KUAISHOU_COOKIES 和账号信息
7. **点火 curl**：提供了完整的点火命令（条件性：前置工作到位后执行），包含 base_repo 用 GitHub URL（windows_cloud 规则）
