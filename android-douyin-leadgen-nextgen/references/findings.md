# 0920 实测数据点（供下一 session 直接核对，不用重测）

## 评论打分三轮实测（36 个真实历史标注样本，`entered_final_lead` 为 ground truth）

| 轮次 | 模型/配置 | 一致率 | FN | 备注 |
|---|---|---|---|---|
| 1 | Jev（TypeSafe「System One」，无生产上下文） | 61.1% | 10/21 | 只做schema归一化时表现最好的一轮，但仍不够 |
| 2 | `gpt-5.6-luna-official`（真实模型串 `gpt-5.6-luna-2026-07-09`），喂真实「客户分群」表意向/排除规则 | 55.6% | 16/21 | 加规则反而更保守 |
| 2 | `gpt-5.6-terra-official`，同上下文 | 55.6% | 16/21 | 与 Luna 结果完全一致（非缓存——三次独立调用 reason 文本互不相同） |
| 3 | `gpt-5.6-luna-official` + 少样本校准 | 55.6% | 16/21 | 校准未改善 |

**调用方式**：`https://toapis.com/v1/chat/completions`，复用 `~/.config/openclaw/locate-api.key`（与 vision-locate 共用同一凭据）。

## 根因已查清（0921凌晨追查）：不是模型能力问题，是评分尺度用错了

派了一个只读调查 agent 追查 `entered_final_lead` 真实来源，找到权威源：生产在跑的
`services/phone-adb-controller/sort-comments.js`（首次引入 commit `6a8fb8db`/PR#1819，最近改动
`b17e2fc3`/PR#1869 字段收敛，判定逻辑未变）。真实判定链：

1. `ruleJudge()` 正则规则闸（注释写明"0914 KPI 夜 102 条人工判例提炼"）：GOLD词（问价/报名/求资料）→留A级；
   JUNK_WORDS(引流广告)/同行企业号/同名陷阱→弃；**纯表情/寒暄("哈哈""加油""厉害"等)→也判"留"，C级，
   理由="画像内人群,低意向留档"**
2. 规则判不了的中间地带交给分拣agent(便宜模型)按SOP判定

**关键口径**（L98注释，0914主理人拍板"分拣理念修正"）：`const keep = it.rel === "相关"` ——
**"相关即留档(含C级)，仅同行企业号/广告引流号两类真排除"**。原始设计更严格会把寒暄判"不相关"丢弃，
被主理人当场纠偏为"能看到视频还留言=天然画像内人群，分级不丢弃"。

而昨晚(0920)的三轮评分测试(见上表)全部用的是错误尺度——`strong_intent/weak_intent/peer/irrelevant/spam`
四级分类，`is_lead` 只认 strong_intent。抽样验证：36个真实样本里 `entered_final_lead=true` 的21条中，
只有1条 `intent_grade` 是"强"，其余6条A级+4条B级+**10条C级**（"绝了""幸福瞬间🥰""学AI锁定三个大神..."
这种纯情绪反应/复述内容，压根没有explicit intent）——尺度完全对不上，这才是55-61%的根因，不是模型不行。

### 用正确尺度重测（0921凌晨，同一批36样本，真实API调用）

把评分prompt改成"相关/不相关"二元宽松判定（照抄 ruleJudge() 的真实标准）后重测：

| 管线 | 一致率 | FN | 说明 |
|---|---|---|---|
| 规则闸单独（GOLD/JUNK/CHITCHAT正则，纯代码） | 4/4=100% | 0 | 能直判36条中的4条(11%)，全部判对 |
| `gpt-5.6-terra-official`（新二元宽松口径，喂ruleJudge同款排除规则+8条真实校准示例） | 25/36=69.4% | 4 | 比昨晚55.6%提升13.8点 |
| **规则闸+LLM组合（照抄生产真实架构：规则先判，剩下交模型）** | **28/36=77.8%** | — | 比昨晚最佳的61.1%提升16.7点 |

剩余约22%误差里有几条像是ground truth自身的噪声，不是判定逻辑漏洞：如"我就让我儿子学厨师"
(完全跟AI无关)、"@抖音求真"(纯@人无内容)都被标 `entered_final_lead=true`——怀疑有"首评"标记
或账号级历史信号影响了原始判定，但没有体现在评论文本本身里，我们的评分输入拿不到这个信号。

**结论更新**：评论打分不是不能用，是用错了标准。规则闸+LLM(二元宽松口径)组合能到 77.8%，比昨晚
任何一条路线都好，可以作为下一步迭代的起点，但仍未到能完全自动放行/排除的精度（~1/4误判），
**仍建议保留"待复核"人工兜底**，不要直接替换现有 `push-leads-v2.mjs` 的全量待复核路由——
下一步应该是把这套"规则闸+二元宽松LLM"组合接进 `orchestrator-v2.mjs`，正式测试成"低置信度自动
待复核、高置信度自动通过"的分级方案，而不是继续在prompt措辞上打磨。

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
