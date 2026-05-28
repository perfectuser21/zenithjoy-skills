# 画像诊断 Step 3 — 第一版 thin Feature 设计

按 walking-skeleton thin Feature 4 条铁律（可被 smoke 验证 / 不依赖未做 Feature / 明确允许丑 / < 1 周工作量）来设计。这是 user_facing Path 第 3 步的"端到端贯穿但极其简陋"版本。

---

## 做什么（thin 范围内）

1. **3 个字段，就 3 个**（不要 4 个，不要 5 个）：
   - `行业`：text input，用户随便填（"美妆"、"理财"、"健身"等）
   - `目标受众`：text input，一句话描述（"30 岁宝妈"、"刚工作的程序员"）
   - `内容风格`：text input 或 3 个 radio（"专业"、"亲和"、"犀利"），二选一即可，不要做下拉
2. **一个表单页面**，路由 `/profile/setup`，复用 Dashboard 现有布局/组件库，不要单独排版
3. **存进 DB**：新建一张表 `user_profile`，字段 `user_id / industry / audience / style / created_at`，没有 update 接口（thin 只支持 1 次写入）
4. **存完跳到 Step 4**：写完 redirect 到下一步路径即可，不要任何"诊断结果展示"
5. **Smoke 验证**：写一个 `.github/workflows/scripts/smoke/profile-setup-smoke.sh`，用 curl 走完"登录 → POST /api/profile → SELECT user_profile WHERE user_id=X 验证 3 字段非空 → 返回 200"，5 行以上实质内容

---

## 不做什么（这些都是 medium / thick 才碰）

1. **不做表单校验**：industry 留空也让它过；不做长度限制、不做格式校验、不做 required 提示
2. **不做错误处理**：DB 写失败就让它崩，不 try/catch、不 toast、不重试；happy path 跑通即可
3. **不做 AI 推荐 / 自动诊断**：不要"根据行业推荐受众"、不要"AI 帮你写画像"——那是后续 thick 版本
4. **不做美化 UI**：不自定义组件、不画图标、不做 hover 动效、不做响应式断点；input + button 即可
5. **不做编辑 / 多次填写**：用户填完就锁，第二次进来直接读已存的 — 不做 PUT、不做 history、不做版本
6. **不做画像预览 / 总结卡片**：不要"你的画像是 XXX"展示页
7. **不做字段联动**：选了"美妆"不联动受众选项，3 个字段全独立
8. **不做埋点 / 监控 / A/B**：进 thick / mature 才加
9. **不做 unit test 边界情况**：1 个 happy path smoke 就够，不要 edge case test
10. **不做"待 AI 模块就绪"的等待**：Step 4（AI 生成）此时哪怕完全没做，画像表单也要能独立写完跑通——这就是 walking skeleton 的纪律：每段独立薄但端到端通

---

## 验收（Feature 0 / smoke 必须绿）

```
bash .github/workflows/scripts/smoke/profile-setup-smoke.sh
# 期望：登录 → POST 3 字段 → DB 有记录 → 跳转 Step 4 路由 → exit 0
```

smoke 红 = 这个 thin Feature 没完成，不论 UI 多漂亮。范围控制在 3-5 天，超 1 周说明你又在偷偷做 medium。
