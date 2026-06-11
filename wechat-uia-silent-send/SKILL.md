---
name: wechat-uia-silent-send
description: |
  微信后台静默发送（UIA 纯路径）的实现模式。当需要从后台/最小化微信窗口发送消息、
  不允许抢占焦点、或调试 listen_chat.py 发送逻辑时触发本 skill。
  包含：两种回复模式对比、后台静默完整实现、正确路由到目标人、主动发送（IPC）、
  版本要求、成功验证方法，以及禁止使用的死路（前台键盘/鼠标注入）。
  触发场景：微信 RPA 发送不成功 / 消息发到群而不是私聊 / 需要后台静默发送实现 /
  listen_chat.py 发送相关改动 / Path 4 微信通道开发。
---

# 微信 UIA 后台静默发送

## 两种回复模式

### 模式一：前台回复模式（已废弃，禁止使用）

把微信窗口激活到前台，用键盘/鼠标注入输入+发送。

**表现**：用户能看到微信窗口弹出、文字被输入、然后消失。

**问题**：
- 抢占前台焦点，用户正在操作其他程序时会被打断
- `keybd_event`/`SendInput`/`mouse_event` 是全局事件，在后台 session 下会发到当时获得焦点的任意窗口
- 会把消息发给错误的人（发现的 bug：无论谁发消息都只回复同一个人）
- 客户机器上不可接受（会让客户察觉到有程序在操控微信）

**对应的函数**（已从代码库删除）：
`_force_foreground()` / `_abs_click()` / `_set_clipboard_text()` / `send_keys()`

### 模式二：后台静默模式（当前实现，正确）

微信窗口在屏幕外（-2600, 60），用户完全看不到任何操作，但 UIA 控件树完整可用。

**表现**：用户看不到任何窗口弹出，消息静默发出。

**实现路径（完整调用链）**：
```
_open_chat(mw, sender)        ← 切换到目标会话（含验证）
    ↓
_find_chat_input(mw)          ← 找到输入框（UIA Edit 控件）
    ↓
_uia_send(uia_edit, mw, text) ← 写文字 + 发送（纯后台）
    ↓
_navigate_away(mw)            ← 发完跳到文件传输助手（确保下条消息有未读角标）
```

---

## 架构说明（客户部署）

**listen_chat.py 是独立 daemon**，运行在客户 Windows 机器上，无需 Claude Code / AI 工具。
调用链：`Node.js Agent → spawn listen_chat.py → 轮询微信 UIA → POST 中台 API（autopilot.zenjoymedia.media）获取 AI 回复`。
Claude Code 只用于**开发调试**，客户机器上不存在。

---

## 环境前提

微信版本必须 ≤ 4.1.8（当前用 **4.1.8.107**）。
4.1.10+ 把聊天主窗口从 `mmui::MainWindow`（有完整 UIA 控件树）改成了 `Qt51514QWindowIcon`
+ 不透明渲染层，所有 UIA API 返回空，RPA 完全失效。

### ⚠️ xwechat 自动更新陷阱（2026-06-10 发现）

微信 4.1.8.107 内置了一套 **xwechat 插件更新机制**，独立于安装目录的 `WeixinUpdate.exe.disabled`：
- 路径：`%AppData%\Tencent\xwechat\update\patch\4.1.10.xx\Weixin.exe`

**拦截方法**：
```powershell
Rename-Item "$env:APPDATA\Tencent\xwechat\update\patch\4.1.10.27" "4.1.10.27.BLOCKED"
Rename-Item "$env:APPDATA\Tencent\xwechat\update\patch\4.1.10.31" "4.1.10.31.BLOCKED"
Rename-Item "$env:APPDATA\Tencent\xwechat\xplugin\plugins\WeixinUpdate\9013\extracted\WeixinUpdate.exe" "WeixinUpdate.exe.disabled"
```

**确认当前版本**：
- 窗口类名 `mmui::MainWindow` → 4.1.8.107，RPA 可用 ✅
- 窗口类名 `Qt51514QWindowIcon` → 4.1.10.x，RPA 不可用 ❌

---

## 窗口可见性管理（后台静默的基础）

### SW_SHOWNOACTIVATE(4) vs SW_SHOWNA(8)

最小化的窗口必须先还原才能操作 UIA，**还原时绝对不能用 SW_SHOWNA(8)**：

| ShowWindow 参数 | 行为 | 后果 |
|---------------|------|------|
| `SW_SHOWNA=8` | "以当前状态显示"——最小化窗口仍留在 (-32000,-32000) 幽灵坐标 | UIA 坐标全错、PostMessage 事件无订阅者、切换不触发重绘 |
| `SW_SHOWNOACTIVATE=4` | 还原到正常位置，不抢焦点，不激活 | UIA 坐标变为真实屏幕坐标，事件正常传递 ✅ |

### 离屏静默模式

还原后立即移到屏幕外，用户看不到但 UIA 完全可用：

```python
# _open_chat 开头：还原最小化 + 移出屏幕
if user32.IsIconic(main_hwnd):
    user32.ShowWindow(main_hwnd, 4)   # SW_SHOWNOACTIVATE
    time.sleep(0.8)

# 检查是否在可见区，是则移出去
GetWindowRect(main_hwnd, byref(rc))
if rc.left > -2000:
    SWP_FLAGS = 0x0001 | 0x0004 | 0x0010  # NOSIZE | NOZORDER | NOACTIVATE
    SetWindowPos(main_hwnd, 0, -2600, 60, 0, 0, SWP_FLAGS)
    # 窗口现在在屏幕外，用户不可见，但 UIA 树活着，坐标相对于 (-2600, 60) 起点计算
```

**关键**：绝不最小化（最小化 = UIA 死亡）。只要保持"已还原但在屏幕外"即可。

---

## 正确路由：给对的人发消息（_open_chat）

### 历史上犯过的错

**错误做法（已修复）**：直接调 `item.iface_invoke.Invoke()` 后就写入文字发送。

**表现**：所有消息都发给同一个人（最后活跃的会话），谁发消息都只有一个人收到回复。

**根因**：`item.Invoke()` 在后台 session 中只切换内部状态，不触发聊天面板的重绘。面板停留在上次活跃会话（如"文件传输助手"），所有写入都进了错误会话。

### 正确实现（_open_chat + 三层验证）

```python
def _open_chat(mw, sender, expect_content=""):
    # === Step 1: 窗口状态准备 ===
    # 最小化 → SW_SHOWNOACTIVATE(4) 还原（不用SW_SHOWNA=8！）
    # 在可见区域 → SetWindowPos 移到 (-2600, 60) 离屏

    # === Step 2: 三种切换策略（按 attempt 轮换）===
    for attempt in range(3):
        if attempt == 0:
            item.iface_selection_item.Select()   # UIA SelectionItem（最快）
            # 若无 iface_selection_item 则 Invoke()
        elif attempt == 1:
            # PostMessage 鼠标点击 → MMUIRenderSubWindowHW 渲染子窗口
            EnumChildWindows(main_hwnd) → 找 MMUIRenderSubWindowHW
            ScreenToClient(render_hwnd, item_center_point)
            PostMessageW(render_hwnd, WM_MOUSEMOVE, 0, lp)
            PostMessageW(render_hwnd, WM_LBUTTONDOWN, 1, lp)
            PostMessageW(render_hwnd, WM_LBUTTONUP, 0, lp)
        elif attempt == 2:
            # PostMessage 鼠标点击 → 主窗口 hwnd（兜底）
            PostMessageW(main_hwnd, WM_LBUTTONDOWN, ...)

        time.sleep(2.0)   # CRITICAL：等 UIA 树更新

        # === Step 3: 三种验证方式（任一通过即成功）===
        if _chat_title_matches(mw, sender):    # 聊天面板顶部标题 == sender
            return True
        if expect_content and frag in bubble_list:  # 消息列表有对方来信内容
            return True
        if item.iface_selection_item.CurrentIsSelected:  # 会话条目处于选中态
            return True

    # === Step 4: 兜底 - 搜索框导航 ===
    search_box.SetValue(sender)
    time.sleep(1.5)
    PostMessage(Enter)
    if _chat_title_matches(): return True

    # === Step 5: 全失败 ===
    _log("全部方式都无法切到 sender，放弃（绝不发进错误聊天）")
    return False
```

### _chat_title_matches 实现

```python
def _chat_title_matches(mw, sender):
    wr = mw.rectangle()  # 窗口矩形（注意：在离屏模式下如 (-2600,60,x,y)）
    for t in mw.descendants(control_type="Text"):
        r = t.rectangle()
        # 标题在窗口上部（top < wr.top+150）且在会话列表右侧（left > wr.left+1/4宽）
        if r.left > wr.left + (wr.right - wr.left)//4 and r.top < wr.top + 150:
            if t.element_info.name == sender:
                return True
    return False
```

---

## 写入文字（_uia_send）

### SetValue 写入（主路径）

```python
# 1. 最小化时先还原（SW_SHOWNOACTIVATE=4）并刷新 UIA 引用
if was_minimized:
    ShowWindow(main_hwnd, 4)
    time.sleep(0.8)
    uia_edit = _find_chat_input(mw)  # 刷新引用

# 2. SetValue 写入（IValueProvider，绕过输入渲染，无需焦点）
uia_edit.iface_value.SetValue(reply_text)
time.sleep(0.3)

# 3. 验证写入（防止 Qt5 控件假成功）
written = uia_edit.get_value() or ""
if not written:
    return False  # 写入失败，放弃
```

### 发送（三级兜底）

```python
# 主路径：UIA 发送按钮 Invoke（无需焦点，最可靠）
btn = _find_send_button(mw)
if btn:
    btn.iface_invoke.Invoke()
    time.sleep(0.8)
    if _check_sent("btn Invoke"):
        return True

# 兜底1：PostMessageW(WM_KEYDOWN Enter) → MMUIRenderSubWindowHW
# 兜底2：PostMessageW(WM_KEYDOWN Enter) → main_hwnd（实测是真正有效的路径）
for hwnd in [render_subwindow_hwnd, edit_hwnd]:
    AttachThreadInput(my_tid, wx_tid, True)
    SetFocus(hwnd)
    PostMessageW(hwnd, WM_KEYDOWN, VK_RETURN, 0x001C0001)
    PostMessageW(hwnd, WM_CHAR, '\r', 0x001C0001)
    PostMessageW(hwnd, WM_KEYUP, VK_RETURN, 0xC01C0001)
    AttachThreadInput(my_tid, wx_tid, False)
    time.sleep(0.6)
    if _check_sent(f"Enter→hwnd={hwnd}"):
        return True
```

### _find_send_button（排除表情按钮）

```python
for c in mw.descendants(control_type="Button"):
    nm = c.element_info.name or ""
    if "表情" in nm:        # 排除"发送表情(Alt+E)"——旧版 startswith("发送") 会误匹配
        continue
    if nm == "发送" or nm.startswith("发送(") or "send" in aid.lower():
        return c
```

### _check_sent（发送成功判断）

```python
def _check_sent(tag):
    rem = find_chat_input().get_value() or ""
    if rem:                          # 输入框还有文字 → 未发出
        return False
    v = _verify_sent(mw, sender, reply_text)
    if v is False:                   # verify 明确说没发出
        return False
    return True                      # 输入框空 + (verify=True 或 None) → 判定成功
```

**_verify_sent 的问题**：在离屏后台模式下，气泡列表可能不刷新（Qt 渲染节流），
导致 `_verify_sent` 返回 False → `_check_sent` 返回 False → 触发外层重试 → 重发消息。
见"禁止使用"表和变更记录。

---

## 实测有效的发送路径（来自日志）

从 xian-pc 实测日志（2026-06-11）：

```
_find_send_button: 命中 '发送'
_uia_send: btn Invoke 后输入框仍有84字 → 未发出    ← btn.Invoke 无效（UIA 按钮在后台不触发）
_uia_send: Enter→hwnd=27003868 后输入框仍有84字 → 未发出   ← MMUIRenderSubWindowHW 无效
_verify_sent: 消息气泡命中 → 确认已发出
_uia_send: Enter→hwnd=52169456 成功（验证=True）    ← PostMessage(main_hwnd, Enter) 有效 ✅
auto-replied OK sender=默忆
```

**结论**：在当前 WeChat 4.1.8.107 + 离屏模式下，真正发送消息的路径是 `PostMessageW(main_hwnd, WM_KEYDOWN/WM_CHAR/WM_KEYUP, Enter)`。`btn.Invoke` 和 `MMUIRenderSubWindowHW Enter` 均失效，但代码保留做兜底（不同机器/版本可能不同）。

---

## 定位输入框（_find_chat_input）

```python
def _find_chat_input(mw):
    # 优先：automation_id == 'chat_input_field'
    for c in mw.descendants(control_type="Edit"):
        if c.element_info.automation_id == "chat_input_field":
            return c
    # 回退：面积最大的 Edit（输入框 area≈70818；搜索框 area≈6660）
    max_area, best = 0, None
    for c in mw.descendants(control_type="Edit"):
        r = c.rectangle()
        area = (r.right-r.left) * (r.bottom-r.top)
        if area > max_area:
            max_area, best = area, c
    return best  # None if nothing found
```

**时序要求**：`_open_chat()` 内部已等 2.0s。如果 `_find_chat_input` 返回 None，再等 2.0s 重试一次：

```python
uia_edit = _find_chat_input(fmw)
if uia_edit is None:
    time.sleep(2.0)    # 等 UIA 树更新
    fmw = _fresh_mw()  # 拿新鲜引用
    uia_edit = _find_chat_input(fmw)
```

---

## 监听与回复循环（listen_chat.py 主逻辑）

### 消息检测（scan_unread）

每 3 秒扫一次会话列表 ListItem，两条路径触发回复：

```
路径1（角标路径）：ListItem.name 含 '[N条]' → 有未读消息
路径2（内容变化路径）：无角标但预览内容 != last_content[sender] → 聊天面板当前打开，消息即时已读但内容变了
```

### 四道去重闸门（按顺序，均可能静默跳过）

```
闸门1: sender_reply_cooldown[sender]    成功回复后 30s 冷却（无日志）
闸门2: replied 集合  (sender,content)   TTL=120s 但内存清理每小时才跑（只记一次日志）
闸门3: reply_failed_at[key]            失败冷却（记日志）
闸门4: rate_limiter.can_send()         频控（无日志，静默 continue）
```

**注意**：闸门1和2的静默跳过 + `_skip_logged` 去重日志，会造成"发消息没回复、日志里没报错"的死锁现象（见故障模式2）。

### 两个已知故障模式

**故障模式1：自回复风暴（发一条 AI 回 N 条）**

触发链：
1. AI 回复发出 → `_navigate_away()` 跳到文件传输助手
2. WeChat 离屏后台下未清角标
3. 下轮扫描：角标还在 → 触发角标路径 → 预览变成了 AI 的上条回复（截断版）
4. `last_content[sender] = reply`（完整原文）≠ 预览截断版 → Path2 也触发
5. `replied` 集合 key=(sender, 预览截断版) ≠ (sender, AI完整回复原文) → 不在replied → 再回一次
6. 每 30s 循环一次，风暴持续

**故障模式2：客户发消息不回复（replied 死锁）**

触发链：
1. 某次回复被判"成功"（可能是假成功）→ `replied.add((sender, content))`
2. 后续：sender 继续发同内容 → `key in replied` → 静默 continue（且已在 `_skip_logged`，无日志）
3. TTL 120s 过期但内存清理要等 1 小时 → 该 sender 最长被封锁 1 小时
4. 解锁后仍对旧消息回复 → 成为风暴种子

**应急修复**：重启 daemon（`wmic process where "name='python.exe'" call terminate`）。重启时 `_load_replied()` 过滤掉过期条目，`_skip_logged` 内存清零。

---

## 主动发送（命令文件 IPC）

**触发方式**：写入 `C:\Users\Public\zj-proactive-send.json`，daemon 每轮心跳检测后处理删除。

**写入格式**（必须 ASCII-only JSON，中文用 `\uXXXX`）：
```bash
# SSH 写入（避免 BOM、编码问题）
ssh xian-pc "powershell -NoProfile -Command \"\$j='{\\\"target\\\":\\\"\\u4e8e\\u745c\\\",\\\"message\\\":\\\"\\u6d4b\\u8bd5\\\"}'; [System.IO.File]::WriteAllText('C:\\Users\\Public\\zj-proactive-send.json',\$j,[System.Text.Encoding]::ASCII)\""
```

**注意**：`Out-File -Encoding UTF8` 写 BOM → Python json.load 报错 → 文件未删 → 无限循环。

---

## 禁止使用（已验证无效/有害）

| 方法 | 问题 |
|------|------|
| `keybd_event(VK_RETURN)` | 全局事件，后台会话发到错误窗口 |
| `SendInput` | 同上 |
| `mouse_event / _abs_click` | 需要前台焦点 |
| `ShowWindow(SW_RESTORE=9)` | 把微信激活到前台 |
| `ShowWindow(SW_SHOWNA=8)` 还原最小化 | 最小化窗口停在幽灵坐标，UIA 事件无订阅者 |
| `SetForegroundWindow` / `_force_foreground` | 抢焦点，前台可见 |
| `_set_clipboard_text + Ctrl+V` | 依赖前台焦点 |
| `_set_clipboard_text + WM_PASTE(0x0302)` | Qt mmui::MainWindow handle=0 时被无声丢弃 |
| `item.Invoke()` 直接切换（不验证）| 后台不真正切换面板，发到错误会话 |
| `send_keys()` / `type_keys()` | 依赖焦点，后台不可用 |
| `_open_chat` 死等固定 `sleep(2.0)` | 多人排队每条白等，改轮询 `_chat_title_matches` 切中即走 |
| 客服回复用推理模型（deepseek-v4-flash 等）| 思考烧 token、慢、token 给小了 content 返回空；用非推理 deepseek-v3.2 |
| 真机热改后不回灌 repo + build-modules | 重装/覆盖即丢，串台复发（见「部署纪律」）|

---

## 变更记录（Change Log）

| 日期 | 变更 | 触发原因 | 结论 |
|------|------|----------|------|
| 2026-06 | 引入 `WM_PASTE` 替代 SetValue（PR #717） | SetValue 报告不写入文本 | ❌ 回滚：handle=0 WM_PASTE 无声丢弃 |
| 2026-06-09 | 恢复 SetValue + AttachThreadInput（PR #723） | WM_PASTE 确认无效 | ✅ |
| 2026-06-09 | 删 SW_RESTORE，改直接 Invoke()（PR #727） | Enter 失败触发 SW_RESTORE→前台激活 | ✅ |
| 2026-06-10 | SW_SHOWNA(8) 改为 SW_SHOWNOACTIVATE(4) | SW_SHOWNA 留窗口在幽灵坐标 | ✅ |
| 2026-06-10 | 新增 `_open_chat()`：离屏+三策略切换+三方式验证 | Invoke 后台不切面板，发到文件传输助手 | ✅（三人路由验证通过）|
| 2026-06-10 | `_verify_sent()` 加标题验证 | 气泡在错误会话找到文字→假阳性 | ✅ |
| 2026-06-10 | `_find_send_button()` 排除"发送表情" | startswith("发送") 误匹配表情按钮 | ✅ |
| 2026-06-10 | 离屏模式 SetWindowPos(-2600, 60) | 用户观察到微信窗口在前台 | ✅ |
| 2026-06-10 | xwechat patch 目录拦截 | xwechat 插件悄然升级到 4.1.10.31 | ✅ |
| 2026-06-11 | 实测确认有效发送路径：PostMessage(main_hwnd, Enter) | btn.Invoke 和 render_hwnd Enter 均失效 | ✅ |
| 2026-06-11 | 发现自回复风暴和 replied 死锁两个故障模式 | last_content 截断 vs 完整原文不匹配；_skip_logged 无声封锁 | ⚠️ 待修 |
| 2026-06-11 | **`_open_chat` 修复丢失复发串台 → 重新进 repo + 同步 build-modules**（PR #752） | 06-10 的 `_open_chat` 只在真机热改、**从没进 repo**，被裸 Invoke 版覆盖回去 → 串台复发（我→于锦、于锦→苏的一致性偏移） | ✅ 见下「部署纪律」 |
| 2026-06-11 | `_open_chat` 死等 `sleep(2.0)` 改**轮询验证**（每 0.4s 查 `_chat_title_matches`，切中即走，上限 2s） | 多人排队时每条白等 6s（3 attempt × 2s）；实测多数 attempt=0 即切中 | ✅ 每条省 3-5s |
| 2026-06-11 | 主循环改**两阶段**：先并行（线程池≤5）向中台要所有草稿，再串行切窗发送 | 多人同时来时逐个等模型生成；生成纯网络可并发，发送才受单窗口限制 | ✅ |
| 2026-06-11 | 客服回复模型用**非推理** deepseek-v3.2（≠ 推理版 deepseek-v4-flash） | v4-flash 是推理模型：思考走 reasoning_content，先烧 token、慢（5-12s）、token 给小了 content 返回空 | ✅ v3.2 ~1.5s 出答案 |

## ⚠️ 部署纪律（血泪教训，2026-06-11）

**最贵的一个坑：真机热改的修复"丢失"，导致串台复发。**

- 06-10 在 xian-pc 上热改出能用的 `_open_chat`（三人路由验证通过），但**只改了机器上"已安装模块目录"里的文件，从没 commit 进 repo**。后来 Agent 模块以官方包重装/覆盖 → 热补丁被冲掉 → 退回裸 `item.Invoke()` 版 → **串台复发**。
- **铁律：任何在真机上 SSH 热改的修复，必须立刻回灌 repo，否则一定会丢。** 具体三步缺一不可：
  1. 改 `services/agent/wechat-rpa/*.py`（源）
  2. **同步到 `services/agent/build-modules/line04/wechat-rpa/`**（打包真源）—— CI `ci-l4-runtime` 有 `diff -r 源 build-modules` 强校验，不同步直接红。修法：`rsync -av --exclude='__pycache__' --exclude='*.pyc' services/agent/wechat-rpa/ services/agent/build-modules/line04/wechat-rpa/`
  3. 合并 main → `agent-installpack.yml`（push main + paths `services/agent/**` 触发）自动重打包 + 传 COS → 重装才拿到修复
- **热补丁 ≠ 固化**：机器上能跑不代表重装不丢。版本号没 bump 时存量机器不会自动更新（重装会，因为重新下载）。

**中台 API（mmv，launchd）重启的坑：**
- 别混用 `bootout`/`bootstrap`/`kickstart`/`pkill` 试错式重启 —— 会造成**多进程抢端口（EADDRINUSE）+ plist 环境变量没加载进进程**，客服直接"不理人"。
- GUI 会话域(gui/$UID) 和 SSH 会话域不同，SSH 的 launchctl 常常管不动 GUI 里加载的 job。**实测可靠：`launchctl unload <plist>` → `pkill -9 -f dist/index.js` → `launchctl load <plist>`，然后用真实请求（draft-generate 有没有 reply + llm_audit 有没有新行）验证，别信 `ps eww` 的 env 显示。**
- **env 要惰性读**：`CS_LLM` 这类配置若是模块级 const，import 那刻就锁死 `process.env`；改成函数调用时读，测试/部署后改 env 才生效。

## 调试指引

**问题：消息发到"文件传输助手"**
→ `item.Invoke()` 后台不切面板，改用 `_open_chat(mw, sender)` + `_chat_title_matches()` 验证

**问题：找不到 chat_input_field**
→ 等待不足。确认 `_open_chat` 内 sleep 2.0s，`_find_chat_input` 失败后再 sleep 2.0s 重试

**问题：窗口仍然前台可见**
→ 确认 `SW_SHOWNOACTIVATE(4)` 之后立即 `SetWindowPos(-2600, 60)`

**问题：某人发消息无回复（日志静默）**
→ 可能是 replied 死锁 + _skip_logged 去重。应急：重启 daemon
→ 根治：清理逻辑改为每轮心跳过期即清，不依赖每小时 purge

**问题：AI 回复风暴（同一人收到多条重复消息）**
→ replied 失效：last_content 存完整回复，预览是截断版，两者不等→Path2 重触发
→ 根治：last_content[sender] 存预览截断版（前20字），或回复成功后短暂关闭Path2路径

**问题：微信悄然升级到 4.1.10.x**
→ 检查 `%AppData%\Tencent\xwechat\update\patch\` 是否有新目录，按拦截方法处理

**问题：schtasks 看不到微信窗口**
→ schtasks 在 session 0，微信在 session 1，进程隔离。必须在 listen_chat.py 主循环内处理

**问题：串台突然复发（之前明明好了）**
→ 八成是代码被回退/重装覆盖。先确认机器上 `listen_chat.py` 有 `_open_chat`+`_chat_title_matches`，且 repo 的 `build-modules/line04` 也同步了（见「部署纪律」）。别只在真机热改。

**问题：回复很慢（尤其多人同时）**
→ 两个大头：① 切窗死等 2s（改轮询）② 用了推理模型（换 deepseek-v3.2）。多人还要并行生成草稿、串行只留切窗+发送。

**问题：改完模型/配置重启后客服"不理人"、回复空**
→ 多为 mmv API 重启后 env 没加载进进程（plist 环境变量丢）或多进程抢 5200。用 legacy `unload/load` + `pkill` 干净重启，用 draft-generate 真实 reply + llm_audit 验证（见「部署纪律」）。CS_LLM 这类配置要惰性读 env。
