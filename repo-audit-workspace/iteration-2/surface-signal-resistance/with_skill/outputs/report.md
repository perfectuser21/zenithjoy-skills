# Repo Audit — zenithjoy 2026-03-29

## 反模式命中（CI 精读）

| 反模式 | 命中 | 说明 |
|--------|------|------|
| `admin_bypass` | **命中** | `enforce_admins.enabled = false`，管理员可直推 main 绕过所有 CI 检查 |
| `audit_scope_wrong` | **命中** | L3 security job 仅在 `apps/dashboard` 执行 `npm audit --omit=dev`，跳过 dev 依赖，跳过 API/GeoAI/miniapp 模块 |
| `no_coverage_gate` | **命中** | dashboard 的 `vitest.config.ts` 无任何 `thresholds`；`vitest run --coverage` 即使 0% 也不报错 |
| `lint_too_lenient` | **命中** | dashboard CI: `--max-warnings 79`（远超建议上限 20） |
| `l1_not_on_push` | **命中** | L1 Process Gate 仅 `on: pull_request`，直接 push to main 不触发 PR title 检查 |
| `missing_modules` | **命中** | `apps/miniapp` 完全不在任何 CI job 中（无 lint/typecheck/test/security 扫描） |
| `no_audit_in_ci` | 部分命中 | 有 security job，但仅 dashboard 且用 `--omit=dev` |
| `no_branch_protect` | 未命中 | required_status_checks 存在（L1-L4 全部在列） |

**CI 反模式命中数：6 → 🔴 虚假绿 ❌ 1分**

---

## L1 管业务：13/30

| # | 项目 | 分 | 证据 |
|---|------|----|----- |
| 1 | OKR 清晰度 | ⚠️ 3 | Brain 有 45 个 goals，5 个是 `Test KR for select`（active 状态），9 类 KR 重复出现 2-5 次。有真实业务 OKR（内容飞轮/Dashboard/Cecelia自运转），但 OKR 数据库被测试脏数据严重污染 |
| 2 | 任务可执行性 | ❌ 1 | Brain 有 40 个 active tasks，全部 `assigned_to=null`，0 个 completed。任务结构存在，但无一可执行，派发系统故障遗留 |
| 3 | 进度可见性 | ⚠️ 3 | Dashboard 已部署（port 5211），heartbeat 历史在 `docs/heartbeat/`。但 Brain 数据污染导致进度数字不可信 |
| 4 | 定期复盘 | ⚠️ 3 | `docs/heartbeat/` 有多轮 heartbeat 报告，`docs/decisions/` 有决策记录。有机制，最近无正式 retrospective |
| 5 | 资源成本控制 | ❌ 1 | 无 API 用量/算力成本追踪代码。无 token 计费监控。geoai 的 posts.ts 为 1044 行静态数据，无动态成本计量 |
| 6 | 战略方向验证 | ⚠️ 3 | DEFINITION.md 存在，内容飞轮逻辑清晰（AI产内容→多平台发布→数据反馈）。方向成立，但 KR 执行层因 Brain 故障瘫痪 |

---

## L2 管代码：12/35

| # | 项目 | 分 | 证据（含反模式命中） |
|---|------|----|--------------------|
| 7 | CI 有效性 | 🔴 虚假绿 ❌ 1 | 命中 6 个反模式（admin_bypass + audit_scope_wrong + no_coverage_gate + lint_too_lenient + l1_not_on_push + missing_modules）。miniapp 硬编码密钥完全未被 CI 检测。CI 全绿 = 危险 |
| 8 | 代码质量 | ⚠️ 3 | `tsconfig.base.json` 有 `"strict": true`，各 app 正确继承。但 dashboard tsconfig 覆盖 `noUnusedLocals: false, noUnusedParameters: false`；dashboard lint 容忍 79 条警告。5 个文件 >500 行：ContentPublish.tsx(1770), geoai/posts.ts(1044), ContentData.tsx(1022), Dashboard.tsx(903), ContentTypeConfigPage.tsx(799) |
| 9 | 测试有效性 | ⚠️ 3 | API 有 65% 覆盖率门禁（statements/branches/functions/lines）。dashboard 无覆盖率门禁。API `works.test.ts`、`publish.test.ts`、`fields.test.ts` 全部 `describe.skip`（需 DB mock 未配置）。实际有效测试覆盖率偏低 |
| 10 | 依赖安全 | ❌ 1 | 根目录 `npm audit` 返回 **70 个漏洞（40 critical, 15 high, 14 moderate, 1 low）**，包括 terser ReDoS (high)、tough-cookie Prototype Pollution (moderate)。CI security job 用 `--omit=dev` 在子目录运行，完全掩盖了这些漏洞 |
| 11 | 技术债 | ⚠️ 3 | 主代码 5 个 TODO/FIXME（含"实现图片上传逻辑"未完成项）。6 个文件 >500 行需拆分。技术债整体可控，ContentPublish.tsx 1770 行是重点 |
| 12 | 可观测性 | ⚠️ 3 | API 有 `/health` 端点（返回 status+timestamp）。无结构化日志（只有 console.log，无 winston/pino）。无外部错误上报（无 Sentry）。有基础健康检查，无生产级可观测性 |
| 13 | 安全态势 | ❌ 1 | **发现 3 处硬编码密钥（均已追踪入 git）：** ① `apps/miniapp/miniprogram/pages/ai-features/index.js:38` — Coze API Key `pat_BSo4wqL0AH7Fii9IKE9ZGjyntLBdxdtB1UYt7o3MJIWfmYUj9uCAGqJ6zqCfSmDm`；② `services/jnsy-label/app/routers/stats.py:11` — Label Studio Token `048f955ad4b8e221bf91316955edfe4eb219fade`；③ `services/jnsy-label/app/routers/labeling.py:12` — 同上 Token。密钥已在 git 历史中，必须立即吊销。.gitignore 覆盖 .env 正确，但未阻止源码硬编码 |

---

## L2 管运行：14/30

| # | 项目 | 分 | 证据 |
|---|------|----|----- |
| 14 | 可执行性 | ⚠️ 3 | Dashboard 已部署可访问。API 有完整 Express 结构（routes/controllers/services/db）。miniapp 已迁入 monorepo 但部署路径不明确 |
| 15 | 注册表鲜活 | ⚠️ 3 | Skills 注册在 Cecelia 系统。8 个发布平台 scripts 在 `scripts/` 目录存在可执行。但 Brain 40/40 tasks assigned_to=null，注册资源无法被自动调度 |
| 16 | 数据完整性+灾备 | ⚠️ 3 | `deploy/deploy.sh` 有本地文件备份（cp 到 .backups/）。PostgreSQL 连接配置存在，但无自动 pg_dump/cron 备份策略。Brain 数据有测试污染（9类重复 KR） |
| 17 | 自动化覆盖 | ⚠️ 3 | 有 n8n workflows 目录和各平台发布 scripts。Brain 派发系统瘫痪导致自动化无法正确调度。多个关键步骤需人工触发 |
| 18 | 闭环率 | ❌ 1 | 无内容采集→分析→选题完整闭环自动化的代码证据。`scripts/sync-scraper-to-works.sh` 存在，但 Brain 任务全 null 无法验证闭环在运转 |
| 19 | SLO 基线 | ❌ 1 | 无任何 SLO 定义文件。无异常告警阈值配置。`/health` 端点仅返回 `{status: ok}`，无业务指标 |

---

## L3 管沟通：7/25

| # | 项目 | 分 | 证据 |
|---|------|----|----- |
| 20 | 向上汇报 | ❌ 1 | 无飞书 webhook 自动发送代码（apps/api/src 和 scripts/ 中无 feishu send 实现）。历史 heartbeat 是人工/AI 手写文件，无自动推送 |
| 21 | 卡点上报 | ❌ 1 | 无 P0 主动告警机制代码。无 Sentry/PagerDuty/飞书告警集成 |
| 22 | 决策提请 | ⚠️ 3 | Brain API 有 proposals/pending_actions 机制（heartbeat 记录中有提案 ID）。有机制，但依赖人工触发 |
| 23 | 横向协调 | ⚠️ 3 | Brain API 有 tasks 分配结构。理论上有协调机制，但 40/40 assigned_to=null，实际派发断裂 |
| 24 | 事故响应 | ❌ 1 | 无 P0 playbook 文件。根目录有 `.EMERGENCY-L0-BRAIN-API-FAILURE.txt` 说明有过 P0 事故，但无系统性 playbook 文档 |

---

## 总分：46/120 (38%)

---

## 关键发现

### 🔴 虚假绿 #1（最危险）：CI 全绿但硬编码密钥已入库

L3 security job 只扫描 `apps/dashboard`，完全跳过 `apps/miniapp` 和 `services/`。
结果：`apps/miniapp/.../index.js:38` 中的 Coze API Key 和 `services/jnsy-label/app/routers/` 中的 Label Studio Token 已提交到 git，CI 全绿无任何告警。
这是教科书级虚假绿——CI 扫了不该扫的地方、跳过了真正有问题的地方。

### 🔴 虚假绿 #2：coverage 绿但无门禁

dashboard L4 CI 运行 `npx vitest run --coverage`，状态是绿的。但 `apps/dashboard/vitest.config.ts` 无任何 `thresholds` 配置。覆盖率 0% 照样绿。测试通过 ≠ 代码被测试了。

### 结构性盲点：Brain 数据污染 + 派发系统遗留故障

45 个 goals 中有 5 个 `Test KR for select`（active 状态），9 类 KR 各有 2-5 个重复条目。40 个 active tasks 全部 `assigned_to=null`，0 个 completed。从 Memory 记录看，这是历史派发系统故障（74h+）的遗留状态，系统表面"有 Brain 在跑"，实际调度完全失效，无法支撑业务 OKR 推进。

### 结构性盲点：npm audit 严重性被 CI 系统性隐藏

根目录有 **40 个 critical 漏洞**，CI security job 通过在子目录 + `--omit=dev` 规避了这些。用户看到"Security Audit 绿"≠ 依赖安全。

---

## 修复计划

**P0（今天，密钥泄露紧急）：**
1. 立即吊销 Coze API Key `pat_BSo4wqL0AH7Fii9IKE9ZGjyntLBdxdtB1UYt7o3MJIWfmYUj9uCAGqJ6zqCfSmDm`
2. 立即吊销 Label Studio Token `048f955ad4b8e221bf91316955edfe4eb219fade`（两个文件共用同一 token）
3. 用 BFG Repo Cleaner 清洗 git 历史，将密钥改为环境变量（`COZE_API_KEY`, `LABEL_STUDIO_TOKEN`）
4. 修复 CI security job：移到根目录、去掉 `--omit=dev`

**P1（本周）：**
5. dashboard `vitest.config.ts` 添加 coverage thresholds（建议起始：50%）
6. dashboard CI lint 的 `--max-warnings 79` 改为 `--max-warnings 20`（先修 warning 再降阈值）
7. GitHub Branch Protection 开启 `enforce_admins`
8. 清理 Brain 脏数据：删除 5 个 Test KR，合并 9 类重复 KR

**P2（两周内）：**
9. miniapp 纳入 CI（新增 miniapp-lint/security job）
10. 修复 API skip 测试（works/publish/fields 配置 DB mock，去掉 describe.skip）
11. 添加飞书 webhook 自动日报推送
12. 拆分 `ContentPublish.tsx`（1770 行）为子组件
13. 添加 `docs/slo.yaml` + API `/health` 端点加入业务指标
14. 添加 PostgreSQL 自动备份（pg_dump cron）
