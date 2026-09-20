# 0920 实测数据点（供下一 session 直接核对，不用重测）

## 评论打分三轮实测（36 个真实历史标注样本，`entered_final_lead` 为 ground truth）

| 轮次 | 模型/配置 | 一致率 | FN | 备注 |
|---|---|---|---|---|
| 1 | Jev（TypeSafe「System One」，无生产上下文） | 61.1% | 10/21 | 只做schema归一化时表现最好的一轮，但仍不够 |
| 2 | `gpt-5.6-luna-official`（真实模型串 `gpt-5.6-luna-2026-07-09`），喂真实「客户分群」表意向/排除规则 | 55.6% | 16/21 | 加规则反而更保守 |
| 2 | `gpt-5.6-terra-official`，同上下文 | 55.6% | 16/21 | 与 Luna 结果完全一致（非缓存——三次独立调用 reason 文本互不相同） |
| 3 | `gpt-5.6-luna-official` + 少样本校准 | 55.6% | 16/21 | 校准未改善 |

**调用方式**：`https://toapis.com/v1/chat/completions`，复用 `~/.config/openclaw/locate-api.key`（与 vision-locate 共用同一凭据）。

**结论**：三条路线都没到能自动放行/自动排除的精度。下一步怀疑方向是原始 `entered_final_lead`
标注口径本身比"只有 strong_intent 才算"更宽松，需要去找原始判定链核实，而不是继续换模型/调prompt。

## ASR 模型

`gemini-3-flash-official`：OpenAI 兼容 `input_audio` content block 可用，真实录音(19.8s)转写连贯准确。
**已知坑**：喂静音/空音频会幻觉出内容，不会老实报"没有语音"——下游必须自己判断录音时长/能量是否正常，
不能依赖模型自报"无语音"。

## Jev 的正确用法边界（0920 实证）

- ✅ **适合**：把不规整的脚本输出归一化成 `status`/`next_action` 这两个语义字段（4 个真实测试用例，
  包括一个把枚举值原样吐出来的畸形样本，Jev 仍正确抽出真实值；一个验证码场景正确区分 blocked vs failed）
- ❌ **不适合**：评论打分这种需要业务判断的任务（见上表，61.1%不达标）
- **判定依据必须是 schema 合法性，不是 Jev 自报的置信度分数**——0920 主理人当场纠偏，第一版
  `orchestrator.mjs` 拿 0.85 置信度阈值当 gate 是错的设计，已重写为 `orchestrator-v2.mjs` 改用
  `protocol.md` 的结构化契约校验。

## protocol.md 契约要点（`agentic-workflow-runtime/references/protocol.md`，Commander protocol v2）

`WORKER_RESULT` 消息硬性字段：
- `schema_version` = 2
- `status` ∈ `{completed, blocked, failed}`（恰好一个词，非自由文本）
- `recommended_next_action` ∈ `{accept, retry, stop, request_approval}`
- `evidence`：`status=completed` 时必须是非空数组，元素为带类型的证据对象
- `metrics`：4 个通用键（全阶段共有）+ 各阶段附加键（闭集，非白名单外自由添加）

`orchestrator-v2.mjs` 的 `validateSchema(stage, candidate)` 就是照这份契约写的纯代码结构校验，
不调用任何 LLM/Jev 做这一步判定——只有归一化环节（把原始日志填成候选 schema）才叫 Jev。

## 账号身份读取（真机 XML 属性顺序，坑）

`account-identity`/`preflight-full` 最初假设 `resource-id="..." text="..."` 顺序，真机 dump 出来
其实是 `text="..." resource-id="..."`（先 text 后 resource-id）。已在 grep 正则里修正，
`scripts/controller-new-commands.patch` 里的版本是修正后的。

CGTN 等认证媒体号主页没有「抖音号」字段——`account-identity` 在这种情况下安全 `die`（`TARGET_ABSENT`），
不会静默返回错误值；`tap-video-author` 过滤器把这种"读不出来"按"未知=不过滤"处理（fail-open 过滤，
fail-safe 命令本身）。
