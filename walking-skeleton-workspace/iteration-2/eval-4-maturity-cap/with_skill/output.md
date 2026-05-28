# 不行，这个请求必须拒绝。

直接说结论：**不能这样干**。把 user_facing path 上的"AI 生成"Feature 一上来就做成 thick（含 prompt 工程 + 风格控制 + A/B），违反 walking-skeleton skill 第 1.5 节 Maturity 表格里写死的纪律。

## 引用规则原文

skill 1.5 节 Maturity 5 阶段表格里有一列叫 **"Feature thickness 上限"**，明确写：

| 阶段 | 进入条件 | Feature thickness 上限 |
|---|---|---|
| `not_started` | 默认 | **thin** |
| `skeleton` | 所有 step 至少 1 个 thin Feature + E2E smoke 全绿 | medium |
| `mvp` | ≥50% Feature → medium + 可面客户演示 | thick |
| `production` | ≥80% Feature → thick + 真实客户在用 | mature |

紧跟着的纪律一句话原文：
> **Feature thickness 不能超过 Journey Maturity 对应上限——否则就是浪费（单 Feature 完美但 Journey 死亡）。**

你这条 user_facing path 现在是 `not_started`（你自己说的，还没有任何 Feature），上限就是 **thin**。直接做 thick 等于跳两级（thin → medium → thick），三级跳级，规则不允许。

而且 5 条铁律里第 4 条写得很死：**"Journey 第一刀只贯穿不加厚 — 6 步 path 第一刀必须 6 个 thin feature 全在"**。你现在连骨架都没立起来就要在某一节肌肉上堆 prompt 工程 + A/B，这是典型的"单 Feature 完美但 Journey 死亡"反模式。

## 正确做法

1. **先把整条 Journey 的所有 step 都挂上 thin Feature**：注册、画像、绑平台、AI 生成、发布、看回执——每一步都来一个最简陋的 thin（AI 生成这一步的 thin = 接 Claude API + 硬编码 prompt 拼画像 + 返回一段文本，1 周内能跑完）。
2. **跑通 E2E smoke 让 Journey 升到 `skeleton`**——这时 thickness 上限才升到 `medium`。
3. **再升到 `mvp`（≥50% Feature → medium + 可面客户演示）**——这时 thickness 上限才到 `thick`。
4. **拿真实用户反馈驱动**决定哪个 Feature 先加厚（铁律 5）。如果用户根本不在乎风格 A/B，那 prompt 工程永远停在 thin 也 OK。

## 为什么这条纪律不能破

你现在做 thick AI 生成（假设花 3 周），其他 5 步还是 0。结果：没有 demo、没有真实用户、prompt 工程是你拍脑袋的方向、A/B 没流量可测。3 周后大概率推翻重来。先 6 个 thin 跑通（也就 1-2 周），拿到第一批真实用户反馈，再决定 AI 生成是不是真的需要 A/B，需要朝哪个方向加厚——这才是 walking skeleton 的本意。
