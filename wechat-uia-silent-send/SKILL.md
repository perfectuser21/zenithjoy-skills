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

微信窗口移到屏幕外（`(OFFSCREEN_X, 60)`，默认值举例 `-2600`），UIA 控件树完整可用。

> **真静默 = 真屏外 + 绝不最小化（这才是主线，先记住）**：静默不是靠"挪到 -2600"这个数字，而是靠两件事——① 窗口【持续】待在【该机器真屏外】坐标（`OFFSCREEN_X` **从虚拟屏几何推导** = `GetSystemMetrics(SM_XVIRTUALSCREEN) - 窗宽 - 200`，保证整窗在所有显示器左侧之外，任何机器自适应；**别写死 -2600**——写死值无法适配未知几何机器，详见「真静默铁律」）；② 全程【绝不最小化】。唯一会让用户看到窗口"闪一下"的动作就是【取消最小化】（还原最小化窗口必先回 `left=0` 屏内再被移走，唯一来源=取消最小化）——`_open_chat`/`_uia_send` 本身都不抬窗。

**表现**：用户看不到窗口弹出（前提：窗口真在屏外 + 全程不最小化，否则取消最小化会闪一下）。

**实现路径（完整调用链）**：
```
_open_chat(mw, item, sender, expect_content="")  ← 切换到目标会话（含验证）；item = 会话列表里目标的 ListItem
    ↓
_find_chat_input(mw)          ← 找到输入框（UIA Edit 控件）
    ↓
_uia_send(uia_edit, mw, text) ← 写文字 + 发送（纯后台）
    ↓
_navigate_away(mw)            ← 发完跳到文件传输助手（确保下条消息有未读角标）
                                ⚠️ 跳文件传输助手会导致离屏下角标不清 → 自回复风暴
                                  （见「两个已知故障模式·故障模式1」），是否保留/如何缓解见该节
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
    SetWindowPos(main_hwnd, 0, OFFSCREEN_X, 60, 0, 0, SWP_FLAGS)
    # OFFSCREEN_X 从虚拟屏几何推导，别写死：
    #   OFFSCREEN_X = GetSystemMetrics(76 = SM_XVIRTUALSCREEN) - 窗宽 - 200
    # 这样整窗保证落在所有显示器左侧之外，任何机器自适应——详见「真静默铁律」。
    # 窗口移到屏外后用户不可见，但 UIA 树活着，坐标相对于 (OFFSCREEN_X, 60) 起点计算
```

**关键**：绝不最小化（最小化 = UIA 死亡）。只要保持"已还原但在屏幕外"即可。

### 唤起窗口（闪）的唯一来源 = 取消最小化（2026-06-19 xian-rog 真机定位）

在 xian-rog 真机用**看门狗线程逐步追踪** `GetWindowRect().left`，逐调用记录窗口位置，实测定位出"用户看到微信闪一下"的唯一来源：

- **从最小化态起步**：`start left=0`（窗口先蹦回屏内 `left=0`）→ 之后才被代码移到屏外。**用户看到的就是这一闪。**
- **窗口已在屏外 + 非最小化起步**：全程 `left=-9000`，`_open_chat` 后 `-9000`、`_uia_send` 后仍 `-9000`，看门狗一次没出手（`pushes=0`）。**完全静默，用户全程看不到。**
- **结论**：`_open_chat`（Select / PostMessage）和 `_uia_send` 本身**完全不抬窗口**。唯一抬窗口的是"还原最小化窗口"那一下——最小化窗口还原时必然先回到 `left=0` 屏内，再被移走，中间这一帧用户能看见。

### 真静默铁律（4 条，xian-rog 真机验证）

> ⚠️ **读前先分清（2026-06-20 澄清，详见 Change Log）**：本节「持续屏外」是**追求"零闪"的可选部署建议**，**不是代码强制态**。**代码实际行为**是 `reply_in_chat`/`scan_unread` 每次操作前 `_ensure_tray_visible` 挪屏外、`finally: _restore_window_state` **还原回窗口原状态/原位置**（visible→原屏幕坐标，minimized→原最小化，tray→托盘）——即"操作时挪屏外、操作完放回用户原处、用户随时可点开看"。别把「持续屏外」误读成"代码一直把窗口藏起来让用户看不到"。另：个人微信**没有"真·后台无窗口发送"**，那只在官方 API 通道（企微/iLink）才有；这里说的"真静默"指"真正不被看见的离屏静默"，不是 headless。

1. **窗口必须【持续】待在屏外 + 【绝不最小化】。** 这才是 xian-pc 一直静默的真正原因——守护连续跑、窗口从不最小化，所以**根本没有"取消最小化"那一下**。一旦窗口被最小化，下次还原必然闪。
2. **`OFFSCREEN_X` 必须从虚拟屏几何推导，绝不写死。** 写死 `-2600` 的**真实风险不是"-2600 在 ROG 屏内"**（2026-06-19 真机 `GetSystemMetrics` 实测：ROG 是**单屏 2560×1600，虚拟屏 `left=0 right=2560`，`-2600` 整窗在 `x<0` 本就屏外**——ROG 上的闪源是「取消最小化」让窗口先回 `left=0` 屏内，不是 `-2600` 这个值）。真实风险是 **写死值无法适配未知几何的机器**：比如某机左侧另接一块显示器，虚拟屏 `left` 为负（如 `-1920`），那 `-2600` 就可能落在那块屏里 → 可见。
   - **这是「禁止写死环境假设值」的活案例**：屏外坐标本该按屏幕几何推导，不能写死。
   - **正解**：`OFFSCREEN_X = GetSystemMetrics(SM_XVIRTUALSCREEN=76) - 窗宽 - 200`（窗宽取当前窗口宽或默认 1200），保证整窗落在**所有**显示器最左边界之外，任何机器自适应。实测 ROG 推导出 `-1400`（虚拟屏左界 0 − 窗宽 1200 − 200），静默自检 386 次采样、0 次进入可见区 → SILENT。换机/改动后跑「静默自检」出 SILENT 才算 done（见下节）。
3. **看门狗（watchdog）安全网**：开后台线程每 ~20ms 检查窗口 `left`，若 `> -2000` 立刻 `SetWindowPos(hwnd, 0, OFFSCREEN_X, OFFSCREEN_Y, 0, 0, 0x0015)` 摁回屏外。稳定屏外时 `pushes=0`；能兜住"取消最小化"等瞬时抬头（把可见时间压到 ≤1 帧）。
4. **诊断手法**：在每步操作前后记录 `GetWindowRect().left`，看哪一步从 `OFFSCREEN_X` 变正——就能定位是哪个调用抬了窗口。实测**只有取消最小化会**。

### 静默自检（接缝断言，别靠肉眼）

真机验证"静默"不能靠人眼看（一帧露头肉眼根本抓不住），必须用客观断言。**以后换任何机器 / 任何改动，跑静默自检出 `SILENT ✅` 才算 done——这是本功能的接缝断言**（对齐 CLAUDE.md「DoD 分逻辑断言/接缝断言」：窗口在真实显示器上碰真实世界的那个点，必须真目标验证，不能 mock/CI 绿了就宣布）。

1. **推导 `OFFSCREEN_X`（确认非写死）**：
   ```python
   vleft = GetSystemMetrics(76)          # SM_XVIRTUALSCREEN = 虚拟屏最左边界
   win_w = 当前窗口宽 or 1200            # 取 GetWindowRect 宽，拿不到用默认 1200
   OFFSCREEN_X = vleft - win_w - 200     # 整窗保证在所有显示器左侧之外
   print(f"derived OFFSCREEN_X={OFFSCREEN_X} (vleft={vleft}, win_w={win_w})")  # 打印确认非写死
   ```

2. **采样断言（发送全程不碰可见区）**：发送整个过程开一条后台线程，每 5ms 采样一次 `GetWindowRect`，判断窗口矩形 `rc` 是否与虚拟屏矩形相交：
   ```python
   # 虚拟屏矩形：vleft/vtop/vright/vbottom 由 GetSystemMetrics(76/77/78/79) 取
   def visible(rc):
       # 与虚拟屏矩形是否相交（不相交 = 整窗在屏外 = 不可见）
       return not (rc.right <= vleft or rc.left >= vright
                   or rc.bottom <= vtop or rc.top >= vbottom)
   # 整个发送过程统计 intrude = 命中 visible(rc)==True 的采样次数
   ```
   - **断言 `intrude == 0`**（整个发送过程一次没碰可见区）→ 判 `SILENT ✅`。
   - 否则 `NOT SILENT ❌`，报：露头次数 × 5ms ≈ 露头时长 + 最坏（最靠右的）`left`，用于定位是哪一步抬了窗。

3. **实测样例（ROG）**：推导 `OFFSCREEN_X=-1400`、采样 386 次、`intrude=0` → `SILENT ✅`。

> 代码侧实现见 `listen_chat` 的 `--verify-silent` 模式（另一 PR 加）：推导 OFFSCREEN_X + 起采样线程 + 跑一遍真实发送 + 打印 `SILENT`/`NOT SILENT` 裁决。

---

## 正确路由：给对的人发消息（_open_chat）

### 历史上犯过的错

**错误做法（已修复）**：直接调 `item.iface_invoke.Invoke()` 后就写入文字发送。

**表现**：所有消息都发给同一个人（最后活跃的会话），谁发消息都只有一个人收到回复。

**根因**：`item.Invoke()` 在后台 session 中只切换内部状态，不触发聊天面板的重绘。面板停留在上次活跃会话（如"文件传输助手"），所有写入都进了错误会话。

### 正确实现（_open_chat + 三层验证）

```python
def _open_chat(mw, item, sender, expect_content=""):
    # item = 会话列表里目标的 ListItem（用于 Select / 点击切换）
    # === Step 1: 窗口状态准备 ===
    # 最小化 → SW_SHOWNOACTIVATE(4) 还原（不用SW_SHOWNA=8！）
    # 在可见区域 → SetWindowPos 移到 (OFFSCREEN_X, 60) 离屏（OFFSCREEN_X 须真屏外，默认 -2600，见「真静默铁律」）

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

> 注意：聊天面板顶部【标题】是 `Text` 控件（本函数读标题，没问题）；但聊天区的【消息气泡】是 `ListItem` 不是 `Text`（见「方向检测」节）——别混淆这两者。

```python
def _chat_title_matches(mw, sender):
    wr = mw.rectangle()  # 窗口矩形（注意：在离屏模式下如 (OFFSCREEN_X,60,x,y)，OFFSCREEN_X 默认 -2600）
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
| `ShowWindow(SW_SHOWNA=8)` 还原最小化 | 最小化窗口停在幽灵坐标，UIA 事件无订阅者。⚠️ 注意：现有 `_uia_send`（listen_chat.py ~line 591）仍有 `ShowWindow(main_hwnd, 8)` 调用，属待清理的历史残留——仅在窗口已非最小化时无害（SW_SHOWNA 只对最小化窗口才有幽灵坐标问题）；**新代码勿用** |
| `SetForegroundWindow` / `_force_foreground` | 抢焦点，前台可见 |
| `_set_clipboard_text + Ctrl+V` | 依赖前台焦点 |
| `_set_clipboard_text + WM_PASTE(0x0302)` | Qt mmui::MainWindow handle=0 时被无声丢弃 |
| `item.Invoke()` 直接切换（不验证）| 后台不真正切换面板，发到错误会话 |
| `send_keys()` / `type_keys()` | 依赖焦点，后台不可用 |
| `_open_chat` 死等固定 `sleep(2.0)` | 多人排队每条白等，改轮询 `_chat_title_matches` 切中即走 |
| 客服回复用推理模型（deepseek-v4-flash 等）| 思考烧 token、慢、token 给小了 content 返回空；用非推理 deepseek-v3.2 |
| 真机热改后不回灌 repo + build-modules | 重装/覆盖即丢，串台复发（见「部署纪律」）|
| **让窗口最小化**（哪怕只是中途短暂最小化）| 下次还原必然先回 `left=0` 屏内再被移走 → 用户必看到一闪（隐性坑：`_open_chat`/`_uia_send` 本身都不抬窗，唯一抬窗就是取消最小化）|
| `OFFSCREEN_X` 写死 `-2600`（或任何固定值） | 写死值无法适配未知几何机器：某机左侧另接显示器（虚拟屏 `left` 为负，如 `-1920`）时 `-2600` 可能落进那块屏 → 可见。正解 = `GetSystemMetrics(SM_XVIRTUALSCREEN=76) - 窗宽 - 200` 推导（ROG 上是单屏 0~2560，`-2600` 本就屏外，闪源是取消最小化不是这个值）。换机/改动后跑「静默自检」出 SILENT 才算 done |
| `_last_bubble_direction` 找 `Text` 控件判方向 | 消息气泡是 `ListItem` 不是 `Text`，找 Text 永远抓到底部输入区 → 全判 outgoing → 谁都不回（REPLY_DIRECTION_CHECK 默认关的根因）|
| `_last_bubble_direction` / `REPLY_DIRECTION_CHECK` 气泡方向检测（任何形态） | **UIA 无方向信号**：真机 dump 证实 ListItem 是叶子(子元素=0，无行内气泡子元素)/聊天区无头像/收发 `automation_id` 完全相同/ListItem 满宽 → 收发无任何可区分特征 → 方向检测**物理不可能，永久废弃**（不重开）。**不回自己用未读角标**（自己发的不产生角标 → scan_unread 路径1 只对有角标会话动手）；自回复风暴是 content bug（故障模式1）不碰方向 |

---

## 变更记录（Change Log）

| 日期 | 变更 | 触发原因 | 结论 |
|------|------|----------|------|
| 2026-06-20 | **澄清「真静默 vs 假静默」+ 纠正"持续屏外"的误读**：① 个人微信**从未有过"真·后台无窗口发送"(真静默)**——只有模式一(前台注入,已废弃)→模式二(离屏 UIA,当前)两种;真·后台直发只在**官方 API 通道(企微/iLink)**才有,不在这套个人微信 RPA 里。② **代码实际行为 = 每次操作临时挪屏外、操作完还原回原状态**:`reply_in_chat`(~行931/966)与 `scan_unread`(~行398/427)成对调 `_ensure_tray_visible`(记原状态+挪屏外,带 DWM cloak) → 操作 → `finally: _restore_window_state`(还原:visible→`_saved_visible_pos` 原屏幕坐标 / minimized→原最小化+修回 rcNormalPosition / tray→放回托盘)。**所以是"操作时挪屏外(尽量不闪)、操作完放回用户原来的位置、用户随时可点开看"**,不是把窗口锁死屏外。③ **「真静默铁律 持续屏外」是追求"零闪"的可选部署建议**(守护连续跑+窗口一直留屏外,连"挪进挪出"那一帧都省),**不是代码强制态**——别读成"代码一直把窗口藏屏外让用户看不到"。 | 用户追问"代码到底有没有写过真静默/是不是一直假静默",逐调用点核对发现先前口述自相矛盾 | ✅ 以代码调用点为准:per-操作挪+还原(尊重用户窗口原状态)。真静默只有官方 API 通道有;"持续屏外"=可选零闪建议非代码现状;"假静默(闪一下回原位+随时可看)"是个人微信 UIA 路天花板,够用 |
| 2026-06-20 ⭐xian-rog真机 (PR #806) | **开机自检接入只读静默检 `listen_chat --verify-silent --no-send`**:只读模式跳过"选会话+发消息"(`sent:false,target:null`),只移屏外+采样 2s 验"窗口持续屏外",**不发任何消息**。真机双向 proven-to-fire:推导 OFFSCREEN_X=-1400 采样374/碰0 → SILENT;machine.config 强制 OFFSCREEN_X=100 屏内 → 采样378/碰378 → NOT SILENT 报红。结果经 line04 preflight 透出 `module_status.reason`(微信版本号+静默状态)→ 车队看板。 | 哨兵 P0:把"静默接缝"接入开机自检上报(之前完全没接) | ✅ 只读不发守住"只读检不实发";⚠️ **已知待办:`--verify-silent` 自检跑完不调 `_restore_window_state`,会把窗口留屏外**(诊断工具行为≠回复路径)——后续给自检补"量完还原原位",免得在客户机做开机自检把人家微信窗口弄屏外 |
| 2026-06-19 ⭐xian-rog真机 | **新增静默自检（接缝断言）**：几何推导 `OFFSCREEN_X = GetSystemMetrics(SM_XVIRTUALSCREEN=76) - 窗宽 - 200`（非写死）+ 发送全程每 5ms 采样 `GetWindowRect` 判与虚拟屏矩形是否相交，断言 `intrude==0` → `SILENT` | 「静默"不能靠肉眼」，要客观断言；写死值不可靠 | ✅ ROG 实测推导 `-1400`、386 次采样、`intrude=0` → SILENT；换机/改动跑出 SILENT 才算 done（代码侧 `listen_chat --verify-silent`，另一 PR）|
| 2026-06-19 ⭐xian-rog真机 | **修正**：先前判"`-2600` 在 ROG 在屏内→才闪"**有误**（真机 `GetSystemMetrics` 实测 ROG 单屏 `0~2560`，`-2600` 本就屏外）；真闪源 = 取消最小化（窗口先回 `left=0` 屏内）。写死值的真实风险 = 未知几何机器（如左侧负坐标显示器，虚拟屏 `left=-1920` 时 `-2600` 可能落进那块屏）| 真机测量证伪旧判断 | ✅ 正解 = 从 `SM_XVIRTUALSCREEN` 推导 + 静默自检断言；删「machine.config.json 每机覆盖 -9000」临时解 |
| 2026-06-19 ⭐xian-rog真机 | 看门狗安全网：后台线程每 ~20ms 查 `left`，`> -2000` 立刻 `SetWindowPos(...,0x0015)` 摁回屏外；稳定时 `pushes=0`，兜瞬时抬头到 ≤1 帧 | 兜"取消最小化"等瞬时露头 | ✅ |
| 2026-06-19 ⭐xian-rog真机 | **真机调试必须在 session 1**：SSH 在 session 0 看不到 session 1 微信（`Desktop(uia)` 返回 `NO_WINDOW`）；用 `PsExec.exe -i 1 -accepteula <bat>` 送脚本进 session 1，python stdout 重定向到文件再 `Get-Content` 读 | dump 不到 `mmui::MainWindow` | ✅ Windows SSH 输出 GBK，复杂脚本 scp 文件进去跑别内联 |
| 2026-06-19 ⭐xian-rog真机 | **方向检测物理不可能 → REPLY_DIRECTION_CHECK 永久废弃（终结结论）**：逐条 ListItem 内部全 dump 证伪——ListItem 是叶子(子元素=0，无"行内气泡子元素")/聊天区无头像/收发 `automation_id` 完全相同(都=`chat_bubble_item_view`)/ListItem 满宽 → **UIA 无任何方向信号**。不回自己一直靠未读角标(自己发的不产生角标→scan_unread 路径1 只对有角标会话动手)，与方向检测无关；自回复风暴是 content 追踪 bug(故障模式1)不碰方向 | 进一步真机 dump 证伪先前"改找 ListItem+校准重开"中间结论 | ✅ REPLY_DIRECTION_CHECK / 气泡方向检测永久废弃，不重开；不回自己靠未读角标 |
| 2026-06-19 ⭐xian-rog真机 | **修正方向检测认知：消息气泡是 `ListItem` 不是 `Text`**（全窗口仅 3 个 Text=标题×2+输入区）；`_last_bubble_direction` 找 Text→抓到底部输入区→全判 outgoing→谁都不回 | 排查 REPLY_DIRECTION_CHECK 默认关的根因 | ⚠️ 此结论已被上一行进一步真机 dump 证伪：ListItem 叶子无子元素/无头像/收发 automation_id 相同 → UIA 无方向信号 → 方向检测物理不可能，REPLY_DIRECTION_CHECK 永久废弃；不回自己靠未读角标 |
| 2026-06-18 | listen_chat 的 draft-generate body 带 `agent_id`；中台 `resolveTenantId` 缺显式 tenant 时按 agent_id 反查 tenant_id（PR #796） | 中台 draft-generate 加租户隔离要 `tenant_id/X-Tenant-Id`，listen_chat 不传 → 全部 400 NO_TENANT_CONTEXT，客服谁都不回 | ✅ 租户绑定时已定，不该每条消息让 caller 传 |
| 2026-06-18 | 模块版本号 6 处一致 bump；改 agent core 还要 bump `services/agent/package.json` | 不 bump → 心跳报旧版，已装客户端不自动更新；core 版本不一致 CI「Lint Agent Version Bump」拦 | ✅ |
| 2026-06-18 | 厘清「模块自动更新 ≠ core 更新」 | 模块版本 bump 只让客户端拉新 line04（含 listen_chat.py），改动若在 agent core（spawn 参数等）必须重下安装包 | ✅ |
| 2026-06-18 | mmv 中台部署改 `pkill -9` + `bootout`/`bootstrap`/`kickstart`，并强制验证新 PID + required_version + 真 reply | `launchctl stop/start`/`kickstart -k` 卡旧进程 PID 不变，旧进程继续服务、required_version 不更新（坑了 3 次） | ✅ 建议 deploy 脚本 stop/start 换 bootout/bootstrap |
| 2026-06-18 | apps/api/.env 补 `TOAPI_API_KEY`，key 进 1Password secret 源 + 部署确保写进 .env | .env 漏 TOAPI_API_KEY → AI 生成静默失败（aiError 不打日志）→ auto 返回 `{ok:true,status:pending_review}` 但 reply undefined → listen_chat skip | ✅ 别只手动加，下次部署/换机又丢 |
| 2026-06-18 | 加 `REPLY_DIRECTION_CHECK` 开关默认 False（真机校准前关）（PR #797） | `_last_bubble_direction` 按假设写，真机把所有收到消息判 outgoing → 全 skip(direction='outgoing') → 永不回 | ⚠️ 已被 06-19 终结结论覆盖：UIA 无方向信号，方向检测物理不可能，REPLY_DIRECTION_CHECK 永久废弃（不再"校准后重开"）；不回自己靠未读角标 |
| 2026-06-18 | 记录 license QUOTA_EXCEEDED：同机重装/换机注册 403 走 v1.1 兼容路径生成新 agent_id | free 装机上限 1，旧 agent 占着；同机反复重装会撞 | ⚠️ 测试环境注意 |
| 2026-06-18 | `OFFSCREEN_X` 按机器调更负（machine.config.json 覆盖，如 -5200/-9000） | -2600 在双屏/高分屏不够，扫描读消息时窗口闪到前台 | ✅ |
| 2026-06~06-09 | 试过 `WM_PASTE` 替代 `SetValue`（PR #717 加 → PR #723 回滚） | SetValue 曾报告不写入文本 | ✅ **现用 `SetValue` + AttachThreadInput**：WM_PASTE 在 handle=0 时被无声丢弃，确认无效已回滚 |
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

## 方向检测：UIA 没有方向信号，物理不可能 → REPLY_DIRECTION_CHECK 永久废弃（2026-06-19 xian-rog 真机 dump 终结）

**最终真相：微信 4.1.8 的 UIA 里【根本没有方向信号】。"读 UIA 判 incoming/outgoing"物理上不可能——不是阈值/校准问题，是没信号。** `_last_bubble_direction` / `REPLY_DIRECTION_CHECK` 是过度设计 + 物理不可能，**永久废弃**（不是"待校准后重开"）。

### 真机 dump 实测证据（逐条 ListItem 内部全 dump）

2026-06-19 xian-rog 真机进一步 dump 每条消息 ListItem 的完整内部，证明 UIA 无任何方向信号：

- **消息 ListItem 是叶子节点：子元素数 = 0**。没有所谓"行内气泡子元素"可读——之前以为能靠"行内气泡子元素左右偏移"判方向，**根本不存在那个子元素**。
- **没有头像元素**：聊天区找不到 Button/Image 头像，无法靠头像左右位置判方向。
- **收发的 `automation_id` 完全相同**：我发的"测试消息X"和对方发的"你叫啥"，automation_id 一模一样，都是 `chat_message_list.qt_scrollarea_viewport.chat_bubble_item_view`。
- **ListItem 满宽**（L/R 相同），自身矩形无左右差异。
- **结论：UIA 里收发消息无任何可区分特征 → 方向检测物理不可能。**

### 那"不回自己"靠什么？→ 未读角标机制（一直如此，无需方向检测）

**"不回自己"从来不靠方向检测，靠【未读角标机制】**：你自己发的消息**不产生未读角标** → `scan_unread` 路径1 只对【有角标】的会话动手 → **天然不回自己**。这是已经在跑的机制，根本不需要任何方向信号。

### 唯一真"回自己"风险 = 自回复风暴（故障模式1），是 content bug，不碰方向

唯一会"回自己"的场景是 **scan_unread 路径2（内容变化路径）**：聊天窗开着时，AI 回完 → 预览内容变了 → 再触发回复。这是 **`last_content` 追踪 bug**（`last_content` 存完整回复原文 vs 预览是截断版，两者不等 → 误判内容变化）——见「两个已知故障模式·故障模式1」。**治它要修 content 追踪，跟方向检测毫无关系。**

---

## 调试指引

**问题：消息发到"文件传输助手"**
→ `item.Invoke()` 后台不切面板，改用 `_open_chat(mw, item, sender)` + `_chat_title_matches()` 验证

**问题：找不到 chat_input_field**
→ 等待不足。确认 `_open_chat` 内 sleep 2.0s，`_find_chat_input` 失败后再 sleep 2.0s 重试

**问题：窗口仍然前台可见**
→ 确认 `SW_SHOWNOACTIVATE(4)` 之后立即 `SetWindowPos(OFFSCREEN_X, 60)`，且 `OFFSCREEN_X` 从虚拟屏几何推导（`GetSystemMetrics(SM_XVIRTUALSCREEN=76) - 窗宽 - 200`，别写死；详见「真静默铁律」）。跑「静默自检」确认 SILENT

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
→ `_last_bubble_direction` 按假设（气泡水平中心相对聊天面板中线）写，真机上把所有收到的消息判成 outgoing → 全 `skip(direction='outgoing')`。已加 `REPLY_DIRECTION_CHECK` 开关默认 False（PR #797）。**注意：后续真机 dump 已证实 UIA 根本没有方向信号 → 方向检测物理不可能，REPLY_DIRECTION_CHECK 永久废弃，不要再"校准后重开"；不回自己靠未读角标。详见「方向检测」节及上一条「方向检测判反」。**

**问题：注册报 403 / license QUOTA_EXCEEDED**
→ free 装机上限 1，旧 agent 占着名额。同机重装/换机注册会 403，走 v1.1 兼容路径（生成新 agent_id）。测试时同机反复重装会反复撞这个。

**问题：扫描读消息时微信窗口闪到前台**
→ 先查两件事：① `OFFSCREEN_X` 是否从虚拟屏几何推导——别写死 `-2600`（写死值在左侧接负坐标显示器的机器上可能落进那块屏 → 可见），正解 `GetSystemMetrics(SM_XVIRTUALSCREEN=76) - 窗宽 - 200`，跑「静默自检」出 SILENT 才放心；② 窗口有没有被最小化——**唯一会抬窗口的就是"取消最小化"那一下**（`_open_chat`/`_uia_send` 本身都不抬窗），铁律是窗口持续屏外 + 绝不最小化（见「窗口可见性管理」）。看门狗每 ~20ms 摁回屏外做兜底。诊断手法：每步前后记 `GetWindowRect().left`，看哪步从 `OFFSCREEN_X` 变正。

**问题：方向检测判反（所有人都被判 outgoing → 谁都不回）**
→ **根治：方向检测物理不可能（UIA 无方向信号），废弃 `REPLY_DIRECTION_CHECK`，不要再试图重开。** 真机逐条 ListItem 全 dump 证实：ListItem 是叶子（子元素=0，没有"行内气泡子元素"可读）、聊天区无头像、收发 `automation_id` 完全相同、ListItem 满宽 → UIA 里收发消息无任何可区分特征。**不回自己靠未读角标**（你自己发的消息不产生未读角标 → scan_unread 路径1 只对有角标会话动手 → 天然不回自己，无需方向检测）。唯一真"回自己"是**自回复风暴，另见故障模式1**（content 追踪 bug，不碰方向）。详见「方向检测」节。
