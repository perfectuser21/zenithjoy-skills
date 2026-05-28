# 拦截：本 Sprint 不允许直接调 sprint-planner，必须先走 harness-bridge

打住——按 walking-skeleton 的 **harness-bridge 强制流程**，"直接调 sprint-planner" 是反模式 1，明确禁止。理由很硬：sprint-planner 默认假设 sprint = 多个 feature，没有 Journey / 端到端概念。直接进 planner 的后果就是每个 ws 各自验证通过 → sprint APPROVED，但**端到端从来没人测**。这正是过去几个 sprint "都通过" 但产品端到端跑不通的根因。

在调 sprint-planner **之前**，必须先把下面这几件事弄清楚，否则不开 sprint。

## 1. 你列的 4 个 ws，根本不是一条 Journey

你说的"license 系统 sprint = 后端 API + Dashboard 客户面板 + admin 后台 + CI 部署"——这 4 个 ws 至少跨了 **3 条不同 Journey**，不能塞进一个 sprint：

- **Dashboard 客户面板**（终端客户买 license / 看 license 状态）→ `user_facing` Journey，对应"客户首次成功路径"或"客户 license 续费路径"。
- **admin 后台**（super-admin / 运营人员管理客户 license）→ **独立的 user_facing Journey**，因为管理员是**独立角色**，端到端路径完全不同（登录后台 → 查客户 → 改 license → 看审计）。skill 文档里 `super-admin 后台管理` 明确举例为 Journey 而非 Feature。
- **CI 部署**（commit → 构建 → 上线 → 客户用上）→ `dev_pipeline` 类型 Journey，跟 user_facing 必须分开，不允许混进客户路径。
- **后端 API** 不是独立 Journey，它是上面任意一条 Journey 的"肌肉"，必须挂到具体 Journey 的具体 step 上。

按铁律 5 条之"反模式 3：单 sprint 同时推进多条 Journey"——**一个 sprint 只推进一条 Journey**。所以你这一波至少要拆成 3 个 sprint，独立串行。

## 2. 必须先回答的问题

请先告诉我：

1. **本 Sprint 推进哪一条 Journey？**（客户 license 路径 / admin 运营路径 / license 部署 pipeline，三选一）
2. 这条 Journey 在 Notion 是已有的还是要新建？没有就先 `init journey`，把端到端 step 拆出来（5–10 步）。
3. 选定 Journey 后，本 Sprint 推进的 Feature 清单 + 每个 from→to thickness（如 0→thin、thin→medium）+ 它们各自挂在 Journey 哪一步。

## 3. Feature 0 必须存在，不可省

bridge Step 3 / Step 6 强制：sprint-prd.md 第一个 Feature 必须是 **Feature 0 = Journey 端到端 smoke**，跑 `golden-path-X-smoke.sh` 从 step 1 到本 Sprint 推进的最后一步。Feature 0 是 **gating**——其他 ws 全 PASS、Feature 0 红 = 整 Sprint FAIL。没有 Feature 0 的 sprint-prd 我会打回让 planner 重写，不会进入 contract-proposer。

## 下一步

回答上面 3 个问题，我用 `status ZenithJoy` 把现有 Journey 列出来给你挑，然后按 bridge Step 1–7 把 Journey 上下文 + Feature 0 注入 sprint-planner——再开 sprint。
