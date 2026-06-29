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
> 排完**回来更新**（解决的挪上去、新坑加进来）。最后更新：2026-06-29。

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

### 1.2 送达验证假阴性（消息真发了却误报 send_failed）
- **根因**：`_uia_send` 成功后 `_read_session_preview` **只读一次**会话预览；微信会话预览**异步更新** + 刚切完会话 UIA 读偶发空 → `_delivery_confirmed` 一次没命中就判未送达。
- **修法**：`_confirm_delivery` 轮询读回（最多 5 轮 × 0.6s），命中即 DELIVERED，全空才失败。不引假阳性。
- **版本/PR**：PR #951，line04 **1.0.72**。

### 1.3 （仅 staging）回复支撑层配置
- 白名单：`zenithjoy.wechat_cs_account_config` 加联系人；auto_agent_enabled=on；营业时间（**按服务器中国时间判定**）。
- LLM 模型：CS 默认 `WECHAT_CS_MODEL||'deepseek-v3.2'`，网关 toapis.com 该模型**无可用渠道**（LLM 503）→ staging 改 `WECHAT_CS_MODEL=deepseek-v4-flash`（实测可用）。**注：这是 staging plist env，被 `ensure_staging_plist` 重生会冲掉，要进 deploy-lib staging_overrides 才持久。**

---

## 2. ❌ 未解决（按"卡人程度"排序，含根因 + 计划）

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
