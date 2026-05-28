# Repo Audit — zenithjoy-workspace 2026-03-29

## 反模式命中（CI 精读 Step 1.5）

| 反模式 | 命中 | 证据 |
|--------|------|------|
| `admin_bypass` | ✅ 命中 | `enforce_admins.enabled = false` — 管理员可绕过所有保护规则直推 main |
| `audit_scope_wrong` | ✅ 命中 | L3 security job 只审计 `apps/dashboard`，跳过 `apps/api`、`apps/geoai`、`apps/miniapp` |
| `no_coverage_gate` | ✅ 命中（dashboard）| `apps/dashboard/vitest.config.ts` 无 `coverage.thresholds`；CI 运行 `npx vitest run --coverage` 但不设门禁，0% 也能通过 |
| `lint_too_lenient` | ✅ 命中 | dashboard `--max-warnings 79`（远超 20 的合理阈值） |
| `l1_not_on_push` | ✅ 命中 | `ci-l1-process.yml` 仅触发 `pull_request`，不覆盖 `push to main` |
| `missing_modules` | ✅ 命中 | `apps/miniapp` 完全不在任何 CI workflow 中，含硬编码 API key |
| `no_audit_in_ci`（根目录）| ✅ 命中 | 根目录 `npm audit` 有 70 个漏洞（40 critical, 15 high）；CI 只在子目录审计，且用 `--omit=dev` |

**命中 7 个反模式 → 🔴 虚假绿 — CI 全绿不等于代码安全**

---

## L1 管业务：12/30

| # | 项目 | 分 | 证据 |
|---|------|----|------|
| 1 | OKR 清晰度 | ⚠️ 3 | Brain API 显示 45 个 goals，18 个 active；其中 5 个 "Test KR for select" 污染 OKR 空间 |
| 2 | 任务可执行性 | ⚠️ 3 | 最近 10 条 commit 有实际交付（feat/fix 为主），但 Brain tasks 与 git commits 映射不清晰 |
| 3 | 进度可见性 | ❌ 1 | docs/reports 只有 3 个文档（最新 2026-03-08），距今 3 周无更新；无 KR 进度面板 |
| 4 | 定期复盘 | ❌ 1 | 无 retrospective 记录，无固定复盘周期证据 |
| 5 | 资源成本控制 | ❌ 1 | 无 API 成本追踪代码；无 cost tracking middleware |
| 6 | 战略方向验证 | ⚠️ 3 | ZenithJoy 内容飞轮方向成立，但 miniapp 含硬编码 API key 说明安全执行有盲区 |

---

## L2 管代码：15/35

| # | 项目 | 分 | 证据（含反模式命中） |
|---|------|----|------|
| 7 | CI 有效性 | 🔴 虚假绿 ❌ 1 | 命中 7 个反模式。admin bypass + audit_scope_wrong + no_coverage_gate + lint_too_lenient + l1_not_on_push + missing_modules + no_audit_in_ci |
| 8 | 代码质量 | ⚠️ 3 | `tsconfig.base.json` 有 `strict: true`；但 dashboard `noUnusedLocals/Parameters: false`，且 `--max-warnings 79` |
| 9 | 测试有效性 | ⚠️ 3 | 18 个测试文件；api 有 coverage thresholds(65%)，dashboard 无 gate；api tests 全为 mock DB，无真实集成测试 |
| 10 | 依赖安全 | 🔴 虚假绿 ❌ 1 | 根目录 `npm audit`：**70 vulnerabilities（40 critical, 15 high）**；CI 只跑 dashboard 子目录且 `--omit=dev`，根目录 critical 漏洞完全不可见 |
| 11 | 技术债 | ❌ 1 | 8 个文件超 500 行：ContentPublish.tsx(1770)、posts.ts(1044)、ContentData.tsx(1022)、Dashboard.tsx(903)、ContentTypeConfigPage.tsx(799)、ContentFactoryPage.tsx(776)、CeceliaContext.tsx(602)、PublishStats.tsx(566) |
| 12 | 可观测性 | ❌ 1 | 无 winston/pino（只有 console.log）；有 `/health` 端点；无 Sentry 或外部错误上报 |
| 13 | 安全态势 | 🔴 虚假绿 ❌ 1 | 硬编码 Coze PAT token 已提交 git（apps/miniapp/miniprogram/pages/ai-features/index.js:38）；.gitignore 覆盖 .env；branch protection 有 required checks 但 `enforce_admins=false` |

---

## L2 管运行：18/30

| # | 项目 | 分 | 证据 |
|---|------|----|------|
| 14 | 可执行性 | ⚠️ 3 | Dashboard 有 build artifact；API 有 `/health`；但 miniapp 构建未验证，无端到端 smoke test |
| 15 | 注册表鲜活 | ⚠️ 3 | 4 个子应用均在 monorepo；但 miniapp 未接入 CI（注册了无人管），geoai 无 lint/typecheck job |
| 16 | 数据完整性+灾备 | ❌ 1 | regression-contract.yaml 存在；但无 DB backup cron 配置 |
| 17 | 自动化覆盖 | ⚠️ 3 | scripts 目录有发布脚本；多个脚本仍需手动触发，无 scheduler 自动调用证据 |
| 18 | 闭环率 | ⚠️ 3 | 有内容发布→采集→展示链条；但 AI 选题/生成→分析的反馈环未见自动闭环 |
| 19 | SLO 基线 | ❌ 1 | 无 SLO 定义文件；无异常阈值配置；zenithjoy 自身无 SLO 文档 |

---

## L3 管沟通：10/25

| # | 项目 | 分 | 证据 |
|---|------|----|------|
| 20 | 向上汇报 | ⚠️ 3 | dashboard 有 Feishu webhook 配置 UI，但 apps/api 无 feishu push 实现，无日报自动发送逻辑 |
| 21 | 卡点上报 | ❌ 1 | 无 P0 主动告警机制；无 error monitoring；无 webhook 触发告警代码 |
| 22 | 决策提请 | ⚠️ 3 | Brain API 有 pending_actions 机制（历史有使用记录）；但 zenithjoy repo 自身无自动触发代码 |
| 23 | 横向协调 | ❌ 1 | 无 Agent 任务分配文档；miniapp 迁移进 monorepo 后无人认领 CI 接入，协调缺失 |
| 24 | 事故响应 | ⚠️ 3 | docs/SECURITY-VULNERABILITIES.md 存在，但非 P0 playbook；无 incident response 流程文档 |

---

## 总分：55/120 (45.8%)

---

## 关键发现

### 1. 🔴 虚假绿：安全审计盲区三层叠加

CI 全绿背后有三层安全审计缺失：

- **根目录 70 个 CVE（40 critical）完全不被 CI 检测**：CI 只在 `apps/dashboard` 子目录跑 `npm audit --omit=dev`，根目录 miniprogram-ci 依赖链中的 terser（高危 ReDoS）、tough-cookie（Prototype Pollution）等 critical 漏洞对 CI 透明。
- **`--omit=dev` 遮蔽 dev 依赖漏洞**：开发依赖漏洞被系统性忽略。
- **apps/miniapp 完全游离于 CI 之外**：含硬编码 Coze PAT token（`pat_BSo4wqL0AH7Fii9IKE9ZGjyntLBdxdtB1UYt7o3MJIWfmYUj9uCAGqJ6zqCfSmDm`），该 token 已存在于 git 历史中，立即需要吊销。

### 2. 🔴 虚假绿：Dashboard Coverage Gate 缺失

`apps/dashboard/vitest.config.ts` 无 `coverage.thresholds`，CI 运行 `npx vitest run --coverage` 只生成报告不做门禁。实际覆盖率是多少无从知晓，但 CI 永远绿。对比：api 有 65% thresholds，但 tests 全为 mock DB（无真实集成测试）。

### 3. 🔴 虚假绿：Branch Protection 有规则无执行

`enforce_admins: false` 意味着 repo admin 可直接 push main 绕过所有 required status checks。4 个精心设计的 L1-L4 Gate 对 admin 账户形同虚设。

### 4. 结构性技术债：8 个超 500 行文件

ContentPublish.tsx(1770行) 是建议拆分阈值的 3.5 倍，是维护高危区。

### 5. OKR 数据污染未清理

Brain API 中 5 个 "Test KR for select"（status=active）持续污染 OKR 视图，Memory 多轮 heartbeat 记录了此问题但长期未解决。

---

## 修复计划

### P0（今天）：
1. **吊销 Coze API key**：`apps/miniapp/miniprogram/pages/ai-features/index.js:38` 中 `pat_BSo4wqL0AH7Fii9IKE9ZGjyntLBdxdtB1UYt7o3MJIWfmYUj9uCAGqJ6zqCfSmDm` 已在 git 历史中，立即在 Coze 控制台吊销该 token，用 wx.getStorageSync 动态读取替代硬编码
2. **开启 enforce_admins**：`gh api -X PATCH repos/perfectuser21/zenithjoy-workspace/branches/main/protection -f enforce_admins=true`

### P1（本周）：
3. **修复 CI 审计范围**：将 L3 security job 改为在根目录运行 `npm audit`，删除 `--omit=dev`，改用 `--audit-level=high`，或建立例外清单机制
4. **接入 miniapp 到 CI**：至少加 sensitive file scan 和 `npm audit`
5. **dashboard 添加 coverage thresholds**：在 `vitest.config.ts` 补充 `coverage.thresholds`（建议从 50% 起步）
6. **清理 OKR 测试污染**：删除 Brain API 中 5 个 "Test KR for select" 条目

### P2（两周内）：
7. **拆分超大文件**：ContentPublish.tsx(1770行) 和 ContentData.tsx(1022行) 优先拆分
8. **添加结构化日志**：引入 winston 或 pino，替换 console.log
9. **添加 Sentry 错误上报**：前端 + 后端
10. **修复 L1 CI 触发**：`ci-l1-process.yml` 补充 `push: branches: [main]` 触发，防止直推 main 绕过 PR title 检查
