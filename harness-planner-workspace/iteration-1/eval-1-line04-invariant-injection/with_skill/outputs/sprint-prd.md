# Sprint PRD — Line04 微信客服：高峰期排队安抚

## OKR 对齐

- **对应 KR**：KR2（AI私域线跑通 — 4条私域内容/天，微信发布成功率≥90%）
- **当前进度**：100%
- **本次推进预期**：巩固 Line04「客户私域 AI 接管」的客服体验（高峰期不失联），不改变 KR 数值

## 背景

Line04（客户私域 AI 接管，journey_id=bfeed805-deed-46c3-8624-87f0028101d4）的微信客服 agent 在高峰期会积压待回复消息。客户长时间收不到任何回应会流失。本 sprint 为客服 agent 增加「高峰期排队安抚」行为：队列超阈值时先私聊安抚每位等待客户，再按顺序逐条正常回复。

## Golden Path（核心场景）

系统从 [某租户待回复消息队列长度超过 5 条] → 经过 [先安抚、后逐条回复] → 到达 [每位等待客户先收到安抚语、再收到正常回复]

具体：
1. [触发条件] 某租户待回复消息队列长度超过 5 条（高峰期）
2. [系统处理] 客服 agent 先对每位等待客户私聊发送一条安抚语（例如：消息较多请稍等）
3. [系统处理] 安抚语频控：每位客户每小时最多发一次；1 小时内已发过的客户跳过安抚、直接排队
4. [系统处理] 随后按队列顺序逐条正常回复每位客户
5. [可观测结果] 每位等待客户先收到安抚语（不超频控），随后按顺序收到正常回复

<!-- Response Schema由Proposer在Step 1.1读api_registry后推导，Planner不负责定义技术规范。 -->

## 边界情况

- 队列长度恰好 5 条：不触发安抚（阈值为「超过 5 条」）
- 同一客户 1 小时内遇到两次高峰：第二次不再收到安抚语，仅收到正常回复
- 安抚期间队列继续增长：新进消息按顺序追加到正常回复队列，不重复触发对同一客户的二次安抚
- 群聊消息：不计入触发队列、不发安抚（铁律：不进群）
- 人工已介入的消息：按 NFR「人工介入后AI行为」逐条判断，人工已回的不发正常回复
- 多租户并发高峰：各租户队列独立计数、独立安抚，绝不串（铁律：租户隔离）

## 范围限定

**在范围内**：高峰触发判定（队列>5）、安抚语私聊发送、每客户每小时一次的频控、安抚后按顺序正常回复
**不在范围内**：安抚语文案的中台可配化、队列阈值的动态调参、非微信渠道、客服回复内容本身的质量优化

## 假设

- [ASSUMPTION: PrepPRD 未提供，本 PRD 从 task.payload.thin_prd 推断；安抚语具体文案以「消息较多请稍等」类占位，最终文案由实现方使用现有配置或默认值]
- [ASSUMPTION: 「待回复消息队列」指该租户下所有等待 AI 回复的私聊消息集合，按到达顺序排列]
- [ASSUMPTION: KR 对齐取最接近的 KR2（AI私域线）；Line04 无独立 KR]

## 预期受影响文件

- Line04 微信客服 agent 的消息调度/回复模块（thin_prd 无明确位置词，落点在客服 agent 现有队列处理逻辑内，由 Proposer 按仓库现状锚定）

## NFR 约束

<!-- 来源: decisions 表 category=nfr，PrepPRD 显式值优先 -->
- 超时/延迟: 待定（PrepPRD 未指定）
- 频控: 安抚语每位客户每小时最多发一次（PrepPRD 显式，主源）
- 版本要求: 待定（PrepPRD 未指定，decisions 无值）
- 可观测: 待定（PrepPRD 未指定，decisions 无值）
- 工作开关与时段: 中台可配工作时段窗口 + 工作总开关；开启=纯AI自动回，不开启=AI完全不回——安抚语同样受总开关约束（来源: decisions 副源，journey_feature 级）
- 转人工设置: 中台可配转接人+转接条件；命中条件不由AI答，转指定人（来源: decisions 副源，journey_feature 级）
- 内容红线: 中台提供 Prompt 输入位/文档上传位，定义AI不能回答/不能说的内容（来源: decisions 副源，journey_feature 级）
- 人工介入后AI行为: 按条判断非整会话停手；人工已回的消息AI不回；人工介入过后AI等待窗口拉长至约20-30秒，窗口内人工回了AI跳过该条（来源: decisions 副源，journey_feature 级）

## Invariant 约束（铁律，proposer/evaluator 不得违反）

<!-- 来源: decisions category=invariant，step + journey_feature + area 三源合并去重 -->
- [记忆按租户×联系人隔离] 对话记忆库按 租户×联系人 隔离,绝不串（来源: journey_feature）
- [防假成功] 发送后必须确认真发出,气泡未刷新不得判成功（来源: journey_feature）
- [后台静默发送] 只走后台 UIA;禁前台键鼠全局注入(抢焦点/发错人)（来源: journey_feature）
- [不进群] 只私聊;群一律跳过(读方向/成员结构判定,不只靠名字)（来源: journey_feature）
- [不回自己] 只对【对方发来】的消息回,读最后一条气泡方向;永不回自己/AI发出的（来源: journey_feature）
- [禁止写死环境假设值] 屏幕外坐标/UIA气泡阈值/假设调用方传X/假设.env有Y 等环境假设值禁止写死，要么从环境推导要么真机校准——这类值是接缝，必真验（来源: area）
- [真环境验证才算done] 依赖真机/生产env/真实调用方的【接缝断言】必须在真目标上验证过才算done；未真验的只能标 logic-done-pending，绝不标 done（来源: area）
- [测试默认多租户] 单元/E2E 测试默认种≥2个租户并断言互不串(让隔离漏洞当场暴露)（来源: area）
- [凭据安全] secrets 不硬编码、不进 git、不进日志（来源: area）
- [日志脱敏] 客户隐私/PII/聊天内容不得明文进日志（来源: area）
- [端点鉴权] 每个 API 端点必须有 auth;无鉴权端点不准 ship（来源: area）
- [租户隔离] 碰租户数据的查询/写入必须 scope 到当前租户;跨租户数据绝不混读/混写（来源: area）

## 累积 FR（本 line 已验收行为，本 sprint 不得回退/重复）

<!-- 来源: 本 line 已完成 ability 的 golden_path，按 ability 分组、order_no 排序 -->
- （本 line 暂无历史）

## E2E 验收

> Planner 初稿此区块可留空（只写占位 + 期望验收点的自然语言描述）。最终可执行的 E2E 脚本由 proposer 在 GAN 阶段产出（按 target_environment 选 bash/.ps1 模板，写进 contract-draft.md 的 `## E2E 验收` 区块）。

```bash
# 占位：proposer 将按 target_environment=windows_wechat 填入真实脚本（xian-rog self-hosted，真实微信 4.1.8 已登录环境，.ps1）
# 期望验收点（自然语言）：
# 1. 种 ≥2 个租户，租户A 队列积压 6 条私聊消息（>5 触发），租户B 队列 2 条（不触发）
# 2. 租户A 每位等待客户先收到一条安抚语（真实气泡刷新确认，防假成功），随后按队列顺序收到正常回复
# 3. 租户B 客户不收到任何安抚语，正常逐条回复；两租户数据互不串
# 4. 1 小时内对租户A 再造一次高峰：同批客户不再收到第二条安抚语，只收到正常回复
# 5. 队列中混入群聊消息：群聊不计数、不安抚、不回复
```

## journey_type: agent_remote
## journey_type_reason: Line04 客服 agent 是部署在远端 Windows 真机（xian-rog）的 RPA agent，经 agent 协议派发执行，非 dashboard/engine/brain 本地路径
## target_environment: windows_wechat
## target_environment_reason: 微信 RPA（Path4 个微接管）命中 windows_wechat 规则，E2E 在 xian-rog self-hosted runner 的真实微信已登录环境执行（GHA 无微信会全部假绿）
## journey_id: bfeed805-deed-46c3-8624-87f0028101d4
## step_id: 无（PrepPRD 未提供 Golden Path 锚定，本 task 的 golden_path 表暂无步骤记录，待 Proposer 阶段登记）
