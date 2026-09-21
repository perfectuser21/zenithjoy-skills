# 真实模拟协议（full 模式 Step 5）

## 三配置对照（缺一不可）

| 配置 | 内容 | 为什么要它 |
|------|------|-----------|
| Baseline 0 | 裸模型 + 任务描述 | 地板：不给 skill 模型自己能做到什么 |
| Baseline 1 | 普通模板（一段朴素 prompt）+ 任务 | **反直觉实证：B1 比 B0 更容易诱发编造**——普通模板给了结构却没给红线，模型为填格子而编。没有 B1 就看不到这个风险 |
| Skill Run | 完整 skill + 任务 | 被测对象 |

## 运行形态（两种都要测，如果 skill 有批量线）

- **批量模式**：全量输入一次跑。放大编造（长输出中经济档模型倾向"补偿性给东西"）。
- **独立模式**：每个对象单独请求只带自己的资料。**实证：v4-pro 批量模式编造复发、独立模式 15 客户零编造**。生产形态若是单对象查询，独立模式的结果才是作者真实能拿到的。

## 宿主模型选择

- 评估引擎（造题/评分/汇总）走包月 Claude 无头（`claude -p --model sonnet`，Sonnet 7d 池长期空置），零现金成本。
- 被测宿主按用户指定。**公平性纪律**：别拿旗舰当默认被测模型去对比经济档——按作者实际要部署的模型测，报告里按价位分档下结论。
- 跨模型对比走 toapis，做成可选项，默认关。

## toapis 坑清单（全部实测踩过）

- 凭据：`source ~/.credentials/toapis.env`（TOAPIS_BASE_URL=https://toapis.com/v1）
- **必须用 curl 脚本，python urllib 会被 Cloudflare 拦**（403/503）
- 长任务 524 → 必须走流式（stream=true）
- `max_tokens` 太小会被 reasoning 吃光返回空 content——v4-pro 这类带 reasoning_content 的模型要给足
- 模型可用性以实测为准，`/models` 列表会骗人（v3.2 在列表里但渠道 model_not_found；无 reasoner/R1）
- mini 类模型会幻觉工具调用，prompt 里要写明"你没有任何工具，直接输出文本"
- 计价 = model_ratio × $2/1M 输入 × completion_ratio 输出。参考价：v4-pro $0.43/$0.86 · v4-flash $0.14/$0.29 · gpt-5.4 $0.75/$4.5 · gpt-5.5 $1.5/$9。单轮全套评估历史实测 ≈ $0.4
- 温度对齐：API 侧和 Claude 子代理侧尽量一致，不一致要在方法局限里声明

## 断言消费方式声明

Claude 宿主走"子代理读文件"（渐进披露），API 宿主是"skill 全文塞 system prompt 单轮生成"——两者不等价，Claude 占 harness 优势。报告里必须写清被测配置是哪种，别让读者拿不同消费方式的分数直接互比。
