# Janitor 误伤豁免 + kill 复查 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** kill_if_orphan / kill_if_claude_orphan 豁免 cecelia 常驻路径；kill 后复查死活，失败不计数不谎报；新守卫+存量 orphan 测试点名进 CI。

**Architecture:** 单文件 bash 改动 + 新静态断言测试（TDD 红→绿）+ lint-skills.yml 两个 step。

**Tech Stack:** bash（macOS 3.2 兼容）、GitHub Actions。

## Global Constraints

- 工作目录：`/Users/administrator/worktrees/zenithjoy-skills/janitor-kill-exempt-verify`
- TDD：commit-1 = 新测试 + CI 点名（红）；commit-2 = janitor.sh 实现（绿）
- 豁免匹配必须是全路径子串 `*"/usr/local/libexec/cecelia/"*`，**禁用裸 `*cecelia*`**
- 注释简体中文；commit message 结尾：`Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: 全部改动（红→绿两个 commit）

**Files:**
- Create: `janitor/__tests__/janitor_kill_exempt.test.sh`（chmod +x）
- Modify: `.github/workflows/lint-skills.yml`（audiomxd step 之后加两个 step）
- Modify: `janitor/janitor.sh`（kill_if_orphan 282 行附近、kill_if_claude_orphan 340 行附近）

- [ ] **Step 1（commit-1 红）: 新守卫测试**

创建 `janitor/__tests__/janitor_kill_exempt.test.sh`：

```bash
#!/usr/bin/env bash
# 回归守卫：janitor 误伤豁免 + kill 复查（2026-08-05，决策 e8427238，issue ab1da1d7）
# 背景：fleet-worker(/usr/local/libexec/cecelia/)被当 node 孤儿，kill EPERM 静默失败仍谎报 killed。

set -uo pipefail
PASS=0; FAIL=0
ok() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

JANITOR="$(dirname "$0")/../janitor.sh"
[ -f "$JANITOR" ] || { echo "ERROR: janitor.sh not found"; exit 1; }

# 1. 豁免路径字面量在两个 kill 函数中各出现一次（共≥2处）
EXEMPT_COUNT=$(grep -c '/usr/local/libexec/cecelia/' "$JANITOR")
if [ "$EXEMPT_COUNT" -ge 2 ]; then
  ok "cecelia 常驻路径豁免存在（${EXEMPT_COUNT}处）"
else
  fail "cecelia 常驻路径豁免缺失或不足两处（当前${EXEMPT_COUNT}处）"
fi

# 2. 禁用过宽匹配：不得出现裸 *cecelia* 匹配（会误豁免 perfect21/cecelia* 开发目录）
if grep -qE 'in \*cecelia\*' "$JANITOR"; then
  fail "检测到过宽的 *cecelia* 裸匹配"
else
  ok "无过宽裸匹配"
fi

# 3. kill-failed 复查分支存在（两处）
KF_COUNT=$(grep -c 'kill-failed' "$JANITOR")
if [ "$KF_COUNT" -ge 2 ]; then
  ok "kill-failed 复查分支存在（${KF_COUNT}处）"
else
  fail "kill-failed 复查分支缺失或不足两处（当前${KF_COUNT}处）"
fi

# 4. 行序：每个 KILLED 自增之前必须先有 kill-failed 复查（用 awk 检查每个
#    'KILLED=$((KILLED + 1))' 行号之前 12 行内出现过 kill-failed）
ORDER_OK=$(awk '
  /kill-failed/ { last_kf = NR }
  /KILLED=\$\(\(KILLED \+ 1\)\)/ { if (last_kf == 0 || NR - last_kf > 12) bad = 1 }
  END { print (bad ? "BAD" : "OK") }
' "$JANITOR")
if [ "$ORDER_OK" = "OK" ]; then
  ok "KILLED 计数均在 kill-failed 复查之后"
else
  fail "存在未经复查即计数的 KILLED 自增"
fi

echo "结果: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
```

然后 `chmod +x janitor/__tests__/janitor_kill_exempt.test.sh`。

- [ ] **Step 2: CI 点名两个测试**

`.github/workflows/lint-skills.yml` 在 `Regression — janitor audiomxd 日志格式` step 之后追加：

```yaml
      # 回归守卫：janitor 误伤豁免与 kill 复查（决策 e8427238）
      - name: Regression — janitor kill 豁免与复查
        run: bash janitor/__tests__/janitor_kill_exempt.test.sh

      # 存量守卫接入：janitor 基础函数/阈值断言（此前从未进 CI）
      - name: Regression — janitor 基础断言
        run: bash janitor/__tests__/janitor_orphan.test.sh
```

- [ ] **Step 3: 跑测试确认红**

Run: `bash janitor/__tests__/janitor_kill_exempt.test.sh`
Expected: 断言 1/3/4 FAIL（现代码无豁免、无 kill-failed），退出码 1。亲见红记报告。同时跑 `bash janitor/__tests__/janitor_orphan.test.sh` 确认存量测试本身是绿（30/30），保证点名不引爆。

- [ ] **Step 4: Commit（红）**

```bash
git add janitor/__tests__/janitor_kill_exempt.test.sh .github/workflows/lint-skills.yml
git commit -m "fix(janitor): 误伤豁免+kill复查守卫测试并点名进 CI（红）"
```

- [ ] **Step 5（commit-2 绿）: janitor.sh 两函数改造**

a) `kill_if_orphan` 中 `if is_orphan "$pid"; then` 一行**之前**插入：

```bash
    # cecelia 常驻服务豁免（fleet-worker/toolchain 等，issue ab1da1d7 误伤实证）。
    # 全路径子串匹配（覆盖外部解释器拉起形态）；禁用裸 *cecelia*——会误豁免
    # ~/perfect21/cecelia* 开发目录进程，那些正是本函数该管的对象。
    local cmd
    cmd=$(ps -o command= -p "$pid" 2>/dev/null)
    case "$cmd" in *"/usr/local/libexec/cecelia/"*) return ;; esac
```

b) `kill_if_orphan` 中 `kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null` 与 `KILLED=$((KILLED + 1))` 之间插入：

```bash
      # kill 后复查：无 sudo 杀非本人进程会 EPERM 静默失败，此前仍计数打 killed
      # 日志（谎报数周，issue ab1da1d7）。仍存活 → 打 kill-failed 不计数。
      sleep 1
      if kill -0 "$pid" 2>/dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] kill-failed node/vitest pid=$pid 仍存活（疑似权限不足），不计数"
        return
      fi
```

c) `kill_if_claude_orphan` 中 `if is_claude_orphan "$pid" "$tty" "$ppid"; then` 一行**之前**插入与 a) 相同的豁免块（注释可简写为 `# cecelia 常驻服务豁免（同 kill_if_orphan，issue ab1da1d7）`）。

d) `kill_if_claude_orphan` 中 `kill -0 ... && kill -9 ...` 与 `KILLED=$((KILLED + 1))` 之间插入：

```bash
      sleep 1
      if kill -0 "$pid" 2>/dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] kill-failed claude pid=$pid 仍存活（疑似权限不足），不计数"
        return
      fi
```

（return 同时跳过 KILLED 自增、killed 日志与 `notify_brain_orphan_killed`——这正是要的语义。）

- [ ] **Step 6: 验证绿**

```bash
bash janitor/__tests__/janitor_kill_exempt.test.sh
bash janitor/__tests__/janitor_orphan.test.sh
bash janitor/__tests__/janitor_etime_octal.test.sh
bash janitor/__tests__/janitor_audiomxd_log_format.test.sh
bash -n janitor/janitor.sh && /bin/bash -n janitor/janitor.sh
```
Expected: 四测试全 PASS、双版本语法过。

- [ ] **Step 7: Commit（绿）**

```bash
git add janitor/janitor.sh
git commit -m "fix(janitor): cecelia 常驻路径豁免 + kill 后复查防谎报（绿）"
```
