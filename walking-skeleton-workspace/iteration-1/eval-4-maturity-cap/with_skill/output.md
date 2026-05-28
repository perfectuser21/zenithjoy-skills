# Maturity 上限校验：not_started 时不允许直接做 thick Feature

**结论先说：不行，必须拒绝。**

你这条 user_facing path 当前 Journey Maturity = `not_started`，按 walking-skeleton 方法论的硬纪律，此时挂上去的任何 Feature **上限只能是 `thin`**，不允许越界做 medium / thick / mature。这条规则不是建议、不是偏好，是 skill 第五部分"5 条铁律"里的第 2 条 + 第 4 条，违反了走不下去。

## 为什么 not_started 时 Feature 上限是 thin

回到 1.5 节 Maturity 的 5 阶段定义：

| 阶段 | 进入条件 |
|---|---|
| `not_started` | 默认状态，只有概念无 Feature |
| `skeleton` | **所有 step 至少 1 个 thin Feature 通过 + Journey 的 E2E smoke 全绿** |
| `mvp` | ≥50% Feature 升到 medium + 关键步骤可面客户演示 |
| `production` | ≥80% Feature 是 thick + 错误处理完整 + 真实客户在用 |
| `mature` | 所有核心 Feature mature + 完整监控/回滚/SLA |

注意 `mvp` 的进入条件是"≥50% Feature 升到 medium"——也就是说，**medium Feature 只有在 Journey 至少进了 skeleton 阶段后才合法存在**。同理 thick Feature 是 `production` 阶段的物种，更不该出现在 `not_started` 的 Journey 上。

更关键的是铁律第 4 条："Journey 第一刀只贯穿不加厚"。你现在还没第一刀，端到端骨架根本没贯穿过，就要在某一个关节直接长出 thick 的肌肉——这就是典型的"跳级幻觉"：以为做完一个豪华的 AI 生成模块就离 production 近了，实际上注册、画像、发布、回执这些 step 还是空的，整个路径从来没真跑通过。这种局部豪华、整体断链的状态，是 walking skeleton 方法论最核心要规避的反模式。

## 正确做法：先做 thin AI 生成，让 Journey 升 skeleton

把"AI 生成"先做成合格 thin（参考 1.3 节四个标准）：

- **接 Claude API**，prompt 硬编码拼上一步的画像输出（最丑那种）
- **返回一段文本**就算成功，不做风格控制、不做 A/B、不做 prompt 工程
- **可被 smoke 验证**：`curl /api/generate -d '{"profile":...}'` 拿到非空文本即通过
- **范围 < 1 周**

同时把 Journey 其他 step（注册 / 画像 / 发布 / 回执）也都各挂一个 thin Feature。等所有 step 都有 thin Feature 通过 + E2E smoke 全绿 → Journey 自动升 `skeleton`。

**那"prompt 工程 + 风格控制 + A/B"放哪？** 进 backlog，标注"等 AI 生成 Feature 升 medium 时再做"。加厚的触发条件是真实反馈（铁律第 5 条），不是"我现在想做"。等 skeleton 跑出来、有真实客户用了、知道了痛点是 prompt 不准还是风格不对，那时候再决定加厚顺序，比现在拍脑袋设计 thick 高效得多。

要建 thin 版本就走动作 2 `add feature`，默认 thickness=thin，我可以现在帮你下脚本。
