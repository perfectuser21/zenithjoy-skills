# 第一版"用户填画像诊断"thin Feature 设计

## 先对齐：这是 user_facing Journey 第 3 步的 thin Feature

按 walking-skeleton 纪律，新 Feature **默认 thin**。thin 的目的不是"做完这一步"，而是**让 Journey 这一步从"完全没有"变成"端到端贯穿但极其简陋"**，让骨架先通。所以下面这版必须同时满足 4 条 thin 标准：可被 smoke 验证 / 不依赖未做 Feature / 明确允许丑 / 范围 < 1 周。

---

## 做什么（Do）

1. **3 个字段，仅此而已**：`行业`（单行文本）、`目标受众`（单行文本）、`内容风格`（单行文本或 3 选 1 单选）。够下游第 5 步 AI 生成拼 prompt 用即可。
2. **一个最丑的表单页**：复用 Dashboard 已有的页面布局/通用 Input 组件，不做自定义样式，不做响应式优化，不做暗色模式适配。Submit 按钮一个，标题一行，结束。
3. **存进 DB 一张表**：`user_profiles(user_id, industry, audience, style, created_at)`，单条 upsert by user_id。没有版本历史，没有草稿，没有审计字段。
4. **happy path 提交成功后跳到第 4 步**：哪怕第 4 步是占位页都行，但路径必须接通（这是骨架"贯穿"的关键）。
5. **写一个 smoke 脚本** `.github/workflows/scripts/smoke/profile-step3-smoke.sh`：用 curl 模拟登录 → POST 画像 → 查 DB 验证写入 → assert 跳转 URL 正确。≥5 行实质内容，CI 必须能跑通。

## 不做什么（Don't）

1. **不做字段校验**：空提交、超长字符串、特殊字符 — 全部不管，崩了就崩了，happy path 跑通就行。
2. **不做错误处理**：API 500、网络断开、DB 写失败 — **try/catch 一个不写**，不显示错误提示。错误处理是 medium 才做的事。
3. **不做 UI 美化**：无图标、无插画、无配色调优、无 loading 动效、无 empty state。"难看到工程师本能想优化"才是合格 thin。
4. **不做 AI 推荐字段**、不做行业下拉枚举、不做受众多选、不做风格预览。这些是 medium/thick 的肌肉。
5. **不做历史记录 / 重新填 / 编辑入口**：第一版只允许填 1 次，再次进入页面直接显示已填值（甚至可以直接跳过）。
6. **不写 unit test 边界 case**：1 个 happy path smoke 就是全部测试预算。

---

## 验收标准（一句话）

`bash .github/workflows/scripts/smoke/profile-step3-smoke.sh` 退出码 0，DB 里能查到这条 profile，浏览器手测能从第 2 步走到第 4 步占位页。**仅此**。任何超出这条线的工作都不属于本 thin Feature，留给真实用户反馈触发的 thicken。

工作量预估：**1.5–2 天**，远小于 1 周上限，符合 thin 范围。
