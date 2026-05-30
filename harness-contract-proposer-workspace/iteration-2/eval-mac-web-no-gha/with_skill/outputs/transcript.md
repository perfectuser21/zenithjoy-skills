# Eval Transcript — harness-contract-proposer（mac_web，无 GHA）

**Skill 版本**: harness-contract-proposer v8.2.0
**日期**: 2026-05-30
**目标环境**: mac_web（Playwright 本地，localhost:5173/5174）
**journey_type**: user_facing
**任务描述**: ZenithJoy Dashboard 登录页面交互验收合同

---

## Step 1: 读取 PRD

本 eval 无正式 sprint-prd.md；从用户 task prompt 提取需求：

- 用邮箱密码登录成功
- 看到 Dashboard 首页
- 退出后重新登录能正常工作
- target_environment: mac_web

**代码探索路径**:

1. 读取 SKILL.md — 确认 mac_web 模板（Playwright localhost:5174，storageState: undefined，截图三段，模式A+B两层验证架构）
2. 探索 `apps/dashboard/e2e/` — 已有 walking-skeleton-1.spec.ts，确认 `e2e/` 目录位置 + 现有 Playwright 模式（page.route mock API）
3. 读取 `apps/dashboard/playwright.config.ts` — baseURL=http://localhost:5173，testDir=./e2e，timeout=30s
4. 读取 `apps/dashboard/src/pages/SignIn.tsx` — 登录页入口：`#si-email` / `#si-password` input id，form onSubmit → signInEmail API，成功后 navigate('/')，错误展示 `error` state（red 样式）
5. 读取 `apps/dashboard/src/api/better-auth.api.ts` — 端点：POST /api/auth/sign-in/email，GET /api/auth/get-session，POST /api/auth/sign-out；AuthResult = { user: { id, email, name }, token }
6. 读取 `apps/dashboard/src/contexts/AuthContext.tsx` — login() 函数写 cookie + state；logout() 清 cookie + signOut()；isAuthenticated = !!user && !!token；`VITE_SKIP_AUTH=true` 绕过登录（E2E 需避开此模式）
7. 读取 `apps/dashboard/src/App.tsx` — 未认证时渲染 SignIn（不是 redirect，是条件渲染）；PUBLIC_AUTH_PATHS=['/login','/signup','/forgot-password']；退出确认弹窗 showLogoutConfirm → confirmLogout()
8. 读取 `apps/dashboard/src/pages/Dashboard.tsx` — 首页显示 `{greeting.greeting}，{user?.name}`（h1 标题）

**journey_type 推断**: user_facing（Dashboard UI 交互，Playwright 真实浏览器验证）

---

## Step 2: Golden Path 设计

**Golden Path**:
```
[未认证访问 /] → [SignIn 页显示] → [填邮箱密码提交] → [API mock 返回成功] 
→ [Dashboard 首页，user?.name 可见] → [点退出+确认] → [SignIn 页重新出现] 
→ [二次填邮箱密码提交] → [Dashboard 首页再次可见]
```

**关键技术决策**:

1. **Playwright mock vs 真实后端**: mac_web eval 环境下真实后端可能未启动，采用 `page.route()` mock `/api/auth/sign-in/email`、`/api/auth/get-session`、`/api/auth/sign-out`，与 walking-skeleton-1.spec.ts 模式一致
2. **sessionActive 动态切换**: 通过监听 response 事件，sign-in 200 后置 sessionActive=true，sign-out 后置 false，保证 getSession() mock 与登录态同步
3. **退出确认弹窗处理**: App.tsx 有 showLogoutConfirm 弹窗，spec 用 `isVisible().catch()` 软检查是否需要二次确认
4. **input id 定位**: SignIn.tsx 使用 `htmlFor="si-email"` / `htmlFor="si-password"`，Playwright 用 `#si-email`/`#si-password` 直接定位（精确且稳定）
5. **Dashboard 用户名断言**: Dashboard.tsx 的 h1 内容为 `{greeting}，{user?.name}`，使用 `getByText(TEST_USER.name)` + `getByRole('heading', {level:1}).toContainText(name)` 双重断言

**两层验证架构检查（skill v7.8 要求）**:

- 模式 A（evaluator 逐 ws）: 4 条 [BEHAVIOR] curl/manual:bash 命令，覆盖登录成功schema/session持久/错误密码/退出重定向
- 模式 B（final-e2e）: 2 条 [BEHAVIOR:E2E] Playwright spec，覆盖完整登录路径 + 退出重新登录闭环
- 截图 DoD: 5 张截图（01-initial / 02-action / 03-result / 04-logout / 05-relogin）

---

## Step 2b: contract-dod.md 自查结果

| 检查项 | 结果 |
|---|---|
| PRD Response Schema 字段 | 不适用（UI 交互无 JSON Schema 合同） |
| BEHAVIOR 数量 ≥ 4 | ✅ 4 条 [BEHAVIOR] + 2 条 [BEHAVIOR:E2E] |
| 假绿检查（代码未实现时是否 FAIL） | ✅ 所有 manual:bash 命令在 API 未注册时返回非 0 exit |
| 禁用字段反向检查 | 不适用 |
| 来源标注（FROM_PRD / AI_ADDED） | ✅ 全部 Step 标注来源 |
| 错误路径覆盖 | ✅ Test 4：错误密码 → 401 → 登录页显示红色错误提示 |

---

## 关键文件路径

- **登录页**: `apps/dashboard/src/pages/SignIn.tsx`
- **Auth API**: `apps/dashboard/src/api/better-auth.api.ts`
- **Auth Context**: `apps/dashboard/src/contexts/AuthContext.tsx`
- **Dashboard 首页**: `apps/dashboard/src/pages/Dashboard.tsx`
- **App 路由**: `apps/dashboard/src/App.tsx`（PUBLIC_AUTH_PATHS, showLogoutConfirm）
- **Playwright config**: `apps/dashboard/playwright.config.ts`（baseURL=localhost:5173）
- **生成 spec 目标路径**: `apps/dashboard/e2e/login-interaction.spec.ts`

---

## GAN Round 1 Verdict

**proposer 自评**:

| 维度 | 分数 | 理由 |
|---|---|---|
| Golden Path 覆盖完整性 | 9/10 | 覆盖首次登录/退出/重新登录/错误路径四场景；扣 1 分因无真实后端 E2E 测试 |
| 验证命令防造假性 | 9/10 | Playwright mock 动态切换 sessionActive，防止历史 session 污染；模式 A curl 含 SKIP 出口减少误报 |
| 来源标注完整性 | 10/10 | 所有 Step 均有 FROM_PRD / AI_ADDED 标注 |
| BEHAVIOR 数量 | 10/10 | 6 条（4 模式A + 2 模式B），> 4 条阈值 |
| 截图 DoD | 10/10 | 5 张截图，含期望描述 |
| schema 字段覆盖 | 不适用 | UI sprint 无 Response Schema |

**建议 Reviewer 重点审查**:
1. sessionActive 动态切换逻辑是否覆盖所有 session 状态转换
2. 模式 A BEHAVIOR 中 `SKIP_NO_BACKEND` 出口是否可能被用于逃避验证
3. 退出确认弹窗处理是否足够健壮（软检查 isVisible catch 模式）
