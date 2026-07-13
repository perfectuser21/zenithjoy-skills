# 诊断：BOM 死循环 —— 命令文件编码 + 删除时机双重 bug

## 一句话结论

写命令文件 `C:\Users\Public\zj-proactive-send.json` 时用了**带 BOM 的 UTF-8**（典型来源：PowerShell `Out-File -Encoding UTF8`），而当前跑在 xian-rog 上的 `listen_chat.py` 这一版**先 `json.loads` 解析、parse 失败时没删文件**，于是：

1. `json.loads` 撞上文件头的 BOM（`﻿`）→ 抛 `Unexpected UTF-8 BOM (decode using utf-8-sig)`
2. 异常被外层 `except` 吃掉，只打一行日志，**`os.remove` 没执行**
3. 文件还在 → 下一个心跳周期（≈3 秒）又读到它 → 又炸 → **每 3 秒一条，永远循环**

这正是 skill 里明确警告的死路（SKILL.md「写入命令文件」一节）：

> `Out-File -Encoding UTF8` 写 UTF-8 **带 BOM**，Python `json.load(encoding='utf-8')` 会报 `Unexpected UTF-8 BOM` 并死循环（文件未删，每次轮询重试）

## 怎么回事（根因拆两层）

| 层 | 问题 | 证据 |
|----|------|------|
| 写入端 | 命令文件带 UTF-8 BOM | 报错文案直接点名 `Unexpected UTF-8 BOM`，BOM 只可能来自写入工具（`Out-File -Encoding UTF8` / 某些编辑器另存） |
| 读取端 | 解析放在删除之前 + 用 `utf-8`（非 `utf-8-sig`） | 文件一直没被删、错误循环不停 = `os.remove` 在 `json.loads` 之后，parse 异常时根本走不到删除那行 |

注意：报错前缀是 `[主动发送] 指令处理异常:`，对应的是**外层 except**（SKILL.md 中 `except Exception as _exc: _log(f"[主动发送] 指令处理异常: {_exc}")`）。能命中外层 except，说明炸在 `with open(...) / json.loads` 阶段，也就说明这台机器上跑的 listen_chat.py 还是「读编码错 + 删除时机错」的旧逻辑，**没有更新到 skill 里的修复版**。

## 怎么修（三步，从止血到根治）

### 第 1 步 —— 立刻止血（停掉死循环）

在 xian-rog 上手动删掉这个文件，循环马上停：

```bash
ssh xian-rog "del C:\\Users\\Public\\zj-proactive-send.json"
```

> 这只是止血。文件删了循环会停，但只要下次还有人用错误方式写命令文件、或代码不改，问题会复发。

### 第 2 步 —— 根治读取端（改 listen_chat.py，按 skill 标准 patch）

把主动发送处理块改成 skill 的标准写法，关键两点：**`utf-8-sig` 容忍 BOM** + **读完立即 `os.remove`，放在 parse 之前**，这样即使以后再来个坏文件，也最多炸一次、立刻被删，不会死循环。

```python
_psc = r"C:\Users\Public\zj-proactive-send.json"
if os.path.exists(_psc):
    try:
        # utf-8-sig 兼容带 BOM 的 UTF-8（PowerShell 常见输出）
        with open(_psc, "r", encoding="utf-8-sig") as _f:
            _raw = _f.read()
        os.remove(_psc)   # ← 读完立即删，parse 异常也不会死循环（关键）
        _cmd = json.loads(_raw)
        _tgt, _msg = _cmd.get("target", ""), _cmd.get("message", "")
        ...
    except Exception as _exc:
        _log(f"[主动发送] 指令处理异常: {_exc}")
```

代码文件：`services/agent/wechat-rpa/listen_chat.py`，插入点在 `last_unread_senders = [...]` 之后、`for m in unread:` 之前。

**改完必须重启 listen_chat.py 进程才生效**（SKILL.md「调试指引」明确：修改后需重启进程）。

### 第 3 步 —— 根治写入端（别再产生 BOM 文件）

以后所有写命令文件的地方，统一走 skill 规定的**纯 ASCII JSON + `\uXXXX` 转义**，从源头杜绝 BOM 和中文乱码：

```bash
# 1. 查目标联系人的 Unicode 码位
python3 -c "print([hex(ord(c)) for c in '默忆'])"
# → ['0x9ed8', '0x5fc6']

# 2. SSH 写入：用 WriteAllText + ASCII 编码（绝不带 BOM）
ssh xian-rog "powershell -NoProfile -Command \"\$j='{\\\"target\\\":\\\"\\u9ed8\\u5fc6\\\",\\\"message\\\":\\\"\\u6d4b\\u8bd5\\\"}'; [System.IO.File]::WriteAllText('C:\\Users\\Public\\zj-proactive-send.json',\$j,[System.Text.Encoding]::ASCII)\""
```

**禁止**：
- `Out-File -Encoding UTF8` —— 会写 BOM（就是这次的元凶）
- `cmd /c echo` —— 遇中文/引号乱码

`\uXXXX` 是标准 JSON Unicode 转义，Python `json.load` 会自动解码成中文；文件纯 ASCII，无任何编码歧义。

## 为什么这套修法对（双保险）

- **写入端改对**（ASCII，无 BOM）→ 正常情况下不会再触发 BOM 错误；
- **读取端改对**（`utf-8-sig` + 先删后解析）→ 即使哪天又混进一个坏文件，也只炸一次、文件立刻被删，**绝不再死循环**。

两端任一改对都能让当前循环停，但**两端都改**才是根治：写入端防复发，读取端兜底防死循环。

## 验证

修完重启进程后：

1. 确认 `C:\Users\Public\zj-proactive-send.json` 不再自动出现、日志不再每 3 秒刷 `指令处理异常`；
2. 用第 3 步的 ASCII 写法投一条真实命令（如 target=默忆），看日志出现 `[主动发送] target=...` → `[主动发送] ok=True`，且文件被处理后立即消失；
3. （回归）故意用 `Out-File -Encoding UTF8` 写一个带 BOM 的坏文件，确认日志最多报**一次**异常、文件随即被删、**不再循环** —— 证明读取端兜底生效。
