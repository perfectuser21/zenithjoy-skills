# 排查 `[主动发送] 找不到 糊糊大老婆`

## 根因判断

日志里出现 `[主动发送] 找不到 糊糊大老婆`，对应 listen_chat.py 主动发送逻辑里 `_psi is None` 分支被命中——也就是在会话列表（`mw.descendants(control_type="ListItem")`）里**没有任何 ListItem 的首行名字包含你给的 target 字符串 `糊糊大老婆`**。

命令文件本身是被正常消费了的（文件已删除、日志打出了 target），所以问题不是 IPC、不是编码、不是发送时序，而是**纯粹的名字匹配不上**：

1. 微信会话列表里显示的是**备注名 / 昵称**，不是你心里叫她的外号"糊糊大老婆"。匹配用的是 `_tgt in name`（子串包含），只要列表里那条的真实显示名不包含"糊糊大老婆"这几个连续字符，就匹配失败。
2. 次要可能：她那条会话不在当前会话列表里（列表只展示最近 N 条对话），那也 match 不到。

无论哪种，下一步都一样：**先把会话列表里所有 ListItem 的真实显示名 dump 出来看一眼**，名字就清楚了。

## 怎么查清真实名字（按 skill 的标准做法）

### 步骤 1：在 listen_chat.py 里加一行会话列表 dump

在主动发送逻辑的 `_psi is None` 分支**之前**插入 dump，把当前会话列表里每条 ListItem 的首行名字打到日志：

```python
_names = [(it.element_info.name or "").split("\n")[0]
          for it in mw.descendants(control_type="ListItem")]
_log(f"[主动发送] 会话列表: {_names}")
```

放在已有的查找循环附近即可，例如：

```python
_psi = None
for _it in mw.descendants(control_type="ListItem"):
    try:
        if _tgt in (_it.element_info.name or "").split("\n")[0]:
            _psi = _it
            break
    except Exception:
        continue

# ↓ 新增：无论匹配成功与否都 dump，方便对照
_names = [(it.element_info.name or "").split("\n")[0]
          for it in mw.descendants(control_type="ListItem")]
_log(f"[主动发送] 会话列表: {_names}")

if _psi is not None:
    ...
else:
    _log(f"[主动发送] 找不到 {_tgt!r}")
```

### 步骤 2：重启 listen_chat.py 进程

改完代码**必须重启进程才生效**（listen_chat.py 是常驻轮询循环，热改文件不会重新加载）。

### 步骤 3：发一条故意不匹配的命令触发 dump

写一条 target 随便填（甚至就用 `糊糊大老婆`）的命令文件，让轮询循环走到这段逻辑、打出 dump。注意命令文件要用 **pure ASCII JSON + `\uXXXX` 转义**写入，别用 `cmd /c echo`（中文乱码）或 `Out-File -Encoding UTF8`（带 BOM 会让 Python `json.load` 死循环）：

```bash
# 先查 "糊糊大老婆" 的 Unicode 码位
python3 -c "print(''.join('\\\\u%04x' % ord(c) for c in '糊糊大老婆'))"
# 然后 SSH 用 ASCII encoding 写入命令文件
ssh xian-rog "powershell -NoProfile -Command \"\$j='{\\\"target\\\":\\\"<上面的转义>\\\",\\\"message\\\":\\\"test\\\"}'; [System.IO.File]::WriteAllText('C:\\Users\\Public\\zj-proactive-send.json',\$j,[System.Text.Encoding]::ASCII)\""
```

### 步骤 4：从日志读出真实名字

dump 出来的 `[主动发送] 会话列表: [...]` 里，对照哪一条是她——那个就是微信会话列表里的**真实备注名**。比如可能是 `糊糊`、`老婆大人`、某个真名或带 emoji 的昵称，跟你口语叫的"糊糊大老婆"不一致。

### 步骤 5：用真实名字重发

把命令文件里的 `target` 改成 dump 出来的真实显示名（或它的一个唯一子串，因为匹配是 `_tgt in name` 子串包含，填一个能唯一定位、不会撞到其他会话的片段即可），再发一次就能 match 上。

## 两个容易踩的附加点

- **必须在 listen_chat.py 主循环内 dump**，不能另起一个独立脚本去扫窗口。如果 listen_chat.py 跑在 xian-rog 的 schtasks（session 0），而微信在用户桌面（session 1），独立子进程因为 session 隔离根本看不到微信窗口，会扫出空列表，误导排查。
- 如果 dump 出来的列表里**压根没有她**（不只是名字对不上，是整条会话不在），那是"会话列表只显示最近 N 条对话"导致的——先在微信里跟她说句话把会话顶到列表里，再发命令。

## 一句话总结

加 `_log(f"[主动发送] 会话列表: {_names}")` dump → 重启进程 → 发一条故意不匹配的命令触发 dump → 从日志看到她在会话列表里的真实备注名 → 用真实名字（或唯一子串）当 target 重发。问题不在发送链路，纯粹是"糊糊大老婆"是你的口语外号、和微信里的备注名对不上。
