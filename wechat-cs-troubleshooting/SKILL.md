---
name: wechat-cs-troubleshooting
description: |
  Line04 微信客服（个微 RPA）系统的当前状态 + 已知问题 catalog。任何排查"微信客服不回复 /
  读不到会话 / 客服模块显示未安装 / 客户全是黑名单改不了 / 新装 agent 旧进程没杀 /
  staging 看不到机器" 等问题时，先读本 skill —— 已解决速查表防重复诊断已知问题、
  未解决清单防把不同根因的 bug 混在一起。
  触发场景：微信客服不回复 / 客服 bot 没反应 / line04 / 客服模块未安装 / 读不到会话 /
  sessions=0 / 全黑名单 / 接管开关改不了 / 客服页空白 / agent 多进程 / preflight 未通过 /
  rog 微信客服 / Path 4 私域 AI 排障。
  历史台账已全部迁至 Notion Notes（标题前缀 [Line04][台账]）；新教训写 Notes，不要写回本文件。
version: 2.0.0
---

# Line04 微信客服 — 排障操作手册

> **更新纪律（2026-07-10 skill 分层 P0 起，正文只读）**：排查得到的新教训、实证过程、日志证据
> → 写 Notion Notes（`POST localhost:5221/api/brain/notes`，Type=`Learning`，标题前缀 `[Line04][台账]`），
> **不写回本文件**。唯一例外：§2「未解决清单」允许更新行项——解决了 → §1 速查表加一行 + 细节进 Notes；
> 新坑 → 加一行。攒够一批教训后做一次「回头重写」（机械检查 + 人工看 diff 批准），平时不动正文。

## 0. 系统一句话 + 关键事实
- **rog（xian-rog）= Lead 自检机**。环境随复测节奏切换：2026-07-06 起 rog 在【staging】随 main 自动 OTA（.env 备份 `.env.prod-backup-0706` 是生产配置，测完切回用它）。**排障第一步永远看 listen_chat 进程命令行 `--middleware-url` 确认环境**，别信文档记忆。
- **改 rog `.env` 后必须杀掉旧 start.bat 监督 cmd 再重启**：start.bat 常驻监督循环持有它启动时的 env 快照，只杀 agent.exe 会被它用【旧环境】拉回去。正确顺序 = 杀 `cmd.exe *start.bat*` + 全部 `zenithjoy-agent.exe` + `python *listen_chat.py*` → `schtasks /run /tn ZenithJoyAgent`（session-1 交互令牌，重读 .env）。
- **`.env` 是 UTF-8**，PowerShell 改它要 `Get-Content/Set-Content -Encoding UTF8`；用 `-Encoding ascii` 会把 `ZJ_MAIN_DATA_DIR` 的中文路径写成 `???`。
- **health json `login_present` 字段语义 = "是否弹着扫码登录窗"，false=已登录=健康态**（dashboard 需扫码标志依赖它，1.0.108 起心跳 login 派生真实登录态、此字段语义不动）。别再把 false 当"没登录"误报。
- **客户机（同事的）默认连【生产】`autopilot.zenjoymedia.media`** —— 安装包 `start.bat` 写死的，不是 staging。
- 回复链三层，**任一层断都不回复**：① listen_chat 读会话未读 → ② 中台 `draft-generate` 出草稿（whitelist/接管/LLM）→ ③ UIA `_open_chat` 切会话 + `_uia_send` 发 + 读回验证 DELIVERED。
- **staging 库 = `zenithjoy_test`（本机 :5201）；生产 = autopilot 独立库**。同一个 license/email **两库各有一份副本**（staging 从生产播种），登录/验证两边都过，但读写不同库 —— **排障第一件事：确认看的是哪个环境**，别拿 staging 旧数据当生产真相。

---

## 1. ✅ 已解决速查表（防重复诊断；根因/修法/实证全文见 Notion Notes《[Line04][台账] 微信客服已解决问题全录》）

| § | 症状 | 根因一句话 | PR | 版本 |
|---|------|-----------|-----|------|
| 1.1 | sessions=0 永不回复 | UIA 树塌缩：微信启动时 SPI_SETSCREENREADER 未置位，事后救不了 | #950 | 1.0.71 |
| 1.2 | 真发了却报 send_failed | 送达读回只读一次，会话预览异步更新 | #951 | 1.0.72 |
| 1.3 | staging 不回复（配置层） | 白名单/营业时间/LLM 模型死渠道 | - | staging |
| 1.4 | 微信自升 4.1.10 树又塌 | 关更新只在装机 preflight 跑，常驻期不压 | #984 | 1.0.81 |
| 1.5 | 连发多条只回第一条 | scan_unread 只读最后一条预览，漏上下文 | #984 | 1.0.81 |
| 1.6 | 客户全黑名单改不了 | 缺省 takeoverMode 退化"whitelist 空=全黑" + manage 403 | #954 | 中台 |
| 1.7 | staging 模型 env 被部署冲掉 | plist 重生不带 override | #982 | 中台 |
| 1.8 | 1.0.108 全环境零回复 | 桌面租约打中台地址（应打本机 broker）恒 404 | #1142 #1141 | 1.0.110 |
| 1.9 | "全接管"形同虚设只回旧白名单 | getCSConfig SELECT 漏 takeover_mode/blacklist 两列 | #1146 | 中台 |
| 1.10 | 小窗口/欢迎屏/回顶三停摆 | 单栏布局漏检测 + 欢迎屏无自愈 + 回顶用屏幕绝对坐标 | #1182 | 1.0.114 |
| 1.11 | #998 滚动回归：scan_unread 被塞回"滚动+开群"，AST 纯度守卫被放松 | #998 误把滚动机制复用进 scan_unread；revert #998 + AST 守卫（`_scroll_session_list_wheel` 只许 `scan_recent_contacts` 调用）已恢复 | #1002 | 1.0.84 |

---

## 2. ❌ 当前未解决清单（防混因；完整实证过程/日志证据见 Notion Notes《[Line04][台账] 微信客服未解决问题实证细节》）

- 🔴 **状态判定不可靠**：送达/登录/隐私锁/树塌判定横跳，读回空预览即判失败 → 冷却重发可能给同一人发两遍。
- 🔴 **多微信实例**：agent 自拉没登录的微信、同账号两开读错实例。正确骨架 = 单登录实例 + agent 先起置无障碍标志、微信后登。
- 🔴 **离屏 `_open_chat` 切不到会话**：虚拟列表离屏项坐标 ~32000，点击打空，回不了视口外会话。修法参考跑通版 git 74654efd §5（重扫 item 引用 + 拉回前台）。
- 🔴 **固定目标切会话秒失败死循环（§2.I 残留）**：回顶部分已由 #1182 修；剩 sender 名字识别错（列表'苏' vs 目标'苏小x'，目标会话可能不存在）+ 待发队列无过期/无上限（永远重试）。
- 🟠 **新装 agent 不杀旧 listener（B/C 同根）**：start.bat/OTA 只杀 core，python listen_chat 孙进程杀不到 → 双 listener 抢窗口 + preflight 并发上报 ok:false → 假"未安装"。
- 🟠 **NO_TENANT_CONTEXT**：agent 心跳没进 `agents` 表/没带租户 → draft-generate 400。rog 手插 agents 行热修，代码没修。
- 🟠 **生产 LLM `deepseek-v3.2` 死渠道**：只修了 staging；动生产 env 需用户点头。
- 🟡 **安装包写死生产**（staging 测试要手改 .env）｜ **listAllMachines 漏机**（只认 license_machines，应 ∪ service_agents）｜ **微信 4.1.10 上能否回复未验证**。

---

## 3. 诊断复用法（Line04 专属）

> Windows 真机通用诊断通道（SSH=session 0 边界、schtasks session-1 通道、中文日志编码、
> 诊断脚本写法、UIA 判据截图 ground truth 铁律）已抽出 → **skill `windows-agent-diagnostics`**，先读它。

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
2. **读会话了吗**：`sessions>0`？否 → §1.1（树塌缩，看是否已 OTA ≥1.0.72）；窗口是不是小窗/通讯录 tab → §1.10。
3. **检测到未读了吗**：`unread>=1`？否 → §2 离屏/检测项。
4. **出草稿了吗**：日志 `skip(no reply) result_ok=False` → §1.6/§1.9（接管/白名单）或 §2 生产 LLM 死渠道。看 staging stderr 的 route 行定位 not_in_whitelist / skip_offhours / LLM 失败。
5. **发出去了吗**：`无法切到 X` → §2 离屏/固定目标死循环；`DELIVERED` = 真送达成功。
6. **模块"未安装"**：先看 agent 日志是否其实 `已激活 ok=true` → 是则 §2 双 listener/preflight 并发假象，不是真没装。

---

## 5. 相关资料
- **Notion Notes（台账正身）**：`[Line04][台账]` 前缀三条 —— 已解决问题全录 §1.1-1.10 / 未解决问题实证细节 §2 / 守卫架构规划 §4.5+memory 索引
- skill `windows-agent-diagnostics`（Windows 真机通用诊断通道）｜ skill `wechat-uia-silent-send`（发送机制/禁止死路）
- 主文档 `docs/line04-master.md`（zenithjoy repo）
- memory `line04_wechat_uia_tree_collapse_rootcause_0629`（树塌真因最全）｜ `line04_wechat_cs_working_impl_0621`（跑通版 git 74654efd 完整实现）
