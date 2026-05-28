停一下，按 walking-skeleton skill 动作 5 `harness-bridge` 的铁律，**在四问 checklist 没填齐之前，绝对不允许调 sprint-planner**。先把 checklist 贴出来：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Sprint 启动 4 问 checklist（必填）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

□ 1. 本 sprint 推进哪条 Journey？
     名称：______
     Notion URL：______
     当前 Maturity：______（决定 Feature 升级上限）

□ 2. 本 sprint 涉及几个角色？
     1 个角色 → 1 条 Journey 即可
     ≥2 个角色（如客户 + admin）→ 必须拆多个 sprint，每个 1 条 Journey
     CI / 部署属于 dev_pipeline 类型 → 单独的 Journey，不能混进业务 sprint

□ 3. 本 sprint 推进哪些 Feature？（必须按 Journey Step 编号列）
     - Feature A: <名> | Journey Step <N> | thickness <from> → <to>
     - Feature B: <名> | Journey Step <M> | thickness <from> → <to>
     - ...
     说不清楚某 Feature 在哪一步 → 先回去把 Journey 步骤拆清楚

□ 4. Feature 0（端到端 smoke）是什么？
     smoke 路径：______
     验证范围：从 Journey Step 1 跑到 Step <K>（K = 本 sprint 推进的最后一步）
     gating 规则：Feature 0 FAIL = 整 sprint FAIL，不论其他 Feature 状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 拦截直调 sprint-planner 的理由

直接调 sprint-planner 是 `references/harness-bridge.md` 里的**反模式 1**：sprint-prd.md 没有 Journey 上下文，每个 Feature 各自验证通过，但端到端从来没人测——这就是过去 sprint 都"通过"但产品端到端跑不通的根因。所以现在不能调，必须先走 bridge。

## 你给的范围本身就违反铁律

你说的 "4 个 ws：后端 API + Dashboard 客户面板 + admin 后台 + CI 部署" 一眼看下去就是 **3 个不同角色的 Journey 混在一个 sprint 里**，触犯反模式 3"单 sprint 同时推进多条 Journey"：

| ws | 角色 | Journey Type | 该挂的 Journey |
|---|---|---|---|
| 后端 API + Dashboard 客户面板 | 终端客户 | `user_facing` | "客户 license 自助管理路径" |
| admin 后台 | 超级管理员 | `user_facing` | "管理员 license 运营路径"（独立角色 = 独立 Journey） |
| CI 部署 | 开发者 | `dev_pipeline` | "license 系统部署管线"（基建独立 Journey） |

按 SKILL.md 1.1 的判断规则：admin 是独立角色，独立的端到端路径；CI/CD 属于 `dev_pipeline` 类型不能混进 user_facing。**所以这不是 1 个 sprint，是 3 个独立 sprint**，串行或并行都行，但绝不能塞进一个 contract。

## 下一步建议

1. 先调 `status ZenithJoy` 看现在有没有这 3 条 Journey；没有就用 `init journey` 先把骨架建起来（每条都填 E2E Test Path = 那条 Journey 的 golden-path smoke）。
2. 选**一条**先做（建议从客户面板开始，最贴近交付价值），把 4 问 checklist 答完。
3. 重点确认每条 Journey 的 **Feature 0 端到端 smoke 路径**——它是 gating Feature，单 Feature 全 PASS 但 Feature 0 FAIL = 整 sprint FAIL（反模式 2 警告：smoke 不能写成 `echo "done"; exit 0` 这种永远 PASS 的占位）。
4. 4 问填齐 + Feature 0 落地后，再把答案作为前置 prompt 注入 sprint-planner。

请先回答：这 3 条 Journey 哪条优先？以及当前 Maturity（决定 Feature 升级上限，比如 not_started 阶段所有 Feature 只能停在 thin）？
