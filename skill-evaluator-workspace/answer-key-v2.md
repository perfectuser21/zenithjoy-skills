# 日报skill v1.2-7.7 考试标准答案（修正版 v2，共 14 项）

原 15 项（skill_holistic_review.md，对打补丁前的 v1-2 写）逐项对照 v1.2-7.7 zip 实物验证后修正：
- **原 H2 已在 zip 内修复**（SKILL.md L163 已明确"只问价格不触发收口"），残留形态改列为 H2r。
- **原 M1（四感占比无用法定义）已修复**（SKILL.md L142 已定义"权重非字数比例"），从考卷移除。
- 其余 13 项验证仍然存在。

| # | 缺陷 | 验证位置（v1.2-7.7 zip 内） |
|---|------|---------------------------|
| H1 | eval 规则多处重复且不一致（断言表/覆盖表 2-4 处复制） | SKILL §16.5 / eval-v2-sop / eval-v2-scorecard |
| H2r | 价格矛盾残留：钱总 golden 期望"给价格区间"，与 §11.2/§14/golden-template"未提供不得给量级"冲突 | references/eval-simulation.md L83 vs SKILL L176 |
| H3 | "按客户名读数据库"核心前提无任何数据接口定义，主路径不可执行 | 全包无接口定义；agents/openai.yaml 零 schema |
| H4 | 通过标准依赖"核心项/大部分"未定义概念，不可机械执行 | eval-v2-scorecard §五/§七 |
| M2 | 身份命名三套并存（daily-report-v1-2 / customer-chat-analyzer / 日报skill-v1.1-7.6） | frontmatter / 正文 / openai.yaml |
| M3 | 无 CHANGELOG，补丁无留痕；openai.yaml 版本 stale | 全包 + agents/openai.yaml |
| M4 | eval-run-result.md 9 行空壳，但被当"最近 eval 记录"入口引用 | references/eval-run-result.md |
| M5 | description 偏内部术语堆砌，触发覆盖不全 | SKILL.md frontmatter |
| M6 | "详细版"与"eval/验收"混在同一条路由规则，会给错输出 | SKILL.md L53 |
| M7 | "本月第几周"无定义 | references/data-fetch-rules.md L58 |
| L1 | customer-long-term-profile-template.md 已退化为 13 行废止说明，文件名仍叫 template | references/ |
| L2 | agents/openai.yaml 用途未文档化，与 SKILL 描述会漂移 | agents/ |
| L3 | "字段 11-13 个"与模板实际字段数不符 | references/output-template.md L11 |
| L4 | "本次分析资料范围"格式块与固定公式重复（25 处） | 多文件 |
