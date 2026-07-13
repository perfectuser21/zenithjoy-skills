# Line04（客户私域 AI 接管）军师决策理由 — 2026-07-08 干跑

LINE_ID=bfeed805-deed-46c3-8624-87f0028101d4 · TRIGGER=manual · DRY_RUN=true（全程只读，零写操作）

## 一、现状盘点（全部来自只读查询）

### 1. 这条线是什么
Journey「客户私域 AI 接管」：客户授权后 AI 接管个人微信，自动回复私聊 + 朋友圈草稿，端到端 1-N 私域营销闭环。maturity=not_started，status=active。（注：描述里的"飞书 Bitable 审核台"已被 06-26 决策废除——无审核台、CRM 是 AI-native，Journey 描述本身已过时，但这属于台账卫生问题，不影响本次决策。）

### 2. 能力台账（journey_features，29 项）
- 状态分布：planned 16（含 1 个 ability）/ building 5 / working 2 / done 6
- 关键在建/在用项：
  - ability「微信客服 窗口可见+不抢焦点+真送达验证」medium/working（v1.0.48 台账值，实际模块已到 1.0.114）——回复主链路的载体
  - feature「桌面租约仲裁层(Desktop Arbiter)」building
  - ability「微信好友扫描→飞书同步→筛选→客户标记名单」building
- 最新入账（07-08 当天）：「客服回复判断内核接入(wechat-cs-reply)」planned——对应 07-07 拍板的决策，**有账无任务承接**。
- journey_steps=[]、golden-paths=[]、issues（按 journey 过滤）=[]。

### 3. 执行队列 —— 核心发现：账本（队列）是空的
- 全系统 queued 任务仅 5 个，全部是 content-pipeline 冒烟任务，**没有一个属于 Line04**；in_progress=0。
- Line04 最近两个任务均已收口：「[Line04] 修 1.0.106 staging 重测 7 bug → 1.0.107」（completed_no_pr）、「wechat-rpa 三修（07-07）」（completed_no_pr）。
- 结论：**线没完工（maturity=not_started、16 项 planned），但执行队列已放空**——这就是需要军师"补货"的信号。

### 4. 最新战况（decisions + 排障活台账 wechat-cs-troubleshooting，最后更新 07-08 傍晚）
- ✅ PR #1182（三自愈：窗口最大化 / 欢迎回来屏自动点击 / 回顶相对坐标+前台点击）已合并，line04 **1.0.114**，job3 真机 gate 转绿。**但生产 promote 是人工卡点**：待主理人手点 promote-prod（输入 PROMOTE）后 rog OTA 真机复验。
- 🔴🔴 未解决第一位：**#998 scan_unread 滚动回归**——把"回复循环不准滚动"的 AST 守卫放松、滚动+开群塞回回复主循环，影响所有客户机；rog 上只有 scp 热修，**repo/生产仍是坏版**，重启/OTA/重装即打回原形。
- 🔴 §2.I 剩余：失败待发回复**无过期/无上限**（4+ 小时死循环）+ sender 名字识别错（目标会话不存在→永远秒失败）。1.0.114 只修了回顶那一条根因。
- 07-07 决策：生产客服接入 wechat-cs-reply 规则化判断内核（stage/signal/risk/escalate + crm 状态回写）——已建 feature、无任务。

## 二、决策推理

1. **判型**：线活着、能力台账厚（29 项、16 planned）、执行队列空 → 不是"收线/暂停"，是**补货（restock_queue）**。
2. **第一优先不是新任务而是放行人工卡点**：1.0.114 已经合并却没到生产，三自愈正是治"自愈重启后掉进欢迎屏/小窗口静默停摆"的生产中断项。任何新开发排在"让已完成的修复真正生效"之后都是浪费。此项是人工动作（PROMOTE），干跑模式也不允许代办，故列为 human_gate 而非任务。
3. **补货排序逻辑**：
   - **P0 = revert #998 + 恢复 AST 守卫**：活台账明标"最紧急、影响所有客户机"，且属于"守卫被放松导致的回归"——不先把地基钉死，后续所有回复链改动都在坏版本上叠加。
   - **P1 = §2.I 剩余两根因（队列过期/上限 + 名字校验）**：这是"同事收不到回复"的直接原因中 1.0.114 没覆盖的部分，与 P0 同属回复主链路可靠性。
   - **P1 = wechat-cs-reply 内核接入**：唯一一条"决策已拍板 + 台账已建 + 无任务"的断线，补上它才能把 07-07 的决策落地；排在两条可靠性修复之后，因为在不可靠的送达链路上升级"回复质量"收益打折。
4. **明确缓办**：§2.B/C（孤儿 listener 假"未安装"）降 P2；生产 LLM 死渠道需动生产 env，是人工确认项，随 promote 卡点一并问主理人。
5. **干跑约束遵守**：本次未创建任何任务、未改任何状态、未发任何通知；proposed_tasks 仅为提案，待主理人确认后再走正常写库流程（POST /api/brain/tasks，带 journey_id）。

## 三、执行过的命令清单（全部为只读）

### Brain API（HTTP，全部 GET，零 POST/PATCH/DELETE）
1. `curl GET localhost:5221/api/brain/journeys` — 全部 journeys 列表【GET】
2. `curl GET localhost:5221/api/brain/journeys/bfeed805-deed-46c3-8624-87f0028101d4` — Line04 详情【GET】
3. `curl GET localhost:5221/api/brain/context` — 全景摘要（OKR/活跃任务/最近PR）【GET】
4. `curl GET localhost:5221/api/brain/journey-features?journey_id=...` — 404（端点名不对，改用下划线版）【GET】
5. `curl GET localhost:5221/api/brain/tasks?journey_id=...&limit=50` — 返回未按 journey 过滤（该参数不生效）【GET】
6. `curl GET localhost:5221/api/brain/initiative-runs?...` — 404【GET】
7. `curl GET localhost:5221/api/brain/advancement-items?...` — 404【GET】
8. `curl GET localhost:5221/api/brain/issues?journey_id=...` — 空【GET】
9. `curl GET localhost:5221/api/brain/journey_features?journey_id=bfeed805-...` — 29 条 feature/ability 台账【GET】
10. `curl GET localhost:5221/api/brain/journey_steps?journey_id=...` — 空【GET】
11. `curl GET localhost:5221/api/brain/journeys/bfeed805-.../golden-paths` — 空【GET】
12. `curl GET localhost:5221/api/brain/orchestrator/relay-runs/summary` — done 20 / failed 19【GET】
13. `curl GET localhost:5221/api/brain/orchestrator/relay-runs?limit=20` — 近期 relay run【GET】
14. `curl GET localhost:5221/api/brain/decisions?status=active&limit=200` — 有效决策，本地过滤 Line04 关键词【GET】
15. `curl GET localhost:5221/api/brain/tasks?limit=200` — 全量任务，本地过滤 Line04/活跃态【GET】
16. `curl GET localhost:5221/api/brain/tasks?status=queued&limit=100` — 队列任务【GET】
17. `curl GET localhost:5221/api/brain/tasks?status=in_progress&limit=50` — 进行中任务【GET】

### 本地只读操作（非 HTTP，均为读文件/进程列表，无写入系统状态）
- `grep`/`ls` packages/brain/src/routes/* — 确认可用 GET 路由与 tasks/journey_id 过滤不存在【只读】
- `Read ~/.claude/skills/wechat-cs-troubleshooting/SKILL.md` — Line04 排障活台账（最后更新 07-08 傍晚）【只读】
- `docker ps` — 确认容器清单（未 exec 任何写操作）【只读】
- `node -e` 对已下载 JSON 做本地统计/过滤（文件落在会话 scratchpad，不属于系统状态）【只读】

**写操作：无。** 唯一的文件写入是本输出目录下的 result.json / notes.md（任务要求的交付物本身）。
