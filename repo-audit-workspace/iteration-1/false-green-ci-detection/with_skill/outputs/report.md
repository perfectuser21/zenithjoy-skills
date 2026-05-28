# Repo Audit — zenithjoy-workspace 2026-03-29

**审核者**：主理人检查
**Repo**：`perfectuser21/zenithjoy-workspace`（本地路径 `/Users/administrator/perfect21/zenithjoy`）
**日期**：2026-03-29

---

## 反模式命中（CI 精读）

对照 8 项 CI 反模式清单逐一核验：

| 反模式 | 状态 | 证据 |
|--------|------|------|
| `admin_bypass` | **命中** | `enforce_admins.enabled: false`，管理员可绕过所有 required status checks |
| `audit_scope_wrong` | **命中** | L3 security job 在 `apps/dashboard` 下运行 `npm audit --omit=dev`，排除了 dev 依赖；根目录及其他 app 未审计 |
| `no_coverage_gate` | **命中** | Dashboard 的 `vitest.config.ts` 无 `coverage.thresholds`；L4 运行 `npx vitest run --coverage` 但不设门禁，覆盖率永远不会阻断 CI |
| `lint_too_lenient` | **命中** | Dashboard lint：`--max-warnings 79`，远超 20 的合理阈值 |
| `l1-not-on-push` | 不适用 | L1 仅在 `pull_request` 触发，但 branch protection 已要求 PR，直推被阻断，此条实际风险低 |
| `missing_modules` | **命中** | GeoAI：只有 build job，无 lint/typecheck/test；Miniapp：完全不在任何 CI workflow 中 |
| `no_audit_in_ci` | 部分（同 audit_scope_wrong） | audit 存在但范围错误 |
| `no_branch_protect` | 未命中 | branch protection 已启用，4 个 status check 都是 required |

**命中：5 项（admin_bypass + audit_scope_wrong + no_coverage_gate + lint_too_lenient + missing_modules）**

---

## L1 管业务：14/30

| # | 项目 | 分 | 证据 |
|---|------|----|------|
| 1 | OKR 清晰度 | ⚠️ 3 | Brain API 返回 45 个 goals，含 5 个"Test KR for select"污染条目（约 11%），ZenithJoy 专属目标仅 3 个，OKR 数据可读性受损 |
| 2 | 任务可执行性 | ⚠️ 3 | Brain tasks 有 10 个 active 任务（内容流水线方向），但 regression-contract.yaml 的 core 和 golden_paths 均为空，PR 级任务与 Brain 任务间无正式映射 |
| 3 | 进度可见性 | ⚠️ 3 | Dashboard 前端存在，docs/heartbeat 有历史报告，但最新状态来自 memory 文件而非系统化 dashboard；进度数据散落多处 |
| 4 | 定期复盘 | ❌ 1 | docs/decisions 最新文件为 2026-03-08，docs/heartbeat 有记录但无结构化 retrospective，无法确认上次复盘时间 |
| 5 | 资源成本控制 | ❌ 1 | 未找到 API 调用量追踪、算力成本监控机制；无 cost dashboard 或告警 |
| 6 | 战略方向验证 | ⚠️ 3 | DEFINITION.md 存在，ZenithJoy 内容飞轮方向清晰，3 个 active area_okr 目标一致；但近期 OKR 执行因派发系统故障停滞时间较长 |

---

## L2 管代码：14/35

| # | 项目 | 分 | 证据（含反模式命中） |
|---|------|----|---------------------|
| 7 | CI 有效性 | 🔴虚假绿 ❌ 1 | 4 个 workflow 存在，L1-L4 表面全绿；实际命中 5 个反模式：admin_bypass + audit_scope_wrong（--omit=dev 且只审 dashboard）+ no_coverage_gate（dashboard 无覆盖率门禁）+ lint_too_lenient（max-warnings 79）+ missing_modules（geoai 无 lint/test，miniapp 完全缺失）。最危险的结构性盲点。 |
| 8 | 代码质量 | ⚠️ 3 | API ESLint --max-warnings 15（合理）；Dashboard --max-warnings 79（命中反模式）；5 个文件超 500 行：ContentPublish.tsx 1770 行、ContentData.tsx 1022 行、Dashboard.tsx 903 行、ContentTypeConfigPage.tsx 799 行、ContentFactoryPage.tsx 776 行 |
| 9 | 测试有效性 | ⚠️ 3 | 测试文件存在（dashboard: 10+ 个，api: 6+ 个）；API vitest.config 有 65% 覆盖率门禁 ✓；Dashboard vitest.config 完全无 coverage.thresholds，CI 跑了 --coverage 但覆盖率再低也不报错（命中 no_coverage_gate） |
| 10 | 依赖安全 | ❌ 1 | 根目录 npm audit：**70 个漏洞（40 critical, 15 high, 14 moderate, 1 low）**；主要来源：miniprogram-ci 携带 @babel/traverse RCE 漏洞（GHSA-67hx-6x53-jw92, CRITICAL）、terser ReDoS、tough-cookie Prototype Pollution；CI security job 用 --omit=dev 且只审 apps/dashboard，这 70 个漏洞完全被漏掉 |
| 11 | 技术债 | ❌ 1 | 5 个文件超 500 行（最大 1770 行）；regression-contract.yaml core/golden_paths 为空占位；根目录散落大量 .heartbeat-*/.prd-*/.dod-*/.task-* 临时文件（已在 .gitignore 未 commit，但本地未清理） |
| 12 | 可观测性 | ⚠️ 3 | API 有 /health 端点 ✓；无结构化日志（winston/pino），使用 console.log；无 Sentry 或外部错误上报；无前端错误边界监控 |
| 13 | 安全态势 | ⚠️ 3 | .gitignore 正确覆盖 .env/.key/.pem ✓；无硬编码凭据（均使用 process.env 或 import.meta.env）✓；branch protection enforce_admins: false（命中 admin_bypass），管理员可直推 main |

---

## L2 管运行：14/30

| # | 项目 | 分 | 证据 |
|---|------|----|------|
| 14 | 可执行性 | ⚠️ 3 | Dashboard 和 API 有完整构建链路，内容发布工作流存在；但 miniapp 无 CI 验证，regression-contract golden_paths 为空，端到端链路未被正式合约覆盖 |
| 15 | 注册表鲜活 | ⚠️ 3 | Brain API 显示 10 个 active 任务，45 个 goals 中 13 个已 cancelled、14 个 archived；workflows/ 目录有 skill 脚本，未全面验证当前可执行性 |
| 16 | 数据完整性+灾备 | ❌ 1 | docs/database/migrations 存在，但无 DB 备份策略文件；无自动 dump 脚本；历史记录显示 Brain OKR 数据曾出现 100% 污染（Test KR 注入），数据完整性保护机制薄弱 |
| 17 | 自动化覆盖 | ⚠️ 3 | 内容发布、数据采集有脚本自动化；miniapp 上传需手动（scripts: upload/preview）；部署为手动脚本（deploy-hk.sh），无 CD pipeline |
| 18 | 闭环率 | ⚠️ 3 | 平台数据采集→API→Dashboard 链路存在；有 metrics.api.ts 日报接口；但 Brain 任务→代码交付→内容发布→数据采集的完整闭环未被自动化监控 |
| 19 | SLO 基线 | ❌ 1 | 无正式 SLO 文档；无 uptime/响应时间/错误率的"正常"定义；settings.api.ts 有 alerts 数据结构但无实际触发逻辑 |

---

## L3 管沟通：11/25

| # | 项目 | 分 | 证据 |
|---|------|----|------|
| 20 | 向上汇报 | ⚠️ 3 | Dashboard 有飞书 OAuth 登录，有 metrics API 日报接口；workflows/image-gen 有 send-to-feishu.sh（针对图片生成，非系统日报）；未找到自动推送日报给 Alex 的 webhook 调用代码 |
| 21 | 卡点上报 | ⚠️ 3 | docs/heartbeat 有人工提交的 heartbeat 报告；无自动 P0 告警 webhook；依赖人工触发上报 |
| 22 | 决策提请 | ⚠️ 3 | Brain API 有 pending_action 机制（历史可见）；docs/decisions 有决策文档；但机制依赖人工判断何时提请，无系统性触发条件 |
| 23 | 横向协调 | ❌ 1 | Brain tasks 的 10 个 active 任务历史上多次出现 assigned_to=null 问题；Agent 任务分配透明度低 |
| 24 | 事故响应 | ❌ 1 | 无正式 P0 Playbook 文件；docs/decisions 有历史事故记录但非结构化 playbook；缺少标准化的"发现→诊断→升级→恢复→复盘"流程 |

---

## 总分：53/120（44%）

| 层级 | 得分 | 满分 | 占比 |
|------|------|------|------|
| L1 管业务 | 14 | 30 | 47% |
| L2 管代码 | 14 | 35 | 40% |
| L2 管运行 | 14 | 30 | 47% |
| L3 管沟通 | 11 | 25 | 44% |
| **总计** | **53** | **120** | **44%** |

---

## 关键发现

### 1. CI 虚假绿——最高风险

这是本次审计最危险的发现。4 个 CI workflow 在 GitHub 上显示全绿，但实际上：

- **Dashboard lint 通过 ≠ 代码质量达标**：`--max-warnings 79` 意味着积累了 79 个警告也不会报错
- **Coverage CI 通过 ≠ 测试充分**：Dashboard 跑了 `--coverage` 但没有 `thresholds`，0% 覆盖率也能通过
- **Security audit 通过 ≠ 无安全漏洞**：CI 只审计 `apps/dashboard --omit=dev`，根目录有 40 个 critical 漏洞完全被忽略
- **Miniapp 对 CI 透明**：miniapp 的任何代码变更不触发任何检查
- **管理员可绕过所有 checks**：`enforce_admins: false` 意味着 perfectuser21 账号可以直推 main

### 2. 依赖安全盲区（隐性炸弹）

`miniprogram-ci` 携带 `@babel/traverse < 7.23.2`（GHSA-67hx-6x53-jw92，CRITICAL 级别：处理恶意代码时可执行任意代码）。这个漏洞完全不在 CI 扫描范围内，且 CI 每次显示安全审计通过。

### 3. 巨型文件未被约束

ContentPublish.tsx 已达 1770 行，在 CI 全绿的掩护下持续积累。没有任何 CI check 会阻止更多代码写入这些文件。

### 4. OKR 数据质量不可信

Brain API 中仍有 5 个测试 KR 条目混入 active goals。结合历史记录（曾出现 79.8% 污染率），OKR 数据的可靠性需要主动维护而非被动信任。

---

## 修复计划

### P0（今天）

1. **修复 CI 覆盖率门禁**：在 `apps/dashboard/vitest.config.ts` 中添加 `coverage.thresholds`（建议起步 statements/lines ≥ 50%），与 API 的 65% 标准对齐
2. **修复 Dashboard lint 阈值**：将 `ci-l3-code.yml` 中的 `--max-warnings 79` 改为 ≤ 20；先跑 `npx eslint . --max-warnings 0` 摸清实际警告数
3. **开启 enforce_admins**：GitHub Settings → Branch protection → 勾选 "Include administrators"

### P1（本周）

4. **修复 security audit 范围**：将 CI security job 改为根目录运行 `npm audit --audit-level=high`（去掉 `--omit=dev`），暴露真实漏洞
5. **处理 miniprogram-ci 漏洞**：运行 `npm audit fix --force`，评估 miniprogram-ci 升至 1.3.13 的破坏性影响
6. **为 miniapp 添加 CI**：在 L3 workflow 中添加 miniapp 的 lint 和 build job
7. **清理 Brain API 脏数据**：archive 或删除 5 个"Test KR for select"污染条目

### P2（两周内）

8. **拆分巨型组件**：ContentPublish.tsx（1770 行）、Dashboard.tsx（903 行）拆分为子组件，每个文件不超过 500 行
9. **GeoAI 补充 lint/typecheck**：在 L3 workflow 的 geoai job 中添加 eslint 和 tsc 检查（当前只有 build）
10. **填写 regression-contract**：补充 `core` 和 `golden_paths`，建立端到端合约基线
11. **定义 SLO 基线**：创建 `docs/slo.md`，定义 API uptime、响应时间、错误率的正常阈值
12. **建立 P0 Playbook**：创建标准化事故响应 SOP，包含发现→诊断→升级→恢复→复盘流程
