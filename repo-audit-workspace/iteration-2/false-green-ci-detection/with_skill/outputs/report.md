# Repo Audit — zenithjoy 2026-03-29

## 反模式命中（CI 精读）

| 反模式 | 状态 | 证据 |
|--------|------|------|
| admin_bypass | 命中 | branch protection `enforcement_level: non_admins`，admin 可绕过全部 L1-L4 CI |
| audit_scope_wrong | 命中 | L3 security job 在 `apps/dashboard` 子目录跑 `npm audit --omit=dev`；根目录 `npm audit` 揭示 70 个漏洞（40 critical），CI 完全看不到 |
| no_coverage_gate | 命中 | Dashboard `vitest.config.ts` 无 `thresholds`，有 `--coverage` 但无门禁，覆盖率降到 0% 也绿 |
| lint_too_lenient | 命中 | Dashboard ESLint `--max-warnings 79`（>20 标准）|
| missing_modules | 部分命中 | miniapp 完全无 CI jobs |
| l1_not_on_push | 未命中 | — |
| no_audit_in_ci | 未命中 | 有 audit job，但 scope 错误 |
| no_branch_protect | 未命中 | protection 已启用但 enforce_admins 关闭 |

**命中反模式：4 个 → 🔴 虚假绿**

---

## L1 管业务：11/30

| # | 项目 | 分 | 证据 |
|---|------|----|------|
| 1 | OKR 清晰度 | 3 | Brain API 45 goals，18 active。但 5 个完全相同的 "Test KR for select [active]" 测试条目污染 OKR（11%）。主线目标清晰 |
| 2 | 任务可执行性 | 3 | 近 20 次 commits 有真实交付（scraper、integration test、CI 分层）。但 Brain tasks 全为"内容流水线"in_progress，未见拆解到 PR 级的工程任务 |
| 3 | 进度可见性 | 3 | Dashboard 已部署（5211），有 Works 列表和数据看板。但无法验证"团队每天用"KR 的真实使用数据 |
| 4 | 定期复盘 | 1 | 190+ 轮 heartbeat 是系统监控日志，非业务复盘。无 sprint retrospective、KR 回顾、业务学习记录 |
| 5 | 资源成本控制 | 1 | Dashboard 有"费用统计"占位符 UI，无实际数据采集或告警逻辑。无 API 成本追踪 |
| 6 | 战略方向验证 | 3 | "AI 一人公司内容自动化"方向在 2026-03 成立，内容流水线持续推进。但多个 KR 历史曾被取消又恢复，战略稳定性存疑 |

---

## L2 管代码：16/35

| # | 项目 | 分 | 证据 |
|---|------|----|----|
| 7 | CI 有效性 | 1 (🔴虚假绿) | 4 层 CI 全绿。但命中 4 反模式：admin_bypass + audit_scope_wrong + no_coverage_gate + lint_too_lenient。真实漏洞 CI 看不到 |
| 8 | 代码质量 | 3 | `tsconfig.base.json` strict=true。ESLint dashboard `--max-warnings 79` 过松（命中 lint_too_lenient）。API `--max-warnings 15` 较严。TODO/FIXME 34 个（可接受）|
| 9 | 测试有效性 | 3 | 18 测试文件 vs 120 源文件（15%，偏低）。API 有 65% 覆盖率门禁。Dashboard 有 `--coverage` 但无 thresholds = 🔴虚假绿门禁 |
| 10 | 依赖安全 | 1 | 根目录 `npm audit`：70 个漏洞（1 low, 14 moderate, 15 high, 40 critical）。terser ReDoS（high）、tough-cookie Prototype Pollution（moderate）。CI 的 audit scope 错误，看不到这些漏洞 |
| 11 | 技术债 | 3 | 大文件：ContentPublish.tsx 1770 行、ContentData.tsx 1022 行、Dashboard.tsx 903 行（均超 500 行）。TODO/FIXME 34 个 |
| 12 | 可观测性 | 3 | API 有 /health 端点（代码已验证）。无 winston/pino 结构化日志（仅 console.log）。无 Sentry。Docker 有 healthcheck |
| 13 | 安全态势 | 1 | Step 2b grep 发现硬编码凭据：(1) services/jnsy-label/app/routers/stats.py:11 + labeling.py:12 硬编码 LABEL_STUDIO_TOKEN；(2) apps/miniapp/miniprogram/pages/ai-features/index.js:38 硬编码 pat_BSo4wq...（Notion PAT）。两个 token 已进 git 历史。直接 ❌ 1，无例外 |

---

## L2 管运行：16/30

| # | 项目 | 分 | 证据 |
|---|------|----|----|
| 14 | 可执行性 | 3 | API /health 端点存在，Docker compose 配置存在。deploy 需手动触发（deploy-hk.sh）。端到端链路无法在审计时验证 |
| 15 | 注册表鲜活 | 3 | Brain API 45 goals / 40 tasks 均 active/in_progress。但 tasks 全为内容流水线主题，5 个测试 KR 仍为 active |
| 16 | 数据完整性+灾备 | 1 | deploy/docker-compose.hk.yml 只有 nginx 容器，无 PostgreSQL。无 pg_dump cron，无备份文档，无任何备份策略 |
| 17 | 自动化覆盖 | 3 | N8N workflow 覆盖内容发布/采集。但 deploy、DB 迁移、内容采集→分析链路需人工触发 |
| 18 | 闭环率 | 3 | 发布端有 8 平台发布器，采集端有 scraper（已关联 work_id），content-output/ 有产出。但采集→分析→选题自动反馈环未验证为全自动运行 |
| 19 | SLO 基线 | 1 | DEFINITION.md 仅有"P0 <15分钟"文字，无量化 SLO（延迟、可用率、发布成功率阈值），无告警阈值配置 |

---

## L3 管沟通：10/25

| # | 项目 | 分 | 证据 |
|---|------|----|------|
| 20 | 向上汇报 | 3 | workflows/image-gen/scripts/send-to-feishu.sh 有飞书发送脚本（AppleScript 操作飞书客户端）。但无自动日报 cron，无每日推送给 Alex 的代码 |
| 21 | 卡点上报 | 1 | 无 P0 主动告警代码。190+ 轮 heartbeat 全靠人工感知系统故障，无 webhook 告警或监控触发器 |
| 22 | 决策提请 | 3 | Brain API pending_actions 机制存在（heartbeat 历史记录有使用证据）。但依赖人工触发（发现问题后手动发），非自动检测 |
| 23 | 横向协调 | 3 | Brain API 40 个 tasks 有分配记录。但历史上大量 assigned_to=null（heartbeat 多轮记录）。分配机制可靠性存疑 |
| 24 | 事故响应 | 3 | DEFINITION.md 有简短故障处理流程（发现→定位→修复→验证→总结）和 P0-P3 分级。无详细 runbook、无联系人列表。有 playbook 但格式不规范 → 3 分 |

---

## 总分：53/120 (44%)

- L1 管业务：11/30 (37%)
- L2 管代码：16/35 (46%)
- L2 管运行：16/30 (53%)
- L3 管沟通：10/25 (40%)

---

## 关键发现

### 1. 🔴 虚假绿：安全审计 CI 是空壳
CI security job 在 apps/dashboard 子目录运行 `npm audit --omit=dev`，根目录 `npm audit` 显示 **70 个漏洞（40 critical）**。CI 永远绿，真实漏洞完全不可见。这是 audit_scope_wrong 反模式的典型案例：看起来有审计，实际上审的是假目标。

### 2. 🔴 虚假绿：Dashboard 测试有覆盖报告但无门禁
L4 CI 跑 `npx vitest run --coverage`，生成覆盖率报告，但 `apps/dashboard/vitest.config.ts` 无 `thresholds`。覆盖率跌到 0% CI 依然绿。与 API（已配置 65% 门禁）形成鲜明对比——同一仓库，两套标准。

### 3. 硬编码凭据已进 git 历史（安全 P0）
两处硬编码凭据在正式提交代码中（非 worktree）：
- `services/jnsy-label/app/routers/stats.py:11` + `labeling.py:12`：Label Studio token `048f955ad4b8e221bf91316955edfe4eb219fade`
- `apps/miniapp/miniprogram/pages/ai-features/index.js:38`：Notion PAT `pat_BSo4wqL0AH7Fii9IKE9ZGjyntLBdxdtB1UYt7o3MJIWfmYUj9uCAGqJ6zqCfSmDm`

token 已进 git 历史，即使现在删除代码也无法消除风险，必须立即在服务端吊销。

### 4. admin_bypass 使全部 CI 门禁对最高权限账号无效
`enforcement_level: non_admins` 让 admin 可直接推 main 绕过 L1-L4 全部检查。整个 CI 保护体系对拥有最高权限的人形同虚设。

### 5. 结构性盲点：DB 无任何备份策略
PostgreSQL（works、platform_links 等业务核心数据）无备份配置、无 pg_dump cron、无云备份。单点故障导致数据永久丢失。

---

## 修复计划

### P0（今天——安全风险）

1. **吊销硬编码凭据（立即执行）**
   - Label Studio：吊销 `048f955ad4b8e221bf91316955edfe4eb219fade`，生成新 token 存入 `~/.credentials/label-studio.env`
   - Notion：吊销 `pat_BSo4wqL0...`，生成新 token
   - 修复 `services/jnsy-label/app/routers/stats.py` + `labeling.py`：改用 `os.environ.get("LABEL_STUDIO_TOKEN")`
   - 修复 `apps/miniapp/miniprogram/pages/ai-features/index.js`：改用环境变量注入

2. **修复 CI 安全审计范围**
   - L3 CI security job 改为根目录运行 `npm audit --audit-level=moderate`（移除 `--omit=dev`，移出子目录）

### P1（本周）

3. **启用 enforce_admins**（GitHub 仓库设置 → Branch Protection → 勾选 "Include administrators"）

4. **Dashboard 覆盖率门禁**（在 `apps/dashboard/vitest.config.ts` 添加 `coverage.thresholds`，建议从 60% 开始）

5. **PostgreSQL 备份策略**（pg_dump 每日 cron 脚本，备份文件推 NAS 或对象存储）

### P2（两周内）

6. 拆分大文件：ContentPublish.tsx (1770行)、ContentData.tsx (1022行)、Dashboard.tsx (903行)

7. 依赖漏洞清理：`npm audit fix`（根目录），评估 40 个 critical 的修复方案

8. SLO 定义：在 DEFINITION.md 添加量化 SLO + 至少 1 个飞书告警触发器

9. OKR 清理：通过 Brain API 将 5 个 "Test KR for select" 设为 archived

10. 结构化日志：API 引入 pino 替换 console.log
