# [主动发送] BOM 死循环 — 诊断与修复

报错本身和"死循环不删文件"是**两个独立的 bug**，必须分开看。光改编码只能救今天这个 BOM，救不了下一个写坏的文件。

## 根因

### Bug 1：文件带 BOM，但你用 `utf-8` 读（不剥 BOM）

`Unexpected UTF-8 BOM (decode using utf-8-sig)` 是 Python 标准库给的明确提示。意思是：文件开头有 3 个字节 `EF BB BF`（UTF-8 BOM）。

- `encoding="utf-8"` **不会**剥掉 BOM，于是 `json.load` 拿到的第一个字符是 `﻿` 而不是 `{`，直接抛 `json.JSONDecodeError`。
- `encoding="utf-8-sig"` 会在解码时自动吃掉开头的 BOM，正常读到 `{`。

**为什么文件会带 BOM？** 几乎可以肯定是写 `zj-proactive-send.json` 的那一端用了 Windows/PowerShell 的默认写法。常见元凶：

- PowerShell 5.x 的 `Out-File` / `>` / `Set-Content`——默认就给 UTF-8 加 BOM；
- `Add-Content` 在某些编码设置下也会；
- 记事本"另存为 UTF-8"；
- 某些 .NET `StreamWriter` 默认编码。

### Bug 2（更严重）：`os.remove` 在 `json.load` 之后 → 死循环

这才是"每 3 秒一条、文件永远在"的真正原因。看你的代码顺序：

```python
_cmd = json.load(_f)   # ← 这里抛异常
os.remove(_psc)        # ← 永远执行不到
```

只要解析失败，`os.remove` 就被跳过，文件留在原地，下一轮轮询又读到同一个坏文件，又失败……**无限循环**。

换句话说：就算今天是 BOM，明天换成任何一个写坏的 / 写到一半的 JSON，这段代码都会卡死在同一个文件上刷屏。**删除动作必须保证无论解析成功失败都执行。**

## 修复

两个都要修。

```python
if os.path.exists(_psc):
    _cmd = None
    try:
        # 修 Bug 1：utf-8-sig 兼容带不带 BOM 两种情况
        with open(_psc, "r", encoding="utf-8-sig") as _f:
            _cmd = json.load(_f)
    except Exception as _exc:
        _log(f"[主动发送] 指令文件解析失败，丢弃: {_exc}")
    finally:
        # 修 Bug 2：无论成功失败都删，绝不让坏文件卡住轮询
        try:
            os.remove(_psc)
        except OSError:
            pass

    if _cmd is not None:
        try:
            # ... 处理命令 ...
            pass
        except Exception as _exc:
            _log(f"[主动发送] 指令处理异常: {_exc}")
```

关键三点：

1. **读用 `utf-8-sig`**：带 BOM、不带 BOM 都能正常读，是读"别人写的 JSON"最稳的选择。
2. **删除放进 `finally`**：解析成功也删、失败也删，从根上消灭死循环。坏指令丢一次就过去了，不会刷屏。
3. **解析和处理分开 try**：解析坏 = 丢弃文件；处理逻辑报错 = 单独记日志。两类错误不要混在一个 `except` 里，否则你永远分不清是"文件坏"还是"业务逻辑坏"。

## 顺手治本：让写文件那端别再产 BOM

读端用 `utf-8-sig` 已经够稳了，但最好同时管住写端，避免以后别的程序也踩。

- **写端是 Python**：`open(path, "w", encoding="utf-8")`（Python 的 `utf-8` 写出来本来就不带 BOM，没问题）。
- **写端是 PowerShell 5.x**：别用 `Out-File`/`>`，改用明确不带 BOM 的写法：
  ```powershell
  [System.IO.File]::WriteAllText($path, $json, (New-Object System.Text.UTF8Encoding($false)))
  ```
  （`$false` = 不带 BOM）
- **写端是 PowerShell 7+**：`Set-Content -Encoding utf8NoBOM`。

## 立即止血

线上正在刷屏的话，先手动删掉那个卡住的文件让循环喘口气：

```powershell
Remove-Item C:\Users\Public\zj-proactive-send.json -Force
```

然后再按上面改代码，根治。

## 一句话总结

`utf-8` 读不剥 BOM → `json.load` 抛错；而 `os.remove` 排在 `json.load` 之后 → 坏文件永不删除 → 每 3 秒刷屏死循环。改成 `utf-8-sig` 读 + `finally` 里删文件，两个一起修。
