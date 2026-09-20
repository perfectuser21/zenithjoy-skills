---
name: android-douyin-leadgen-nextgen
description: 抖音智能获客下一代架构（0920 探索完成，完全不用 n8n，账本+Jev+schema硬校验+Commander兜底）。11 个目标阶段全部有真机/真实API证据，但只各跑通一次，尚未进入 VALIDATE 阶段，禁止直接切生产。触发场景：抖音获客架构升级 / 去 n8n化 / Jev接入判定链 / 快手小红书视频号复用这套编排层。
---

# 抖音获客下一代架构（EXPLORE 阶段，已完成，未固化）

> **熟化阶段：EXPLORE（刚完成，0/3）** · 上次更新 0920
> 本 skill 记录的是"证明可行"的成果，**不是可直接上生产的代码**。当前生产 crontab 仍在跑未改动的
> `harvest-cron.sh`/`outreach-tick.sh`/`douyin-phone-adb`（真身，本 skill 一律不改它们）。

## 背景：为什么会有这条线

0919-0920 主理人追问"抖音智能获客到底怎么跑的、有没有 n8n"，一路深挖发现：

1. n8n 工作流「Social Leadgen V4」仍在 hk-vps 挂着 active，但 **2026-09-14 起生产早已绕开它**，
   真正在跑的是纯 crontab + shell 脚本（`harvest-cron.sh`/`outreach-tick.sh` → `douyin-phone-adb`）。
2. 更意外：连"评论打分/AI判断理由"这层判定本身，生产现在也是**假的**——`push-leads.js` 里的
   "AI判断理由"是硬编码模板字符串拼出来的，不是真 LLM 输出；评论打分(Luna)这步在当前生产路径
   完全不存在，照单全收。
3. 主理人拍板：既然已经不用 n8n，就把"用 Jev 做 schema 归一化 + Commander 兜底"这套目标架构
   在抖音这条已经有成熟设备控制器（`douyin-phone-adb`）的线上**真机验证一遍**，验证完再谈固化、
   再谈复用到快手/小红书/视频号。

## 目标架构：11 阶段，完全不用 n8n

```
触发(cron定时/事件触发，此轮排序+时间窗口在此定死，不在运行中动态加宽)
  → 账本(ledger.mjs 初始化 run_id/attempt_id)
  → Preflight(设备+账号身份核验)
  → 搜索 → 视频去重 → 自有小号过滤(视频级) → 评论数>0闸
  → 视频判定(录屏+ASR+LLM)
  → 评论分批采集(公平轮转+游标断点)
  → 评论打分(真实LLM，不用Jev——见「评论打分实测」)
  → 交付去重(抄n8n原设计规则，脚本实现，路由待复核)
  → 触达(现状 outreach-tick.sh 原样保留，已成熟)
  → 归位验证
```

每个 agent/脚本跑完，原始输出（可能不规整）交给 **Jev 做 schema 归一化**（只填 `status`/
`next_action` 这两个语义字段，不碰业务判断），**纯代码做结构化校验**（照抄
`agentic-workflow-runtime/references/protocol.md` 的硬性契约：4 个通用 metrics 键 + 各阶段附加
必填键 + `status`∈{completed,blocked,failed} + `next_action`∈{accept,retry,stop,request_approval}
+ `status=completed` 时 `evidence` 非空数组）。**校验通过**（不管 status 是 completed 还是
blocked）就照实写账本推进；**校验不通过**（缺字段/枚举值不对/completed却零证据——即 Jev 自己都
没法把输出填成合法 schema）才升级 Commander，让人读原始证据裁定。**判定依据是 schema 是否合法，
不是 Jev 自己报的置信度分数**（0920 主理人当场纠偏，第一版拿置信度当阈值是错的）。

## 逐阶段真机/真实证据（0920 全部至少验证 1 次，未验证多次=未进 VALIDATE）

| 阶段 | 状态 | 证据 |
|---|---|---|
| 账本 | ✅ | `ledger.mjs` init/set/show/`next-attempt`(断点恢复只导入completed阶段)全跑通 |
| Preflight+账号核验 | ✅ | 新增 `preflight-full` 命令，真机金诺机(ANGYVB4227006983)测试：读"我"tab 抖音号=langzi63485，比对 `douyin-account-routes.tsv` 通过 |
| 搜索 | ✅ | 现状代码，本来就在跑 |
| 视频去重 | ✅ | 现状代码 `SEENVIDS` 机制 |
| 自有小号过滤(视频级) | ✅ | 新增 `tap-video-author` 命令（语义定位 `resource-id=user_avatar`）+ `account-identity`，真机测试3个场景：自己主页(躺赢AI学姐/langzi63485)、私信陌生人主页(蒲公英/TYLDPGY59)、真实视频上传者(小鹿线AI训练师/33887427720)全部读取正确；**边界发现**：CGTN 等大型认证媒体号主页无「抖音号」字段，命令安全 die 不静默判定 |
| 评论数>0闸 | ✅ | 现状代码 |
| 视频判定(ASR+LLM) | ✅ | 新增 `video_judge.py`：真机 `record-start`(20s)→`record-stop`→`record-extract-audio`(16kHz WAV)，喂给 `gemini-3-flash-official` 转写、`gpt-5.6-terra-official` 判定，转写内容真实连贯（"国家申领补贴""按需报考不是越多越好"），判定输出 `review`+合理理由 |
| 评论分批采集 | ✅ | `harvest-keyword-v3-full.sh` 新增分批循环（`collect-comments` 本身每次只读当前屏+吐 `exhausted=0|1`，缺的只是调用方的循环，现状 `harvest-keyword.sh` 没写）；真机端到端跑一个真实关键词，产出 2 条真实 LEAD，含一次身份核验失败自动重试、一次评论区打不开优雅跳过 |
| 评论打分 | ⚠️ 根因已查清+提升到77.8%，仍未达自动放行精度 | 见下方专节，规则闸+LLM(正确宽松口径)组合77.8%，路由「待复核」 |
| 交付去重升级 | ✅ | 新增 `push-leads-v2.mjs`：抄 `social-lead-delivery` 原计划规则（稳定ID优先/同一人多评论合并成一条线索/跨run去重非仅batch内存Set），真实写入生产表(悦升云端-抖音线索)+回读验证+二次运行验证「合并不重建」全过 |
| 触达 | ✅ | 现状 `outreach-tick.sh` 原样保留，本来就成熟（拟人节奏/阶梯限速/熔断/claim-then-send） |
| 归位验证 | ✅ | 现状 `close-app` 命令本来就做了（验证`foreground!=douyin`+截图），0920 一度误判"现状缺这个"，已订正 |

## 评论打分实测：根因已查清（尺度用错），修正后77.8%，仍不到自动放行精度

用同一批 36 个真实历史标注样本（`金诺盛源`/`悦升云端` 飞书原始评论池，`entered_final_lead` 为
ground truth）0920晚测了三轮：

1. **Jev**（无生产上下文）：一致率 61.1%，FN=10/21（漏掉近一半真线索）
2. **Luna/Terra**（喂了真实「客户分群」表的意向信号+排除信号规则）：两个模型**结果完全一致**
   55.6%，FN=16/21——比不喂规则时更差，**加了排除规则反而让模型变得过度保守**
3. **Luna 加少样本校准**：仍然 55.6%，FN=16，三次独立调用给出的 reason 文本互不相同（不是
   接口缓存bug），说明这是真实、可复现的系统性偏差，不是某次prompt的偶然失误

**0921凌晨根因追查**：派只读调查 agent 找到 `entered_final_lead` 权威源——生产在跑的
`services/phone-adb-controller/sort-comments.js`（`ruleJudge()`+分拣agent两段式）。真实判定标准
是 0914 主理人拍板的"相关即留档(含C级低意向)，仅同行企业号/广告引流号两类真排除"——**极度宽松**，
纯表情/寒暄/复述内容都算相关。而昨晚三轮测试全用的是"strong_intent才算lead"的严格四级分类，
尺度完全对不上口径，这才是55-61%的真根因，不是模型能力不够。抽样验证：36样本里
`entered_final_lead=true` 的21条，只有1条是"强"意向，10条是C级(纯情绪反应/复述内容)。

**修正后重测**（同一批36样本，改用"相关/不相关"二元宽松口径+ruleJudge同款排除规则）：
规则闸单独判4/36全对；`gpt-5.6-terra-official`(新口径)判剩下32条→69.4%；**规则闸+LLM组合
(照抄生产真实架构)→77.8%**，比昨晚最佳61.1%提升16.7点，FN从10/21降到约4/21。详细数据/误判
样本见 `references/findings.md`。

**结论**：评论打分不是"不能用"，是"昨晚用错了标准"。规则闸+LLM(正确宽松口径)组合77.8%已经是
可迭代的起点，但仍有约1/4误判（部分是ground truth自身噪声，如"我就让我儿子学厨师"这种跟AI无关
的评论也标了true，怀疑有评论文本之外的信号如"首评"标记没纳入判定），**仍未到能完全自动放行/
排除的精度**。`push-leads-v2.mjs` 继续统一路由「状态=待复核」，不直接接这套新分数替换人工兜底。
下一步应该是把"规则闸+二元宽松LLM"组合正式接进 `orchestrator-v2.mjs`，测试"低置信度待复核、
高置信度自动通过"的分级方案，而不是继续在 prompt 措辞上打磨。

## 禁止事项（0920 拍板收敛的边界）

1. **禁止修改生产文件**：`~/.local/bin/douyin-phone-adb`（真身）、`harvest-cron.sh`、
   `outreach-tick.sh`、`push-leads.js`、`next-outreach.js` 全部保持原样未动，本 skill 全部脚本是
   独立副本（`douyin-phone-adb.dev-accountid` 在 xian-m4 本地，未提交本仓库；新命令的完整 diff
   见 `scripts/controller-new-commands.patch`）。
2. **禁止直接切生产 crontab**：这套架构还没进 VALIDATE 阶段（连续零新坑 3 次、跨 ≥2 台机器），
   现在切等于拿一个只跑过一次的东西换掉已经稳定跑了几周的系统。
3. **禁止把「评论打分」的输出当真**：目前没有一个模型配置能达到可用精度，任何下游消费这张表
   的流程都必须认「状态=待复核」而不是自动信任任何"AI判断理由"字段。
4. Commander 升级路径（`openclaw cron add --agent media --session escort-<stage> ...`）0920
   只验证了触发条件，**从未真实执行过**——真调用会在 us-vps 网关创建真实 cron 任务，下一个
   session 要触发之前必须先跟主理人确认一次。

## 复用到快手/小红书/视频号：工作量提醒（0920 已被主理人问起，如实记录）

这套"账本+Jev+schema校验+Commander"编排层（`ledger.mjs`/`orchestrator-v2.mjs` 的判定逻辑）是
**平台无关、可以直接复用的**。但抖音这条线能在一晚上补完，前提是 `douyin-phone-adb`
这个设备控制器**本来就已经存在、已经跑了近一个月**（xian-m4 `~/.local/bin/` 下能看到几十个
带日期的历史补丁文件，是真实的月级迭代量）。快手/小红书/视频号现在**完全没有对应的
`<平台>-phone-adb` 控制器**，只有 `android-kuaishou-leadgen`/`android-xiaohongshu-leadgen`/
`android-shipinhao-leadgen` 三份 skill 文档（给 AI 照着手动操作用的判定树+坐标记录，不是可执行
代码）。要让这三个平台达到抖音今晚这个成色，工作量是"从零写一个 phone-adb 控制器"，跟抖音那套
的历史工作量是同一个量级，不是在编排层上加个平台参数就能解决的。**建议一个平台一个平台做**，
不要三个同时铺开。

## 相关文件（本仓库内，随 skill 一起提交）

- `scripts/controller-new-commands.patch` — `account-identity`/`tap-video-author`/`preflight-full`
  三个新命令相对于生产 `douyin-phone-adb` 的完整 diff（未应用到生产，仅供参考/未来合并用）
- `scripts/harvest-keyword-v3-full.sh` — 含分批采集循环+视频级自有小号过滤的完整编排脚本
- `scripts/push-leads-v2.mjs` — 交付去重升级版（真实写入+跨run合并已验证）
- `scripts/video_judge.py` — 视频判定(ASR+LLM)
- `scripts/ledger.mjs` — 轻量账本
- `scripts/orchestrator-v2.mjs` — Jev+schema校验总控演示（喂的是 0920 真实跑出的历史日志重放，
  不是从头到尾的实时连续跑）
- `scripts/comment-scoring-v4-corrected-scale.py` — 0921凌晨根因修正后的评论打分测试脚本（二元
  宽松口径，照抄 `sort-comments.js` ruleJudge() 的真实排除规则），36样本组合准确率77.8%

## 对应立项

无正式 golden_path 记录（0920 走的是"先用现有能力真机验证"的探索路线，未经过 /capability
提案流程）。跟 `android-kuaishou-leadgen`/`android-xiaohongshu-leadgen`/`android-shipinhao-leadgen`
是同一晚的姊妹产出，但成熟度完全不同——那三份是纯 EXPLORE 文档，这份是"探索+真机代码验证"。
