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

### 唤起窗口（闪）的唯一来源 = 取消最小化（2026-06-19 xian-rog 真机定位）

在 xian-rog 真机用**看门狗线程逐步追踪** `GetWindowRect().left`，逐调用记录窗口位置，实测定位出"用户看到微信闪一下"的唯一来源：

- **从最小化态起步**：`start left=0`（窗口先蹦回屏内 `left=0`）→ 之后才被代码移到屏外。**用户看到的就是这一闪。**
- **窗口已在屏外 + 非最小化起步**：全程 `left=-9000`，`_open_chat` 后 `-9000`、`_uia_send` 后仍 `-9000`，看门狗一次没出手（`pushes=0`）。**完全静默，用户全程看不到。**
- **结论**：`_open_chat`（Select / PostMessage）和 `_uia_send` 本身**完全不抬窗口**。唯一抬窗口的是"还原最小化窗口"那一下——最小化窗口还原时必然先回到 `left=0` 屏内，再被移走，中间这一帧用户能看见。

### 真静默的 4 条铁律（xian-rog 真机验证）

1. **窗口必须【持续】待在屏外 + 【绝不最小化】。** 这才是 xian-pc 一直静默的真正原因——守护连续跑、窗口从不最小化，所以**根本没有"取消最小化"那一下**。一旦窗口被最小化，下次还原必然闪。
2. **`OFFSCREEN_X` 必须是「该机器真屏外」的值。** `-2600` 在单屏机器够用，但 xian-rog（多屏 / 不同屏幕几何）上 **`-2600` 还在屏幕里** → 守护每轮把窗口挪到 `-2600` 就在用户眼前闪。必须用 `C:\Users\Public\zenithjoy\machine.config.json` 写 `{"OFFSCREEN_X": -9000}` 覆盖（实测 `-9000` 在 ROG 真屏外）。
   - **这是「禁止写死环境假设值」的活案例**：屏外坐标本该按屏幕几何推导（取所有显示器最左边界再减去窗口宽度），不能写死 `-2600`。
   - **正解（待实现）**：`OFFSCREEN_X` 从 `GetSystemMetrics` / `EnumDisplayMonitors` 推导最左虚拟屏边界，不硬编码。**当前临时解 = `machine.config.json` 每机覆盖。**
3. **看门狗（watchdog）安全网**：开后台线程每 ~20ms 检查窗口 `left`，若 `> -2000` 立刻 `SetWindowPos(hwnd, 0, OFFSCREEN_X, OFFSCREEN_Y, 0, 0, 0x0015)` 摁回屏外。稳定屏外时 `pushes=0`；能兜住"取消最小化"等瞬时抬头（把可见时间压到 ≤1 帧）。
4. **诊断手法**：在每步操作前后记录 `GetWindowRect().left`，看哪一步从 `OFFSCREEN_X` 变正——就能定位是哪个调用抬了窗口。实测**只有取消最小化会**。

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
| **让窗口最小化**（哪怕只是中途短暂最小化）| 下次还原必然先回 `left=0` 屏内再被移走 → 用户必看到一闪（隐性坑：`_open_chat`/`_uia_send` 本身都不抬窗，唯一抬窗就是取消最小化）|
| `OFFSCREEN_X` 写死 `-2600` | 多屏/高分屏机器（如 xian-rog）上 `-2600` 仍在屏内 → 守护每轮都在用户眼前闪；须按机器 `machine.config.json` 覆盖（如 `-9000`），正解应从屏幕几何推导 |
| `_last_bubble_direction` 找 `Text` 控件判方向 | 消息气泡是 `ListItem` 不是 `Text`，找 Text 永远抓到底部输入区 → 全判 outgoing → 谁都不回（REPLY_DIRECTION_CHECK 默认关的根因）|

---

## 变更记录（Change Log）

| 日期 | 变更 | 触发原因 | 结论 |
|------|------|----------|------|
| 2026-06-19 ⭐xian-rog真机 | **定位"微信闪一下"唯一来源 = 取消最小化**：看门狗逐步追踪 `GetWindowRect().left`，最小化起步 `start left=0`（蹦回屏内）才被移走→用户看这一闪；屏外+非最小化起步全程 `-9000`、watchdog `pushes=0` 完全静默 | 想搞清 ROG 上窗口为何偶尔闪 | ✅ `_open_chat`/`_uia_send` 都不抬窗，唯一抬窗=取消最小化 → 真静默铁律=持续屏外+绝不最小化 |
| 2026-06-19 ⭐xian-rog真机 | `OFFSCREEN_X` 须是"该机真屏外"值：`-2600` 在 ROG 仍在屏内→守护每轮挪过去就闪；`machine.config.json` 写 `-9000` 覆盖 | ROG 多屏/不同几何 | ✅ 临时解=每机覆盖；正解=从 `GetSystemMetrics`/`EnumDisplayMonitors` 推导最左虚拟屏边界（待实现，禁写死 `-2600`）|
| 2026-06-19 ⭐xian-rog真机 | 看门狗安全网：后台线程每 ~20ms 查 `left`，`> -2000` 立刻 `SetWindowPos(...,0x0015)` 摁回屏外；稳定时 `pushes=0`，兜瞬时抬头到 ≤1 帧 | 兜"取消最小化"等瞬时露头 | ✅ |
| 2026-06-19 ⭐xian-rog真机 | **真机调试必须在 session 1**：SSH 在 session 0 看不到 session 1 微信（`Desktop(uia)` 返回 `NO_WINDOW`）；用 `PsExec.exe -i 1 -accepteula <bat>` 送脚本进 session 1，python stdout 重定向到文件再 `Get-Content` 读 | dump 不到 `mmui::MainWindow` | ✅ Windows SSH 输出 GBK，复杂脚本 scp 文件进去跑别内联 |
| 2026-06-19 ⭐xian-rog真机 | **修正方向检测认知：消息气泡是 `ListItem` 不是 `Text`**（全窗口仅 3 个 Text=标题×2+输入区）；`_last_bubble_direction` 找 Text→抓到底部输入区→全判 outgoing→谁都不回 | 排查 REPLY_DIRECTION_CHECK 默认关的根因 | ⚠️ 待修：改找 ListItem，方向看行内气泡子元素左右偏移（ListItem 满宽 L/R 相同），真机校准后再开 REPLY_DIRECTION_CHECK |
| 2026-06-18 | listen_chat 的 draft-generate body 带 `agent_id`；中台 `resolveTenantId` 缺显式 tenant 时按 agent_id 反查 tenant_id（PR #796） | 中台 draft-generate 加租户隔离要 `tenant_id/X-Tenant-Id`，listen_chat 不传 → 全部 400 NO_TENANT_CONTEXT，客服谁都不回 | ✅ 租户绑定时已定，不该每条消息让 caller 传 |
| 2026-06-18 | 模块版本号 6 处一致 bump；改 agent core 还要 bump `services/agent/package.json` | 不 bump → 心跳报旧版，已装客户端不自动更新；core 版本不一致 CI「Lint Agent Version Bump」拦 | ✅ |
| 2026-06-18 | 厘清「模块自动更新 ≠ core 更新」 | 模块版本 bump 只让客户端拉新 line04（含 listen_chat.py），改动若在 agent core（spawn 参数等）必须重下安装包 | ✅ |
| 2026-06-18 | mmv 中台部署改 `pkill -9` + `bootout`/`bootstrap`/`kickstart`，并强制验证新 PID + required_version + 真 reply | `launchctl stop/start`/`kickstart -k` 卡旧进程 PID 不变，旧进程继续服务、required_version 不更新（坑了 3 次） | ✅ 建议 deploy 脚本 stop/start 换 bootout/bootstrap |
| 2026-06-18 | apps/api/.env 补 `TOAPI_API_KEY`，key 进 1Password secret 源 + 部署确保写进 .env | .env 漏 TOAPI_API_KEY → AI 生成静默失败（aiError 不打日志）→ auto 返回 `{ok:true,status:pending_review}` 但 reply undefined → listen_chat skip | ✅ 别只手动加，下次部署/换机又丢 |
| 2026-06-18 | 加 `REPLY_DIRECTION_CHECK` 开关默认 False（真机校准前关）（PR #797） | `_last_bubble_direction` 按假设写，真机把所有收到消息判 outgoing → 全 skip(direction='outgoing') → 永不回 | ✅ UIA 气泡方向必须真机 dump 校准 |
| 2026-06-18 | 记录 license QUOTA_EXCEEDED：同机重装/换机注册 403 走 v1.1 兼容路径生成新 agent_id | free 装机上限 1，旧 agent 占着；同机反复重装会撞 | ⚠️ 测试环境注意 |
| 2026-06-18 | `OFFSCREEN_X` 按机器调更负（machine.config.json 覆盖，如 -5200/-9000） | -2600 在双屏/高分屏不够，扫描读消息时窗口闪到前台 | ✅ |
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

## 真机调试必须在 session 1（PsExec -i 1）（2026-06-19 xian-rog）

- SSH 落在 **session 0**，**看不到** session 1 的微信窗口。pywinauto `Desktop(uia)` 在 session 0 找不到 `mmui::MainWindow`，返回 `NO_WINDOW`。微信 + listen_chat 都跑在 **SessionId 1**。
- **跑法**：下载 PsExec（sysinternals），`PsExec.exe -i 1 -accepteula <bat>` 把脚本送进 session 1。bat 里 python 把 stdout 重定向到文件，跑完再用 `Get-Content` 读文件。
- **编码坑**：Windows SSH 输出是 GBK，PowerShell 内联多行 / `$_` / JSON 大括号容易被转义搞乱 → **复杂脚本用文件 `scp` 进去再跑，别内联。**

---

## 方向检测：消息是 ListItem 不是 Text（2026-06-19 xian-rog 真机 dump 修正）

之前 `_last_bubble_direction` 按"找 `Text` 控件 + 水平中心相对面板中线"判方向，**完全错**：

- **真机 dump 实测**：聊天面板里**消息气泡是 `ListItem` 控件**（`element_info.name` = 消息文本），**不是 `Text`**。整个窗口的 `Text` 只有 3 个（标题 ×2 + 底部输入区元素）。
- `_last_bubble_direction` 当前找 `Text` → **永远找不到真消息** → 抓到底部输入区那个元素（位置在右侧）→ **永远判 outgoing** → 不回自己把所有人都判成"我方" → **谁都不回**。这就是 `REPLY_DIRECTION_CHECK` 默认关的根因。
- **而且 ListItem 都是满宽整行（L/R 相同）**，**方向要看行内气泡子元素的左右偏移，不是 ListItem 自身的 L/R**（待真机进一步校准 incoming/outgoing 判据后才能重新开启 `REPLY_DIRECTION_CHECK`）。

---

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

**问题：客服全员不回，draft-generate 返回 400 NO_TENANT_CONTEXT**
→ 中台加了租户隔离，但 listen_chat 没传任何租户标识。根治：listen_chat 的 post_draft_generate body 带 `agent_id`（agent 自身 id）；中台 `resolveTenantId` 缺显式 tenant 时 `SELECT tenant_id FROM zenithjoy.agents WHERE agent_id=$1` 反查。租户在绑定时已定，不要每条消息让 caller 传（PR #796）。

**问题：改了 agent 代码但已装客户端不更新（心跳报旧版）**
→ 必须 bump 模块版本号，6 处一致：`modules/line04/manifest.json` + `build-modules/line04/manifest.json` + `walking-skeleton.service.ts` 的 `required_version` + `walking-skeleton.service.test.ts` + `heartbeat-modules.test.ts` + `heartbeat-module-health-smoke.sh`。若改的是 agent core（`src/`），还要额外 bump `services/agent/package.json`（独立版本线，CI「Lint Agent Version Bump」会拦）。

**问题：模块版本 bump 了，但 spawn 参数等改动没生效**
→ 模块自动更新 ≠ core 更新。模块版本 bump 只让客户端拉新 line04 模块（含 listen_chat.py）；改动若在 agent core（spawn 参数等），要重新下载安装包，core 不随模块心跳更新。

**问题：部署后 required_version 没变、客户端不更新、PID 没动**
→ mmv `launchctl stop/start`/`kickstart -k` 常卡旧进程，PID 不变、旧进程继续服务。根治：`pkill -9 -f apps/api/dist/index.js` → `launchctl bootout gui/$UID/com.zenithjoy.api` → `launchctl bootstrap gui/$UID <plist>` → `launchctl kickstart`。**必须验证：新 PID 变了 + dist 的 required_version 对 + draft-generate 真返回 reply**。建议把 deploy 脚本的 stop/start 换成 bootout/bootstrap。

**问题：客服"成功但不回"（status=pending_review，reply 为空）**
→ apps/api/.env 漏 `TOAPI_API_KEY`（OPENROUTER 等都有独缺它）→ AI 生成失败 → mode=auto 返回 `{ok:true,status:pending_review}` 但 `reply` undefined → listen_chat skip(no reply)。**失败是静默的（aiError 不打日志）**。诊断：① 直接用 .env/plist 里的 key `curl https://toapis.com/v1/chat/completions` 验 key/模型(deepseek-v3.2)/网络；② 查 `llm_audit` 表（有 0-token 记录 = fetch 失败；无记录 = 没 key，在 fetch 前抛"apiKey 未配置"）。key 应进 secret 源（1Password）+ 部署确保写进 .env，别只手动加（下次部署/换机又丢）。

**问题：所有人发消息都被判 outgoing（我方）→ 永不回**
→ `_last_bubble_direction` 按假设（气泡水平中心相对聊天面板中线）写，真机上把所有收到的消息判成 outgoing → 全 `skip(direction='outgoing')`。已加 `REPLY_DIRECTION_CHECK` 开关默认 False（真机校准前关闭方向检测）。教训：UIA 气泡方向必须真机 dump 校准，不能凭假设写（PR #797）。

**问题：注册报 403 / license QUOTA_EXCEEDED**
→ free 装机上限 1，旧 agent 占着名额。同机重装/换机注册会 403，走 v1.1 兼容路径（生成新 agent_id）。测试时同机反复重装会反复撞这个。

**问题：扫描读消息时微信窗口闪到前台**
→ 先查两件事：① `OFFSCREEN_X` 是否真在屏外——`-2600` 在双屏/高分屏（如 xian-rog）仍露在可见区，按机器用 `machine.config.json` 覆盖更负值（如 `-9000`）；② 窗口有没有被最小化——**唯一会抬窗口的就是"取消最小化"那一下**（`_open_chat`/`_uia_send` 本身都不抬窗），铁律是窗口持续屏外 + 绝不最小化（见「窗口可见性管理」）。看门狗每 ~20ms 摁回屏外做兜底。诊断手法：每步前后记 `GetWindowRect().left`，看哪步从 `OFFSCREEN_X` 变正。

**问题：方向检测判反（所有人都被判 outgoing → 谁都不回）**
→ 消息气泡是 `ListItem` 不是 `Text`（真机 dump 实测，全窗口只有 3 个 Text = 标题×2 + 输入区）。`_last_bubble_direction` 找 `Text` 永远抓到底部输入区元素 → 永判 outgoing。临时解：`REPLY_DIRECTION_CHECK` 默认关。根治：改找 `ListItem`，且方向看**行内气泡子元素的左右偏移**（ListItem 自身满宽 L/R 相同，没法判方向），需真机校准 incoming/outgoing 判据后再开启（见「方向检测」节）。
