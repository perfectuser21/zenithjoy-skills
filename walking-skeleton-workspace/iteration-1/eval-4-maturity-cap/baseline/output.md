# 不可以——这违反了 Walking Skeleton 的成熟度封顶原则

## 直接结论

**不可以**。当 user_facing path 还处于 `not_started` 状态（连一个 Feature 都没跑通端到端）时，把"AI 生成"这个 Feature 直接做成 thick（prompt 工程 + 风格控制 + A/B 实验）是典型的过度工程，会让你陷入"局部完美、整体不通"的陷阱。

## 为什么不行

Walking Skeleton 的核心规则是：**单个 Feature 的成熟度，不能超过它所在 path 的整体成熟度太多**。一般经验法则是"成熟度封顶 = path 状态 + 1 档"：

| user_facing path 状态 | 单 Feature 允许的最高成熟度 |
|---|---|
| not_started | thin（最薄能跑通的版本） |
| thin（已有 1 个 Feature 跑通端到端） | thin / 刚好够用 |
| working（多个 Feature 稳定运行） | 可以选关键 Feature 做 thick |
| mature（整条 path 稳定 + 有数据） | thick（带优化、A/B、调优） |

你现在是 `not_started`，封顶就是 **thin**。"AI 生成"必须先做成最薄的版本：写死一个 prompt、不做风格控制、不做 A/B，能从用户输入 → 调 LLM → 返回结果 → 渲染到前端，**端到端跑通一次**就够了。

## 直接做 thick 会出什么问题

1. **集成风险被推迟**：你花 2 周打磨 prompt 和 A/B 框架，结果发现前端拿到结果后渲染有 bug、鉴权链路没打通、计费没接上——这些是真正的风险，应该最先暴露。
2. **A/B 没有数据基础**：A/B 实验需要流量和指标管道。path 还没跑通，连一条真实请求都没有，A/B 框架就是空转。
3. **风格控制是优化项**：在没有用户反馈、没有 baseline 的情况下做风格控制，等于凭感觉调参，后面大概率推倒重来。
4. **沉没成本绑架决策**：thick 实现一旦写下去，团队会舍不得扔，即使发现方向错了也会硬扛。

## 正确做法

**Iteration 1（thin）**：写死 prompt，调通 LLM → 返回 → 前端展示。把整条 user_facing path 从 not_started 推进到 thin。

**Iteration 2（thin → working）**：补齐其他关键 Feature（输入校验、错误处理、计费、限流），让整条 path 能稳定承接真实用户。

**Iteration 3（working → mature）**：这时候再回头给"AI 生成"加 prompt 工程、风格控制、A/B——这时候你有真实数据、有用户反馈、有 baseline，优化才有意义。

## 一句话总结

先让骨架走起来，再去给某根骨头长肌肉。当下应该做的是 **thin 版的 AI 生成**，不是 thick。
