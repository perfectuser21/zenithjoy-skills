# 从 Mac SSH 远程触发 xian-rog 上的微信主动发送

## 核心难点：编码

这个任务表面是"写个 JSON 文件"，真正的坑在**中文编码**：

- Mac 终端原生是 **UTF-8**，而 Windows 控制台（cmd / PowerShell）默认用 **本地代码页（中文系统是 GBK/936）**。
- 如果直接 `ssh xian-rog "echo {...} > file.json"`，中文 `李芳` / `你好` 会在 Windows 端按 GBK 重新解释或落盘，`listen_chat.py` 用 `json.load(open(..., encoding='utf-8'))` 读时就会 `UnicodeDecodeError` 或读出乱码联系人，导致发错人 / 发送失败。
- PowerShell 的 `Out-File` / `>` 默认还会写 **UTF-16 LE** 或带 **BOM**，`json.load` 同样会炸（`json.decoder.JSONDecodeError: Expecting value`，因为开头是 BOM 字节 `\xef\xbb\xbf` 或 `\xff\xfe`）。

**结论：绝对不要让中文字符"裸奔"穿过 SSH 命令行和 Windows 控制台。** 正确做法是在 Mac 端把 JSON 按 UTF-8 编码成 **base64**（纯 ASCII，穿任何通道都不变形），在 Windows 端用 .NET 的 `WriteAllBytes` 把原始字节直接落盘——这样既不经过代码页转换，也不会被加上 BOM。

---

## 推荐方案：base64 透传（两步，最稳）

```bash
# 第 1 步：在 Mac 上把命令 JSON 编成 base64（UTF-8 字节流，无 BOM、无换行）
B64=$(printf '%s' '{"contact":"李芳","message":"你好，有时间聊聊吗？"}' | base64 | tr -d '\n')

# 第 2 步：SSH 过去，用 .NET WriteAllBytes 把原始字节写入文件（不经代码页、不加 BOM）
ssh xian-rog "powershell -NoProfile -Command \"[IO.File]::WriteAllBytes('C:\\Users\\Public\\zj-proactive-send.json', [Convert]::FromBase64String('$B64'))\""
```

> `printf '%s'` 不会自动加换行；`tr -d '\n'` 是双保险（macOS 自带的 BSD `base64` 默认本就不换行，Linux GNU `base64` 会按 76 列折行，加上它两边都安全）。
> base64 只含 `A-Za-z0-9+/=`，不含 shell 特殊字符，所以塞进双引号里不会破坏引用。

### 一行版（可直接复制执行）

```bash
ssh xian-rog "powershell -NoProfile -Command \"[IO.File]::WriteAllBytes('C:\\Users\\Public\\zj-proactive-send.json', [Convert]::FromBase64String('$(printf '%s' '{"contact":"李芳","message":"你好，有时间聊聊吗？"}' | base64 | tr -d '\n')'))\""
```

`$(...)` 在 Mac 本地先执行、把 base64 串内联进命令；单引号包住的 JSON 内部含双引号不冲突。

---

## 验证发送是否真的触发（强烈建议跟着跑）

写完文件后，确认文件内容字节正确 + 脚本已消费命令：

```bash
# 1) 确认落盘的 JSON 能被 UTF-8 正确解码（应原样打印中文，不报错、无 BOM）
ssh xian-rog "powershell -NoProfile -Command \"Get-Content -Raw -Encoding UTF8 'C:\\Users\\Public\\zj-proactive-send.json'\""

# 2) 轮询脚本通常在消费后会删除/重命名命令文件；过几秒确认文件已被处理
ssh xian-rog "powershell -NoProfile -Command \"Test-Path 'C:\\Users\\Public\\zj-proactive-send.json'\""
#   -> 返回 False 说明 listen_chat.py 已读取并触发发送
```

---

## 备选方案（如果不方便用 base64）

显式让 PowerShell 写 **无 BOM 的 UTF-8**（注意：`Out-File -Encoding utf8` 在 Windows PowerShell 5.x 会带 BOM，必须用 .NET 的 `UTF8Encoding($false)`）：

```bash
ssh xian-rog "powershell -NoProfile -Command \"[IO.File]::WriteAllText('C:\\Users\\Public\\zj-proactive-send.json', '{\\\"contact\\\":\\\"李芳\\\",\\\"message\\\":\\\"你好，有时间聊聊吗？\\\"}', (New-Object Text.UTF8Encoding \\\$false))\""
```

这种写法中文仍要穿过 SSH + Windows 控制台代码页，**不如 base64 稳**，仅在临时调试时用。

---

## 命令文件本身的内容

落盘后 `C:\Users\Public\zj-proactive-send.json` 的实际内容（UTF-8，无 BOM）：

```json
{"contact":"李芳","message":"你好，有时间聊聊吗？"}
```

> 字段名 `contact` / `message` 是按你描述的语义推断的。如果 `listen_chat.py` 实际用的是别的键名（例如 `to` / `target` / `text` / `content`），把 JSON 里的键改掉即可，编码/SSH 部分完全不变。

---

## 前提假设

1. Mac 的 `~/.ssh/config` 里已配置 `Host xian-rog`（含 HostName / User / 必要时 ProxyJump 或 Tailscale），所以能直接 `ssh xian-rog`。若没配，先用 `ssh user@<ip>` 形式。
2. xian-rog 上 SSH 的默认 shell 能调用 `powershell`（OpenSSH for Windows 默认 shell 是 cmd，`powershell -Command` 可正常拉起；若默认 shell 已是 pwsh 也兼容）。
3. `C:\Users\Public\` 对登录用户可写（Public 目录默认所有用户可写，通常没问题）。
4. `listen_chat.py` 正在 xian-rog 上运行并以 UTF-8 轮询读取该文件——这是你描述的既有前提。

## 一句话总结

把 JSON 在 Mac 端编成 base64 走 SSH，到 Windows 端用 `[IO.File]::WriteAllBytes` 还原字节落盘——这是唯一能 100% 避开"GBK 代码页 + UTF-16/BOM"两类中文乱码的写法。
