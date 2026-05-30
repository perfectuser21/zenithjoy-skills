# Eval Transcript — harness-contract-proposer v8.2.0
# Sprint: ZenithJoy Agent 抖音图文 Dryrun 发布
# 日期: 2026-05-30

---

## Step 1: 读取 Skill 文件

- 读取 `/Users/administrator/perfect21/zenithjoy-skills/harness-contract-proposer/SKILL.md`（版本 8.2.0）
- 确认执行规则：按 Step 1 → 2a → 2b → 2c → 3 顺序执行
- 本次为 eval 运行，跳过 Step 4（建分支 + push + verdict）

---

## Step 2: 读取工作流文件（v8.1.0 windows_cloud 强制规则）

执行命令：
```bash
cat .github/workflows/agent-e2e-video.yml
```

**结果**: 文件存在，共 284 行。

**workflow 摘要**：
- `name: Agent E2E -- Real Windows Video Pipeline`
- `runs-on: windows-latest`
- 主要 steps：下载安装包、解压、下载测试视频、写 .env、解压 Node.js、安装 hyperframes、启动 Chrome CDP、清理旧 job、预装 Chrome headless shell、预装 ffmpeg、启动 Agent、等待 Agent 上线、安装 Playwright、运行 Playwright E2E 测试、ffprobe 验证视频质量、上传截图/日志

**关键发现**：
- Playwright E2E test step 执行的是 `e2e/agent-video-pipeline.spec.js`（视频处理流水线，不是抖音图文发布）
- ffprobe step 验证 `.mp4` 输出文件有视频流 + 音频流（视频管道验收，不验 dryrun JSON 回执）
- workflow **不含** DOUYIN_COOKIES secret 注入
- workflow **不含** 向中台下发 `douyin_publish task（type=article）` 的步骤
- workflow **不含** 验证 `ok:true dryRun:true` 回执的步骤

---

## Step 3: 读取相关代码文件

**读取的文件**：

1. `services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs`
   - 完整的 Playwright dryrun 脚本
   - 支持 3 种模式：DOUYIN_COOKIES env（CI）/ DOUYIN_PROFILE_DIR / CDP localhost:19222
   - 输出格式（成功）：`{"ok":true,"dryRun":true,"url":"...","title":"...","publishBtnVisible":...}`
   - 输出格式（失败）：`{"ok":false,"error":"..."}`
   - 内置安全栅栏：监听 `/web/api/media/article/publish` 请求，触发则 dryrun 失守
   - 封面文件不存在时调用 `emitFailure()`，exit 1

2. `services/agent/src/handlers/douyin-publish.ts`
   - `resolveDouyinScriptPath(args, env)` 函数：根据 type + ZENITHJOY_AGENT_REAL_PUBLISH 选择脚本
   - type=article + 未设 real flag → `publish-douyin-article-dryrun.cjs`
   - type=article + real='1'/'true' → `publish-douyin-article.cjs`
   - 日志格式：`[type-route] resolveDouyinScriptPath type=article real=false script=publish-douyin-article-dryrun.cjs`
   - `readLocalDouyinSession()` 桥接本地 QR session → DOUYIN_COOKIES env

3. `e2e/agent-video-pipeline.spec.js`
   - 确认：该 spec 测试的是"口播视频本地生成全链路"（非抖音图文发布）
   - 无 douyin article 发布 task 下发逻辑

4. `.github/workflows/douyin-article-e2e.yml`（对比参考）
   - 存在一个专门的 douyin article e2e workflow，使用 `DOUYIN_COOKIES` secret
   - 直接执行 `publish-douyin-article-dryrun.cjs`，跳过 Agent 中台路径
   - 与本 sprint 目标不同（本 sprint 要验证中台 → Agent → publisher 完整链路）

---

## Step 4: 执行 windows_cloud 用户路径 1:1 映射检查

**用户核心路径**（来自 task prompt）：
```
中台下发 task → Agent 接收 → 调 douyin publisher dryrun → 返回 ok:true dryRun:true
```

**与 workflow steps 的对比**：

| 用户路径步骤 | workflow step | 状态 |
|---|---|---|
| Agent 安装就绪 | Download + Extract install pack | ✅ |
| Node/hyperframes/Chrome/ffmpeg 就绪 | 多个预装 step | ✅ |
| Agent 启动并连接中台 WS | Start Agent + Wait for Agent online | ✅ |
| **中台下发 douyin_publish task（type=article）** | Run Playwright E2E test（内容是视频流水线）| ❌ [CI_GAP] |
| **Agent handler 路由 type=article** | 无 | ❌ [CI_GAP] |
| **spawn publish-douyin-article-dryrun.cjs** | 无 | ❌ [CI_GAP]（含 DOUYIN_COOKIES 缺失） |
| **返回 ok:true dryRun:true** | Verify output quality（验 mp4）| ❌ [CI_GAP] |

**识别到 4 个 CI_GAP**（详见 contract-dod.md）。

---

## Step 5: 起草 PRD 解析

**Task prompt 解析**：

| 字段 | 值 |
|---|---|
| target_environment | windows_cloud |
| workflow | `.github/workflows/agent-e2e-video.yml` |
| journey_type | agent_remote（中台←→Agent 双向通信路径） |
| core_path | 中台下发 task → Agent 接收 → douyin publisher dryrun → ok:true dryRun:true |
| response_schema | `{ok: boolean, dryRun: boolean}` |
| dryRun 约束 | 不触发 `/web/api/media/article/publish`，不点发布按钮 |

**Response Schema 字段**（用于 jq/python3 断言）：
- `ok`: boolean，成功时为 `true`
- `dryRun`: boolean，dryrun 模式时为 `true`
- 禁用字段：`published`（真发专属，dryrun 严禁出现）

---

## Step 6: 写合同（contract-dod.md）

写入 `contract-dod.md`，包含：

**ARTIFACT 段**（3 条）：
1. `publish-douyin-article-dryrun.cjs` 文件存在
2. `douyin-publish.ts` 含 type=article 路由
3. workflow 含 DOUYIN_COOKIES 注入（CI_GAP 补写后验证）

**BEHAVIOR 段**（6 条，覆盖 4 种场景 ≥ 阈值）：
1. type=article 路由正确性（unit-level，测 resolveDouyinScriptPath）
2. dryrun 脚本 stdout JSON ok:true + dryRun:true（integration-level）
3. JSON keys 完整性（`ok` + `dryRun` 都存在）
4. 禁用字段反向（`published` 不为 true）
5. error path（封面不存在 → exit 1 + ok:false）
6. 安全栅栏（不触发文章发布 API）

**E2E 验收段**：
- 使用 windows_cloud 变体 B（publisher dryrun）模板
- 修改为通过中台 API 下发 task（而非直接 spawn 脚本），覆盖完整 Agent 链路
- PASS 标准：exit 0 + ok:true dryRun:true

---

## Step 7: 自查 checklist 执行结果

| 检查项 | 结果 |
|---|---|
| 1. PRD Response Schema 字段提取 | `ok`, `dryRun` |
| 2. Contract python3 断言字段 | `ok`, `dryRun` |
| 3. 字段集合字面相等 | ✅ |
| 4. 禁用字段 `published` 不在正向断言中 | ✅（只在 BEHAVIOR 4 的 `is not True` 中） |
| 5. BEHAVIOR 条目数 ≥ 4 | ✅（6 条） |
| 6. 假绿自查：每条 BEHAVIOR 如果代码未实现是否 FAIL | ✅（6 条均为真红） |

---

## 关键发现与说明

### 1. workflow 不匹配发现

`agent-e2e-video.yml` 是**视频处理流水线**的 E2E，不是抖音图文发布的专用 workflow。用户 task prompt 指定了这个 workflow，但对于"中台下发 task → Agent 调 article dryrun"这条路径，该 workflow 存在 4 个 CI_GAP。

**建议**：Generator 在实现时应选择以下方案之一：
- 方案 A：在 `agent-e2e-video.yml` 新增一个 job（`e2e-article-dryrun`）专门验证 article dryrun 路径
- 方案 B：复用 `douyin-article-e2e.yml` 并扩展为走 Agent 中台路径（当前直接调脚本，跳过 Agent）
- 方案 C：新建 workflow（`agent-e2e-article-dryrun.yml`）

### 2. BEHAVIOR 命令环境说明

BEHAVIOR 2-6 的 `manual:bash` 命令在 macOS 本地执行（evaluator 所在机器）。这些命令直接测 publisher 脚本的本地行为（不依赖 Chrome 抖音登录），通过以下方式绕过登录依赖：
- 测 type 路由（BEHAVIOR 1）：纯 Node.js 函数调用
- 测封面不存在时 error path（BEHAVIOR 5）：不需要 Chrome
- 测 ok:true dryRun:true 输出（BEHAVIOR 2-3）：注：macOS 上不含 Chrome/抖音 session，脚本会走 CDP 模式 → 无 CDP → 抛错 → ok:false。**这意味着 BEHAVIOR 2-3 在 macOS 无 session 时会 FAIL（真红）**，正好符合 TDD Red 阶段目标

### 3. journey_type 判断

task prompt 描述的路径（中台 WebSocket → Agent → publisher）是典型的 `agent_remote` 路径：
- 不是 `user_facing`（用户没有直接操作浏览器 UI）
- 不是 `autonomous`（需要 Agent 作为远端执行器）
- `agent_remote` = 中台控制 + Agent 远程执行

---

*eval 结束时间: 2026-05-30*
*skill 版本: harness-contract-proposer v8.2.0*
*eval run: iteration-2/eval-agent-e2e-video/with_skill*
