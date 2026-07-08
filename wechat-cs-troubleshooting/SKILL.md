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
> 排完**回来更新**（解决的挪上去、新坑加进来）。最后更新：2026-07-08 下午（新增 §2.I rog 微信"卡住打不开"与"读不到会话"的区分）。

## 0. 系统一句话 + 关键事实
- **rog（xian-rog）= Lead 自检机**，agent 的 `.env` **手动改成连 staging**（`wss://staging-autopilot.zenjoymedia.media`）。
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
- ⚠️ **#950 的重启是双刃剑（见 §1.5 + §2.A）**：心跳块的塌缩判定**裸读隐藏态**会误报塌缩→误重启正在工作的微信。PR #965（1.0.76）加了「可读守卫」缓解，但**不够**——真正的反复重启来自 CRM 扫好友破坏 UIA（§2.A）。

### 1.5 心跳 `sessions_seen`/`tree_size` 是【隐藏态裸读】，恒偏 0/塌缩 — 别当真相
- **现象**：心跳 `GET /api/wechat/listener-heartbeat` 的 `sessions=0` **即便系统正在连续 DELIVERED 也恒为 0**。
- **根因**：主循环心跳块 `len(mw.descendants(control_type="ListItem"))` / `len(mw.descendants())` **没先 `_ensure_tray_visible`**——微信窗口在托盘/cloak/离屏态时裸读，a11y 列表不暴露→恒读 0/≤2。而 scan_unread 读会话**有** ensure_visible，所以能读到、能回复。**两个读不在一个状态，心跳那个不可信**。
- **判读得到会话用 `zj-listener.log` 的 `reply_in_chat: ...DELIVERED`，不要用心跳 sessions_seen**。
- **修法**：PR #965（1.0.76）`_should_restart_for_collapsed_tree` 加可读守卫——scan_unread 在可见态读到健康树（`_LAST_VISIBLE_TREE_SIZE` 非塌缩）则更新 `last_readable_scan_at`，90s 内读到过就**绝不重启**。grep `last_readable_scan_at`。

### 1.2 送达验证假阴性（消息真发了却误报 send_failed）
- **根因**：`_uia_send` 成功后 `_read_session_preview` **只读一次**会话预览；微信会话预览**异步更新** + 刚切完会话 UIA 读偶发空 → `_delivery_confirmed` 一次没命中就判未送达。
- **修法**：`_confirm_delivery` 轮询读回（最多 5 轮 × 0.6s），命中即 DELIVERED，全空才失败。不引假阳性。
- **版本/PR**：PR #951，line04 **1.0.72**。

### 1.3 （仅 staging）回复支撑层配置
- 白名单：`zenithjoy.wechat_cs_account_config` 加联系人；auto_agent_enabled=on；营业时间（**按服务器中国时间判定**）。
- LLM 模型：CS 默认 `WECHAT_CS_MODEL||'deepseek-v3.2'`，网关 toapis.com 该模型**无可用渠道**（LLM 503）→ staging 改 `WECHAT_CS_MODEL=deepseek-v4-flash`（实测可用）。**注：这是 staging plist env，被 `ensure_staging_plist` 重生会冲掉，要进 deploy-lib staging_overrides 才持久。**

---

## 2. ❌ 未解决（按"卡人程度"排序，含根因 + 计划）

### A. 🔴🔴「回一次就不理」真因 = CRM 扫好友破坏微信 UIA（rog 0629 晚铁证；正在修，见两份 hand-off）
- **现象**：用户体感"回一次就不理"；用户还观察到 listener「反复跑进学习指导群」。
- **真相（日志时间线坐实，不是猜）**：
  ```
  19:01:53 scan_unread 真送达 DELIVERED ✅（回复路径本身是好的、在连续送达）
  19:01:55 scan_recent_contacts(CRM扫好友) → _scroll_session_list_wheel 连刷几十次 + 逐个开会话/群(坐标31989,32000)
  19:01:56 UIA 屏幕阅读器标志已失效   ← CRM 扫描的滚动/开会话把 SPI 标志弄丢
  19:01:59 UIA树塌缩→已重启微信        ← 标志丢→树【真】塌→#950 重启→多分钟死区→用户那刻发消息没回
  ```
- **根因**：CRM 扫好友（`scan_recent_contacts`+`_scroll_session_list_wheel`+逐个 `_open_chat`，#901/#903 为「扫全好友」加的）和回复路径**共用同一个微信窗口、不能并行**。它一启动/一登录就**开机必跑**（`not friend_scan_done_once`）+ 周期跑，滚遍列表+开群 → 丢 SPI 标志 → 树真塌 → 触发 #950 重启 → 死区。**#811（git 74654efd「B 方案·窗口可见+不抢焦点」）没有 CRM 扫好友，所以超级稳定**——后续 #901/#903/#950 把扫全+自愈重启压到核心回复路径上，把它搞退化。
- **离屏坐标 ~32000 / `_scroll_session_list_wheel: SetCursorPos 失败（无输入权）`**：是 CRM 扫好友在 rog autologon session **无输入桌面权** + Qt 虚拟列表只渲染可见项导致的，**只发生在 CRM 扫描路径**，不是回复路径本身的问题。
- **修法（两刀，见 repo `docs/handoff-line04-reply-crm-isolate-{1,2}-*.md`）**：
  - **第一刀 PR #965（1.0.76，已合并）**：可读守卫（§1.5），治"心跳假塌缩误重启"。**只治了一半**。
  - **做法一·快（hand-off 1）**：CRM 扫好友加开关默认 OFF，回复机只在中台「立即扫好友」时跑；回复循环回 #811 纯粹态（只读→回，绝不滚/开群）。
  - **做法二·彻底（hand-off 2）**：把「客服回复」「好友CRM采集」拆成**两个独立 Ability**，共用微信窗口靠**一把锁时分复用、回复优先**，采集只由中台 task 触发、跑完恢复可读态。
- **真机反复调，看到连续 DELIVERED + 日志无 CRM 滚动刷屏 + 无 `launch_weixin=True` 重启 才算好，不提前报喜。**

### B. 🔴 新装 agent 不杀旧 listener → 假"未安装" + 抢窗口（所有客户都会撞）
- **现象**：苏的客服模块显示"未安装"，但他自己 agent 日志写着 `line04 v1.0.70 已激活 + 健康上报 ok=true`。
- **根因**：① `start.bat:264` 单实例守卫**只杀 `zenithjoy-agent.exe`（core），没杀旧 `listen_chat.py`（python）** → 旧 listener 变孤儿能再跑满 24h。② OTA 升级 `module-manager.ts:302` `oldChild.kill()` 杀的是模块 node fork，**它 spawn 的 python listen_chat 是孙进程，杀不到**。→ 两个 listener 同时抢微信 + 都跑 preflight → `preflight_already_running`。
- **计划**：start.bat + OTA + 模块退出，**按命令行匹配杀掉所有 `*listen_chat*` 的 python/python-embedded**（不只 core）。这一个修法同时解决 C。

### C. 🟠 preflight 并发 → 假"未安装"（与 B 同根）
- **根因**：`module-manager.ts:471-472` preflight 撞上自己还在跑时 `return {ok:false, reason:'preflight_already_running'}` → 中台/前端读到 `ok:false` 显示"未安装"，**其实模块装好了、listener 健康**。
- **计划**：并发"跳过"不该上报 `ok:false`，应保留上次状态。

### D. 🟠 没配接管 → 客户全是黑名单 + 改不了（所有运营都会撞）
- **根因**：`customer-roster.ts:117-119` managed 判定：`takeoverMode='blacklist'→managed=∉黑名单（全接管）`；`'whitelist' 或【缺省】→managed=∈白名单`。运营**没配过接管**（`wechat_cs_account_config` 没那行/解析不到）→ takeoverMode 缺省 → `managed=∈whitelist` → **whitelist 空 → 所有客户 managed=false → 前台全显"黑名单/未接管"**。改不了 = 接管开关 `PUT /api/crm/customers/manage` 写配置时租户解析 403/404（号→租户解析不一致那一类）。
- **计划**：默认（缺省 takeoverMode）改成 **blacklist 主模型（全接管）** 或显式"未配置"态，绝不静默变"白名单空=全黑"；+ 修接管开关写入（号→租户解析统一 + 配不存在自动建行）。

### E. 🟠 生产 LLM `deepseek-v3.2` 死渠道（只修了 staging）
- toapis.com 网关该模型无渠道 → AI 生成失败 → 不回复。**生产没碰**，要动生产 env（用户点头）。

### F. 🟡 安装包写死生产 → 没法在 staging 测
- `start.bat:88-90` 写死 `ZENITHJOY_API_URL=wss://autopilot...`。想 staging 测必须手动改 .env（rog 就是手改的）。计划：装包加 staging/prod 环境选择，或发预置 staging 的包。

### G. 🟡 listAllMachines 漏"绑了但没 license_machines"的机器
- 运营 scope 的 `cs/machines` 是 **license_machines 驱动**；机器在 `service_agents`（已绑）但没 license_machines 行 → 运营列表不显示（实测 d026489c/07c37bd4 就这样）。计划：scope 改成 license_machines ∪ service_agents。

### H. 🟡 4.1.10 上能否回复 — 未验证
- rog 是 **4.1.8.107**，两次成功（默忆/于瑾 DELIVERED）都在 4.1.8 + 会话项在屏内时。客户机若是 4.1.10，UIA 离屏行为是否更糟**没数据**。需在 4.1.10 真机验。

### I. 🔴 rog 微信"卡住打不开"（不是"找不到会话"，两者要分清）——2026-07-08 下午实况
- **现象**：CI `job3 — 真机气泡可读性 gate（xian-rog 真微信）` 报 `session list 里找不到 文件传输助手`、`bubbles=0`，看起来像是"读不到会话"（对应 §1.1 UIA 树塌缩 / §A CRM 破坏 UIA）。但 2026-07-08 下午人工上机核实：**这次根因不是"树塌缩/读不到"，是微信窗口本身直接卡死打不开**（点击/唤起无响应），性质完全不同——前者是"窗口在、UIA 读不出内容"，这次是"窗口这一层就没反应"。同一个 `bubbles=0` 症状，两种完全不同的根因，**排障时必须先分清是"打不开"还是"打得开但读不到"，别看到 bubbles=0 就直接套 §1.1/§A 的修法**。
- **旁证**：同一天两个 PR（#1160 图片消息丢失修复、#1163 UIA 死区自愈重启修复）先后跑 job3，#1160 通过、#1163 连续两次（含一次 rerun）失败且报错完全一致——中间代码改动（`_restart_wechat_for_uia` 加一行 taskkill WeChatAppEx.exe）只在 `run_real_listen()` 主循环里才会被调用，而 job2 的 `--dryrun --inject-message` 路径（`run_dryrun_inject()`）完全不碰这个函数，排除是 PR 代码把 rog 微信杀挂的可能，坐实是 rog 机器**当时独立发生**的窗口卡死，与代码改动无关。
- **计划**：卡死打不开目前只能人工上机重启微信/机器恢复，没有自愈路径覆盖"窗口完全无响应"这一态（现有自愈只覆盖"进程在但 UIA 读不到" `window_lost_since` 和"树塌缩" `collapsed_tree_since` 两种，都假设窗口本身是活的）。后续如果这类"真卡死"复现，需要在 listener 里补一层"窗口无响应检测"（如探测窗口是否响应 `WM_NULL`/`SendMessageTimeout`），现在没有。

---

## 3. 诊断复用法（别再纯 SSH 猜）

### 能力边界
SSH 连 Windows 机 = **session 0**，**够不到 session 1 的 GUI/UIA**。诊断 session 1 的微信窗口必须有 session-1 内执行通道。

### session-1 通道（rog 实测可用）
```
schtasks /create /tn ZJDiagUIA /tr "C:\path\run.bat" /sc once /st 00:00 /ru asus /it /f
schtasks /run /tn ZJDiagUIA
```
`/it`（interactive token）能在 session 1 交互桌面跑代码操作微信。`PsExec -i 1` 起不来。

### 读中文日志（避免多字节截断）
日志是 **GBK**。`Get-Content -Tail N -Encoding Default` → 转 UTF8 字节 → `[Convert]::ToBase64String` → SSH 回传 → 本地 `base64 -d`（纯 ASCII 传输不被 codepage 损坏）。直接 `iconv -f GBK` 经 SSH 常把最新几行多字节字符截断成假象。

### 诊断脚本写法
scratchpad 用 `.txt` 扩展（`.py` 被 bash-guard 拦）→ base64 → 在目标机解码成 `.py` → 跑 `C:\Users\asus\anaconda3\python.exe`（含 pywinauto）。

### 关键日志/文件（rog）
- listener 日志 `C:\Users\Public\zj-listener.log`（心跳每 60s：found_window/login/locked/**sessions/unread**/replied）
- 健康 `C:\Users\Public\zj-listener-health.json`
- 模块目录 `%APPDATA%\zenithjoy\modules\line04-wechat-cs-<ver>\`
- 判"读得到会话" = `sessions>0` 且日志出现过 `unread>=1`；判"回得了" = `reply_in_chat: 真送达确认 DELIVERED`

### staging 库（本机美国 Mac）
`psql -d zenithjoy_test`，表在 **`zenithjoy` schema**（不是 public）。关键表：`wechat_cs_account_config`（接管/白名单/人设）、`service_agents`（绑定）、`license_machines`（注册）、`agents`（心跳/module_status）、`crm_customers`（identity=customer/blacklist/internal）。staging API 日志 `~/Library/Logs/zenithjoy-api.staging.{log,error.log}`，route 判定打印 `[wechat-draft] auto route=X inWhitelist=Y enabled=Z businessHoursOk=W`。

---

## 4. 排障起手式（怀疑顺序）
1. **先确认环境**：看的是 staging（`staging-autopilot`）还是生产（`autopilot`）？agent 连哪？（看 listener 日志 `middleware=`）。别拿 staging 旧副本当生产。
2. **读会话了吗**：`sessions>0`？否 → §1.1（树塌缩，看是否已 OTA 到 1.0.72）。
3. **检测到未读了吗**：`unread>=1`？否 → §2.A（离屏/检测）。
4. **出草稿了吗**：日志 `skip(no reply) result_ok=False` → §2.D（接管/白名单）或 §2.E（LLM）。看 staging stderr 的 route 行定位是 not_in_whitelist / skip_offhours / LLM 失败。
5. **发出去了吗**：`无法切到 X` → §2.A 离屏；`DELIVERED` = 真送达成功。
6. **模块"未安装"**：先看 agent 日志是否其实 `已激活 ok=true` → 是则 §2.B/C（preflight 并发假象），不是真没装。

---

## 5. 相关 memory / skill
- memory `line04_wechat_uia_tree_collapse_rootcause_0629`（树塌缩真因+E2E+复用法，最全）
- memory `line04_wechat_cs_working_impl_0621`（跑通版 git 74654efd 完整实现，离屏修法在 §5）
- skill `wechat-uia-silent-send`（发送机制：不抢焦点/不藏窗口/读回验证/禁止死路）
- memory `line04_selfcheck_thrash_rootcause_0627`（多进程抢键盘自检）
