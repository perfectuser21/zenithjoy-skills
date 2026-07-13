# 从 Mac 远程触发 xian-rog 给「李芳」主动发消息

## 工作原理

`listen_chat.py` 是一个轮询循环，**无法**从外部直接调用它的发送函数。正确的触发方式是写入命令文件：

```
C:\Users\Public\zj-proactive-send.json
```

`listen_chat.py` 每个心跳周期检测到该文件后处理，处理完**立即删除**（防重复）。命令文件内容就是一个简单的 JSON：

```json
{"target": "李芳", "message": "你好，有时间聊聊吗？"}
```

## 关键：编码必须是 pure ASCII + `\u` 转义

这是这个流程最容易踩坑的地方，**绝对不能**用下面两种写法：

| 错误写法 | 后果 |
|---------|------|
| `cmd /c echo` | 遇到中文/引号直接乱码或失败 |
| PowerShell `Out-File -Encoding UTF8` | 写出的 UTF-8 **带 BOM**，Python `json.load` 报 `Unexpected UTF-8 BOM`，文件未删 → **每次轮询重试 → 死循环** |

**正确做法**：把 JSON 写成纯 ASCII，中文字符用标准 JSON 的 `\uXXXX` 转义，再用 `[System.IO.File]::WriteAllText(..., [System.Text.Encoding]::ASCII)` 落盘。这样文件无任何编码歧义，Python `json.load` 会自动把 `\uXXXX` 解码回中文。

本次两个中文字段的码位（已用 Python 验证）：

- `李芳` → `李芳`
- `你好，有时间聊聊吗？` → `你好，有时间聊聊吗？`
  （注意「，」和「？」是全角标点，码位分别是 `，` / `？`，不是 ASCII 逗号问号）

最终要写入文件的 JSON（纯 ASCII）：

```json
{"target":"李芳","message":"你好，有时间聊聊吗？"}
```

## 可直接复制执行的 SSH 命令

在 Mac 终端直接粘贴运行：

```bash
ssh xian-rog "powershell -NoProfile -Command \"\$j='{\\\"target\\\":\\\"\\u674e\\u82b3\\\",\\\"message\\\":\\\"\\u4f60\\u597d\\uff0c\\u6709\\u65f6\\u95f4\\u804a\\u804a\\u5417\\uff1f\\\"}'; [System.IO.File]::WriteAllText('C:\\Users\\Public\\zj-proactive-send.json',\$j,[System.Text.Encoding]::ASCII)\""
```

写完后 `listen_chat.py` 会在下一个心跳周期里：在会话列表里 `Invoke()` 选中「李芳」→ 等 2s 让 UIA 树更新 → 定位 `chat_input_field` → 用 `SetValue + PostMessageW` 后台静默发送 → 处理完删除命令文件。整个过程**不抢前台焦点**，微信可以保持后台/最小化。

## 验证是否成功

发送是后台异步的，写完命令文件后建议查日志确认结果（关键字 `[主动发送]`）：

```bash
# 看进程日志里主动发送的结果（ok=True 即成功）
ssh xian-rog "powershell -NoProfile -Command \"Get-Content C:\\Users\\Public\\zj-listen-chat.log -Tail 30\""

# 确认命令文件已被消费（文件已删 = 已处理；仍在 = 还没轮询到或解析失败）
ssh xian-rog "powershell -NoProfile -Command \"Test-Path C:\\Users\\Public\\zj-proactive-send.json\""
```

> 日志路径以 xian-rog 上 listen_chat.py 实际配置为准，若上面路径取不到日志，到 listen_chat.py 所在目录找 `_log` 输出文件。

## 如果日志显示「找不到 '李芳'」

会话列表里只显示最近 N 条对话，不在列表内的联系人无法 match。两个排查点：

1. **先在 xian-rog 的微信里手动点开一次和「李芳」的会话**，让她进入会话列表，再发命令。
2. 名字对不上（带备注/群名前缀等）→ 在 listen_chat.py 的 `_psi is None` 分支前加一行 dump 会话列表真实名字：
   ```python
   _names = [(it.element_info.name or "").split("\n")[0]
             for it in mw.descendants(control_type="ListItem")]
   _log(f"[主动发送] 会话列表: {_names}")
   ```
   改完**重启 listen_chat.py 进程**才生效，然后发一条故意不匹配的 target 触发 dump，从日志读出真实名字再用真实名字发。

## 环境前提（务必确认）

- xian-rog 上 `listen_chat.py` 进程**正在运行**（否则命令文件永远不会被消费）。
- 微信版本必须 ≤ 4.1.8（当前用 4.1.8.107）。4.1.10+ 主窗口换成 `Qt51514QWindowIcon`，UIA 全部失效，RPA 不可用。
- 微信处于已登录状态（后台/最小化都行，不需要在前台）。
