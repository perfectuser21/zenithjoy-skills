# Repo Audit — zenithjoy 2026-03-29

## 反模式命中（CI 精读）

| 反模式 | 状态 | 说明 |
|--------|------|------|
| admin_bypass | ✅ 命中 | `enforce_admins: false`，管理员可绕过所有 status checks |
| audit_scope_wrong | ✅ 命中 | CI security job 只对 `apps/dashboard` 跑 `npm audit --omit=dev`，未覆盖根目录；根目录有 70 个漏洞（15 high, 40 critical）被完全忽略 |
| no_coverage_gate | ✅ 命中 | dashboard 的 `vitest.config.ts` 有 `--coverage` 但**无** `thresholds`；CI L4 只运行 `npx vitest run --coverage` 无门禁 |
| lint_too_lenient | ✅ 命中 | dashboard: `--max-warnings 79`（远超 20）；API: `--max-warnings 15`（勉强合格） |
| l1_not_on_push | ❌ 未命中 | L1 PR title 检查仅在 PR 触发，符合预期 |
| missing_modules | ✅ 命中 | `apps/miniapp` 和 `apps/geoai` 完全没有 lint/typecheck/test job |
| no_audit_in_ci | ❌ 未命中 | 有 security job，但覆盖范围有问题（见 audit_scope_wrong） |
| no_branch_protect | ❌ 未命中 | 有 required status checks（但 enforce_admins=false） |

**命中 5 个反模式 → 🔴 虚假绿 ❌ CI 整体不可信**

---

## L1 管业务：12/30

| # | 项目 | 分 | 证据 |
|---|------|-----|------|
| 1 | OKR 清晰度 | ⚠️ 3 | Brain API 返回 45 条记录，其中 5 条 "Test KR for select" 仍为 active 状态，污染 OKR 视图；存在重复 area_okr（"Cecelia 基础稳固" 出现两次，"数据闭环/内容生成 KR" 同时有 active 和 archived 版本） |
| 2 | 任务可执行性 | ⚠️ 3 | 近期有实际交付（scraper work_id、coverage threshold、CI L1-L4 分层、miniapp 迁移等），但任务拆解停留在 initiative 级，PR 级拆解不系统 |
| 3 | 进度可见性 | ⚠️ 3 | Dashboard 存在且有内容（ContentData、PublishStats 等页面），但 Brain API OKR 数据污染导致真实进度不可信；Dashboard 近期需要 hotfix 修复登录问题 |
| 4 | 定期复盘 | ⚠️ 3 | `docs/learnings/` 和 `docs/database/` 有 heartbeat 决策记录和 learning 文档；但没有结构化的 retrospective 文档，复盘主要依赖 heartbeat 日报 |
| 5 | 资源成本控制 | ❌ 1 | 无任何 API 调用成本追踪机制；代码中无 token_usage 记录；无 LLM 费用监控 |
| 6 | 战略方向验证 | ⚠️ 3 | `DEFINITION.md` 有明确业务定义（AI 内容运营飞轮），近期迭代方向与战略对齐；但 miniapp 模块的战略定位不明确 |

**L1 小计：12/30**

---

## L2 管代码：18/35

| # | 项目 | 分 | 证据（含反模式命中） |
|---|------|-----|------|
| 7 | CI 有效性 | 🔴 1 | **虚假绿**：4 个 CI gate 全部 passing，但命中 5 个反模式：admin_bypass + audit_scope_wrong + no_coverage_gate(dashboard) + lint_too_lenient(dashboard 79) + missing_modules(miniapp/geoai) |
| 8 | 代码质量 | ⚠️ 3 | TypeScript strict: true（根配置已设置，各 app 继承）；dashboard `--max-warnings 79` 过于宽松；`noUnusedLocals: false` 关闭了有用的检查 |
| 9 | 测试有效性 | ⚠️ 3 | API 有覆盖率门禁（65% thresholds，实测 68%/79%）；dashboard vitest 无 thresholds；miniapp/geoai 无测试；ai-video 模块全部 skip |
| 10 | 依赖安全 | ❌ 1 | 根目录 `npm audit` 发现 **70 个漏洞（1 low, 14 moderate, 15 high, 40 critical）**，包括 terser ReDoS (high) 和 tough-cookie prototype pollution；CI 安全扫描仅覆盖 dashboard 且用 `--omit=dev` |
| 11 | 技术债 | ❌ 1 | 8 个文件超过 500 行：ContentPublish.tsx(1770行)、posts.ts(1044行)、ContentData.tsx(1022行)、Dashboard.tsx(903行)、ContentTypeConfigPage.tsx(799行) 等；TODO/FIXME 仅 4 条，但大文件数量严重超标 |
| 12 | 可观测性 | ⚠️ 3 | API 有 `/health` 端点（返回 `{status: 'ok', timestamp}`）；但使用 `console.log` 而非 winston/pino 结构化日志；无 Sentry 或外部错误上报 |
| 13 | 安全态势 | ⚠️ 3 | `.gitignore` 覆盖 `.env/*.key/*.pem`（合规）；但 `apps/miniapp/miniprogram/pages/ai-features/index.js` 中**硬编码了 Coze API key**（`pat_BSo4wqL0...`）且已提交 git；branch protection `enforce_admins: false` |

**L2 代码小计：18/35**

---

## L2 管运行：16/30

| # | 项目 | 分 | 证据 |
|---|------|-----|------|
| 14 | 可执行性 | ⚠️ 3 | Dashboard build 在 CI 可通过，API /health 可达；但 miniapp 有硬编码 key 且 CI 不检查；主链路端到端未有自动化验证 |
| 15 | 注册表鲜活 | ⚠️ 3 | workflows/ 下有 content-creator、image-gen、platform-data、n8n、jnsy-label 等多个工作流；但部分状态不明，无 liveness 检查机制 |
| 16 | 数据完整性+灾备 | ⚠️ 3 | `docs/database/migrations/` 目录存在；scraper 使用 TimescaleDB；但无明确备份策略文档；历史 heartbeat 中多次出现 OKR 数据污染问题 |
| 17 | 自动化覆盖 | ⚠️ 3 | 发布流程：多平台 publisher 脚本存在（8 平台清单有文档）；scraper 有自动化脚本；但仍有较多步骤需要手动触发（`publish-by-content-id.sh`、`nas-fetch-content.sh` 等） |
| 18 | 闭环率 | ⚠️ 3 | scraper → TimescaleDB → Dashboard 数据链路存在；`metrics.api.ts` 有 daily report API；但数据→分析→选题 的自动闭环证据不充分，分析→下轮内容选题仍依赖人工 |
| 19 | SLO 基线 | ❌ 1 | `DEFINITION.md` 有"响应时间: P0 < 15分钟"但这是事故响应时间，不是服务 SLO；无 uptime 目标、错误率阈值、API P95 响应时间 SLO；无异常触发机制 |

**L2 运行小计：16/30**

---

## L3 管沟通：13/25

| # | 项目 | 分 | 证据 |
|---|------|-----|------|
| 20 | 向上汇报 | ⚠️ 3 | `settings.api.ts` 有 `testFeishuWebhook` 和 `dailyMetrics` cron 配置；`workflows/image-gen/scripts/send-to-feishu.sh` 有飞书发送脚本；但自动日报推送闭环无法从代码确认 |
| 21 | 卡点上报 | ❌ 1 | 无 P0 自动告警机制；卡点上报依赖 heartbeat 手动汇报；无自动告警集成 |
| 22 | 决策提请 | ⚠️ 3 | Brain API decisions 表有记录；历史记录显示 repo-lead 会发 pending_action；但提请机制依赖人工触发 |
| 23 | 横向协调 | ⚠️ 3 | `docs/learnings/` 记录了跨模块决策；多 PR 协作有记录（PR #85-91）；但横向协调主要靠文档而非系统化机制 |
| 24 | 事故响应 | ⚠️ 3 | `DEFINITION.md` 有"响应时间: P0 < 15分钟"；有 SECURITY-VULNERABILITIES.md；heartbeat 报告系统作为事故追踪存在；但无正式 P0 playbook |

**L3 小计：13/25**

---

## 总分：59/120 (49%)

| 层级 | 得分 | 满分 | 百分比 |
|------|------|------|--------|
| L1 管业务 | 12 | 30 | 40% |
| L2 管代码 | 18 | 35 | 51% |
| L2 管运行 | 16 | 30 | 53% |
| L3 管沟通 | 13 | 25 | 52% |
| **总计** | **59** | **120** | **49%** |

---

## 关键发现

### 1. 🔴 虚假绿 CI — 最危险的发现
CI 全部 passing，但实际上：
- **根目录 70 个漏洞（40 critical）完全不在 CI 扫描范围**：安全 job 只扫 `apps/dashboard` 且用 `--omit=dev` 过滤，root 的 `miniprogram-ci`（terser ReDoS）和 `request`（tough-cookie prototype pollution）等严重漏洞被系统性忽略
- **dashboard 测试无覆盖率门禁**：跑了 coverage 但没有 thresholds，覆盖率可以是 0% 也能通过
- **dashboard lint 容忍 79 个警告**：质量标准已松弛到不可信程度
- **miniapp 和 geoai 完全不在 CI 保护范围**：这两个模块的代码可以任意腐烂而 CI 不会感知

### 2. 🔴 硬编码 API Token 已提交 Git
`apps/miniapp/miniprogram/pages/ai-features/index.js` line 38 有明文 Coze Personal Access Token（`pat_BSo4wqL0AH7Fii9IKE9ZGjyntLBdxdtB1UYt7o3MJIWfmYUj9uCAGqJ6zqCfSmDm`），已提交到 git 历史。**此 token 现在对所有 git 历史访问者可见，必须立即吊销。**

### 3. 结构性技术债
8 个文件超 500 行，其中 ContentPublish.tsx 达 1770 行。这意味着这些模块极难被测试和维护，且 CI 对此没有任何约束。

### 4. OKR 数据污染
Brain API 中 5 条 "Test KR for select" 仍为 active 状态，加上重复 area_okr 条目，使得基于 Brain API 的进度报告数据失真。

### 5. admin_bypass 分支保护漏洞
`enforce_admins: false` + `required_approving_review_count: 0` = 管理员可不经任何 CI 检查、不经任何 reviewer 批准直接 push 到 main。分支保护对管理员形同虚设。

---

## 修复计划

### P0（今天必须做）：
1. **吊销并轮换 miniapp Coze API Token**（`pat_BSo4wqL0...`）——已暴露在 git 历史，立即到 Coze 平台吊销
2. **修复 miniapp 硬编码 key**——改用 wx.getStorageSync 用户输入，删除 fallback 硬编码值

### P1（本周）：
3. **修复 CI 安全审计范围**——security job 改为在根目录运行 `npm audit --audit-level=moderate`（不加 `--omit=dev`）
4. **给 dashboard vitest 添加覆盖率门禁**——在 `vitest.config.ts` 添加 thresholds（从 50% 开始）
5. **开启 enforce_admins**——GitHub branch protection 开启管理员也必须经过 CI 检查
6. **降低 dashboard lint --max-warnings**——从 79 逐步降低，目标 ≤ 20
7. **清理 Brain API 测试数据**——将 5 条 "Test KR for select" 改为 archived/deleted

### P2（两周内）：
8. **拆分 >500 行文件**——优先处理 ContentPublish.tsx（1770行）
9. **为 miniapp 和 geoai 添加 CI coverage**——至少添加 lint/typecheck job
10. **定义服务 SLO**——为 API 添加 uptime、P95 响应时间、错误率三个基础 SLO
11. **添加 P0 自动告警**——集成飞书 bot webhook，在 API /health 失败时自动推送

---

## 分数写入确认

脚本执行命令：
```
bash /Users/administrator/.claude-account1/skills/repo-audit/scripts/save-score.sh zenithjoy 59 "虚假绿CI(5反模式命中)+硬编码APIToken已泄露+70个npm漏洞被CI忽略+dashboard无覆盖率门禁"
```

✅ 分数已通过 `save-score.sh` 写入历史记录（见下方执行输出）。
