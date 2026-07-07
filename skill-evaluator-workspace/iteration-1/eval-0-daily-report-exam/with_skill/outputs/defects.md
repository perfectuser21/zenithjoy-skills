# 逻辑校验缺陷清单（7 类静态审查）

对 daily-report-v1-2 全部 12 个文件逐类过一遍。共 8 条缺陷：3 H · 4 M · 1 L。
严重度口径：H = 会导致某条功能线输出错误或不可执行；M = 降低跨模型稳定性或可维护性；L = 文档卫生。

## H 级（会致输出错误或不可执行——建议回 skill-creator 走修复迭代）

### H1 · 输入无来源（类别 2）· 数据源接口全包缺失
- 描述：1-5 条日报线的主路径核心前提是"按客户名从数据库/文档/连接器读取当天聊天、当日状态、日报、周报、月报、客户档案、企业信息、产品信息"，但整个 skill 包（含 agents/openai.yaml）**没有任何数据源接口定义**：无 API 路径、无数据库 schema、无连接器/MCP 声明、无工具定义。openai.yaml 只声明了 interface 元数据和 policy，无数据访问。
- 原文位置：SKILL.md §1、§5.2、§7；references/data-fetch-rules.md §二/§五；agents/openai.yaml。
- 影响：主路径（客户名 → 自动读库）在裸宿主里不可执行。**注**：降级路径已定义（§1、data-fetch §二、example-input.md：无库时请用户贴资料包并标"未提供/待补充"），故非彻底死路，但等于把自动化日报降级为手工喂料。
- 修复建议：在 skill 包内明确声明目标宿主的数据源接口（连接器名/查询契约/字段映射）；或在 SKILL 显式声明"本 skill 仅消费用户贴入的资料包，不承担自动读库"，把主路径与降级路径的边界写死。

### H2 · 标准模糊（类别 5）· Eval 最终裁决不可机械执行
- 描述：Eval 通过标准写"无关键失败项；**核心项全部通过**；整体**大部分**评测项通过"。但 11 项二值断言表中**从未标注哪些是"核心项"**，"大部分"也无阈值。二值评测无法机械得出最终"通过/部分通过"结论。这正是 0707 实证 H4 的同型问题。
- 原文位置：references/eval-v2-scorecard.md §五/§七；eval-v2-sop.md §十一。
- 影响：Eval 线（6、7）的最终裁决靠评分员主观判断，破坏"纯二值、可复测"的设计目标。
- 修复建议：在 11 项表中显式标注 核心/参考 分级，并把"大部分"改为可判定阈值（如"参考项失败≤N 且核心项 0 失败"）。

### H3 · 内部矛盾（类别 1）· 冒烟旗舰样本 golden 与反编造铁律冲突
- 描述：eval-simulation.md 对"钱总"（调研型询价，样本只给聊天记录、**未提供产品价格信息**）的期望下一步动作写"**给价格区间**、适用条件和二次沟通节点"。但 §14 与 §11.2 明令：产品价格信息未提供时**不得给出任何价格数字或量级**，只能写"报价区间待产品信息提供后输出"；eval-v2 golden-answer 示例（§六 钱总）也明确"不得编造具体价格…只能写待补充"。故冒烟样本 golden 与 skill 反编造铁律 + v2 golden 三处冲突，模型照冒烟 golden 执行会直接触发关键失败项"事实越界编造"，且撞在 skill 最引以为傲的调研型询价场景上、跑得最多的冒烟线上。
- 原文位置：references/eval-simulation.md 期望核心判断表（钱总行）vs SKILL.md §11.2/§14 vs eval-v2-golden-answer-template.md §六。
- 影响：冒烟线在旗舰场景诱导编造输出；也证明多文件重复已发生实质漂移（见 M1）。
- 修复建议：把 eval-simulation 钱总期望改为"产品信息已提供才给区间，否则写待补充"，与 §14/§11.2/v2 golden 对齐。

## M 级（降低跨模型稳定性或可维护性）

### M1 · 规则重复（类别 4）· eval 规则与两层日报规则多文件重复
- 描述：同一批规则在多处复制：测试类型/样本数量表（SKILL §16.1-16.2、eval-v2-sop §二/§五）；6/15/30 样本覆盖表（SKILL §16.3、eval-v2-sop §五、eval-simulation）；11 项二值断言表（SKILL §16.5、eval-v2-sop §十、eval-v2-scorecard §二，三处几乎逐字重复）；事实边界/编造定义（SKILL §5.8/§14/§16.4、eval-v2-sop §六、eval-v2-scorecard §一、data-fetch §七、golden-answer §一）；两层日报结构（SKILL §3、output-template 20 条、eval-simulation 11 条、capability-scorecard）。改一处必漏多处——H3 已是一个实际漂移实例。
- 原文位置：见上述各文件。
- 修复建议：每类规则收敛到单一出处（如 eval-v2-scorecard 为二值断言唯一出处），其余文件改为引用；对齐后可大幅缩短。

### M2 · 字段无填法（类别 3）· 多个判断字段档位边界未定义
- 描述：输出模板多个档位字段缺可判定口径：`适配风险` 的"正常 ↔ 谨慎推进"分界无定义（只定义了高风险/暂不适配触发条件）；`阶段置信度` 高/中/低无判定标准；详细版 `跟进优先级` 四档（今日必须/24 小时/观察培育/暂不推进）无从阶段+信号映射的规则。没看过例子的模型各填各的。
- 原文位置：references/output-template.md 单客户/详细版模板；SKILL.md §9（置信度）。
- 修复建议：为每个档位字段补一句可判定判据（如"正常=无风险信号且证据充分；谨慎推进=证据不足或有价格异议但未拒配合"）。

### M3 · 无 CHANGELOG + 版本号 stale（类别 7）
- 描述：无 CHANGELOG 文件记录 v1.1→v1.2 改动；版本信息散落且不一致——agents/openai.yaml `display_name: 日报skill-v1.1-7.6` 仍是旧版号，与包名 daily-report-v1-2 / v1.2-7.7 冲突。多轮补丁后无法定位哪条是新哪条是旧（放大了类别 1 矛盾）。
- 原文位置：agents/openai.yaml 第 2 行；缺 CHANGELOG.md；SKILL.md frontmatter 无 version 字段。
- 修复建议：加 CHANGELOG.md；frontmatter 补 version: 1.2；openai.yaml display_name 统一为 v1.2-7.7。

### M4 · 缺料替代句式散落，无统一"缺料标准句式库"（类别 6）
- 描述：反编造禁令旁**有**替代写法（§14"报价区间待产品信息提供后输出"、§16.4"标注未提供/待核实后补充并给替代动作"），比裸禁令好；但替代句式散落各处，无一个可照抄的"缺料标准句式库"参考文件。0707 实证表明句式库对经济档模型（gpt-5.5-mini 等）最能压编造。
- 原文位置：SKILL.md §14、§16.4；无独立句式库文件。
- 修复建议：新增 references/missing-data-phrases.md，把"缺价格/缺案例/缺合同/缺交付周期"等各写一句可照抄合规话术。

## L 级（文档卫生）

### L1 · skill 命名三处不一致
- 描述：同一 skill 在不同文件用了三个名字：SKILL.md name=`daily-report-v1-2`、data-fetch-rules/eval-v2-* 正文自称 `customer-chat-analyzer`、openai.yaml display_name=`日报skill-v1.1-7.6`。显补丁拼接痕迹。
- 原文位置：SKILL.md frontmatter；data-fetch-rules.md §1、eval-v2-sop.md 标题；agents/openai.yaml。
- 修复建议：全包统一为一个 canonical 名（如 daily-report / 客户日报），版本号单列。
