---
name: wechat-uia-silent-send
description: |
  微信后台静默发送（UIA 纯路径）的实现模式。当需要从后台/最小化微信窗口发送消息、
  不允许抢占焦点、或调试 listen_chat.py 发送逻辑时触发本 skill。
  包含：主动发送（命令文件 IPC）、被动回复（reply_in_chat）、关键时序知识、
  版本要求、成功验证方法，以及禁止使用的死路（前台键盘/鼠标注入）。
  触发场景：微信 RPA 发送不成功 / 消息发到群而不是私聊 / 需要后台静默发送实现 /
  listen_chat.py 发送相关改动 / Path 4 微信通道开发。
---

# 微信 UIA 后台静默发送

## 核心原则

**绝对禁止前台键盘/鼠标注入**。`keybd_event`、`SendInput`、`mouse_event` 都是全局事件，
在后台 session 下会发到当时获得焦点的任意窗口，导致消息发错地方且无报错。
唯一可靠路径：**UIA IValueProvider.SetValue + PostMessageW**，整个操作无需获得焦点。

## 环境前提

微信版本必须 ≤ 4.1.8（当前用 **4.1.8.107**）。
4.1.10+ 把聊天主窗口从 `mmui::MainWindow`（有完整 UIA 控件树）改成了 `Qt51514QWindowIcon`
+ 不透明渲染层，所有 UIA API 返回空，RPA 完全失效。
详见 memory `wechat_version_accessibility`。

## 发送机制（_uia_send）

### 主路径（后台静默，实测有效）

```python
# 1. SetValue 直接写值：绕过输入渲染，无需焦点
uia_edit.iface_value.SetValue(reply_text)
time.sleep(0.2)

# 2. 若窗口最小化：SW_SHOWNA 还原但不抢焦点（CRITICAL）
if was_minimized:
    user32.ShowWindow(main_hwnd, 8)  # SW_SHOWNA = 8
    time.sleep(0.3)

# 3. AttachThreadInput + SetFocus（仅转移焦点到编辑框，不抢前台）
my_tid = kernel32.GetCurrentThreadId()
wx_tid = user32.GetWindowThreadProcessId(edit_hwnd, byref(pid_buf))
user32.AttachThreadInput(my_tid, wx_tid, True)
prev_focus = user32.SetFocus(edit_hwnd)
time.sleep(0.1)

# 4. PostMessageW：投递 Enter 到消息队列，不需要前台焦点
user32.PostMessageW(edit_hwnd, 0x0100, VK_RETURN, 0x001C0001)  # WM_KEYDOWN
time.sleep(0.05)
user32.PostMessageW(edit_hwnd, 0x0101, VK_RETURN, 0xC01C0001)  # WM_KEYUP

# 5. 恢复焦点 + 断开线程绑定
if prev_focus:
    user32.SetFocus(prev_focus)
user32.AttachThreadInput(my_tid, wx_tid, False)
time.sleep(0.4)

# 6. 验证：输入框被清空 = 消息已发出
remaining = uia_edit.get_value() or ""
if not remaining:
    if was_minimized:
        user32.ShowWindow(main_hwnd, SW_MINIMIZE)
    return True
```

### 兜底路径（静默，绝对禁止 SW_RESTORE）

仅当主路径失败时：直接调用 `_find_send_button().iface_invoke.Invoke()`。
- `SW_SHOWNA` 已在主路径还原窗口，UIA `Invoke()` 不依赖前台焦点
- **绝对禁止** `ShowWindow(SW_RESTORE)`——这会把微信激活到前台，违反零前台原则
- 兜底失败 → 静默返回 `False`，不做任何窗口操作

### 成功验证的坑

`get_value()` 抛异常时 `remaining=""` → 会误判为成功（False Positive）。
代码里对 `get_value()` 的调用必须 `try/except`，异常时不要直接 return True。

## 定位输入框（_find_chat_input）

会话切换后 UIA 控件树需要时间更新，**`Invoke()` 后必须等 ≥2.0s**，再扫描 Edit 控件。
等 0.5s 时只能找到搜索框（area≈6660），等 2s 后才会出现 `chat_input_field`（area≈70818）。

```python
item.iface_invoke.Invoke()
time.sleep(2.0)  # CRITICAL：等 UIA 树更新，少了这个找不到输入框

fmw = get_main_window() or mw   # 拿新鲜窗口引用
uia_edit = _find_chat_input(fmw)
```

`_find_chat_input` 搜索优先级：
1. `automation_id == 'chat_input_field'`（精确匹配，直接返回）
2. 回退到面积最大的 Edit 控件（面积最大=输入框，非搜索栏）

## 主动发送（命令文件 IPC）

listen_chat.py 是一个轮询循环，无法直接从外部调用。
**触发方式**：写入命令文件 `C:\Users\Public\zj-proactive-send.json`。
listen_chat.py 每个心跳周期检测到该文件后处理，处理完立即删除（防重复）。

```json
{"target": "默忆", "message": "你好，这是一条测试消息"}
```

### 写入命令文件（macOS/Linux 远端触发）

**关键：必须用 ASCII-only JSON + `\u` 转义，避免编码问题。**

`cmd /c echo` 和 PowerShell `Out-File -Encoding UTF8` 均不可用：
- `cmd /c echo` 遇到中文/引号直接乱码或失败
- `Out-File -Encoding UTF8` 写 UTF-8 **带 BOM**，Python `json.load(encoding='utf-8')` 会报 `Unexpected UTF-8 BOM` 并死循环（文件未删，每次轮询重试）

**正确写法：pure ASCII JSON，中文字符用 `\uXXXX` 转义**

```bash
# 1. 查出目标联系人的 Unicode 码位（Python 一行）
python3 -c "print([hex(ord(c)) for c in '默忆'])"
# → ['0x9ed8', '0x5fc6']

# 2. SSH 写入（Windows PowerShell + ASCII encoding）
ssh xian-rog "powershell -NoProfile -Command \"\$j='{\\\"target\\\":\\\"\\u9ed8\\u5fc6\\\",\\\"message\\\":\\\"\\u6d4b\\u8bd5\\\"}'; [System.IO.File]::WriteAllText('C:\\Users\\Public\\zj-proactive-send.json',\$j,[System.Text.Encoding]::ASCII)\""
```

JSON 值里的 `\uXXXX` 是标准 JSON Unicode 转义，Python `json.load` 自动解码为中文字符。文件为纯 ASCII，无任何编码歧义。

### listen_chat.py 轮询中的处理逻辑（patch 位置）

插入点：`last_unread_senders = [...]` 行之后，`for m in unread:` 之前。

```python
_psc = r"C:\Users\Public\zj-proactive-send.json"
if os.path.exists(_psc):
    try:
        # utf-8-sig 兼容带 BOM 的 UTF-8（PowerShell 常见输出）
        with open(_psc, "r", encoding="utf-8-sig") as _f:
            _raw = _f.read()
        os.remove(_psc)   # 读完立即删，parse 异常也不会死循环
        _cmd = json.loads(_raw)
        _tgt, _msg = _cmd.get("target", ""), _cmd.get("message", "")
        if _tgt and _msg:
            _log(f"[主动发送] target={_tgt!r}")
            _psi = None
            for _it in mw.descendants(control_type="ListItem"):
                try:
                    if _tgt in (_it.element_info.name or "").split("\n")[0]:
                        _psi = _it
                        break
                except Exception:
                    continue
            if _psi is not None:
                try:
                    _psi.iface_invoke.Invoke()
                    time.sleep(2.0)  # CRITICAL: wait 2s for UIA tree to update
                    fmw = get_main_window() or mw
                    uia_edit = _find_chat_input(fmw)
                    if uia_edit is not None:
                        ok = _uia_send(uia_edit, fmw, _msg)
                        _log(f"[主动发送] ok={ok}")
                    else:
                        _log(f"[主动发送] chat_input_field 未找到")
                except Exception as _pe:
                    import traceback as _tb
                    _log(f"[主动发送] 异常: {_pe}\n{_tb.format_exc()}")
            else:
                _log(f"[主动发送] 找不到 {_tgt!r}")
    except Exception as _exc:
        _log(f"[主动发送] 指令处理异常: {_exc}")
```

## 禁止使用（已验证无效/有害）

| 方法 | 问题 |
|------|------|
| `keybd_event(VK_RETURN)` | 全局事件，后台会话发到错误窗口 |
| `SendInput(VK_RETURN)` | 同上 |
| `mouse_event / _abs_click` | 需要前台焦点，后台静默必失败 |
| `ShowWindow(SW_RESTORE)` + Invoke | SW_RESTORE 把微信激活到前台，等同 SetForegroundWindow；UIA Invoke 直接调即可，不需要 SW_RESTORE |
| `_force_foreground + SetForegroundWindow` | 抢焦点，用户可感知，且不稳定 |
| `_set_clipboard_text + Ctrl+V` | 依赖前台焦点，后台 session 下无效 |
| `_set_clipboard_text + WM_PASTE(0x0302)` | 同上；mmui::MainWindow 控件 handle=0 时 PostMessage 被无声丢弃，且无法验证结果 |

代码文件：`services/agent/wechat-rpa/listen_chat.py`
以上方法对应的函数 `_force_foreground()` / `_abs_click()` / `_set_clipboard_text()` 已从
代码库删除，不得重新引入。

## 变更记录（Change Log）

> **规则**：每次对 `_uia_send` / `reply_in_chat` 做变更，必须在此表追加一行。
> 遇到"SetValue/AttachThread 不行了"的报告，先查这里，再决定是否改路径。

| 日期 | 变更 | 触发原因 | 结论 |
|------|------|----------|------|
| 2026-06 | 引入 `_set_clipboard_text + WM_PASTE` 替代 SetValue（PR #717） | 报告 mmui::MainWindow SetValue 不写入文本 | ❌ 失败回滚：handle=0 WM_PASTE 无声丢弃，日志假成功用户收不到；PR #722 加验证，PR #723 整块删除 |
| 2026-06-09 | 恢复 SetValue + AttachThreadInput 主路径，删 WM_PASTE（PR #723） | WM_PASTE 确认无效，skill 原方案 4.1.8.107 实测有效 | ✅ |
| 2026-06-09 | 删除 fallback 中 SW_RESTORE，改为直接 Invoke()（PR #727） | 实测日志：Enter 偶发失败触发 SW_RESTORE→微信前台激活；UIA Invoke 不需要前台 | ✅ |

## 调试指引

**问题：发送后消息到了群聊而不是私聊**
→ 检查 `reply_in_chat` 是否在 `item.iface_invoke.Invoke()` 之前调用了 `_navigate_away`（已修复）
→ 确认 2s 等待后拿的是新鲜 `mw` 引用（不是 Invoke 前的旧引用）

**问题：找不到 chat_input_field**
→ 99% 是等待时间不足。先检查 sleep 是否 ≥2.0s，再看微信版本是否 ≤4.1.8

**问题：消息发出但返回 False（ok=False）**
→ `get_value()` 抛异常被吞掉，`remaining=""` 误判为失败
→ 用日志确认：看 `AttachInput+Enter 成功` 还是 `Enter未清空`

**问题：log 显示 `找不到 'xxx'`，联系人名字对不上**
→ 会话列表里最多显示最近 N 条对话，不在列表内的联系人无法 match
→ 在 `_psi is None` 分支前加一行 dump：
```python
_names = [(it.element_info.name or "").split("\n")[0]
          for it in mw.descendants(control_type="ListItem")]
_log(f"[主动发送] 会话列表: {_names}")
```
修改 listen_chat.py 后需重启进程才生效，然后写一条 target 故意不匹配的命令触发 dump，从日志读出真实名字。

**问题：在 xian-rog 上 schtasks 进程看不到微信窗口**
→ schtasks 在 session 0，微信在 session 1（用户桌面），进程隔离
→ 必须在 listen_chat.py 主循环内处理，不能从独立子进程扫描窗口
