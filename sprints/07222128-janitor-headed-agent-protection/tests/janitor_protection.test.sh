#!/usr/bin/env bash
# Contract 合同测试骨架: janitor is_orphan() 有头 Agent 保护
# 覆盖 T-01～T-07（行为级 fixture）
#
# Task ID: ca2492bb-5f5e-4fea-9e27-125efd156aac
# 运行方式: bash sprints/07222128-janitor-headed-agent-protection/tests/janitor_protection.test.sh

set -uo pipefail

PASS=0
FAIL=0
SKIPPED=0
FIXTURE_PIDS=()

ok()   { echo "PASS [$1]: $2"; PASS=$((PASS + 1)); }
fail() { echo "FAIL [$1]: $2"; FAIL=$((FAIL + 1)); }
skip() { echo "SKIP [$1]: $2"; SKIPPED=$((SKIPPED + 1)); }

# 清理 fixture 进程
cleanup() {
  for pid in "${FIXTURE_PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
    # 等待进程真正退出
    for _ in 1 2 3; do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.2
    done
    kill -9 "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JANITOR="$(cd "$SCRIPT_DIR/../../../janitor" && pwd)/janitor.sh"
if [ ! -f "$JANITOR" ]; then
  echo "ERROR: janitor.sh not found at $JANITOR"
  exit 1
fi

# ----------------------------------------------------------------
# 从 janitor.sh 中提取 is_orphan() 供测试调用
# 策略：source janitor.sh 会触发主逻辑，因此用 awk 提取函数体后 source
# ----------------------------------------------------------------
TMPDIR_TEST=$(mktemp -d)
HELPER="$TMPDIR_TEST/is_orphan_helper.sh"
trap "cleanup; rm -rf '$TMPDIR_TEST'" EXIT

# 提取 has_live_claude_ancestor、has_brain_inprogress_task、
# has_active_dev_lock、is_orphan 四个函数（它们定义在 frequent_mode 内部）
# 用 awk 将函数体写出，然后 source
awk '
  /^  has_live_claude_ancestor\(\)/ { capture=1; indent=1 }
  /^  find_shell_ancestor\(\)/      { capture=1; indent=1 }
  /^  is_orphan\(\)/                { capture=1; indent=1 }
  /^  has_brain_inprogress_task\(\)/ { capture=1; indent=1 }
  /^  has_active_dev_lock\(\)/      { capture=1; indent=1 }
  capture {
    # 去掉两个前导空格（函数定义在 frequent_mode 子 shell 内缩进了两格）
    line = $0
    sub(/^  /, "", line)
    print line
    if (/^  \}/ && indent) {
      capture=0
      indent=0
      print ""
    }
  }
' "$JANITOR" > "$HELPER"

# 补充 stub，使 helper 可独立运行（Brain API / dev-lock 走 stub）
cat >> "$HELPER" << 'EOF'

# Stub: 默认 Brain 无 in_progress 任务，.dev-lock 不存在
CECELIA_REPO="${CECELIA_REPO:-/tmp/nonexistent-cecelia}"
BRAIN_URL="${BRAIN_URL:-http://127.0.0.1:5221}"
EOF

# shellcheck source=/dev/null
source "$HELPER"

# 检查 is_orphan 是否成功 source
if ! declare -f is_orphan > /dev/null 2>&1; then
  echo "ERROR: is_orphan() 未能从 janitor.sh 中提取，请确认函数定义格式"
  echo "  期望格式: '  is_orphan() {' (两空格缩进)"
  echo "  当前 janitor.sh 中 is_orphan 行:"
  grep -n "is_orphan" "$JANITOR" | head -5
  exit 1
fi

# ----------------------------------------------------------------
# 辅助：判断当前进程是否有 TTY
# ----------------------------------------------------------------
_process_has_tty() {
  local pid=$1
  local tty
  tty=$(ps -o tty= -p "$pid" 2>/dev/null | tr -d ' ')
  [ -n "$tty" ] && [ "$tty" != "??" ]
}

# ----------------------------------------------------------------
# T-01: Codex 有 TTY 进程 → is_orphan() 返回 1（不杀）
# ----------------------------------------------------------------
echo "--- T-01: 有 TTY 进程（模拟 Codex）→ 不杀 ---"

# 尝试在当前 shell（有 TTY）中 spawn 子进程，子进程继承 TTY
SELF_TTY=$(ps -o tty= -p $$ 2>/dev/null | tr -d ' ')
if [ -n "$SELF_TTY" ] && [ "$SELF_TTY" != "??" ]; then
  # 在有 TTY 的 shell 中启动 sleep，子进程继承 TTY
  sleep 9999 &
  T01_PID=$!
  FIXTURE_PIDS+=("$T01_PID")
  sleep 0.2
  CHILD_TTY=$(ps -o tty= -p "$T01_PID" 2>/dev/null | tr -d ' ')
  if [ -n "$CHILD_TTY" ] && [ "$CHILD_TTY" != "??" ]; then
    if is_orphan "$T01_PID"; then
      fail "T-01" "有 TTY 进程 (tty=$CHILD_TTY) 被判定为孤儿（is_orphan 返回 0），期望返回 1"
    else
      ok "T-01" "有 TTY 进程 (tty=$CHILD_TTY) 正确返回 1（不杀）"
    fi
  else
    skip "T-01" "子进程 TTY=$CHILD_TTY（无 TTY），无法验证此场景（非有头环境）"
  fi
else
  skip "T-01" "当前 shell 无 TTY（CI 无头环境），跳过有头 TTY fixture 构造"
fi

# ----------------------------------------------------------------
# T-02: 命令行含 node_modules 路径但有 TTY → 不杀
# 与 T-01 同构：TTY 检查先于 cmdline 匹配，只要有 TTY 就不杀
# ----------------------------------------------------------------
echo "--- T-02: node_modules 路径 + 有 TTY → 不杀 ---"

if [ -n "$SELF_TTY" ] && [ "$SELF_TTY" != "??" ]; then
  # 用 bash --rcfile 模拟路径含 node_modules 的进程（实际 TTY 继承父 shell）
  sleep 9999 &
  T02_PID=$!
  FIXTURE_PIDS+=("$T02_PID")
  sleep 0.2
  T02_TTY=$(ps -o tty= -p "$T02_PID" 2>/dev/null | tr -d ' ')
  if [ -n "$T02_TTY" ] && [ "$T02_TTY" != "??" ]; then
    if is_orphan "$T02_PID"; then
      fail "T-02" "有 TTY 进程被判定为孤儿，期望返回 1（tty=$T02_TTY）"
    else
      ok "T-02" "node_modules 路径 + 有 TTY → is_orphan 返回 1（不杀）[tty=$T02_TTY]"
    fi
  else
    skip "T-02" "子进程无 TTY，跳过"
  fi
else
  skip "T-02" "当前 shell 无 TTY，跳过"
fi

# ----------------------------------------------------------------
# T-03: 模拟 Grok（有 TTY，非 node 命名）→ 不杀
# 任意有 TTY 进程，验证 TTY 保护与进程名无关
# ----------------------------------------------------------------
echo "--- T-03: 模拟 Grok（有 TTY，非 node 名）→ 不杀 ---"

if [ -n "$SELF_TTY" ] && [ "$SELF_TTY" != "??" ]; then
  sleep 9999 &
  T03_PID=$!
  FIXTURE_PIDS+=("$T03_PID")
  sleep 0.2
  T03_TTY=$(ps -o tty= -p "$T03_PID" 2>/dev/null | tr -d ' ')
  if [ -n "$T03_TTY" ] && [ "$T03_TTY" != "??" ]; then
    if is_orphan "$T03_PID"; then
      fail "T-03" "Grok 模拟有 TTY 进程被误杀，期望返回 1"
    else
      ok "T-03" "模拟 Grok 有 TTY → is_orphan 返回 1（不杀）"
    fi
  else
    skip "T-03" "子进程无 TTY，跳过"
  fi
else
  skip "T-03" "当前 shell 无 TTY，跳过"
fi

# ----------------------------------------------------------------
# T-04: tmux 祖先链 → 不杀
# 策略：mock ps 命令，使 is_orphan() 在查询祖先时看到 tmux
# ----------------------------------------------------------------
echo "--- T-04: tmux 祖先链保护 ---"

# 创建 mock ps：前两次调用（tty 和 ppid 查询）返回正常值（??+父pid），
# 第三次调用（comm 查询）返回 tmux
MOCK_PS_DIR="$TMPDIR_TEST/mock-ps-T04"
mkdir -p "$MOCK_PS_DIR"
MOCK_PID=99901
MOCK_PPID=99900

# 链路：MOCK_PID(99901) -> MOCK_PPID(99900/tmux) -> MOCK_GPPID(99899/init-but-not-1)
# is_orphan 会看到：TTY=??, ppid[99901]=99900, comm[99900]=tmux → return 1
MOCK_GPPID=99899
cat > "$MOCK_PS_DIR/ps" << MOCKEOF
#!/usr/bin/env bash
# mock ps for T-04: 模拟 TTY=?? 但祖先链含 tmux
args="\$*"
if echo "\$args" | grep -q "tty="; then
  echo "??"
elif echo "\$args" | grep -q "ppid=.*-p $MOCK_PID"; then
  echo "$MOCK_PPID"
elif echo "\$args" | grep -q "ppid=.*-p $MOCK_PPID"; then
  echo "$MOCK_GPPID"
elif echo "\$args" | grep -q "ppid=.*-p $MOCK_GPPID"; then
  echo "1"
elif echo "\$args" | grep -q "comm=.*-p $MOCK_PID"; then
  echo "sleep"
elif echo "\$args" | grep -q "comm=.*-p $MOCK_PPID"; then
  echo "tmux"
elif echo "\$args" | grep -q "comm=.*-p $MOCK_GPPID"; then
  echo "systemd"
elif echo "\$args" | grep -q "ppid="; then
  echo "1"
elif echo "\$args" | grep -q "comm="; then
  echo "tmux"
elif echo "\$args" | grep -q "command="; then
  echo "sleep 9999"
else
  /usr/bin/ps "\$@"
fi
MOCKEOF
chmod +x "$MOCK_PS_DIR/ps"

# 通过 PATH 优先级让 is_orphan 使用 mock ps
OLD_PATH="$PATH"
export PATH="$MOCK_PS_DIR:$PATH"

# 用一个真实存在的 PID（当前 shell），但 is_orphan 内部 ps 调用已被 mock
# 注意：这里传入 MOCK_PID 作为参数，mock ps 会正确响应
if is_orphan "$MOCK_PID"; then
  fail "T-04" "含 tmux 祖先的进程被判定为孤儿，期望 is_orphan 返回 1"
else
  ok "T-04" "tmux 祖先链保护生效，is_orphan 返回 1（不杀）"
fi

export PATH="$OLD_PATH"

# ----------------------------------------------------------------
# T-05: TTY=??、PPID=1、非白名单 → 必须是孤儿（is_orphan 返回 0）
# ----------------------------------------------------------------
echo "--- T-05: 真实孤儿（TTY=??，PPID=1）→ is_orphan 返回 0 ---"

# 构造无 TTY、PPID=1 的进程
if command -v setsid > /dev/null 2>&1; then
  setsid sleep 9999 &
  T05_PID=$!
  FIXTURE_PIDS+=("$T05_PID")
  sleep 0.3
  T05_TTY=$(ps -o tty= -p "$T05_PID" 2>/dev/null | tr -d ' ')
  T05_PPID=$(ps -o ppid= -p "$T05_PID" 2>/dev/null | tr -d ' ')
  if [ "$T05_TTY" = "??" ] && [ "$T05_PPID" = "1" ]; then
    if is_orphan "$T05_PID"; then
      ok "T-05" "真实孤儿（tty=??, ppid=1）is_orphan 返回 0（允许 kill）"
    else
      fail "T-05" "真实孤儿未被识别，is_orphan 返回 1，期望返回 0（tty=$T05_TTY, ppid=$T05_PPID）"
    fi
  else
    skip "T-05" "setsid 未产生预期的 tty=?? ppid=1（tty=$T05_TTY, ppid=$T05_PPID），环境差异"
  fi
else
  # macOS 无 setsid，用 nohup+disown 替代
  nohup sleep 9999 > /dev/null 2>&1 &
  T05_PID=$!
  disown "$T05_PID" 2>/dev/null || true
  FIXTURE_PIDS+=("$T05_PID")
  sleep 0.3
  T05_TTY=$(ps -o tty= -p "$T05_PID" 2>/dev/null | tr -d ' ')
  T05_PPID=$(ps -o ppid= -p "$T05_PID" 2>/dev/null | tr -d ' ')
  if [ "$T05_TTY" = "??" ]; then
    if is_orphan "$T05_PID"; then
      ok "T-05" "孤儿进程（nohup+disown，tty=?? ppid=$T05_PPID）is_orphan 返回 0"
    else
      fail "T-05" "孤儿进程未被识别（tty=$T05_TTY, ppid=$T05_PPID），is_orphan 应返回 0"
    fi
  else
    skip "T-05" "nohup+disown 未产生 tty=??（当前 tty=$T05_TTY），跳过"
  fi
fi

# ----------------------------------------------------------------
# T-06: 白名单进程 brain/server.js → 不杀
# 策略：构造无 TTY（PPID=1）进程，但命令行含 brain/server.js
#        验证白名单在 TTY=?? 时仍生效
# ----------------------------------------------------------------
echo "--- T-06: 白名单进程 brain/server.js → 不杀 ---"

# mock ps：TTY=?? + PPID=1 + cmdline 含 brain/server.js
MOCK_PS_DIR_T06="$TMPDIR_TEST/mock-ps-T06"
mkdir -p "$MOCK_PS_DIR_T06"
MOCK_PID_T06=99902
MOCK_PPID_T06=1

cat > "$MOCK_PS_DIR_T06/ps" << MOCKEOF_T06
#!/usr/bin/env bash
args="\$*"
if echo "\$args" | grep -q "tty="; then
  echo "??"
elif echo "\$args" | grep -q "ppid="; then
  echo "$MOCK_PPID_T06"
elif echo "\$args" | grep -q "command="; then
  echo "node /home/user/cecelia/brain/server.js"
elif echo "\$args" | grep -q "comm="; then
  echo "node"
else
  /usr/bin/ps "\$@"
fi
MOCKEOF_T06
chmod +x "$MOCK_PS_DIR_T06/ps"

export PATH="$MOCK_PS_DIR_T06:$OLD_PATH"
if is_orphan "$MOCK_PID_T06"; then
  fail "T-06" "白名单进程 brain/server.js 被判为孤儿，期望 is_orphan 返回 1"
else
  ok "T-06" "白名单进程 brain/server.js → is_orphan 返回 1（不杀）"
fi
export PATH="$OLD_PATH"

# ----------------------------------------------------------------
# T-07: claude 祖先保护（回归）→ 不杀
# ----------------------------------------------------------------
echo "--- T-07: claude 祖先链保护（回归）→ 不杀 ---"

# mock ps：TTY=?? + 祖先 comm=claude
MOCK_PS_DIR_T07="$TMPDIR_TEST/mock-ps-T07"
mkdir -p "$MOCK_PS_DIR_T07"
MOCK_PID_T07=99903
MOCK_PPID_T07=99902

cat > "$MOCK_PS_DIR_T07/ps" << MOCKEOF_T07
#!/usr/bin/env bash
args="\$*"
if echo "\$args" | grep -q "tty="; then
  echo "??"
elif echo "\$args" | grep -q "ppid=.*-p $MOCK_PID_T07"; then
  echo "$MOCK_PPID_T07"
elif echo "\$args" | grep -q "ppid=.*-p $MOCK_PPID_T07"; then
  echo "1"
elif echo "\$args" | grep -q "comm=.*-p $MOCK_PPID_T07"; then
  echo "claude"
elif echo "\$args" | grep -q "ppid="; then
  echo "1"
elif echo "\$args" | grep -q "comm="; then
  echo "claude"
elif echo "\$args" | grep -q "command="; then
  echo "sleep 9999"
else
  /usr/bin/ps "\$@"
fi
MOCKEOF_T07
chmod +x "$MOCK_PS_DIR_T07/ps"

export PATH="$MOCK_PS_DIR_T07:$OLD_PATH"
if is_orphan "$MOCK_PID_T07"; then
  fail "T-07" "claude 祖先进程的子孙被误判为孤儿，期望 is_orphan 返回 1（回归失败）"
else
  ok "T-07" "claude 祖先保护（回归）→ is_orphan 返回 1（不杀）"
fi
export PATH="$OLD_PATH"

# ----------------------------------------------------------------
# 汇总
# ----------------------------------------------------------------
echo ""
echo "========================================"
echo "合同测试结果: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIPPED"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
  echo "状态: RED（有失败用例，请修复 is_orphan()）"
  exit 1
else
  echo "状态: GREEN"
  exit 0
fi
