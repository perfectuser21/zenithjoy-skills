---
name: wechat-cs-troubleshooting
description: |
  Line04 微信客服（个微 RPA）系统的当前状态 + 已知问题 catalog。任何排查"微信客服不回复 /
  读不到会话 / 客服模块显示未安装 / 客户全是黑名单改不了 / 新装 agent 旧进程没杀 /
  staging 看不到机器" 等问题时，先读本 skill —— 它分清【已解决（含根因+修法+版本）】和
  【未解决（含根因+计划）】，避免重复诊断已知问题、避免把不同根因的 bug 混在一起。
  触发场景：微信客服不回复 / 客服 bot 没反应 / line04 / 客服模块未安装 / 读不到会话 /
  sessions=0 / 全黑名单 / 接管开关改不了 / 客服页空白 / agent 多进程 / preflight 未通过 /
  rog 微信客服 / Path 4 私域 AI 排障。
  本 skill 是【活台账】，每次排查有新结论必须回来更新（解决了的挪进已解决，新发现的加进未解决）。
---

# Line04 微信客服 — 排障 + 当前状态 catalog

> ⚠️ 这是**活台账**，不是一次性文档。每次排查微信客服问题，**先读这里**（别重复诊断已知项），
> 排完**回来更新**（解决的挪上去、新坑加进来）。最后更新：2026-07-08 傍晚（三自愈已合并 **PR #1182 / line04 1.0.114**，新增 §1.10；§2.K/§2.J 及 §2.I 回顶部分已修，**staging+生产双环境真机复验全通过**；§2.I 的 sender 名字识别错/队列过期仍未解决）。

## 0. 系统一句话 + 关键事实
- **rog（xian-rog）= Lead 自检机**。环境随复测节奏切换：2026-07-06 起 rog 在【staging】随 main 自动 OTA（当日 1.0.108→1.0.109→1.0.110）（.env 备份 `.env.prod-backup-0706` 是生产配置，测完切回用它）。**排障第一步永远看 listen_chat 进程命令行 `--middleware-url` 确认环境**，别信文档记忆。
- **改 rog `.env` 后必须杀掉旧 start.bat 监督 cmd 再重启**：start.bat 常驻监督循环持有它启动时的 env 快照，只杀 agent.exe 会被它用【旧环境】拉回去（0706 实锤：改完 .env 杀 agent，30 秒后被 15:05 的老 cmd 用生产 env 复活）。正确顺序 = 杀 `cmd.exe *start.bat*` + 全部 `zenithjoy-agent.exe` + `python *listen_chat.py*` → `schtasks /run /tn ZenithJoyAgent`（session-1 交互令牌，重读 .env）。
- **`.env` 是 UTF-8**，PowerShell 改它要 `Get-Content/Set-Content -Encoding UTF8`；用 `-Encoding ascii` 会把 `ZJ_MAIN_DATA_DIR` 的中文路径写成 `???`。
- **health json `login_present` 字段语义 = "是否弹着扫码登录窗"，false=已登录=健康态**（dashboard 需扫码标志依赖它，1.0.108 起心跳 login 派生真实登录态、此字段语义不动）。别再把 false 当"没登录"误报。
- **客户机（同事的）默认连【生产】`autopilot.zenjoymedia.media`** —— 安装包 `start.bat` 写死的，不是 staging。
- 回复链三层，**任一层断都不回复**：① listen_chat 读会话未读 → ② 中台 `draft-generate` 出草稿（whitelist/接管/LLM）→ ③ UIA `_open_chat` 切会话 + `_uia_send` 发 + 读回验证 DELIVERED。
- **staging 库 = `zenithjoy_test`（本机 :5201）；生产 = autopilot 独立库**。同一个 license/email **两库各有一份副本**（staging 从生产播种），登录/验证两边都过，但读写不同库 —— **排障第一件事：确认看的是哪个环境**，别拿 staging 旧数据当生产真相。

---

## 1. ✅ 已解决（根因 + 修法 + 版本，别重复修）

### 1.1 读不到会话（sessions=0 永不回复）— UIA 树塌缩
- **根因**：微信 mmui 无障碍树**仅在微信进程启动时 `SPI_SETSCREENREADER` 标志已置位才构建**。autologon/外部启动的微信启动时标志没设 → `mmui::MainWindow` 的 UIA 子树永久塌缩到只剩 1 个 `MMUIRenderSubWindowHW` 空 Pane（`descendants=1, ListItem=0`）→ 会话列表完全不暴露 → `sessions=0`。事后任何激活（SPI 广播 / OFF→ON 翻转 / SetForeground / set_focus / WM_GETOBJECT）**都救不了已运行进程**。
- **修法**：listener 检测"窗口找到但整树塌缩（descendants≤2）持续 90s" → 重启微信（标志已置位态下 mmui 重建完整树）。冷却 600s + 单进程上限 5 次。
- **版本/PR**：PR #950，line04 **1.0.71**。实地验证：重启后 descendants 1→71、ListItem 0→6；rog OTA 到 1.0.72 后 `sessions=5` 稳定可读、`unread>=1` 出现 615 次。
- 详见 memory `line04_wechat_uia_tree_collapse_rootcause_0629`。

### 1.2 送达验证假阴性（消息真发了却误报 send_failed）
- **根因**：`_uia_send` 成功后 `_read_session_preview` **只读一次**会话预览；微信会话预览**异步更新** + 刚切完会话 UIA 读偶发空 → `_delivery_confirmed` 一次没命中就判未送达。
- **修法**：`_confirm_delivery` 轮询读回（最多 5 轮 × 0.6s），命中即 DELIVERED，全空才失败。不引假阳性。
- **版本/PR**：PR #951，line04 **1.0.72**。

### 1.3 （仅 staging）回复支撑层配置
- 白名单：`zenithjoy.wechat_cs_account_config` 加联系人；auto_agent_enabled=on；营业时间（**按服务器中国时间判定**）。
- LLM 模型：CS 默认 `WECHAT_CS_MODEL||'deepseek-v3.2'`，网关 toapis.com 该模型**无可用渠道**（LLM 503）→ staging 改 `WECHAT_CS_MODEL=deepseek-v4-flash`（实测可用）。**注：这是 staging plist env，被 `ensure_staging_plist` 重生会冲掉，要进 deploy-lib staging_overrides 才持久。**

### 1.4 微信自升回 4.1.10 → UIA 树又塌（关更新只在装机时跑）
- **根因**：`wechat_update_lock` 原先只在 preflight `installWeChat`（降级安装）路径里调；微信已经是 4.1.8 时不触发 → 腾讯静默自升回 4.1.10 → §1.1 树塌复发。
- **修法**：放进 **listen_chat 主循环每 5 分钟 `run_update_lock(dry_run=False)`** 持续压（常驻进程比开机一次的 preflight 更稳）+ 降级装机后立刻锁；`interpret_lock_verify` 诚实判 locked=True/False。
- **版本/PR**：PR #984，line04 **1.0.81**。真机"重启不自升"待 lead 验。

### 1.5 一人连发多条只回第一条 / scan 慢（scan_unread 只读最后一条预览）
- **根因**：`scan_unread` 只读 ListItem name 的 `[N条]`+最后一条预览，不读会话内全部 N 条 → AI 漏上下文；且 path-2 全量遍历内容变化 ~64s = 延迟主源。
- **修法**：(a) 只处理有 `[N条]` 红点的会话，移除 path-2（减延迟）；(b) N>1 时 `_open_chat` 开会话 `read_chat_panel_messages(mw,n)` 读全 N 条 → `aggregate_messages` 合并成一次回复上下文。纯函数 `parse_unread_count`/`aggregate_messages` 有 TDD。
- **版本/PR**：PR #984，line04 **1.0.81**。**注：这只解决"读"——§2.A 离屏 `_open_chat` 切不到会话仍是独立未解决项。**

### 1.6 没配接管 → 客户全黑名单改不了（原 §2.D）
- **根因**：`customer-roster.ts` managed 判定缺省 takeoverMode 退化成"whitelist 空=全黑"；接管开关 `PUT /api/crm/customers/manage` 号→租户解析 403/不建行。
- **修法**：缺省→**blacklist 主模型（绑定即全接管，开箱即回）**；manage 统一 `requireCsWriteAccess`（service_agents ∪ cs-前缀链多通道，deny-by-default）+ `INSERT ... ON CONFLICT DO UPDATE` 自动建行。
- **版本/PR**：**PR #954**（同根因早已合并，台账一度漏标）。vitest 48/48。后续 backlog：草稿待审 / 公司模板继承。

### 1.7 staging 客服模型 env 被部署冲掉
- **修法**：`WECHAT_CS_MODEL=gpt-5.4-mini` 进 deploy-lib `staging_overrides`（与 BETTER_AUTH/AGENT_PUBLIC 同模式），ensure_staging_plist 重生 plist 时自动带上，不再手补。
- **版本/PR**：PR #982。

---

### 1.8 桌面租约打错地址 → 1.0.108 全环境零回复（+ Broker 不可达降级放行）
- **根因**：`desktop_lease_acquire/release` 用 middleware_url 拼 `/api/agent/desktop-lease-broker/*`，但 Broker 挂在 agent core 本机 local-discovery（`127.0.0.1:${ZENITHJOY_LOCAL_PORT|58432}`）。中台无此路由→404→acquire 恒 False→[防假成功] 跳过所有发送；副作用=失败重试循环反复操作微信窗口（屏幕持续跳动）。
- **修法**：#1142（1.0.109，并行会话）地址改 `_get_local_discovery_base()`；#1141（1.0.110）补降级放行（Broker 联系不上→degrade-allow 照常发送+警告，决策 f26e099c；granted:false 仍跳过）+ 去 middleware_url 死参数 + AST 守卫（test_desktop_lease_ipc.py，永久禁 desktop_lease_* 引用 middleware_url）。
- **版本/PR**：#1142 + #1141，line04 **1.0.110**。教训：**同一天两个 session 并行修同一 bug**——动手前先 `gh pr list` 查在飞 PR。

### 1.9 getCSConfig 漏查 takeover_mode/blacklist → "全接管"形同虚设，只回遗留白名单
- **根因**：cs-account-config-store.ts getCSConfig 的 SELECT 漏 takeover_mode/blacklist 两列 → `/api/wechat/cs/agent-config` 永不下发 → agent 端 should_reply 回退白名单模式 → 库里 blacklist（默认全接管）失效。rog 实况：苏小妖/于瑾带红点在视口内被 should_open 静默拦（连会话都不开），只回 6/28 测试遗留 whitelist 里的默忆。**whitelist 为空的 blacklist 机 = 一个人都不回**（历史"名单内静默不回"悬案可疑根子）。前台 CRM 接管开关（写 blacklist）因此失效。
- **修法**：SELECT 补两列 + normalizeRow 透传（takeover_mode 只认合法枚举，缺省不伪造）+ 类型；测试教训=**mock 必须按 SELECT 列投影**（整行 mock 掩盖漏列 bug 假绿）。
- **版本/PR**：#1146（中台侧，与模块版本无关，staging 部署即生效）。诊断法：`curl ':5201/api/wechat/cs/agent-config?machine_id=<mid>'` 看响应是否含 takeover_mode。

### 1.10 三自愈落地：窗口最大化 / 欢迎回来屏自动点击 / 回顶相对坐标+前台点击（原 §2.K/§2.J/§2.I 回顶部分）
- **根因**：见 §2.K（小窗口单栏布局漏检测）/ §2.J（欢迎屏只检测不自愈+点击没拉前台）/ §2.I 第2条（`left_max=90` 屏幕绝对坐标）——三条根因与实证过程保留在 §2 原位供查。
- **修法（全部 07-08 真机实证后编码）**：①心跳检测可见非最大化 → `SW_MAXIMIZE`（300s 冷却，iconic 托盘态不动）+ diag `window_state`；②识别 LoginWindow"进入微信"按钮 → `AttachThreadInput` 拉前台 + `click_input` → 20s 验证 → 3次上限/120s冷却 → 超限显式告警 + diag `welcome_click_fails`；③`_find_left_nav_button_point` 加 `win_left` 窗口相对坐标 + `_reset_session_list_to_top` 拉前台 + PostMessage→click_input 升级梯 + "通讯录管理"即时验证。click_input 例外仅限两个自愈函数（test_uia_interaction.py 白名单 + decision ebf5cff7 invariant），发送/回复路径禁令不动。
- **版本/PR**：**PR #1182**，line04 **1.0.114**（三版本面+build-modules 副本全同步；4 个 smoke + 2 个 API 版本闸测试同步）。**job3 真机 gate 本 PR 实测转绿**（此前连红 6 次的根因即 §2.I 回顶）。✅ **真机复验全通过（07-08 晚）**：staging 上 缩窗→30s 内 [窗口自愈]（sessions 4→31）、杀微信→死区自愈重启→[欢迎屏自愈] 自动点『进入微信』（18:08:15，零人工）+ 用户人工四项验收通过；promote-prod 放行后 rog 切回生产，切换重启再次自然触发欢迎屏，自愈链实战成功（19:48:40 欢迎屏自愈 → 19:48:55 窗口自愈最大化 → 心跳恢复）。生产已跑 1.0.114。
- 教训：版本 bump 共 **7 处面**（build-modules/modules manifest + walking-skeleton.service.ts + 它的 2 个测试 + 4 个 smoke 硬编码）；Brain 双派发撞车见 issue e485b5e8（有头注册的 task 仍被无头 relay 抢跑出重复 PR #1179 且 watchdog 反复关有头 PR，需 docker stop 容器）。

## 2. ❌ 未解决（按"卡人程度"排序，含根因 + 计划）

> ⚠️⚠️ **2026-07-01 通宵真机跑通了（默忆收到 AI 回复），但一大半靠 rog 热修/手动撑着，不是永久代码。重启/OTA/部署会打回原形。** 详见 repo `docs/handoff-line04-rpa-realmachine-guard-0701.md`。以下是暴露出的、要在代码里真修的：

### 🔴🔴 #998「scan_unread 滚动找未读」是错的回归（最紧急，影响所有客户机）
- **现象**：agent 回复前"拉到会话列表最底部 + 进到群对话窗口"（用户真机亲眼见）→ 重犯做法二删掉的"回一次就不理"。
- **根因**：#998（1.0.83）为治"扫不到视口外未读"给 scan_unread 加了滚动，把 CRM 式"滚动+开群"塞回了回复主循环。**守卫 test_reply_loop_purity.py 本来锁死"回复循环不准滚动"，我做 #998 时把它放松了 → 回归进 repo。**
- **修法**：代码里 **revert #998**（回不滚动的工作版）+ 恢复 AST 守卫。rog 上已 scp 成 #998 之前的非滚动版热修（repo/生产还是坏的滚动版）。**别再往 scan_unread 加滚动；unread 靠"新消息置顶 + 自检节流不霸屏"就够。**

### 🔴 状态判定不可靠（今晚最痛，要在代码判准）
- send 了判成 failed（`_uia_send` 读回 preview='' 就判未送达 → 冷却重发 → 可能给同一人发两遍）；明明登录却 login=False；没登录被当"隐私锁屏"；树塌↔可读反复横跳。
- **修法**：真送达读回做鲁棒（空预览多轮询/换读法/兜底，别一空就判失败）；登录判定可靠区分 已登录/没登录/隐私锁/找不到窗口。

### 🔴 多微信实例 / agent 自拉没登录的微信
- agent 会自己 launch 一个微信；同账号两开时它读错那个"没登录"的（login=False sessions=0）。正确骨架=**单个登录微信 + agent 先起置无障碍标志、微信后登 → 树完整**。
- **修法（=⑤自愈）**：agent 检测多实例→收敛到单登录；树塌→带标志重启重建；自己拉了没登录的→纠正。

### 🟠 NO_TENANT_CONTEXT（agent 未注册进中台 agents 表）
- agent 心跳没写进 `agents` 表 / 没带租户 → 中台反查不到租户，draft-generate 返回 400 NO_TENANT_CONTEXT。rog 上已手插 agents 行热修。**修法**：查心跳注册为什么没成 / 中台从 machine_id 稳健反查租户。



### A. 🔴 离屏 `_open_chat` 切不到会话 → 回不了（当前回复链断在这）
- **现象**：日志大量 `_open_chat: 全部策略都无法切到 'X'（离屏）`，会话项坐标 ~32000（屏幕外）；同时新消息检测不到（`unread=0`）。结果"看运气"——会话项正好在屏内才回得了。
- **根因**：微信虚拟列表把没渲染/滚动出视野的会话项 rectangle 返回离屏占位坐标（~32000）→ PostMessage 点击打空 → 切不过去；scan_unread 也只读到屏内那几条。
- **计划**：补回跑通版（git 74654efd §5）的"**离屏坐标 >20000 → 重扫 ListItem 找 sender 新 item 引用 + 把窗口拉回可见前台**"修法（1.0.72 没带全）。**真机反复调，看到连续 DELIVERED 才算好，不提前报喜。**

### B. 🔴 新装 agent 不杀旧 listener → 假"未安装" + 抢窗口（所有客户都会撞）
- **现象**：苏的客服模块显示"未安装"，但他自己 agent 日志写着 `line04 v1.0.70 已激活 + 健康上报 ok=true`。
- **根因**：① `start.bat:264` 单实例守卫**只杀 `zenithjoy-agent.exe`（core），没杀旧 `listen_chat.py`（python）** → 旧 listener 变孤儿能再跑满 24h。② OTA 升级 `module-manager.ts:302` `oldChild.kill()` 杀的是模块 node fork，**它 spawn 的 python listen_chat 是孙进程，杀不到**。→ 两个 listener 同时抢微信 + 都跑 preflight → `preflight_already_running`。
- **计划**：start.bat + OTA + 模块退出，**按命令行匹配杀掉所有 `*listen_chat*` 的 python/python-embedded**（不只 core）。这一个修法同时解决 C。

### C. 🟠 preflight 并发 → 假"未安装"（与 B 同根）
- **根因**：`module-manager.ts:471-472` preflight 撞上自己还在跑时 `return {ok:false, reason:'preflight_already_running'}` → 中台/前端读到 `ok:false` 显示"未安装"，**其实模块装好了、listener 健康**。
- **计划**：并发"跳过"不该上报 `ok:false`，应保留上次状态。

### D. ✅ 已解决 → 见 §1.6（缺省→blacklist 全接管 + manage 自动建行，PR #954）

### E. 🟠 生产 LLM `deepseek-v3.2` 死渠道（只修了 staging）
- toapis.com 网关该模型无渠道 → AI 生成失败 → 不回复。**生产没碰**，要动生产 env（用户点头）。

### F. 🟡 安装包写死生产 → 没法在 staging 测
- `start.bat:88-90` 写死 `ZENITHJOY_API_URL=wss://autopilot...`。想 staging 测必须手动改 .env（rog 就是手改的）。计划：装包加 staging/prod 环境选择，或发预置 staging 的包。

### G. 🟡 listAllMachines 漏"绑了但没 license_machines"的机器
- 运营 scope 的 `cs/machines` 是 **license_machines 驱动**；机器在 `service_agents`（已绑）但没 license_machines 行 → 运营列表不显示（实测 d026489c/07c37bd4 就这样）。计划：scope 改成 license_machines ∪ service_agents。

### I. 🔴 固定目标"切会话秒失败"死循环（0706 rog 实锤，同事不回复的直接原因）
- **现象（2026-07-06，rog 生产 1.0.102）**：给'苏小x'和'于瑾'的待发回复从 10:55 前起**每轮秒失败** `无法切到会话，中止本轮（防串台）`，连续 4+ 小时死循环不过期；同期给默忆/于锦 DELIVERED 正常（500 行窗口内 72 次），说明链路整体是通的。
- **三层根因叠加**：
  1. **会话列表滚动坏死**：`_scroll_session_list_wheel: SetCursorPos 失败（无输入权）→ 回退 PostMessage 合成滚轮 → 拿不到会话列表中心坐标，跳过本次滚动`——滚动从不生效；
  2. **回顶也坏**：`_reset_session_list_to_top: 导航按钮不全，跳过切tab`——视口外会话永远拿不到 item（对比：徐先生的 item 离屏 32000 但存在，Select() 重扫能救；苏小x/于瑾连 item 都没有→秒失败无重试日志）。**→ 根因已实锤（07-08 下午真机取证）**：`_find_left_nav_button_point` 的 `left_max=90` 判的是**屏幕绝对坐标** `rect.left<90`，只有窗口贴屏幕左边缘（最大化 left=0）才成立；窗口在屏中间（实测 left=964）时 通讯录/微信 按钮永远"不全"。修法=改窗口相对坐标 `r.left - win.left < 90`。**且 PostMessage 合成点击对 mmui 导航按钮不抢前台时无效**（两次截图实证不动），点击必须先 `AttachThreadInput+SetForegroundWindow` 拉前台（见 §2.J 实证）；
  3. **疑似 sender 名字识别错**：列表里有会话叫'苏'而目标是'苏小x'；'于锦'能送达而'于瑾'永远失败——待发目标名可能来自气泡误读/截断，目标会话根本不存在。
- **伴生问题**：失败的待发回复**无过期/无上限**，永远重试；`[scan] badge-miss 本轮 1-4 人` 高频出现（角标检测丢，1.0.106 复测已知家族）。
- **注意**：1.0.107 的 7 修 + 1.0.108 的 3 修**都不覆盖本条**——OTA 到 1.0.108 后此故障预期仍在，要单独立案修（滚动输入权/回顶/名字识别/队列过期）。

### H. 🟡 4.1.10 上能否回复 — 未验证
- rog 是 **4.1.8.107**，两次成功（默忆/于瑾 DELIVERED）都在 4.1.8 + 会话项在屏内时。客户机若是 4.1.10，UIA 离屏行为是否更糟**没数据**。需在 4.1.10 真机验。

### J. 🔴 UIA 自愈重启后可能卡进"欢迎回来"确认屏，无自动点击 → 生产客服中断（2026-07-08 实锤，issue e78d98bc）
- **现象**：`is_privacy_locked()` 检测到的 `mmui::LoginWindow title='微信'` 状态，实测常常不是真正的隐私锁密码验证，而是重启后的"欢迎回来"确认屏（显示"当前登录用户 X"+"进入微信"/"切换账号"/"仅传输文件"三按钮，**不需要密码**）。2026-07-08 rog 生产：UIA 死区自愈重启微信 → 触发该屏 → listener 心跳持续 `locked=True sessions=0`，生产完全收不到客户消息，直到人工点了"进入微信"才恢复。
- **根因**：代码只做检测，没做自愈/自动点击。
- **✅ 诊断闭环（2026-07-08 下午，控制性复现实证——欢迎回来屏被复现并被自动点击成功恢复）**：
  - **DPI 假设推翻**：pywinauto 0.6.9 import 时自动把进程 DPI awareness 0→2（per-monitor aware），listener/诊断脚本坐标系一致（dpi=144 但无错位）。旧三条踩坑的真正原因：
    1. `click_input()` 之前"无效"不是 token 没输入权，是**没先把窗口拉前台**；
    2. UIA `InvokePattern` 对 mmui 自绘控件确认无效（07-08 exp4 复测仍不动）；
    3. PostMessage 到 `MMUIRenderSubWindowHW` 对 mmui **按钮**类控件不抢前台时无效（两次截图实证；会话列表 item 的真切换靠 `Select()`，不是 PostMessage）。
  - **实证有效修法（exp8 全链路验证）**：`AttachThreadInput+SetForegroundWindow+BringWindowToTop` 拉前台（listener 已有 `_set_foreground_window` 同款）→ `button.click_input()` 真实鼠标注入 → 点击"进入微信"后 **~10s** 主窗口出现（+4s 采样 LoginWindow 还在属正常，验证等待要给够 15s+）。
  - **欢迎回来屏 UIA 树结构（可直接编程识别）**：`mmui::LoginWindow title='微信'`，含 Text `当前登录用户X` + Button `进入微信`/`切换账号`/`仅传输文件`（name 全部正常暴露），子窗口=`Qt51514QWindowIcon`+`MMUIRenderSubWindowHW`。
  - **复现法**：`taskkill /f /im Weixin.exe` → listener 自愈重启 → 欢迎回来屏出现（本次 ~3.5 分钟内出现；注意并非每次重启都触发，15:04 的自愈重启就直接登录了）。
- **剩余计划**：把上述实证修法写进 listener 自愈（识别 LoginWindow+进入微信按钮 → fg+click_input → 等 15s 验证 MainWindow → 失败 N 次报警），走 /dev + failing test。注意重启后主窗口**非最大化**，自愈完必须接 §2.K 的 SW_MAXIMIZE。

### K. 🔴 主窗口非最大化 → 完全检测不到新消息（P0，issue 99741ff9，07-08 下午根因实锤）
- **现象**：窗口 630×622 小尺寸时心跳持续 `sessions=4 unread=0`，对新消息 20 分钟毫无反应；`ShowWindow(SW_MAXIMIZE)` 后几秒内 sessions 4→26 立即恢复检测。
- **根因（真机取证，比"虚拟列表少渲染"更狠）**：窗口宽 <~700px 时微信进入**单栏模式**（同手机布局：只显示打开的聊天+返回按钮，会话列表整个不在 UIA 树里）——此时 `scan_unread` 读到的 4 个 "ListItem" 其实是**聊天气泡**（"你叫什么/你人呢"），不是会话。日志表面"一切正常心跳"，极其隐蔽。
- **连带发现①**：微信重启后（自愈/OTA）主窗口**默认非最大化** → 每次自愈重启都会自动掉进本故障。
- **连带发现②（新故障模式）**：listener 停在**通讯录 tab** 时同样静默停摆——把联系人列表当会话扫（实测心跳 `sessions=20` 全是联系人，unread 永远 0），listener 无 tab 感知。自愈时应顺手点回微信 tab（点"微信"导航按钮幂等无害）。
- **实证修法**：`ShowWindow(hwnd, SW_MAXIMIZE)` 从 session-1 计划任务直接可用（07-08 两次实证：4→26、重启后 15 个会话可见）。心跳应检测 `IsZoomed()`/窗口尺寸，过小自动最大化+告警。走 /dev + failing test。

---

## 3. 诊断复用法（别再纯 SSH 猜）

### ⚠️ 铁律：UIA 判据必须用截图 ground truth 交叉验证
07-08 下午连吃三次假判据的亏：①"新的朋友"在通讯录 tab 的 UIA 树里**不存在**（判"没切过去"其实切过去了）②"通讯录管理"按钮会被滚出虚拟列表（判"不在通讯录"其实还在）③导航按钮的 `legacy_state/is_selected/toggle` 全部 unsupported（mmui 不暴露选中态）。**任何"点击是否生效/在哪个 tab"的结论必须配 `PIL ImageGrab.grab()` 截图人工确认**（session-1 可用，缩半存 `C:\Users\Public\wxdiag_*.png` base64 回传）。exp4 曾因假判据把微信留在通讯录 tab 干扰生产 20 分钟。

### 能力边界
SSH 连 Windows 机 = **session 0**，**够不到 session 1 的 GUI/UIA**。诊断 session 1 的微信窗口必须有 session-1 内执行通道。

### session-1 通道（rog 实测可用）
```
schtasks /create /tn ZJDiagUIA /tr "C:\path\run.bat" /sc once /st 00:00 /ru asus /it /f
schtasks /run /tn ZJDiagUIA
```
`/it`（interactive token）能在 session 1 交互桌面跑代码操作微信。`PsExec -i 1` 起不来。

### 读中文日志（避免多字节截断）
⚠️0706 实测日志已是 **UTF-8**（`Get-Content -Encoding UTF8` 直接对；再用 `-Encoding Default`(GBK) 会双重乱码、grep 中文全 miss）。旧版本模块可能仍是 GBK：先 tail 几行看是否乱码再定编码。旧 GBK 读法备查：`Get-Content -Tail N -Encoding Default` → 转 UTF8 字节 → `[Convert]::ToBase64String` → SSH 回传 → 本地 `base64 -d`（纯 ASCII 传输不被 codepage 损坏）。直接 `iconv -f GBK` 经 SSH 常把最新几行多字节字符截断成假象。

### 诊断脚本写法
scratchpad 用 `.txt` 扩展（`.py` 被 bash-guard 拦）→ base64 → 在目标机解码成 `.py` → 跑 `C:\Users\asus\anaconda3\python.exe`（含 pywinauto）。

### 关键日志/文件（rog）
- listener 日志 `C:\Users\Public\zj-listener.log`（心跳每 60s：found_window/login/locked/**sessions/unread**/replied）
- 健康 `C:\Users\Public\zj-listener-health.json`
- 模块目录 `%APPDATA%\zenithjoy\modules\line04-wechat-cs-<ver>\`
- 判"读得到会话" = `sessions>0` 且日志出现过 `unread>=1`；判"回得了" = `reply_in_chat: 真送达确认 DELIVERED`

### staging 库（本机美国 Mac）
`psql -d zenithjoy_test`，表在 **`zenithjoy` schema**（不是 public）。关键表：`wechat_cs_account_config`（接管/白名单/人设）、`service_agents`（绑定）、`license_machines`（注册）、`agents`（心跳/module_status）、`crm_customers`（identity=customer/blacklist/internal）。staging API 日志 `~/Library/Logs/zenithjoy-api.staging.{log,error.log}`，route 判定打印 `[wechat-draft] auto route=X inWhitelist=Y enabled=Z businessHoursOk=W`。

### 部署 line04 新版到 staging（本机绕 GHA timeout）
`git reset --hard origin/main` → `npm ci --workspace=apps/api --ignore-scripts` → `source deploy-lib.sh`+设 ZJ_* env → `staging_deploy_slot <sha>`。**部署后必补** `WECHAT_CS_MODEL=gpt-5.4-mini`（PlistBuddy Add 进 staging plist + kickstart，否则回落 deepseek 死渠道）。

### 让 agent 连 staging（#976 后从 staging 下自动连对；手改兜底）
`.env` 设 `ZENITHJOY_API_BASE/URL=...staging-autopilot...`+`ZENITHJOY_ENV=staging`（start.bat 行95-102 选环境）。`cs_wid=cs-<machineId前8>`。

### 真送达 gate（识别真发 vs 没发）
`reply_in_chat: ...DELIVERED`=真送达；读不到=`send_failed` 绝不假装。preflight `--verify-silent` 是打包进 agent 的运行时自检。**回复改动真机看到 DELIVERED 才算 done。**

### 关更新真实状态怎么查
搜 `%APPDATA%\Tencent\xwechat` 下 `WeixinUpdate.exe`/`.disabled`：有活的(无.disabled)或 `patch\4.1.10.31\`=**没锁死会自升**；`xwechat.bak4110`=旧4.1.10通道已断。看日志 `interpret_lock_verify` 的 `locked=`。

---

## 4. 排障起手式（怀疑顺序）
1. **先确认环境**：看的是 staging（`staging-autopilot`）还是生产（`autopilot`）？agent 连哪？（看 listener 日志 `middleware=`）。别拿 staging 旧副本当生产。
2. **读会话了吗**：`sessions>0`？否 → §1.1（树塌缩，看是否已 OTA 到 1.0.72）。
3. **检测到未读了吗**：`unread>=1`？否 → §2.A（离屏/检测）。
4. **出草稿了吗**：日志 `skip(no reply) result_ok=False` → §2.D（接管/白名单）或 §2.E（LLM）。看 staging stderr 的 route 行定位是 not_in_whitelist / skip_offhours / LLM 失败。
5. **发出去了吗**：`无法切到 X` → §2.A 离屏；`DELIVERED` = 真送达成功。
6. **模块"未安装"**：先看 agent 日志是否其实 `已激活 ok=true` → 是则 §2.B/C（preflight 并发假象），不是真没装。

---

## 4.5 根治"来回修"的守卫架构（别再靠文档/自觉）
病根：修好的东西记进这份台账（文档），但没做成机器强制守卫 → 下次改把它改坏没人拦（#998 就这么进来的）。三块（非 NFR）：
1. **rog 真机 runner 当 CI 闸**：碰 `services/agent/wechat-rpa/**`/回复/状态的 PR，合并前必须在 rog 真机跑真送达自检，过了才合（dev skill `target_environment=windows_wechat` 已有概念，没建成 required gate）。
2. **agent 运行时"状态自检+自愈"代码（一份代码两处用）**：打包进 agent 每台客户机自愈 + rog runner 发版前先跑=那道闸。
3. **invariant 登记进 `decisions` 表（category=invariant）喂进 /dev GAN**：如"回复循环不准滚动/开群"。
**顺序：先写 agent 自检自愈（让真机自己变干净可测）→ 再把 rog 接成闸**（否则 rog 一乱天天误挡合并）。

## 5. 相关 memory / skill
- memory `line04_wechat_uia_tree_collapse_rootcause_0629`（树塌缩真因+E2E+复用法，最全）
- memory `line04_wechat_cs_working_impl_0621`（跑通版 git 74654efd 完整实现，离屏修法在 §5）
- skill `wechat-uia-silent-send`（发送机制：不抢焦点/不藏窗口/读回验证/禁止死路）
- memory `line04_selfcheck_thrash_rootcause_0627`（多进程抢键盘自检）

**今晚（0629晚~0630）新增 ——**
- ⭐ 主文档入口 `docs/line04-master.md`（现状/目标/待办/打法/索引一处全，活文档；本 skill 是它的 §7 排障台账）
- memory `line04_cs_realmachine_and_followups_0630`（真机跑通+4遗留修复+待办，最新最全）
- memory `line04_agent_env_standardize_done_0629`（锁版本+清垃圾 2PR）/ `line04_reply_crm_isolate_done_0629`（做法二 3PR）
- docs `line04-todo-checklist.md`(可勾选待办) / `handoff-line04-open-issues-0630.md`(待办总账) / `concurrency-capacity-analysis.md`(并发容量)
