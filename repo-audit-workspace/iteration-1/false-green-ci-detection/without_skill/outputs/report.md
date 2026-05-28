# ZenithJoy Workspace — 主理人审核报告

**审核时间：** 2026-03-29  
**审核人：** Claude (baseline, no skill)  
**Repo：** https://github.com/perfectuser21/zenithjoy-workspace  
**本地路径：** /Users/administrator/perfect21/zenithjoy

---

## 总体评分

| 维度 | 评分 | 说明 |
|------|------|------|
| CI/CD 架构 | 7/10 | 四层门结构完整，存在 false-green 漏洞 |
| 代码质量 | 6/10 | ESLint 警告容忍度过高，大文件问题 |
| 安全 | 5/10 | 两个 .env 文件已提交 git |
| 测试覆盖率 | 5/10 | Dashboard 无阈值，GeoAI/miniapp 无测试 |
| 仓库健康 | 6/10 | 1900+ 孤立分支，无 PR review 要求 |

**综合：6/10**

---

## 1. CI/CD 架构审查

### 1.1 四层 CI 结构（设计良好）

Repo 实现了四层 CI 门：
- L1 Process Gate：PR 标题格式（仅 PR 触发）
- L2 Consistency Gate：TSConfig 继承、Node.js 版本一致性、敏感文件扫描（push + PR）
- L3 Code Gate：Lint、TypeCheck、Build、Security Audit（按模块变更触发）
- L4 Runtime Gate：单元测试 + Coverage（按模块变更触发）

分支保护已启用，四个 Gate 均为 required status checks，禁止 force push 和直接删除。

### 1.2 [严重] False-Green CI 漏洞

L3 和 L4 Gate 均存在"全跳过即通过"漏洞。

分析 ci-l3-code.yml 的 l3-passed 逻辑：当一个 commit 只改动非 apps/ 路径（如 docs/、services/、scripts/），所有 changes.outputs.* 均为 false，FAILED 变量始终不被设为 true，l3-passed 以 exit 0 通过。

实证验证：最近一次 "chore: ignore temp files and agent directories" commit：
- L3：API Lint/Typecheck/GeoAI Build 全部跳过，Gate 仍显示成功
- L4：API Test 跳过，Gate 仍显示成功

任何针对 services/、scripts/、docs/、workflows/ 的修改都不会触发任何代码检查，CI 全绿但实际什么都没验证。

### 1.3 [中] Security Audit 只检查 Dashboard

L3 的 security job 只在 apps/dashboard/ 目录下运行 npm audit，未覆盖 apps/api/。API 的 pg、express、cors 等依赖未纳入安全扫描。

### 1.4 [中] Node.js Actions 弃用警告

所有 workflow 使用 actions/checkout@v4 和 actions/setup-node@v4，将于 2026-06-02 强制切换到 Node.js 24，2026-09-16 移除 Node.js 20。

### 1.5 [低] L3 变更检测未覆盖 services/

services/creator/ 和 services/jnsy-label/ 在 CI 中完全不检测。

---

## 2. 代码质量审查

### 2.1 [中] ESLint 警告容忍度过高

- Dashboard：--max-warnings 79
- API：--max-warnings 15

### 2.2 [中] 大文件问题（违反项目 CLAUDE.md 规范）

| 文件 | 行数 |
|------|------|
| apps/dashboard/src/pages/ContentPublish.tsx | 1770 行 |
| apps/dashboard/src/pages/ContentData.tsx | 1022 行 |
| apps/dashboard/src/pages/Dashboard.tsx | 903 行 |
| apps/dashboard/src/pages/ContentTypeConfigPage.tsx | 799 行 |
| apps/dashboard/src/pages/ContentFactoryPage.tsx | 776 行 |
| apps/dashboard/src/contexts/CeceliaContext.tsx | 602 行 |
| apps/dashboard/src/pages/PublishStats.tsx | 566 行 |

### 2.3 [低] API 存在重复 index 文件

apps/api/src/ 同时存在 index.ts（TypeScript）和 index.js（CommonJS），造成混淆。

### 2.4 [低] console.log 残留

apps/dashboard/src/contexts/CeceliaContext.tsx、AuthContext.tsx、Dashboard.tsx、FeishuLogin.tsx 及 apps/api/src/index.ts、db/connection.ts 均有 console.log。

---

## 3. 安全审查

### 3.1 [严重] 两个 .env 文件已提交 git

**apps/api/.env.test**（已在 HEAD commit）：
- DATABASE_USER=cecelia
- DATABASE_PASSWORD=cecelia

**apps/dashboard/.env.development**（已在 HEAD commit）：
- VITE_SKIP_AUTH=true
- VITE_SUPER_ADMIN_FEISHU_IDS=dev-user-001

L2 敏感文件扫描盲区：L2 使用模式 *.env（匹配 something.env），不匹配 .env.development 或 .env.test，两个文件均绕过 L2 检查。

### 3.2 [中] 分支保护未要求 PR 审查

- required_approving_review_count = 0，无需任何人审查即可合并
- enforce_admins = false
- dismiss_stale_reviews = false

---

## 4. 测试覆盖率审查

### 4.1 [严重] Dashboard 无覆盖率阈值

apps/dashboard/vitest.config.ts 无 coverage.thresholds。95 个 source 文件，仅 12 个 test 文件（约 12.6%）。

对比：apps/api/vitest.config.ts 已配置 65% 阈值。

### 4.2 [高] GeoAI 和 miniapp 完全无测试

apps/geoai/ 和 apps/miniapp/ 无任何测试文件。

### 4.3 [中] Regression Contract 为空

regression-contract.yaml 的 core: [] 和 golden_paths: [] 从 2026-02-04 至今未填充。

### 4.4 [低] API 合约测试记录了已知不一致

apps/api/tests/contract.test.ts 注释记录了前后端字段名不一致：Work.body vs content_text、WorkStatus.ready vs pending、PublishLog.status 枚举不匹配。已知但未修复。

---

## 5. 仓库健康审查

### 5.1 [高] 1900+ 分支积压

git branch -a 显示 1920 个分支，12 个本地分支超过 30 天未活动（2026-02-15 时间戳）。

### 5.2 [中] miniapp 模块未纳入任何 CI

apps/miniapp/ 迁入 monorepo 后（PR #88），L3/L4 变更检测不包含该路径。

### 5.3 [正常] TSConfig 继承结构正确

### 5.4 [正常] 提交历史规范（Conventional Commits 遵循良好）

---

## 优先修复计划

### P0（立即处理）

1. 从 git history 中移除 .env.test 和 .env.development（使用 git filter-repo 或 BFG）
2. 更换 DATABASE_PASSWORD
3. 修正 L2 敏感文件扫描模式，添加 .env.* 匹配规则
4. 修复 L3/L4 false-green 漏洞：将 security audit 移出条件分支，改为无条件运行

### P1（本周内）

5. Dashboard vitest 添加覆盖率阈值（建议从 40% 起步）
6. API security audit 纳入 L3
7. 分支保护：required_approving_review_count 设为至少 1

### P2（两周内）

8. 清理 1900+ 孤立分支，开启 auto-delete head branches
9. 拆分超大文件（ContentPublish.tsx 1770行 优先）
10. miniapp 纳入 CI 变更检测
11. 填充 regression-contract.yaml（至少 3 条 golden path）
12. 删除 apps/api/src/index.js 遗留文件

---

## 关键文件路径

- CI 工作流：/Users/administrator/perfect21/zenithjoy/.github/workflows/
- 安全问题文件（已提交 git）：apps/api/.env.test、apps/dashboard/.env.development
- 覆盖率缺失：apps/dashboard/vitest.config.ts
- 契约漂移：apps/api/tests/contract.test.ts
- 空回归契约：/Users/administrator/perfect21/zenithjoy/regression-contract.yaml
