# CHANGELOG — wechat-uia-silent-send

## 2026-06-19 — ROG 真机定位"微信闪一下"唯一来源 + 修正方向检测认知（xian-rog 真机验证）

**症状**
- xian-rog 真机上微信后台静默发送时，用户偶尔看到微信窗口在屏幕上闪一下（前台露头一帧）；xian-pc 上从来不闪，不知差异在哪。
- `REPLY_DIRECTION_CHECK` 一开就把所有人发来的消息判成 outgoing（我方），导致谁都不回，只能默认关掉。
- SSH 上去 dump 微信控件树拿不到 `mmui::MainWindow`（`Desktop(uia)` 返回 `NO_WINDOW`），没法在真机调试。

**根因**
- 用看门狗线程逐步追踪 `GetWindowRect().left` 定位：`_open_chat`（Select/PostMessage）和 `_uia_send` **本身完全不抬窗口**。**唯一抬窗口的是"还原最小化窗口"那一下**——最小化窗口还原必然先回到 `left=0` 屏内再被移走，中间这一帧用户看得见。窗口持续屏外+从不最小化时全程 `left=-9000`、watchdog `pushes=0`，完全静默。xian-pc 不闪正是因为守护连续跑、窗口从不最小化。
- `OFFSCREEN_X=-2600` 在 xian-rog（多屏/不同屏幕几何）上**仍在屏幕里**，守护每轮把窗口挪到 `-2600` 就在用户眼前闪。这是"禁止写死环境假设值"的活案例。
- 真机 dump 实测：聊天面板里消息气泡是 `ListItem` 控件（`element_info.name`=消息文本），**不是 `Text`**；全窗口只有 3 个 Text（标题×2+底部输入区）。`_last_bubble_direction` 找 `Text` → 永远抓到底部输入区那个元素（在右侧）→ 永远判 outgoing → 谁都不回。
- SSH 落在 session 0，微信+listen_chat 在 SessionId 1，进程隔离，session 0 看不到 session 1 的窗口。

**修改（文档）**
- 「窗口可见性管理」补：唤起窗口唯一来源=取消最小化的实测结论 + 真静默 4 条铁律（持续屏外+绝不最小化 / OFFSCREEN_X 须真屏外+machine.config 覆盖+正解从屏幕几何推导 / 看门狗 ~20ms 兜底 / GetWindowRect 诊断手法）。
- 「禁止使用」表补 3 行：让窗口最小化（下次还原必闪）、`OFFSCREEN_X` 写死 `-2600`、`_last_bubble_direction` 找 Text。
- 新增「真机调试必须在 session 1（PsExec -i 1）」小节。
- 新增「方向检测：消息是 ListItem 不是 Text」小节。
- 「调试指引」补：前台闪→查 OFFSCREEN_X 真屏外 + 是否被最小化；方向检测判反→消息是 ListItem 不是 Text。
- 「变更记录」表加 5 行 2026-06-19（标注 xian-rog 真机验证）。
