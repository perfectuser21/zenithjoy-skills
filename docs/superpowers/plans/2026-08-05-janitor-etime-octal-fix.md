# Janitor etime 八进制换算修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `janitor/janitor.sh` 中 `etime_to_secs()` 对 `DD-` 前缀（days=08/09）按八进制解析导致的致命错误与调用点阈值 fail-open 穿透，并留下 proven-to-fire 的 CI 守卫。

**Architecture:** 纯 bash 修复：函数内全部算术改 `10#` 强制十进制 + 入参正则校验返 0；两个调用点加空值 fail-loud 兜底。守卫测试从 janitor.sh 实文件 sed 提取函数体 eval 执行（防测试与实现漂移），并在 lint-skills.yml 点名（该仓 CI 不自动发现测试）。

**Tech Stack:** bash（须兼容 macOS /bin/bash 3.2 与 CI ubuntu bash 5，已实测双版本）、GitHub Actions。

## Global Constraints

- 工作目录：`/Users/administrator/worktrees/zenithjoy-skills/janitor-etime-octal-fix`（分支 `cp-0805085034-janitor-etime-octal-fix`）
- TDD 铁律：NO PRODUCTION CODE WITHOUT FAILING TEST FIRST；commit-1 = 红测试，commit-2 = 实现转绿
- 正则必须放变量再 `[[ =~ $re ]]`（bash 3.2 兼容写法）
- 不改 audiomxd 逻辑、不动 is_orphan、不迁移旧 grep 式测试
- 所有注释/输出简体中文

---

### Task 1: 守卫测试（红）+ CI 接线

**Files:**
- Create: `janitor/__tests__/janitor_etime_octal.test.sh`（chmod +x）
- Modify: `.github/workflows/lint-skills.yml`（lint-skills job 末尾，post-pr-create regression step 之后）

**Interfaces:**
- Produces: 测试断言 `etime_to_secs` 9 个样本的精确秒数 + stderr 干净；Task 2 的实现必须让它转绿

- [ ] **Step 1: 写守卫测试**

创建 `janitor/__tests__/janitor_etime_octal.test.sh`，内容如下：

```bash
#!/usr/bin/env bash
# 回归守卫：etime_to_secs 八进制换算炸弹（2026-08-05，决策 616183dc）
# 根因：ps -o etime 的 DD- 前缀 days=08/09（进程运行满 8~9 天）被 bash 按八进制解析，
# 致命算术错误 → $() 子 shell 退出 → 函数返回空串 → 调用点阈值比较 fail-open 穿透。
# 本测试从 janitor.sh 实文件提取函数体执行——实现改回旧写法必然报红。

set -uo pipefail

PASS=0
FAIL=0

ok() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

JANITOR="$(dirname "$0")/../janitor.sh"
if [ ! -f "$JANITOR" ]; then
  echo "ERROR: janitor.sh not found at $JANITOR"
  exit 1
fi

# 从实文件提取 etime_to_secs 函数体（两空格缩进定义）
FN_SRC=$(sed -n '/^  etime_to_secs() {/,/^  }/p' "$JANITOR")
if [ -z "$FN_SRC" ]; then
  fail "无法从 janitor.sh 提取 etime_to_secs 函数体"
  echo "结果: PASS=$PASS FAIL=$FAIL"
  exit 1
fi
eval "$FN_SRC"

# 断言：样本 → 期望秒数，且 stderr 必须干净（八进制炸弹的症状就是 stderr 报错 + 返回空串）
assert_secs() {
  local sample="$1" expected="$2"
  local stderr_file got err
  stderr_file=$(mktemp)
  got=$(etime_to_secs "$sample" 2>"$stderr_file")
  err=$(cat "$stderr_file")
  rm -f "$stderr_file"
  if [ "$got" = "$expected" ] && [ -z "$err" ]; then
    ok "etime_to_secs '$sample' → $expected"
  else
    fail "etime_to_secs '$sample' → got='$got' expected='$expected' stderr='$err'"
  fi
}

assert_secs "08-16:10:29" 749429   # 真实触发形态：days=08 八进制炸点（2026-08 现场 pid 64880）
assert_secs "09-00:00:01" 777601   # days=09 炸点
assert_secs "3-08:00:00" 288000    # 单位数 days + HH=08
assert_secs "1-02:03:04" 93784     # 正常 days 回归
assert_secs "00:08:30" 510         # HH=00 + MM=08
assert_secs "08:09" 489            # MM:SS 两段形态
assert_secs "45" 45                # 单段形态
assert_secs "" 0                   # 空串兜底出口
assert_secs "garbage" 0            # 非法输入兜底出口

echo "结果: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
```

然后 `chmod +x janitor/__tests__/janitor_etime_octal.test.sh`。

- [ ] **Step 2: 跑测试确认对旧实现报红**

Run: `bash janitor/__tests__/janitor_etime_octal.test.sh`
Expected: `08-16:10:29`、`09-00:00:01` 两条 FAIL（got 为空串、stderr 含 `value too great for base`），退出码 1。**必须亲眼看到这两条红**——这是 proven-to-fire 证据。

- [ ] **Step 3: CI 接线**

在 `.github/workflows/lint-skills.yml` 的 lint-skills job 中，`Regression — post-pr-create rewrite/* 豁免` step 之后追加：

```yaml
      # 回归守卫：janitor etime 八进制换算（决策 616183dc）
      - name: Regression — janitor etime 八进制换算
        run: bash janitor/__tests__/janitor_etime_octal.test.sh
```

- [ ] **Step 4: Commit（commit-1，红）**

```bash
git add janitor/__tests__/janitor_etime_octal.test.sh .github/workflows/lint-skills.yml
git commit -m "fix(janitor): 增加 etime 八进制换算守卫测试并接进 CI（红）"
```

---

### Task 2: 修复实现（绿）

**Files:**
- Modify: `janitor/janitor.sh:97-116`（etime_to_secs 函数）
- Modify: `janitor/janitor.sh:271-272`（kill_if_orphan 调用点）
- Modify: `janitor/janitor.sh:328-329`（kill_if_claude_orphan 调用点）
- Modify: `docs/superpowers/specs/2026-08-05-janitor-etime-octal-fix-design.md`（正则收紧一行，与实现对齐）

**Interfaces:**
- Consumes: Task 1 的测试（必须转绿）
- Produces: `etime_to_secs` 对任意输入恒返回十进制秒数或 0，永不输出空串/报错

- [ ] **Step 1: 改 etime_to_secs**

将 `janitor/janitor.sh` 第 97-116 行整体替换为：

```bash
  # etime 格式（[[DD-]HH:]MM:SS）转秒数；非法输入返回 0。
  # 勿删 10#：前导零会被 bash 按八进制解析，days=08/09（进程运行满 8 天）曾致命报错
  # 并返回空串穿透调用点阈值检查，见 __tests__/janitor_etime_octal.test.sh
  etime_to_secs() {
    local elapsed="$1"
    local secs=0
    local re='^([0-9]+-)?[0-9]{1,2}(:[0-9]{2}){0,2}$'
    if ! [[ "$elapsed" =~ $re ]]; then
      echo 0
      return
    fi
    if echo "$elapsed" | grep -q '-'; then
      local days rest
      days=$(echo "$elapsed" | cut -d'-' -f1)
      rest=$(echo "$elapsed" | cut -d'-' -f2)
      secs=$((10#$days * 86400))
      elapsed="$rest"
    fi
    local parts
    IFS=: read -ra parts <<< "$elapsed"
    case ${#parts[@]} in
      3) secs=$((secs + 10#${parts[0]}*3600 + 10#${parts[1]}*60 + 10#${parts[2]})) ;;
      2) secs=$((secs + 10#${parts[0]}*60 + 10#${parts[1]})) ;;
      1) secs=$((secs + 10#${parts[0]})) ;;
    esac
    echo "$secs"
  }
```

（原第 97 行注释被上面前三行注释替代；函数名、缩进、签名不变，旧测试 `janitor_orphan.test.sh` 的函数存在性 grep 不受影响。）

- [ ] **Step 2: 改两个调用点**

`kill_if_orphan` 内（原 271-272 行）：

```bash
    secs=$(etime_to_secs "$elapsed")
    [ -z "$secs" ] && { echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] etime_to_secs 解析失败 elapsed=$elapsed pid=$pid，保守跳过"; secs=0; }
    [ "$secs" -lt "$threshold" ] && return
```

`kill_if_claude_orphan` 内（原 328-329 行）同样处理：

```bash
    secs=$(etime_to_secs "$elapsed")
    [ -z "$secs" ] && { echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] etime_to_secs 解析失败 elapsed=$elapsed pid=$pid，保守跳过"; secs=0; }
    [ "$secs" -lt "$threshold" ] && return
```

- [ ] **Step 3: spec 正则一行对齐**

`docs/superpowers/specs/2026-08-05-janitor-etime-octal-fix-design.md` 中
`^([0-9]+-)?[0-9:]+$` 替换为 `^([0-9]+-)?[0-9]{1,2}(:[0-9]{2}){0,2}$`
（收紧以杜绝 `:30`/`5:` 这类畸形串在 bash 5 下 `10#` 空段报错的理论出口）。

- [ ] **Step 4: 跑测试确认转绿**

Run: `bash janitor/__tests__/janitor_etime_octal.test.sh`
Expected: 9 条全 PASS，`结果: PASS=9 FAIL=0`，退出码 0。

- [ ] **Step 5: 双 bash 版本验证**

Run: `/bin/bash janitor/__tests__/janitor_etime_octal.test.sh && /opt/homebrew/bin/bash janitor/__tests__/janitor_etime_octal.test.sh`
Expected: 两次都 `PASS=9 FAIL=0`（bash 3.2 与 bash 5 兼容）。

- [ ] **Step 6: 真机 etime 回放（integration，不跑完整 janitor，避免真杀进程）**

```bash
FN_SRC=$(sed -n '/^  etime_to_secs() {/,/^  }/p' janitor/janitor.sh); eval "$FN_SRC"
ps -axo etime | tail -n +2 | tr -d ' ' | while read -r et; do
  [ -z "$et" ] && continue
  s=$(etime_to_secs "$et" 2>&1)
  case "$s" in (*[!0-9]*|"") echo "BAD: '$et' -> '$s'";; esac
done; echo "回放完成"
```

Expected: 只输出 `回放完成`，无 BAD 行（本机现存 8 天+ 进程，天然覆盖炸点形态）。

- [ ] **Step 7: Commit（commit-2，绿）**

```bash
git add janitor/janitor.sh docs/superpowers/specs/2026-08-05-janitor-etime-octal-fix-design.md
git commit -m "fix(janitor): etime_to_secs 强制十进制 + 调用点空值兜底（绿）"
```
