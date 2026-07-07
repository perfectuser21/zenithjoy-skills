# 最近 Eval 记录

## 2026-07-07 小型回归（15 样本 9 层级，v1.1→v1.2 两轮）
- Claude Fable 5 × v1.2：通过，断言 11/11，核心四维 60/60。
- GPT-5.4 × v1.2：通过，断言 11/11，核心四维 56/60。
- DeepSeek v4-pro × v1.2（H2 修复后）：部分通过，核心四维 57/60，编造 0。
- 硬结论：skill 消灭 Baseline 的编造硬伤（DeepSeek 两次 Baseline1 均编造价格/案例，套 skill 后清零）；结构件（资料范围/两层日报/变更记录）为 Skill Run 独占。
- 完整报告：https://docs.zenjoymedia.media/daily-report-skill-eval-0707/
