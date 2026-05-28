# Repo Audit — zenithjoy-workspace 2026-03-29

## 反模式命中（CI 精读）

| 反模式 | 状态 | 证据 |
|--------|------|------|
| `admin_bypass` | **命中** | `enforce_admins.enabled = false`：管理员可直推 main，绕过所有 CI 门禁 |
| `audit_scope_wrong` | **命中** | CI 安全审计仅在 `apps/dashboard` 目录运行，且加了 `--omit=dev`；根目录 `npm audit` 显示 **70 个漏洞（40 critical，15 high）**，全部在 `miniprogram-ci`、`cos-nodejs-sdk` 等根目录依赖中，CI 视而不见 |
| `no_coverage_gate` | **命中** | Dashboard (`apps/dashboard`) 的 `vitest.config.ts` 有 `--coverage` 但**无 `thresholds`**；CI L4 运行 `npx vitest run --coverage` 时零覆盖率门禁，任何覆盖率都能通过 |
| `lint_too_lenient` | **命中** | Dashboard `--max-warnings 79`，当前警告数恰好 **79/79**（满格运行），只要新增一个警告就 CI 失败；处于临界状态 |
| `l1_not_on_push` | **命中** | `ci-l1-process.yml` 只触发 `pull_request`，不触发 `push`；直推 main 时 PR 标题检查不运行 |
| `missing_modules` | **命中** | `apps/miniapp`（微信小程序）无任何 CI 覆盖（lint/typecheck/test），完全处于 CI 盲区 |
| `no_audit_in_ci` | 未命中 | L3 有 `npm audit --audit-level=moderate --omit=dev`（虽然范围错误，但形式上存在） |
| `no_branch_protect` | 未命中 | 分支保护已开启，required_status_checks 包含 L1-L4 四个 Gate |

**反模式命中数：6/8 → 🔴 虚假绿 ❌**

---

## L1 管业务：11/30

| # | 项目 | 分 | 证据 |
|---|------|----|------|
| 1 | OKR 清晰度 | ⚠️ 3 | Brain API 返回 45 个 goals，其中 5 个 `Test KR for select [active]` 污染生产 OKR 数据；`Cecelia 基础稳固` 出现两次重复条目 |
| 2 | 任务可执行性 | ⚠️ 3 | Brain 有 40 个 tasks，近期 git log 有实际 PR 合并；但全部 40 个 tasks 状态均为 `in_progress`，无一 `done`，疑似批量卡住 |
| 3 | 进度可见性 | ⚠️ 3 | Dashboard 存在，`docs/reports/` 有历史 heartbeat 报告；但 `regression-contract.yaml` 的 `core` 和 `golden_paths` 均为空数组 |
| 4 | 定期复盘 | ❌ 1 | `docs/` 下无独立 retrospective 记录，仅有 heartbeat 和 decisions；无法证明有定期复盘机制 |
| 5 | 资源成本控制 | ❌ 1 | 代码库中无 API 成本追踪逻辑；无 token_count/cost 字段；无外部成本仪表板证据 |
| 6 | 战略方向验证 | ✅ 5 | `DEFINITION.md` 明确定义内容飞轮战略；近期 commits 集中在内容流水线（ContentFactory、ContentTypeConfig）；方向一致 |

**L1 小计：11/30**

---

## L2 管代码：19/35

| # | 项目 | 分 | 证据（含反模式命中） |
|---|------|----|---------------------|
| 7 | CI 有效性 | 🔴虚假绿 ❌ 1 | 4 个 CI workflow 结构完整，全部绿色；但命中 6 个反模式（admin_bypass、audit_scope_wrong、no_coverage_gate、lint_too_lenient、l1_not_on_push、missing_modules）——表面全绿，防线多处失守 |
| 8 | 代码质量 | ⚠️ 3 | `tsconfig.base.json` strict=true；Dashboard 当前 79/79 警告（临界状态）；API 15/15 警告（临界）；8 个 pages 超 500 行（最大 ContentPublish.tsx 1770 行） |
| 9 | 测试有效性 | ⚠️ 3 | API 有覆盖率门禁（65% 阈值）；Dashboard 12 test/95 source 文件（13%），无覆盖率门禁；`regression-contract.yaml` 的 `golden_paths` 为空，无 E2E 保障 |
| 10 | 依赖安全 | 🔴虚假绿 ❌ 1 | CI 仅扫 `apps/dashboard --omit=dev`（0 漏洞）；根目录 70 个漏洞（40 critical），包含 `miniprogram-ci/terser`（高危 ReDoS）、`babel-traverse`（严重），CI 完全不可见 |
| 11 | 技术债 | ⚠️ 3 | TODO/FIXME 仅 4 个（低）；但超 500 行文件 8 个；`ContentPublish.tsx` 1770 行、`ContentData.tsx` 1022 行 |
| 12 | 可观测性 | ⚠️ 3 | API 有 `/health` 端点；全部日志为 `console.log/error`（非结构化）；无 Sentry 或等价外部错误上报；无 winston/pino |
| 13 | 安全态势 | ⚠️ 3 | `.gitignore` 覆盖 `.env`/`*.key`；未发现硬编码密钥；但 `enforce_admins=false` 允许管理员绕过所有检查 |

**L2 代码小计：19/35**

---

## L2 管运行：14/30

| # | 项目 | 分 | 证据 |
|---|------|----|------|
| 14 | 可执行性 | ⚠️ 3 | Dashboard build + deploy 脚本存在；API Dockerfile 存在；但 `regression-contract.yaml` golden_paths 为空，无端到端链路验证 |
| 15 | 注册表鲜活 | ⚠️ 3 | Brain API 40 个 tasks 全部 `in_progress`，无一完成；miniapp 在 CI 盲区运行；注册资源是否真实运转存疑 |
| 16 | 数据完整性+灾备 | ❌ 1 | 无 DB 备份策略文档；无备份 cron 或迁移策略证据；`docs/database/` 存在但内容未验证 |
| 17 | 自动化覆盖 | ⚠️ 3 | `workflows/` 下有 n8n 和自定义 workflow；`deploy/deploy.sh` 存在；但 miniapp 上传仍需手动执行 |
| 18 | 闭环率 | ⚠️ 3 | `settings.api.ts` 定义飞书 webhook 配置接口；但 `apps/api` 无实际 webhook 发送代码，闭环依赖外部 n8n，代码层未验证 |
| 19 | SLO 基线 | ❌ 1 | 无 SLO 定义文档；`regression-contract.yaml` core 为空；无异常阈值或告警触发条件 |

**L2 运行小计：14/30**

---

## L3 管沟通：9/25

| # | 项目 | 分 | 证据 |
|---|------|----|------|
| 20 | 向上汇报 | ⚠️ 3 | `settings.api.ts` 有飞书 webhook 配置接口定义；但 API 层无自动日报发送代码，依赖外部 n8n（有登录组件，无 webhook 推送代码证据） |
| 21 | 卡点上报 | ❌ 1 | 无主动 P0 告警代码（无 Sentry、无 webhook 触发、无结构化日志）；卡点发现依赖人工 heartbeat |
| 22 | 决策提请 | ⚠️ 3 | Brain API 有 proposals 机制（当前 1 个 open proposal）；但触发全靠人工，无自动提请逻辑 |
| 23 | 横向协调 | ❌ 1 | Brain tasks 40 个全 `in_progress`，assigned_to 不可见；无 Agent 间反馈回收机制证据 |
| 24 | 事故响应 | ❌ 1 | 无 P0 playbook 文件；`docs/` 中无 incident response 文档 |

**L3 小计：9/25**

---

## 总分：53/120（44%）

| 层级 | 得分 | 满分 | 比率 |
|------|------|------|------|
| L1 管业务 | 11 | 30 | 37% |
| L2 管代码 | 19 | 35 | 54% |
| L2 管运行 | 14 | 30 | 47% |
| L3 管沟通 | 9 | 25 | 36% |
| **总计** | **53** | **120** | **44%** |

---

## 关键发现

### 1. 双重虚假绿（最危险）

**CI 安全审计** 和 **依赖安全** 同时是虚假绿：CI 在 `apps/dashboard` 跑 `npm audit --omit=dev` 出 0 漏洞，显示绿灯；但根目录有 70 个漏洞（40 critical），`miniprogram-ci`（含 terser ReDoS 高危）、`babel-traverse`（严重）、`cos-nodejs-sdk` 均在其中。这些包从未被 CI 扫描过，但 CI 永远显示绿色安全。

**Dashboard 测试覆盖率** 同样虚假绿：CI L4 运行 `npx vitest run --coverage` 绿色通过——但 `vitest.config.ts` 无任何 `thresholds` 配置，哪怕覆盖率是 0% 也能通过。12 个测试文件对应 95 个源文件（13% 比率），实际覆盖率不明，但 CI 永远绿。

### 2. 管理员绕过 + 临界警告数 = 双重逃生门

`enforce_admins=false` 允许管理员直推 main 绕过所有 CI。同时 Dashboard 当前警告数 79/79（满格），API 15/15（满格），任何新增警告都让 CI 失败——但对管理员推送完全无效。两个漏洞组合，CI 门禁对主要操作者实际无效。

### 3. OKR 数据污染 + 全部任务卡在 in_progress

Brain API 中 5 个 `Test KR for select` 处于 active 状态。40 个 tasks 无一 `done`，全部 `in_progress`。这是系统性问题，可能是历史派发系统故障遗留，也可能是任务生命周期管理缺失。OKR 层无法反映真实执行状态。

### 4. miniapp 完全 CI 盲区

`apps/miniapp` 已进入 monorepo，但 CI 无任何覆盖。该模块变更可直接上线，无 lint、typecheck 或 test 门禁。

---

## 修复计划

**P0（今天）：**
- `apps/dashboard/vitest.config.ts` 加入覆盖率 thresholds（lines: 40，statements: 40），消除测试虚假绿
- 将 CI 安全审计移至根目录运行（或单独添加 `npm audit --audit-level=high` job），去掉 `--omit=dev`，消除依赖安全虚假绿
- GitHub Branch protection 开启 `Include administrators`（enforce_admins = true）

**P1（本周）：**
- Dashboard `--max-warnings` 从 79 降至 20，API 从 15 降至 5；清理存量警告
- 清理 Brain 中 5 个 `Test KR for select` 污染数据；审查 40 个 `in_progress` tasks 真实状态
- `apps/miniapp` 添加基本 CI job（至少 typecheck + 敏感文件扫描）
- `ci-l1-process.yml` 在 `on:` 中加入 `push: branches: [main]` 触发器

**P2（两周内）：**
- `regression-contract.yaml` 补充 golden_paths（登录→内容工厂→发布一条完整链路）
- API 日志从 `console.log` 迁移到 `pino` 结构化日志，加请求 ID
- 建立 DB 备份策略文档 + 自动化 backup cron
- 创建 `docs/INCIDENT-RESPONSE.md` P0 playbook
- `ContentPublish.tsx`（1770 行）拆分为子组件
