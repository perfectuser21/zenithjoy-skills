## [2026-07-14] harness-contract-proposer 9.10.0 + harness-contract-reviewer 9.5.0 + harness-controller 2.5.0 — 真实链路四硬规则（handoff 0714 刀2）
**症状**: Contract 断言 ≠ 生产现实——07120952-line02-content-judgment-gate 合同 8 条 BEHAVIOR 里 5 处外部调用全用 force_result/force_timeout/假图顶替，没有一条真调 Gemini → 模型下线(#1269)/API 格式错(#1271)全漏过；DoD 用 body 传 tenant_id，真实 Android agent 发 x-agent-id header，测的永远绿、真的从没人碰(#1267)；windows_wechat 通道存在但 #1256 的 sprint 没路由过去，合并后真机爆 5 个致命 bug。
**根因**: 合同阶段对"真实调用方 shape / 第三方真调 / mock 豁免透明化 / 环境路由"四件事零强制，pipeline 的"完成"定义到 evaluator PASS 为止照不到生产现实。
**修改**: ①proposer 新增「真实链路四硬规则」节+自查 checklist 第 8 条：规则A 真实调用方请求 shape 段（DoD 认证字段与生产调用方逐字段一致）/ 规则B 第三方至少真调一次（真 key 真请求真响应校验）/ 规则C mock 豁免显式登记（## 未覆盖真实链路清单）/ 规则D target_environment 强制路由（微信 RPA 必 windows_wechat，Android 通道未落地前真机段必入清单）；②reviewer Golden Path 覆盖审查新增第 14-17 条逐规则打回判据 + 第 6 维领域清单补两行；③controller Step 3/Step 7 把未覆盖清单原样转呈 PR 描述与最终报告，禁止静默。

## [2026-07-13] harness-generator 7.8.0 + harness-contract-proposer 9.9.0 — updated
**症状**: Generator 开发 RPA 代码时盲写——容器内 vitest 绿≠真机能跑,微信 UIA/几何类改动反复真机炸、来回修二十几轮;合同层"真机真收真回"断言没有统一可执行 oracle,evaluator 无法机检。
**根因**: RPA 快验通道(cecelia #3839/#3843 + zenithjoy-workspace #1270/#1272,已上生产并真机验收)修好了路,但 proposer/generator skill 一个字没提——通道存在与否 Generator 不知情,"不盲写"靠人记得而非系统保证。
**修改**: ①proposer 领域验证规则新增「RPA 快验通道 dev-verify」小节:windows_wechat 等真机 RPA 类合同至少一条 [BEHAVIOR] 必须写成快验通道回执断言(exit_code=0+stdout 领域内容,含防作弊注记);②generator 新增 Step 5.5:碰 RPA 执行路径的 sprint 在 push 前必须经 POST /api/brain/rpa/dev-verify 真机自验(RPA 快验通道纪律),回执贴进 Test Evidence。

## [2026-07-12] line-report v1.0.0 — created（按 Line 维度的经营日报/周报/月报）

**症状**: 系统只有垂直领域报告（daily-report=Line04 客户销售复盘、ci-patrol=CI 健康巡检），没有跨 Line 的经营视角报告——主理人无法回答"每条 Line 今天/这周/这个月完成了多少任务、做了多少决策、和上一周期比怎么样"（用户 2026-07-12 提出，/plan 判 Initiative）。
**根因**: Brain 里数据齐全（tasks/decisions/journeys），但缺聚合层：①Line=journey 的映射只存在于 Memory；②tasks 列表 API 不带 status 过滤时缺 payload/completed_at 字段且截断在旧数据；③约 3/4 completed 任务没盖 completed_at、decisions 无硬归属字段——没有一个 skill 把这些坑封装成可复现的取数+归属纪律。
**修改**: 新建 line-report skill：Step1 取数脚本（因 repo 政策 .py 走 /dev，脚本以 markdown 内联块存于 references/fetch-script.md，运行时落 scratchpad；带 status 过滤取全字段、updated_at 兜底盖章缺失并计数、smoke/deprecated journey 排除、Asia/Shanghai 自然日/周/月窗口+等长环比）→ Step2 语义归属补齐（硬字段优先，推断必须标注，禁止静默丢弃）→ Step3 模板输出（总览表/分线明细/未归属/数据口径四段）。附 references/line-registry.md（Line 编号↔journey 映射+归属关键词）、report-template.md、无头模式（[LINE_REPORT] 定时触发）。
**eval**: 2 用例（今日全线日报、Line2+4 周报）× with/without 对照：with-skill 10/10 (100%)，baseline 83.3%（漏未归属节+口径未披露 completed_at 缺章导致完成数低估），with-skill 平均快 177s。

## [2026-07-12] golden-path-controller / golden-path-proposer / golden-path-reviewer v1.0.0 — created（GP loop T3：AI 自提 Golden Path 提案三件套）

**症状**: 「AI 自提 Golden Path」模式已定稿立项（cecelia decisions cb6be3f6/b416bfb3，架构 docs/architecture/2026-07-12-golden-path-mode），但三镜头对抗流程只在朋友圈试点会话里手工编排过一次，未沉淀成 skill——`golden_path_proposal` task_type（T2 接线）派发后无 controller 可选。
**根因**: 试点是会话内手工编排，提案/对抗/收敛/demo/回写各环节的纪律（判级规则、REFUTE 反驳权、findings_log 归档、无 MAX_ROUNDS）只存在于记忆和 scratchpad。
**修改**: 新建三个 skill：①golden-path-controller——复制 harness-controller 2.1.0 横切纪律（append-only 台账/phase-event 自报/文件接力脚本 vendored/四态出口/Step 0 装载恢复/收尾 tmux 自杀），Step 主线替换为 探索+判级→提案→镜头分级扇出对抗（内部小改 1v1；碰真机/客户/钱三镜头）→收敛→HTML demo（docs-center 发布）→PATCH golden_paths converged+findings_log（含 REFUTED 条目及归属，只存不算分）；②golden-path-proposer——产物契约=提案文档（现状标注必须引用代码证据/Gate 前置/验收断言/判定点登记表），修订轮逐条核销或带证据 REFUTE；③golden-path-reviewer——沿用 rubric+VERDICT 结构，GP 专属 5 维（现状真实性/路径完整/断言可验证/判定点完备/风险与门），镜头参数化 LENS=tech/product/risk/solo，收敛轮兼裁 REFUTE。朋友圈试点 v2.1 提案终稿从 session scratchpad 抢救入 repo 作 golden 样例（golden-path-proposer/examples/moments-golden-path-v2.md）。无 MAX_ROUNDS 纪律保持（DoD N3）。
**eval**: 三个 skill 触发词与 harness-* 系列有区分度（golden path 提案/GP 对抗/镜头审查 vs 合同/GAN/sprint），lint 跨 skill 相似度检测通过；主要触发方=Brain relay loadSkill 按 task_type 机械选择，非语义触发，recall 以接线测试（cecelia T2 的 F2 断言）为准。

## [2026-07-11] engine-pr-watchdog v3.3.0 + harness-controller v2.1.0 — 收尾自杀式 tmux 关窗

**症状**: 有头派发的 tmux 会话跑完任务（handoff 写好 + Brain task status=completed）后不会自己关掉所在的 tmux 窗口，全靠控制会话手动 `send-keys /exit` + `tmux kill-session` 才能收尾。2026-07-08/09 派发的 T2/T3/T4 三个任务就因为控制会话没盯到底，空转了两天没人关。
**根因**: /dev 路径 A/B 终态（engine-pr-watchdog Step 5.5 写完 handoff 之后）与路径 C 终态（harness-controller Step 7 report）都只负责把工作状态收尾干净，从未处理"自己所在的 tmux 会话该由谁关掉"，这个动作此前只存在于控制会话的人工习惯里，没有机器化。
**修改**: 两个 skill 的收尾流程真正最后一步各加一段 bash：检测 `$TMUX` 是否非空 → `tmux display-message -p '#S'` 读自己会话名 → 用 `(sleep 2 && tmux kill-session -t "$SESSION_NAME") & disown` 延迟后台自杀（避免截断尚未输出完的收尾信息）→ 读不到会话名或 tmux 不存在则降级为 echo 提示，不阻塞收尾判定；非 tmux 环境直接跳过。engine-pr-watchdog 新增 Step 5.6，harness-controller 在 Step 7 末尾原地追加。

## [2026-07-11] harness-controller v2.0.0 — 重写（自我进化 P3→P5 试点首刀）

**背景**: skill 分层自我进化蓝图的 P3→P5 试点：controller 从 1.0.0 到 1.9.0 共 9 版全是踩坑打补丁式修订，正文里散落大量历史事故叙事（N4/run4/#3540 实证……），横切纪律（台账 / 进度上报 / phase-event / 文件接力）分散在四处，阅读时序与执行时序脱节。
**修改**: 整体重写重组——①新增「横切纪律」独立一节（A 台账+进度上报 / B phase-event 自报 / C 文件接力），各 Step 只引用不重复；②Step 0 拆出 0.3 前台点火防护 / 0.4 恢复规则子节；③Step 1 验收清单从"两段+四项扩展"合并为五项同权清单；④历史事故叙事压缩为短引用（事件号保留）。
**不变量**: 操作规则零新增零删除；13 个 bash 块原样保留；全部 API 契约字符串（relay-runs / phase-event / judge / staging-e2e / skill-relay）原样保留；check-brain-contract.sh 全过。
**流程**: 走 rewrite/* 分支（decision e6c57e2f，非 cp-* 不 auto-merge），人工 review diff 批准。

## [2026-07-11] harness-controller v1.9.0 — Step 4 补 evaluate_verdict 上报
- 症状：initiative_runs.evaluate_verdict 全 NULL——controller 只在 Step 7 终局发 judge 的 verdict，evaluator 裁决只活在台账文本里，机器不可读，skill 自我进化没有基准线。
- 根因：cecelia#3754 前写侧根本不接这个字段；写侧接住后 controller 没有发送动作。
- 修改：Step 4 evaluator 出裁决（含 fix loop 每轮重评）后立刻 best-effort PATCH relay-runs 带 evaluate_verdict（PASS/FAIL/FIXED 原样发，Brain 侧归一+COALESCE 覆盖）；Step 7 注明不必重发。

## [2026-07-11] line-strategist v1.1.0 手册阅读纪律 + 首次入库（skill 分层配套）
- 症状：line-strategist 目录一直是未跟踪状态（不在 repo 里但已被 sync-skills-snapshot.sh 当 SSOT 源），且军师没有"读哪层手册"的纪律。
- 修改：①目录首次正式入库（SKILL.md + evals）；②frontmatter 补 version；③Step 1 末尾加「手册阅读纪律」——只读操作层（line 作战手册 + 全局操作 skill），不读台账层（Notion Notes [LineXX][台账]/learnings/历史 handoff）。

## [2026-07-10] 九要素 T5：判定点写库通电（harness-contract-reviewer v9.4.0 / harness-contract-proposer v9.8.0 / dev v21.8.0）
**症状**: 判定点登记表模板 07-07 已进 proposer(9.6.0)/reviewer(9.3.0) 合同层，但 `decisions category=judgment` 至今 0 条——登记表写在合同 markdown 里就死在合同里，账本保鲜守卫（T1）的「判定点活性」指标（近 30 天新增 judgment 条数，0 = 学习回路断电告警）没有任何数据源；/dev 的对抗深挖与 PrepPRD 完全没有判定点概念，e035dad8 第②条「误判后果严重的判定点升拍板点请教用户」从未落地。
**根因**: 模板刀只落了"写进合同"，没落"写进库"——缺写入方（谁在什么时机把登记表行变成 judgment 记录）与 /dev 侧入口（拍板点升级 + PrepPRD 段）。
**修改**: ①reviewer 9.4.0：Step 5 APPROVED 后新增逐行解析合同判定点登记表 → POST /api/brain/strategic-decisions category=judgment（跳过表头/示例/N-A，失败只 WARN）；②proposer 9.8.0：登记表加机器可解析约定（行自含语义/示例行前缀/⚠️ 严重后果标记 + judgment-pending-user notes 约定）；③dev 21.8.0：综合呈现两流改三流（判定点流，严重后果升拍板点）+ 大功能 PrepPRD 加判定点登记表段 + 确认后路径 A/B 写 judgment（路径 C 由 reviewer 统一写不重复）。E2E：真实合同样例跑 Step 5 解析脚本，判定点行真实落库 category=judgment。

## [2026-07-10] wechat-cs-troubleshooting v2.0.0 瘦身 + 新增 windows-agent-diagnostics v1.0.0（skill 分层 P0）
- 症状：wechat-cs-troubleshooting 长到 30KB，约六成是历史台账（PR 号/实证时间线/自省记录），操作层被淹没，"活台账"模式让 skill 无限增生。
- 根因：教训记录与操作手册混在同一层，缺少"台账进 Notion Notes、正文只读、攒批定期重写"的分层纪律（决策见 memory handoff_skill_layering_self_evolution_0710）。
- 修改：①§1 已解决全录/§2 实证细节/§4.5 守卫架构/§5 memory 索引迁 Notion Notes（[Line04][台账] 前缀 3 条，Type=Learning，已验证 15 个关键标识可检索）；②skill 瘦身为纯操作层（关键事实+已解决速查表+未解决薄清单+诊断法+起手式），frontmatter 声明"新教训写 Notes 不写回本文件"；③跨线通用诊断通道（session0/1 边界、schtasks、日志编码、截图 ground truth 铁律）抽出为第一个全局 skill windows-agent-diagnostics。

## [2026-07-10] harness-report — updated（九要素 T11：Step 8 learning 模板修真 + 接通 learnings 数据管道）
**症状**: Step 8 用 heredoc 静态模板生成 learning.md：四类目全是「（无 / 填写…）」占位符，「下次预防清单」三条每次一模一样（硬编码文本非真实总结）；且只写 git 文件从不调 Brain API——harness 产出的结构化复盘永远进不了 learnings 表（T9/T10 修好的那条数据管道）。
**根因**: 模板填充式生成没有强制 AI 回顾本次 sprint 真实记录，占位符照样能通过「learning.md 存在」的出口核验；DB 写入步骤从未设计过。
**修改**: harness-report 6.4.0 → 6.5.0 — Step 8 改为 AI 回顾台账/GAN 轮次/fix 记录/CI 往返后亲自撰写；Step 8c 运行时占位符守卫（命中 → DONE_WITH_CONCERNS）；Step 8e 原子条目 POST /api/brain/learnings-received（必带 task_id 挂谱系，issues_found 故意不传防多余 fix task）；Step 8f capture_atoms 探测式 best-effort（T10 入口落地后自愈）；CI 新增 lint-learning-placeholders 闸门（fixture self-test 6/6，proven-to-fire）拦占位符原文与预防清单整段照抄。

## [2026-07-09] dev — updated（新增 Phase 0 --task-id 立即 claim）
**症状**: Phase 2.5 GitHub 撞车检查上线当天，同一个 task（f30dace8，session resume 孤儿 worktree 自愈那个 bug）又撞车了一次——这次是人工交互式 `/dev` 流程和 Brain 自身的 tick 自动派发同时处理了同一个 task，各自独立开出 PR #3665（人工，已合并）和 #3663（Brain 自动，事后关闭），实现方式完全不同（worktree list 校验 vs .meta 文件方案）。
**根因**: `POST /api/brain/tasks` 建的任务默认 `status='queued'` 且 `claimed_by=NULL`；Brain tick 循环每 2 分钟扫一次这个状态的任务自动派发到容器跑 headless claude。注册后如果不立刻上锁，2 分钟内必被 tick 当"无主任务"抢走——这不是查重能防的问题（两边在各自开始时都还没有分支/PR 可查，Phase 2.5 的 `gh pr list` 检查天然查不到），唯一有效防线是注册后立刻 claim。系统本来就有现成的 `POST /api/brain/tasks/:id/claim` 端点和 `claimed_by` 乐观锁，只是没人在注册后调用它。
**修改**: 新增 Phase 0（有头模式第一动作，早于 Phase 1/PrepPRD）：收到 `--task-id` 立即 `POST /tasks/:id/claim`；成功则继续，409（已被抢）则停下告知用户查证，避免在已经跑着的任务上再做一遍。version 21.6.0 → 21.7.0。

## [2026-07-09] dev — updated（新增 Phase 2.5 GitHub 撞车检查）
**症状**: 2026-07-09 同一个 PRD（补齐 task/issue 创建入口的 journey_id 写入）被 4 个独立并发 session 各自实现，产出 4 个内容几乎相同的 PR（#3658/#3659/#3660/#3661），其中 3 个还各自和 main 冲突或 CI 真实失败，靠人工事后 `gh pr list` 才发现撞车并清理。
**根因**: dev skill 路径 A/B 的 Phase 2 上下文查询只查 Brain 的 tasks/decisions/journeys，从不查 GitHub 上是否已有人在做同一件事——Brain 查询看不到"另一个并发 session 已经手动开分支在改"这种状态，导致撞车只能靠运气或事后发现。
**修改**: 新增 Phase 2.5「GitHub 撞车检查」（三路径共用，PrepPRD 前必做）：`gh pr list --search "<关键词>" --state open` 查语义相近的 open PR；查到接近可合并的就认领而非重新实现；查到 stale/冲突/CI真失败的就先关旧 PR 注明重复再动手。version 21.5.0 → 21.6.0。

## [2026-07-08] skill-evaluator — updated（新增 Form B 结构化输出模式 report_data）
**症状**: Form B 网页服务（员工上传 skill zip 自动出报告）需要机器可读的结构化数据来画「输入→skill 内部逻辑→输出」的 n8n 式连线图，但 skill-evaluator 只出人看的 markdown 报告，渲染器无从画图。
**根因**: skill 缺一个稳定的结构化输出契约（report_data schema），尤其是把 skill 的真实执行流程表达成一条可渲染的 pipeline（load 读数据 / judge 判断 / gate 硬闸 + 全部前置 vs 穿插判定）。
**修改**: 新增 references/report-data-schema.md 锁定 report_data pipeline schema（input / loadMode / kernelName / pipeline[按来源方式 库·文档·API·上下文 + 具体来源名] / outputs / verdict / stats / nextSteps / health），SKILL.md 加 Step 7b 结构化输出模式 + description 提及。验证：headless claude 拉起改后 skill 靠自读 schema 即吐出合法 report_data（16 步 pipeline 全合规、JSON 直接解析零加固），渲染器正常出图（40 节点 + 箭头 + 三段带 + 全图弹窗），未走 fallback。

## [2026-07-08] daily-report-cs — renamed to line04-cs-reply
**症状**: daily-report-cs 名字前缀跟 daily-report（日报生成 skill）太像，容易被误认成同一套东西的两个模式，实际它是完全不同职责的"Line04 客服实时对话"内核。
**根因**: 命名未按 Line 层级化约定，两个语义不同的 skill（"customer report" vs "customer talking"）撞了几乎相同的名字。
**修改**: `daily-report-cs/` 目录整体改名 `line04-cs-reply/`，version 1.0.0 → 1.1.0，明确标注已接入生产 wechat-draft.ts（PR #1181）。后续朋友圈回复板块升级时按同一命名法沿用 `line04-cs-moments`。

## [2026-07-08] line-strategist — created
**症状**: 系统缺"谁决定下一个任务"的角色——派发链纯 FIFO 无 ability/line 感知,PR 终局后无人根据结果判定下一步,推进方向全靠主理人人脑。
**根因**: 推进项模型 PR3(军师 producer)此前设计为"全局大军师日批",2026-07-08 主理人 9 条决策重定型为 Line 级原子军师+事件驱动,需要一个承载该角色的 skill。
**修改**: 新建 line-strategist skill:事件驱动决策环(防抖→四查快照→优先级阶梯不跳级→自审 confidence 阈值→执行→决策留痕晨报聚合),跨 line 登记不执行,DRY_RUN 干跑模式。Eval 12/12 (100%) vs 基线 10/12。

## [2026-07-08] harness-controller — updated
**症状**: controller merge PR 后不会产生 staging_e2e 任务，staging→production 放行层自 07-05 relay 迁移后已悬空超过 10 天（消费该任务的旧 LangGraph 图早已停用），zenithjoy 侧新代码上线后缺少 staging E2E 回归验证这道关卡。
**根因**: 唯一能派生 staging_e2e 任务的代码（原 mergePrNode._spawnStagingE2eTask）躺在已停用的 harness-task.graph.js 里，relay 单 session skill 接力模式取代 LangGraph 编排后没人调它。
**修改**: harness-controller Step 6 merge 确认后（自己 merge 或发现已被外部合并两条路径都算）新增 best-effort 调用 cecelia 新上线的 `POST /api/brain/harness/staging-e2e` 端点，恢复该层任务产生入口；version 1.6.0 → 1.7.0。

## [2026-07-08] wechat-cs-troubleshooting — updated（新增 §2.J：自愈重启后欢迎回来确认屏无自动点击）
**症状**: rog 生产实测：清理进程残留后通过正规入口重启 line04 客服，UIA 死区自愈逻辑自动触发一次微信重启，重启后卡进 `mmui::LoginWindow`（title=微信）的"欢迎回来"确认屏（账号已登录，仅需点"进入微信"，不需要密码），listener 心跳持续 `locked=True sessions=0`，生产完全收不到客户消息，直到人工点击"进入微信"才恢复。
**根因**: `find_weixin.py` 的 `is_privacy_locked()` 只做检测，没有自愈/自动点击逻辑；该状态和真正的隐私锁密码验证共用同一窗口 class/title，代码目前无法区分也无法自动跳过。
**修改**: §2 新增条目 J，记录现象、根因，以及三种自动点击方案失败的排除记录（`click_input()` 无效/`InvokePattern.invoke()` 报告成功但控件无视觉响应/复用 `_click_screen_point` PostMessage 方案坐标未命中疑似 DPI 缩放偏差），为下次实现自愈补上排除清单；已建 Notion issue e78d98bc（P1）跟进代码修复。

## [2026-07-08] daily-report-cs — created
**症状**: daily-report skill 生成的是"聊天记录→日报"，报告体、全量 system prompt（~15k tokens），不适合实时客服场景（客户一句话进来要几秒内回一句话），且完整版报告类字段（两层日报/资料范围模块/变更记录）客服场景用不上。
**根因**: 判断内核（A1-A4/四感/推进信号/询价分级/高风险识别/事实边界+资料缺失句式库）本身是通用的，缺的是"单轮、短输出、可控延迟"的裁剪版本。
**修改**: 从 daily-report v1.5 裁出判断内核，砍掉日报结构件，输出格式改为"一条可发送回复+内部判断标签 JSON"。15 客户×3 模型档实测：gpt-5.4-mini 首响 p50≈2s、总时长 p50≈3.5s、零编造，配合代码层兜底（JSON 缺失重试+post_check 编造检测出口+escalate 安全默认值）后，高风险客户转人工 3 遍复测 100% 稳定命中，内部标签准确率追平更贵的 reasoning 档模型。测过 Claude Haiku 4.5 / Gemini 3.5 Flash / Gemini 3.1 Flash-Lite / DeepSeek v4-flash 作为更快候选，均未跑赢 mini（Haiku 4.5 在当前 prompt 封装方式下有 60% 概率拒绝执行/输出元评论，暂不可用）。

## [2026-07-08] wechat-cs-troubleshooting — updated（新增 §2.I：卡住打不开 vs 读不到会话）
**症状**: 2026-07-08 排查 P0 客服丢消息/自愈重启两个 bug 期间，CI `job3 真机气泡可读性 gate` 在 xian-rog 上连续两次（含一次 rerun）报 `bubbles=0`/`session list 里找不到 文件传输助手`——表面看和 §1.1 UIA 树塌缩、§A CRM 破坏 UIA 是同一症状（读不到会话）。
**根因**: 已用代码走读排除是当次 PR 代码把 rog 微信杀挂（改动只在 `run_real_listen()` 主循环，job2 的 dryrun 路径 `run_dryrun_inject()` 完全不碰）。用户下午上机核实：这次是**微信窗口本身直接卡死打不开**，跟"窗口在但 UIA 读不出内容"是两种完全不同的根因，旧台账没有区分这两态，容易误诊。
**修改**: §2 新增条目 I，明确记录"卡住打不开"和"读不到会话"是两个不同现象、排障时要先分清；并指出现有自愈只覆盖"进程在但UIA读不到"和"树塌缩"两态，都假设窗口是活的，"窗口完全无响应"目前没有自愈路径，后续复现需要补窗口无响应检测。

## [2026-07-07] harness-controller — updated（v1.4.0：Step 0.3 前台点火防护）
**症状**: 07-06 infrastructure 前台点火 harness 任务 8e281976：payload 缺 orchestrator 字段被 Brain 41 秒标 terminal failed（missing_orchestrator_flag），前台 session 浑然不觉继续裸跑当 controller，进度上报全 404（v2 run not found）还硬走——Brain 记账与实际执行彻底分裂。
**根因**: controller 的前台接管路径没有任何注册后核验：不查任务是否已被 Brain 判死，不认领任务（queued 停留会被下一 tick 捡走双 spawn），也没写明"前台无 initiative_runs 行、上报 404 属预期"。skill 声称"两种触发行为一致"，但前台缺少 Brain dispatch 自带的建档与状态机保障。
**修改**: Step 0 新增 0.3 前台点火防护段——a. GET 任务确认未被标 failed（failed 即停，禁止带死任务裸跑）；b. queued 则 PATCH status=in_progress 认领防双跑；c. 写明前台无 run 行时 relay-runs 上报 404 是预期行为（relay-watchdog 只扫 initiative_runs 行，不会误重点火），Brain 侧前台建档端点落地后更新本段。

## [2026-07-07] skill-creator — updated
**症状**: sync-skill-to-notion.py 注册新 skill 时，数据被误写进 _smoke-test-skill 脏记录（daily-report 注册时实锤，此前 harness-controller 描述也曾污染同一条）。
**根因**: Brain API GET /api/brain/skills 无视 name= 查询参数返回全表，脚本取 existing[0] 直接 PATCH——找不到目标时误伤列表第一条；且 limit=5 使已存在 skill 也可能查不到导致重复建行。
**修改**: 改为全量拉取(limit=1000)后客户端按名字精确匹配（兼容 / 前缀），匹配不到才 POST 新建。函数级三用例验证：新建走POST/已存在走PATCH/斜杠前缀兼容。

## [2026-07-07] skill-evaluator — created
**症状**: 员工在 Codex/ChatGPT 上做的 skill 交来后无人能系统验收：说不清包几条功能线、输入依赖是否真实存在、有没有内部矛盾/编造红线；0707 日报 skill 四轮人肉评估花了一整天才理清。
**根因**: 缺一个把"功能地图解构 + 逻辑校验 + 断言合同 + 评估管线"固化成流程的验收工具，每次评估都从零手搓。
**修改**: 新建 skill-evaluator（SKILL.md + 6 references）：Step0 归一化（Codex/ChatGPT/Claude 三格式）→ 功能地图（逐线输入依赖审计）→ yes/no 梳理向导（答案转二值断言合同，无头保守替判）→ 8 类逻辑校验（含"样例也是条款"矛盾扫查、全文件清扫、单列纪律）→ full 模式三配置模拟+3遍投票评分 → 验收报告（功能地图第一屏）。Eval：拿日报 skill v1.2 当考题（14 项已验证缺陷为标准答案），3 轮迭代 8/10→9/10→10/10，最终召回 11/14（H 级 4/4 全中），baseline 对照 5/10；全程只读红线守住。

## [2026-07-07] daily-report — created
**症状**: 用户上传的客户日报 skill（v1.1-7.6）只在会话里流转，无仓库注册、无版本管理、无评测留痕。
**根因**: skill 由外部制作，从未走 skill-creator 注册流程进入 zenithjoy-skills。
**修改**: 经 5 轮 Eval 迭代（15 样本小型回归 × 7 模型 × 159 Run）后以 v1.5.0 注册。相对上传版：推进信号判档规则、价格量级禁令、隐含资源承诺越界判定、H2 收口矛盾修复、Eval 纯二值化+3遍多数投票、收口优先范围限定、资料缺失标准句式库、scripts/post_check.py 后置编造检查器。评测结论：Claude/Sonnet/GPT-5.5 通过；gpt-5.4-mini 独立模式 45/45 零编造；DeepSeek v4-pro 需独立模式+检查器兜底。完整报告: https://docs.zenjoymedia.media/daily-report-skill-eval-0707/
## [2026-07-05] repo-audit — updated（check-ci.sh coverage 门禁判定扩展到 vitest/jest config）
**症状**: zenithjoy 给 dashboard vitest.config.ts 加了 coverage thresholds（真实门禁、proven-to-fire），check-ci.sh 仍报 no_coverage_gate 误报。
**根因**: 脚本只 grep .github/workflows/ 找 thresholds，而 vitest 的门禁惯例写在 vitest.config.* 里（`vitest run --coverage` 自动读 config），workflow 里根本不会出现该关键词。
**修改**: THRESHOLD 判定增加第二来源——find 仓库内 vitest.config.*/jest.config.*（排除 node_modules，maxdepth 4）grep thresholds/coverageThreshold；任一来源命中即视为有门禁，并在 ✅ 输出里打印门禁所在文件。局限（保留 heuristic）：不校验每个跑 --coverage 的 app 都各自有门禁。

## [2026-07-05] dev / harness-planner / harness-controller / harness-evaluator / harness-generator / cecelia-harness-debug — updated（relay lockdown 契约对齐 + Brain 契约 CI 守卫）
**症状**: cecelia #3554（2026-07-05）上线 orchestrator 硬校验后，/dev 路径C 点火模板缺 `orchestrator: "skill-relay"` 字段——任何新 harness_initiative 会被 Brain 秒拒（terminal failed / missing_orchestrator_flag），路径C 实质断链；同时多个 harness skill 仍以 LangGraph 图为现行编排语义描述自己（planner 自称"Brain executor Layer 1 节点"、evaluator 称 env 由图注入等），与 relay 单 session 现实矛盾。
**根因**: skills 仓库与 cecelia Brain 分属两 repo，契约变更靠人脑同步；#3554 的 ROLLOUT NOTE 明确要求先改 skills 侧再部署 Brain，实际 Brain 先部署了，协调发布断档；且此类跨 repo 漂移没有任何机器守卫，只能靠人发现。
**修改**: ①dev v21.4.0 点火 payload 补 `orchestrator: "skill-relay"` 硬性字段 + 警示说明；②harness-planner v8.13.0 / harness-controller v1.3.1 / harness-evaluator / harness-generator / cecelia-harness-debug 全部改为 relay 唯一编排语义，LangGraph 表述统一加废弃标注；③新增 `.github/workflows/scripts/check-brain-contract.sh` 契约一致性守卫并接进 lint-skills CI（proven-to-fire：首跑即抓到 generator/evaluator 两处人工漏网的残留），后续 cecelia 侧契约变更 PR 必须同步更新该脚本断言。

## [2026-07-02] harness-planner — updated（v8.12.1：补回 review_required 字段，修 SSOT↔镜像历史漂移）
**症状**: cecelia real-env-smoke 的 b22-review-required-smoke 失败：harness-planner SKILL.md 缺 review_required 字段——发生在镜像同步 v8.12.0（cecelia #3510）之后。
**根因**: review_required（B22：planner 判断 evaluator PASS 后是否需人工确认）当年直接改在 cecelia 镜像里、从未进 SSOT——SSOT 与镜像早已分叉；用 SSOT 覆盖镜像时把该字段覆盖丢了，而 Brain graph 仍消费 planner verdict JSON 的 review_required。
**修改**: SSOT Step 3 最后一条消息补回 review_required 字段 + 判断规则（true=新功能/UI/行为变更需人工确认；false=bugfix/重构/配置/文档自动合；默认 false）。教训：镜像同步前先 diff 双向差异，镜像可能藏有 SSOT 没有的功能字段。

## [2026-07-02] harness-planner — updated（v8.12.0：A1 加载整条 line 历史约束进合同 + 修 Step 0.3 NFR 坏查询）
**症状**: harness 一会儿好一会儿坏——每个 sprint 的 planner 只看自己新合同，Line04 五条客服铁律（不进群/不回自己/防假成功/后台静默/租户隔离）和本 line 已验收行为对 proposer/generator/evaluator 完全不可见，新 sprint 会回退/破坏已验收的行为；且 Step 0.3 的 NFR 查询 `GET /decisions?category=nfr` 是假通的门。
**根因**: ①planner 全流程没有任何一步读 invariant / 累积 FR（验收一次性，没沉淀复用）；②`GET /api/brain/decisions` 路由实际读的是 `decision_log`（LLM 审计日志 9 万+ 行）而非 `decisions` 表，且忽略 category 参数——拉回的是审计噪音。
**修改**: 新增 Step 0.4「加载整条 line 的 invariant + 累积 FR」——step（golden-path-decisions）/ journey_feature（invariants?target_type=journey_feature）/ area（invariants?level=area）三源 invariant 合并去重 + `GET /journeys/:id/golden-paths` 聚合累积 FR，注入 sprint-prd.md「## Invariant 约束」「## 累积 FR」两段（每行 `- [标签] 铁律文字（来源: 层级）`，此格式即 E1 的解析契约）；无数据写占位"（本 line 暂无历史）"优雅降级；两段不计入 Thin Slice 100 行上限。Step 0.3 坏查询改为 golden-path-decisions?category=nfr + abilities/:id/decisions（jq 过滤）双源，并加禁止使用坏端点的警告。Eval 11/11 (100%)（旧版基线 6/11），核心行为断言：Line04 五条铁律真实从 DB 走到合同。

## [2026-06-29] wechat-cs-troubleshooting — created
**症状**: 微信客服一连串问题（不回复 / 读不到会话 / 客服模块显示未安装 / 客户全黑名单改不了 / staging 看不到机器 / 新装 agent 旧进程没杀）反复排查，多个不同根因的 bug 被混在一起说，已修的和没修的分不清，用户每次都要重新理一遍"到底解决了没"。
**根因**: 缺一份把 line04 微信客服系统【已解决 vs 未解决】分清的活台账——读会话（UIA 树塌缩，已修 1.0.72）、回复（离屏 _open_chat，未修）、未安装假象（preflight 并发/旧 listener 没杀，未修）、全黑名单（接管默认 bug，未修）、环境错位（安装包写死生产 vs staging 库）各是独立根因，没台账就反复重诊、反复混淆。
**修改**: 新建 wechat-cs-troubleshooting skill（知识 catalog，非客观输出，eval N/A）。固化：系统三层链路 + 关键环境事实、已解决项（根因+修法+PR/版本）、未解决项（按卡人程度排序，含根因+计划）、session-1 诊断复用法（schtasks /it、GBK 日志 base64 读法）、排障起手式（怀疑顺序）。声明为活台账，每次排查后回来更新。

## [2026-06-24] codex-login — created
**症状**: 西安 Mac 上 codex team3(subodou)账号登不上、跑任务报认证失败;排查耗时极长,反复在"网络/出口/中转/账号"之间打转。
**根因**: ①team3 access_token 过期 + 老 refresh_token 已被轮换作废(refresh_token_reused),只能重登;②国内机器连 auth.openai.com(登录/刷新端点)被地域封 403,但 API 端点其实是通的——缺这条认知导致误判为"网络全坏";③缺一份"怎么修登录"的 runbook。
**修改**: 新建 codex-login skill,固化:四条心智模型(地域只封登录端点/refresh_token 一次性轮换/干净出口判定)、三种失败分诊、codex login + localhost:1455 回调投递重登法、防复发(单机持有+只读同步)、报错速查表。
## [2026-06-19] dashboard-deploy — updated（触发率冲到 100%：补"改了内容要它生效=部署 vs 新建/修bug=开发"区分）
**症状**: 去 DA 换真实词后触发 eval 已 90%，但还差 1 句——"Cecelia 的 dashboard 更新一下，设备页加了新字段"没触发（介于开发和部署两可），用户要 100%。
**根因**: 描述没明确区分"已改好的内容要部署生效"(=触发) 和"还在新建组件/修bug"(=开发不触发)，模型对"改了X更新一下"这类摇摆。
**修改**: description 加一句明确判据——"用户说'dashboard/设备页/某页面 改了/加了字段/加了内容，更新一下/让它生效/让它显示出来/上线' = 部署已改的东西，必触发；只有'新建/做一个/加组件/写新功能/修bug'这种还在写代码没说上线的才是开发(走/dev)不触发"。用修好的触发 eval **每句跑 3 次取多数**实测：**recall 100%(10/10，每句 3/3 全票)、specificity 100%(10/10，每句 0/3)、准确率 100%**。10 个开发/运维近似负例(加组件/修bug/部署后端/重启brain/配电脑等)全部正确不触发。

## [2026-06-19] wechat-uia-silent-send — updated（方向检测物理不可能→永久废弃 REPLY_DIRECTION_CHECK，不回自己靠未读角标，纠正"ListItem 子元素/校准后重开"中间错结论）
**症状**: skill 里多处留着一个过时的中间错结论——"消息是 ListItem，方向看【行内气泡子元素的左右偏移】，真机校准 incoming/outgoing 判据后【再开启 REPLY_DIRECTION_CHECK】"。这会误导后人继续花时间去"校准后重开方向检测"，而这条路根本走不通。
**根因**: 之前的认知只走到"消息气泡是 ListItem 不是 Text"就停了，推测能靠 ListItem 内部"行内气泡子元素左右偏移"判方向，标成"待校准后重开"。这是个被后续真机进一步 dump 证伪的中间结论，但 skill 没回头改。2026-06-19 xian-rog 真机逐条 ListItem 全 dump 证明：ListItem 是叶子（子元素=0，根本没有"行内气泡子元素"）、聊天区无头像、收发 `automation_id` 完全相同（都=`chat_message_list.qt_scrollarea_viewport.chat_bubble_item_view`）、ListItem 满宽 → 微信 4.1.8 的 UIA 里收发消息无任何可区分特征 = **没有方向信号**。方向检测是物理不可能，不是阈值/校准问题。
**修改**: 把"方向检测"节、变更记录、调试指引、禁止使用表里所有"行内气泡子元素 / 校准后重开 REPLY_DIRECTION_CHECK"措辞改成最终真相——(1)「方向检测」节标题与正文改为"UIA 无方向信号→方向检测物理不可能→REPLY_DIRECTION_CHECK 永久废弃（非待校准后重开）"，补 dump 实测证据（子元素=0/无头像/automation_id 相同/满宽），并讲清"不回自己"一直靠**未读角标机制**（自己发的不产生未读角标→scan_unread 路径1 只对有角标会话动手），唯一"回自己"风险=自回复风暴（故障模式1，content 追踪 bug，不碰方向)；(2) 变更记录顶部加 2026-06-19 终结结论行，并把旧"⚠️待修:改找 ListItem+校准后重开"行标为"已被进一步 dump 证伪"；(3) 调试指引「方向检测判反」根治改为"物理不可能→废弃，不回自己靠未读角标，自回复风暴另见故障模式1"，旧 PR #797 那条加覆盖说明；(4) 禁止使用表加一行「REPLY_DIRECTION_CHECK 气泡方向检测=UIA 无方向信号，物理不可能，永久废弃；不回自己用未读角标」。不动 description frontmatter、不删未读角标机制（路径1）、不删故障模式1 描述。

## [2026-06-19] dashboard-deploy — updated（描述去掉误导词 DA，换用户真实说法 + 跑通触发 eval）
**症状**: 上一版描述把"DA"当主触发词加进去，但用户澄清"DA"是语音/手滑的误导词、他根本不用，真实说法是 dashboard / 中控 / 前台 / 前端。另外 skill-creator 的触发 eval 在本机一直跑出 recall=0% 的假结果，没法量化验证。
**根因**: (1) "DA"非用户真实词汇，是噪音；(2) skill-creator 的 run_eval 在本环境两个调用 bug——① subprocess 没设 `stdin=subprocess.DEVNULL`，裸 `claude` CLI 傻等 stdin 行为异常；② 测试用唯一命名临时命令，但真 skill 已安装，模型触发的是真名 `dashboard-deploy`，harness 找临时名永远不匹配 → 假 0%。
**修改**: description 删除所有"DA"，触发词改为用户真实说法（dashboard/中控/前台/前端/ZD）。用修好的自测脚本（裸 claude + stdin=/dev/null + 匹配真 skill 名 + grep 流缓冲 + 检测到即 kill 防执行部署）跑 20 句真实词 eval：**recall 90%（9/10）、specificity 100%（10/10）、准确率 95%**（仅"dashboard 更新一下设备页"这种开发/部署两可的句子没触发）。skill-creator 上游与本副本逐字节相同，无可升级版本；两个 eval bug 待另行修进 run_eval。

## [2026-06-19] dev — updated（立「哨兵(回归守卫)死规矩」）
**症状**: 反复出现的病——bug 修了但没留下"会报警的守卫"，换台机器/换个人就再犯。守卫一直靠人/AI 每次自觉判断（=祈祷），没有像 test 那样的死规矩管谁写/啥时候/写哪/谁卡。环境接缝（真机/生产 env/真实调用方）尤其裸奔，因为 CI 是干净假环境根本测不到。
**根因**: dev skill 只有 regression test（逻辑类守卫）一种形态，缺「环境类守卫=运行时/启动自检，打包进程序」的概念，更缺「机器闸门：PR 碰环境接缝却没带自检→CI 红」这条强制；接缝清单虽已在 pre-PRD/Contract 要求，但没规定每条必须配一个 proven-to-fire 的守卫。
**修改**: dev/SKILL.md（21.2.0→21.3.0）PrepPRD 落地后新增「哨兵（回归守卫）死规矩」节——核心(每 bug/功能配对种类·在对环境跑·被机器卡的守卫) + 谁写(开发者AI同PR，永非用户)/啥时候(接缝清单每条配守卫，标done前必 proven-to-fire 亲眼看报红)/写哪(逻辑接缝→CI test；环境接缝→自检代码打包进程序，CI测不到) + 谁卡(CI闸门，同 lint-feature-has-smoke 性质，实现另一PR建) + 失控程度越高守卫越重(客户机Agent运行时自检>生产机启动自检>Dashboard真URL冒烟>纯逻辑CI test) + 一份代码两处用(检查代码只写一份在主repo，打包进Agent+参考机发版前先跑)；Bug PrepPRD 的 Regression Test 计划加守卫指针 + 验收项加 proven-to-fire。不动现有步骤编号/路径A·B·C/trigger frontmatter。

## [2026-06-19] dashboard-deploy — updated（修正 Cecelia 部署流程 + 触发词补 DA）
**症状**: 部署 Cecelia dashboard 反复出问题——手动 `npm run build` 只更新本机、漏了 HK 生产实例，用户走公网还是看到旧版；改 UI 改错副本（改了 `frontend/` 而非真正服务源 `apps/api/features`，部署后页面没变化）；走 Brain webhook 时漏 deploy token 被拒。另外用户说"部署 DA"时 skill 经常不触发。
**根因**: (1) Cecelia dashboard 有本机 perfect21:5211 + HK 生产（cecelia-core-hk）两个实例，只有 Brain webhook（跑 deploy-local.sh）才同步两个，手动 build 只动本机；(2) apps/dashboard 经 vite 别名 `@features/core→apps/api/features` 构建，改 `frontend/` 副本不生效；(3) Brain deploy 端点要 `DEPLOY_TOKEN`（在 brain 容器 env，不在 ~/.credentials）；(4) description 里压根没有"DA"这个用户最常用的 dashboard 缩写，必然漏触发。
**修改**: Cecelia 章节重写——标注两个实例 + 强制走 Brain webhook（含 token 取法 `docker exec cecelia-node-brain printenv DEPLOY_TOKEN`）、新增「改 `apps/api/features` 不是 `frontend`」小节、轮询改等 `success`、验证改成本机vsHK bundle hash 对比 + 无头浏览器真实渲染断言；description 补「DA/ZD/中台/前端」同义说明 + 大量口语触发说法（部署一下 DA / 推一下 DA / 发一下前端 / DA 没更新）。触发优化 loop 在本环境测量失真（短部署指令 recall 测不准、test 段 0s），故按根因人工定描述，未盲信失真分数。

## [2026-06-18] harness-contract-proposer / harness-contract-reviewer — updated (补接缝断言规则)
**症状**: 微信客服端到端调试发现，很多"修复"在假环境（CI/mock/开发机）绿了就标 done，碰真环境（真机微信几何/UIA、生产 mmv env、真实 agent 调用方）逐个炸，来回修二十几轮。
**根因**: DoD 的验收标准定在了照不到真实世界的地方。两个 contract skill 已有"真实目标环境验证 + 禁止 mock Golden Path + 领域验证规则（视频 ffprobe/发布真出/DB/UI）"，但缺「真机 RPA / 生产 env」这一类领域，也缺「DoD 分逻辑断言 / 接缝断言」的概念——接缝点（真机 UIA、生产 env、真实调用方）没人强制要求在真目标上验。
**修改**: proposer（9.2.0→9.3.0）领域验证规则表加「真机 RPA / 生产环境集成」一行（Final E2E 必须真目标验证，不是 CI 绿），新增「DoD 必须分两类断言（接缝 vs 逻辑）」小节（接缝清单 1-3 条 + logic-done-pending 状态 + 禁写死环境假设值）；reviewer（9.1.0→9.2.0）Golden Path 覆盖审查加两条打回信号（接缝只用 mock 断言 → 打回；写死环境假设值无真验 → 打回）+ 第 6 维核对清单加真机 RPA/生产 env 一行。reviewer 7 个维度名（接口约定）一个未动，只在描述/审查项里加内容。

## [2026-06-18] wechat-uia-silent-send — updated (补客服端到端调试 8 个坑)
**症状**: 微信客服端到端联调连环踩坑——租户隔离回归后客服全员不回（400 NO_TENANT_CONTEXT）；改 agent 代码后已装客户端不更新；mmv 中台 launchctl 重启卡旧进程（坑 3 次）；.env 漏 TOAPI_API_KEY 导致"成功但不回"且失败静默；气泡方向检测假设错把所有来信判 outgoing 永不回；license QUOTA_EXCEEDED；OFFSCREEN_X 不够窗口闪前台。
**根因**: (1) 中台 draft-generate 加租户隔离要 tenant_id/X-Tenant-Id，listen_chat 不传任何租户标识；(2) 模块版本号未 6 处一致 bump、core 改动未 bump package.json；(3) `launchctl stop/start`/`kickstart -k` 不杀旧进程 PID 不变；(4) .env 漏 TOAPI_API_KEY 且 aiError 不打日志 → reply undefined → skip；(5) `_last_bubble_direction` 凭假设写未真机校准；(6) free 装机上限 1 名额被占；(7) -2600 在双屏/高分屏离屏不够。
**修改**: SKILL.md「变更记录」表顶部加 8 行（含 PR #796/#797）；「调试指引」补 8 条对应排查（agent_id 反查租户 / 6 处版本 bump + core bump package.json / 模块更新≠core更新 / pkill+bootout+bootstrap 干净重启并验证 PID+required_version+reply / TOAPI_API_KEY 缺失诊断 llm_audit / REPLY_DIRECTION_CHECK 默认 False + 真机 dump 校准 / QUOTA_EXCEEDED v1.1 兼容路径 / OFFSCREEN_X 按机器调 machine.config.json 覆盖）。

## [2026-06-18] dev — updated (PrepPRD 新增步骤0.5 对抗深挖)
**症状**: /dev 流水线只围绕用户说出口的 golden path（FR）建，系统性漏掉"理所应当但没人写"的横切铁律和 NFR——生产里连续暴露 AI 回复自己、误回群聊、客服数据不按租户隔离三类弱智 bug，全是用户肉眼发现，流程没有任何环节负责挖
**根因**: PrepPRD 阶段只有"展示 Golden Path 草稿"，没有对抗深挖步骤；缺少横切不变量登记表当逼问清单；单租户测试让隔离漏洞看不见
**修改**: PrepPRD 新增「步骤0.5 对抗深挖」——5 轮换镜头（顺利路径/失败边界/横切铁律/NFR/知识记忆），按 /dev 路径缩放深度，先喂横切不变量登记表（decisions category=invariant）+ 历史 learnings，产出分【要用户拍的 policy】与【机器铁律自动标注】两流，并把生产新坑回灌登记表形成闭环；配套已种 10 条铁律（5 系统级 + 5 Line04 级）

## [2026-06-18] dashboard-deploy — updated（合并 upgrade-dashboard，删重复）
**症状**: 同一件事（部署 dashboard / 给页面一个能打开的地址）存在两个 skill——`upgrade-dashboard`（旧）和 `dashboard-deploy`（#34 已是合并版）。生效目录里挂的偏偏是过时的 `upgrade-dashboard`，正确的 `dashboard-deploy` 没接软链、从不触发；还有个死链 `zenithjoy-deploy` 残留。
**根因**: `dashboard-deploy` 建好后没接进 `~/.claude/skills` / `~/.claude-account1/skills`；`upgrade-dashboard` 架构描述已过时（520/521 nginx + deploy-hk.sh + /home/xx 路径），与现实（hk-vps + autopilot-dashboard + Cloudflare Tunnel + perfect21:5211）不符。
**修改**: 以 dashboard-deploy 为唯一 skill，从 upgrade-dashboard 捞两段有用内容补入（SW 注销 console 脚本 + nginx no-cache 配置）；删除 upgrade-dashboard 目录与软链、清死链 zenithjoy-deploy、把 dashboard-deploy 接进两个生效目录；新增 eval-4（单页预览给地址场景）。iteration-3 eval：合并版 20/20 (100%) vs 旧 upgrade-dashboard 12/20 (60%)。

## [2026-06-08] device-transfer — updated (eval iteration-1 + 触发词补全)
**症状**: skill 存在但触发不稳定——Claude 在国内机器遇到下载失败/超时时不会自动调用，每次需要用户手动提醒
**根因**: description 触发词只覆盖主动发起传输的场景，没有覆盖"中途遇到下载失败"的报错词；CLAUDE.md 也没有全局规则兜底
**修改**: 补充 13 个触发词（下载失败、timeout、Connection refused、apt/pip/npm/curl 慢等）；CLAUDE.md 新增"国内外网下载失败"全局规则；新建 evals 3 条，iteration-1 结果 with_skill=12/12 (100%) vs without_skill=1/12 (8.3%)

## [2026-06-08] dev/db-update/feature-update/feature-map — updated
概念对齐到 Ability/Feature/GoldenPath 新模型；feature-update 标废弃。

## [2026-06-08] wechat-uia-silent-send — updated (eval iteration-1 + 2 bug fixes)
**症状**: 实际使用中发现 2 个 bug：(1) skill 里写命令文件的示例用 `cmd /c echo` 遇中文乱码；(2) IPC 代码在 json.load 异常时 os.remove 不执行，带 BOM 的文件导致每 3 秒死循环刷屏
**根因**: (1) `cmd /c echo` 无法处理中文/引号，正确做法是 pure ASCII JSON + `\uXXXX` 转义；(2) `os.remove` 放在 `json.load` 之后，parse 失败时文件未删，需改 `encoding='utf-8-sig'` + 读完立即删
**修改**: 修复写命令文件章节（改为 ASCII+`\uXXXX` 方案），修复 IPC 代码示例（utf-8-sig + 先删后解析），补充"联系人找不到时 dump 会话列表"调试指引；新建 evals 3 条，iteration-1 结果 with_skill=100% vs without_skill=75%

## [2026-06-08] wechat-uia-silent-send — created
**症状**: 无文档说明微信后台 UIA 发送机制，每次开发重复踩坑（等待时间/版本限制/前台路径无效）
**根因**: 经过多轮调试才摸清 `Invoke()` 后需 2s 等待、UIA SetValue+PostMessageW 才是唯一可靠路径
**修改**: 新建 skill，记录静默发送架构、命令文件 IPC、成功验证方法、禁止使用的死路

## [2026-06-03] zenithjoy-deploy — removed
**症状**: zenithjoy-deploy 和 dashboard-deploy 并存，功能重复
**根因**: 应直接替换而不是新建
**修改**: 删除 zenithjoy-deploy，由 dashboard-deploy 完全替代

## [2026-06-03] dashboard-deploy — created
**症状**: zenithjoy-deploy skill 只覆盖 ZenithJoy，Cecelia dashboard 无 skill；旧 skill 缺公网验证步骤
**根因**: 两个 dashboard 架构差异大，需统一入口；旧 skill 不含 Cloudflare tunnel ingress 知识
**修改**: 新建 dashboard-deploy 覆盖 ZenithJoy（rsync+HK VPS）和 Cecelia（本地 bind mount），含公网验证和 502 排查

# ZenithJoy Skills Changelog

每次通过 skill-creator 创建或更新 skill 后，在此文件顶部追加一条记录。

格式（必须含三段）：
```
## [YYYY-MM-DD] <skill-name> — <created|updated>
**症状**: 触发本次修改的现象（什么行为失效、什么 CI 报错、什么用户反馈）
**根因**: 造成症状的根本原因
**修改**: 本次做了什么改动
```

---

## [2026-06-01] db-update — created
**症状**: 无统一数据写入规范，Feature 表被测试数据污染，截图存 COS 费用高
**根因**: notion-sync 名称误导（以为目的是同步 Notion），缺少所有表的 Output Template，截图路径未规范
**修改**: renamed notion-sync → db-update，补全 10 张表 + 5 种 Notes Type 的 Output Template，harness-report 截图改 VPS scp

## [2026-06-01] harness-report — updated
**症状**: Report 格式冗长，缺 Usage 表、DOD 对齐、截图证明
**根因**: Step 6 report 模板无结构，截图走 COS 未规范
**修改**: 新增紧凑 Report 模板，截图改 scp 到 us-vps，Phase B 调用 db-update skill

## [2026-05-30] dev + harness-planner — updated (eval 修复)
**症状**: (1) dev eval：三条路径（Bug/小改动/大功能）写 decision 时用 `type: bug_fix` 而非 `category: bug-fix`，Brain API 只认 category 字段，数据写入失效；(2) harness-planner eval：thin-slice-size 断言以 ≤50 行为标准，但含 smoke script 的真实 PRD 常见 80-110 行，eval 持续误报
**根因**: (1) dev SKILL.md bash snippet 注释说"换成实际值后执行"，Claude 自行重写 JSON 时忽略 category 写成 type；(2) ≤50 行限制是 2026-05-12 防 254 行 PRD 临时设的，未考虑 smoke script 正常占 20-40 行
**修改**: (1) dev v19.4.0: 三条路径 decision bash snippet 加 ⚠️ 注释 + 加粗强调 `category` 不能写 `type`；(2) harness-planner v8.7.0: ≤50 行改为 ≤100 行，evals.json thin-slice-size 断言同步更新为 <=100

## [2026-05-30] harness-report — updated (v6.0.0, merged harness-sprint-state)
**症状**: harness-report 和 harness-sprint-state 是两个独立 skill 但职责重叠（都是 Sprint 完成后的收尾工作），造成混乱
**根因**: 历史上 sprint-state 从 evaluator 拆出后未与 report 合并
**修改**: 将 harness-sprint-state 全部内容合并入 harness-report（Phase A=交付报告 6步，Phase B=Sprint状态同步8个DB）；harness-sprint-state 目录和 symlink 已删除；sprint-state 详细实现移入 harness-report/references/sprint-state-sync.md

## [2026-05-30] harness-evaluator + harness-contract-proposer + harness-contract-reviewer — updated + eval iteration-1
**症状**: (1) harness-evaluator v1.11.0 的空壳 workflow 检测正则漏掉 `npm test`/`npm ci` 和 PowerShell 业务命令，导致真实 `agent-qr-windows-verify.yml`（含 `npm test`）会被误判为空壳，Evaluator 提前 FAIL 而不触发 workflow；(2) harness-contract-proposer 没有 windows_cloud workflow 内容审查规则，直接按假设写 BEHAVIOR 不验证 CI 真实内容；(3) harness-contract-reviewer 缺少 ci_workflow_alignment 维度评审
**根因**: (1) 正则只覆盖 `npm run` 未覆盖 `npm test`/`npm ci`，PowerShell 命令完全未收录；(2)(3) v8.0 上线时只更新了 proposer 描述未添加强制读取 workflow 文件规则，reviewer 未对应增加第 7 维评分
**修改**: (1) evaluator v1.11.1: 正则加入 `npm test|npm ci|Set-Content|New-Item|ConvertTo-Json|Write-Host.*PASS`；(2) proposer v8.1.0: 新增 windows_cloud BEHAVIOR 1:1 映射强制规则 — 必须 cat workflow 读实际内容后对比用户路径；(3) reviewer v8.0.0: 新增第 7 维 ci_workflow_alignment；三个 skill eval iteration-1 完成，with-skill pass rate: evaluator 100%、reviewer 100%、proposer 100%

## [2026-05-29] engine-pr-watchdog — updated
**症状**: PR BEHIND，watchdog 检测到需要 rebase，rebase 完成后 push 用了 run_in_background=true，bash tool 立刻返回，Claude 输出文字结束 turn，轮询循环断裂，PR 永远卡在 BEHIND 未合并
**根因**: run_in_background=true 让 push 异步执行，bash call 立刻返回控制权给 Claude，Claude 自然结束 turn
**修改**: 禁止 run_in_background，Step 4 rebase/push 全部改为同步执行

## [2026-05-29] harness-contract-reviewer + harness-report — updated
**症状**: harness pipeline 在单 Sprint 单 PR 模式下，reviewer 第 7/8 维依赖多 Workstream 前提，评审无意义；report 创建多个 Sprint Task 与单 Sprint 模型矛盾
**根因**: 早期多 Workstream 设计残留，与 Anthropic 官方 v2（一 Sprint = 一 PR）冲突
**修改**: reviewer 删第 7/8 维，report 改为单 Sprint Task 创建

## [2026-05-29] harness-contract-proposer + harness-generator — updated
**症状**: proposer/generator 仍按多 Workstream 逻辑分配任务，产生冗余分支，与 pipeline 整体方向冲突
**根因**: 多 WS 拆分概念在 skill 里未清除，与官方 v2 单 Sprint 设计不兼容
**修改**: 移除 Workstream 拆分概念，对齐官方 v2（一个 Sprint = 一个 Generator = 一个 PR）

## [2026-05-29] hooks/ — created
**症状**: 全局 hooks 散落在 ~/.claude/hooks/，每次修改无版本记录，无法 review，出问题无法回溯
**根因**: hooks 不在 git 管理下，缺乏变更追踪
**修改**: 迁移到 zenithjoy-skills/hooks/，统一版本控制

## [2026-05-29] harness-generator — updated
**症状**: generator 开完 PR 后立刻退出，CI 未等待，PR 长期 open 无人跟进，需要人工手动合并
**根因**: generator 把"开 PR"视为任务终点，没有后续监控机制
**修改**: Step 7.5 PR 创建后轮询 CI 直到合并（后被独立 engine-pr-watchdog skill 接管）

## [2026-05-29] engine-pr-watchdog — updated v3.0.0
**症状**: watchdog 只监控当前 repo，跨 repo PR（cecelia / zenithjoy-workspace / zenithjoy-skills）被漏掉；WTBASE 路径错导致 worktree 找不到
**根因**: scope 设计过窄，只检查当前目录的 repo；路径变量赋值有误
**修改**: 改为查询所有三个 repo 的 open PR，修复 WTBASE 路径错误，放宽 trigger 条件

## [2026-05-29] engine-pr-watchdog — updated
**症状**: watchdog bash loop 运行超 600s（Bash tool 上限）后超时退出，Claude 自然输出文字结束 turn，轮询断裂，PR 被遗忘
**根因**: Bash tool 有 10 分钟硬上限，超时后控制权回到 Claude，Claude 不会自动继续轮询
**修改**: 超时后必须立刻重新发起 Bash 调用，不得输出任何文字，不得结束 turn

## [2026-05-29] skill-creator — updated
**症状**: skill 改动时有人绕过 skill-creator 直接编辑文件，CHANGELOG 未更新，zenithjoy-skills 同步状态不一致
**根因**: 缺少强制约束，AI 可以直接修改 skill 文件跳过流程
**修改**: 加入 ZenithJoy 强制规则（所有改动必须经过 skill-creator）；Post-Creation 步骤新增 zenithjoy-skills 同步 + CHANGELOG 更新