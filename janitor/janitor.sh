#!/usr/bin/env bash
# =============================================================================
# Janitor（小扫）- 系统清扫员（Mac mini 版 v4.0）
# 两种模式：
#   daily    - 磁盘清理（每天 4am）
#   frequent - 僵尸/孤儿进程清理（每 15 分钟）
#
# v4.0 变更：
#   frequent 模式新增 claude 孤儿检测：
#   - 条件：TTY=?? + ppid=1 + 运行>阈值 + Brain无in_progress任务 + 无.dev-lock
#   - 双重验证（Brain DB + .dev-lock），任一存在则保守跳过
#   - 内存 >=90%：阈值从 600s 降至 300s（MEM_HIGH_THRESHOLD_SEC）
#   - CPU >=85%：向 Brain 上报告警任务（CPU_ALERT_THRESHOLD）
#   - crontab 应指向软链接 ~/bin/janitor.sh → 此文件
# =============================================================================

MODE="daily"
for arg in "$@"; do
  case "$arg" in
    --mode=*) MODE="${arg#*=}" ;;
    --mode)   shift_next=1 ;;
    *)
      if [ "$shift_next" = "1" ]; then
        MODE="$arg"
        shift_next=0
      fi
      ;;
  esac
done

# cron 默认 PATH 只有 /usr/bin:/bin，找不到装在 /opt/homebrew/bin 的 npm/brew/docker，
# 导致 cron 触发的清理长期跳过这三步（手动跑因继承交互 shell PATH 能成功，二者对比暴露此差异）。
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

CECELIA_REPO="/Users/administrator/perfect21/cecelia"
BRAIN_API="http://localhost:5221"
TOTAL_STEPS=10
# 磁盘用量必须查实际数据卷，不是 / —— APFS 下 / 是只读系统卷（firmlink），用量长期 ~30%，
# 跟真实数据卷 /System/Volumes/Data 的用量完全对不上，曾导致 70% 告警从未触发。
DISK_VOL="/System/Volumes/Data"

# ─────────────────────────────────────────────
# frequent 模式：清理孤儿/僵尸进程 + 资源压力响应
# ─────────────────────────────────────────────
if [ "$MODE" = "frequent" ]; then
  THRESHOLD_SEC=600          # 正常阈值：10 分钟
  MEM_HIGH_THRESHOLD_SEC=300 # 内存高压阈值：5 分钟
  CPU_ALERT_THRESHOLD=85     # CPU 高压告警触发点（%）
  MEM_HIGH_WATERMARK=90      # 内存高压水位（%）
  KILLED=0

  # ── 检测当前资源压力 ──────────────────────────────
  _get_mem_usage_pct() {
    local total pagesize pages_free pages_spec free_bytes
    total=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
    pagesize=$(sysctl -n hw.pagesize 2>/dev/null || echo "4096")
    pages_free=$(vm_stat 2>/dev/null | awk '/Pages free/{gsub(/\./,"",$3); print $3+0}')
    pages_spec=$(vm_stat 2>/dev/null | awk '/Pages speculative/{gsub(/\./,"",$3); print $3+0}')
    pages_free=${pages_free:-0}
    pages_spec=${pages_spec:-0}
    free_bytes=$(( (pages_free + pages_spec) * pagesize ))
    if [ "$total" -gt 0 ]; then
      echo $(( (total - free_bytes) * 100 / total ))
    else
      echo 0
    fi
  }

  _get_cpu_usage_pct() {
    local load cores
    load=$(sysctl -n vm.loadavg 2>/dev/null | awk '{gsub(/[{}]/,"",$2); print $2}')
    cores=$(sysctl -n hw.logicalcpu 2>/dev/null || echo "1")
    [ -z "$load" ] || [ "$cores" -eq 0 ] && echo 0 && return
    awk "BEGIN{pct=$load/$cores*100; if(pct>100)pct=100; printf \"%d\", pct}"
  }

  MEM_PCT=$(_get_mem_usage_pct)
  CPU_PCT=$(_get_cpu_usage_pct)

  # 内存高压：降低清理阈值
  ACTIVE_THRESHOLD=$THRESHOLD_SEC
  if [ "$MEM_PCT" -ge "$MEM_HIGH_WATERMARK" ] 2>/dev/null; then
    ACTIVE_THRESHOLD=$MEM_HIGH_THRESHOLD_SEC
    echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] 内存高压 ${MEM_PCT}%，清理阈值降至 ${MEM_HIGH_THRESHOLD_SEC}s"
  fi

  # CPU 高压：上报 Brain 告警
  if [ "$CPU_PCT" -ge "$CPU_ALERT_THRESHOLD" ] 2>/dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] CPU 高压 ${CPU_PCT}%，上报 Brain 告警..."
    curl -s -X POST "${BRAIN_API}/api/brain/tasks" \
      -H "Content-Type: application/json" \
      -d "{\"title\":\"⚠️ CPU 高压告警 ${CPU_PCT}%（Janitor 检测）\",\"priority\":\"P1\",\"task_type\":\"alert\",\"domain\":\"agent_ops\",\"description\":\"Mac mini M4 CPU ${CPU_PCT}% 超过 ${CPU_ALERT_THRESHOLD}% 阈值，请检查是否有失控进程。\"}" \
      2>/dev/null || true
  fi

  # ── 工具函数 ──────────────────────────────────────
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
    if echo "$elapsed" | command grep -q '-'; then
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

  # 向上遍历父进程链，找最近 shell 祖先
  find_shell_ancestor() {
    local pid=$1
    local current=$pid
    local depth=0
    local max_depth=20
    while [ $depth -lt $max_depth ]; do
      local ppid
      ppid=$(ps -o ppid= -p "$current" 2>/dev/null | tr -d ' ')
      [ -z "$ppid" ] || [ "$ppid" = "0" ] && break
      [ "$ppid" = "1" ] && { echo "$current"; return; }
      local comm
      comm=$(ps -o comm= -p "$ppid" 2>/dev/null | tr -d ' ')
      case "$comm" in
        *zsh*|*bash*) echo "$ppid" ;;
      esac
      current=$ppid
      depth=$((depth + 1))
    done
  }

  # 检查祖先链中是否有活着的 claude 进程
  has_live_claude_ancestor() {
    local pid=$1
    local current=$pid
    local depth=0
    local max_depth=20
    while [ $depth -lt $max_depth ]; do
      local ppid
      ppid=$(ps -o ppid= -p "$current" 2>/dev/null | tr -d ' ')
      [ -z "$ppid" ] || [ "$ppid" = "0" ] || [ "$ppid" = "1" ] && return 1
      local comm
      comm=$(ps -o comm= -p "$ppid" 2>/dev/null)
      if echo "$comm" | grep -qi "claude"; then
        return 0
      fi
      current=$ppid
      depth=$((depth + 1))
    done
    return 1
  }

  # Brain DB 检查：是否有 in_progress 任务
  # 返回 0 = 有记录（保守：Brain不可达也返回0），返回 1 = 确认无记录
  has_brain_inprogress_task() {
    local resp
    resp=$(curl -s --max-time 3 "${BRAIN_API}/api/brain/tasks?status=in_progress&limit=50" 2>/dev/null)
    [ -z "$resp" ] && return 0  # Brain 不可达 → 保守
    local count
    count=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo "0")
    [ "$count" -gt 0 ] && return 0
    return 1
  }

  # .dev-lock 检查：是否有活跃 dev session
  has_active_dev_lock() {
    local wt_dir="$CECELIA_REPO/.claude/worktrees"
    if [ -d "$wt_dir" ]; then
      local lock_count
      lock_count=$(find "$wt_dir" -maxdepth 2 -name ".dev-lock.*" 2>/dev/null | wc -l | tr -d ' ')
      [ "$lock_count" -gt 0 ] && return 0
    fi
    local main_lock
    main_lock=$(find "$CECELIA_REPO" -maxdepth 1 -name ".dev-lock.*" 2>/dev/null | wc -l | tr -d ' ')
    [ "$main_lock" -gt 0 ] && return 0
    return 1
  }

  # 判断 vitest/node 进程是否为孤儿（三层保护）
  is_orphan() {
    local pid=$1

    # 保护层 A：TTY 检查——有 TTY 的进程绝对不杀（有头 Codex/Grok 等）
    local tty
    tty=$(ps -o tty= -p "$pid" 2>/dev/null | tr -d ' ')
    if [ -n "$tty" ] && [ "$tty" != "??" ]; then
      return 1
    fi

    # 保护层 B：祖先链遍历——找到 tmux/screen/sshd/login/claude → 不杀
    local current=$pid
    local depth=0
    local max_depth=20
    while [ $depth -lt $max_depth ]; do
      local ppid
      ppid=$(ps -o ppid= -p "$current" 2>/dev/null | tr -d ' ')
      [ -z "$ppid" ] || [ "$ppid" = "0" ] && break
      [ "$ppid" = "1" ] && break
      local comm
      comm=$(ps -o comm= -p "$ppid" 2>/dev/null)
      if echo "$comm" | grep -qiE "tmux|screen|sshd|login|claude"; then
        return 1
      fi
      current=$ppid
      depth=$((depth + 1))
    done

    # 保护层 C：cmdline 白名单——brain/server.js、cecelia-bridge.cjs、n8n → 不杀
    local cmdline
    cmdline=$(ps -o command= -p "$pid" 2>/dev/null || echo "")
    if echo "$cmdline" | grep -qE "brain/server\.js|cecelia-bridge\.cjs|n8n"; then
      return 1
    fi

    # 最终判断：PPID=1 → 真实孤儿
    local ppid_final
    ppid_final=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
    [ "$ppid_final" = "1" ] && return 0

    return 1
  }

  # 判断 claude 进程是否为孤儿（双重验证）
  is_claude_orphan() {
    local pid=$1
    local tty=$2
    local ppid=$3

    # 条件1: 无终端（有头进程绝对不动）
    [ "$tty" != "??" ] && return 1

    # 条件2: ppid=1（父进程已死）
    [ "$ppid" != "1" ] && return 1

    # 条件3: 白名单服务进程不动
    local cmdline
    cmdline=$(ps -o command= -p "$pid" 2>/dev/null || echo "")
    if echo "$cmdline" | grep -qE "brain/server\.js|cecelia-bridge\.cjs|n8n"; then
      return 1
    fi

    # 条件4（保守）: Brain 有 in_progress 任务 → 跳过
    if has_brain_inprogress_task; then
      return 1
    fi

    # 条件5（保守）: 有 .dev-lock 文件 → 跳过
    if has_active_dev_lock; then
      return 1
    fi

    return 0
  }

  # vitest/node 通用 kill 函数
  kill_if_orphan() {
    local pid="$1"
    local threshold="${2:-$ACTIVE_THRESHOLD}"
    [ -z "$pid" ] && return

    local elapsed secs
    elapsed=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
    [ -z "$elapsed" ] && return
    secs=$(etime_to_secs "$elapsed")
    [ -z "$secs" ] && { echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] etime_to_secs 解析失败 elapsed=$elapsed pid=$pid，保守跳过"; secs=0; }
    [ "$secs" -lt "$threshold" ] && return

    if is_orphan "$pid"; then
      kill "$pid" 2>/dev/null
      sleep 1
      kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
      KILLED=$((KILLED + 1))
      echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] killed node/vitest orphan pid=$pid (${secs}s)"
    fi
  }

  # kill 后回报 Brain：找到对应 .dev-lock → PATCH 任务状态 → 触发重调度
  # 设计：fire-and-forget，失败只 log 不影响主流程
  notify_brain_orphan_killed() {
    local pid="$1" cwd="$2"
    [ -z "$cwd" ] && return 0

    # 在该目录找 .dev-lock.* 文件
    local lockfile branch
    lockfile=$(ls "$cwd"/.dev-lock.* 2>/dev/null | head -1)
    [ -z "$lockfile" ] && return 0

    branch=$(grep "^branch:" "$lockfile" 2>/dev/null | awk '{print $2}' | tr -d '[:space:]')
    [ -z "$branch" ] && return 0

    echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] 孤儿回报 Brain：pid=$pid branch=$branch"

    # 优先用 .dev-lock 里记录的 task_id 直接 PATCH
    local task_id
    task_id=$(grep "^task_id:" "$lockfile" 2>/dev/null | awk '{print $2}' | tr -d '[:space:]')

    if [ -n "$task_id" ]; then
      curl -s --max-time 5 -X PATCH "${BRAIN_API}/api/brain/tasks/${task_id}" \
        -H "Content-Type: application/json" \
        -d "{\"status\":\"failed\",\"custom_props\":{\"fail_reason\":\"orphan_killed_by_janitor\",\"branch\":\"${branch}\",\"killed_pid\":${pid}}}" \
        > /dev/null 2>&1 || true
      echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] Brain 已更新：task=${task_id} → failed (orphan_killed_by_janitor)"
    else
      # 无 task_id：POST 告警任务让 Brain 感知
      curl -s --max-time 5 -X POST "${BRAIN_API}/api/brain/tasks" \
        -H "Content-Type: application/json" \
        -d "{\"title\":\"[janitor] 孤儿分支 ${branch} 任务需重调度\",\"task_type\":\"alert\",\"priority\":\"p2\",\"description\":\"orphan_killed_by_janitor: pid=${pid} branch=${branch}\"}" \
        > /dev/null 2>&1 || true
      echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] Brain 已告警：分支=$branch 需重调度 (orphan_killed_by_janitor)"
    fi
  }

  # claude 专用 kill 函数
  kill_if_claude_orphan() {
    local pid="$1" tty="$2" ppid="$3"
    local threshold="${4:-$ACTIVE_THRESHOLD}"
    [ -z "$pid" ] && return

    local elapsed secs
    elapsed=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
    [ -z "$elapsed" ] && return
    secs=$(etime_to_secs "$elapsed")
    [ -z "$secs" ] && { echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] etime_to_secs 解析失败 elapsed=$elapsed pid=$pid，保守跳过"; secs=0; }
    [ "$secs" -lt "$threshold" ] && return

    if is_claude_orphan "$pid" "$tty" "$ppid"; then
      # kill 前先取工作目录（kill 后进程消失 lsof 无效）
      local cwd
      cwd=$(lsof -p "$pid" -a -d cwd -Fn 2>/dev/null | grep '^n' | head -1 | sed 's/^n//')

      kill "$pid" 2>/dev/null
      sleep 1
      kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
      KILLED=$((KILLED + 1))
      echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] killed claude orphan pid=$pid tty=$tty ppid=$ppid (${secs}s)"

      # 回报 Brain（fire-and-forget）
      notify_brain_orphan_killed "$pid" "$cwd"
    fi
  }

  # ── 扫描 vitest/jest 孤儿 ─────────────────────────
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    PID=$(echo "$line" | awk '{print $2}')
    kill_if_orphan "$PID" "$ACTIVE_THRESHOLD"
  done < <(ps aux | grep -E "node.*vitest|node.*jest" | grep -v grep)

  # ── 扫描普通 node 孤儿（排除服务进程）──────────────
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    PID=$(echo "$line" | awk '{print $2}')
    kill_if_orphan "$PID" "$ACTIVE_THRESHOLD"
  done < <(ps aux | grep "node" | grep -v grep | grep -v "brain\|server\|n8n\|vscode\|bridge")

  # ── 扫描 claude 孤儿（v4.0 新逻辑）─────────────────
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    PID=$(echo "$line" | awk '{print $2}')
    TTY=$(echo "$line" | awk '{print $7}')
    PROC_PPID=$(ps -o ppid= -p "$PID" 2>/dev/null | tr -d ' ')
    [ -z "$PROC_PPID" ] && continue
    kill_if_claude_orphan "$PID" "$TTY" "$PROC_PPID" "$ACTIVE_THRESHOLD"
  done < <(ps aux | grep -E " claude$| claude " | grep -v grep)

  if [ "$KILLED" -gt 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] 清理完成：killed $KILLED 个孤儿进程（内存 ${MEM_PCT}%，CPU ${CPU_PCT}%）"
  fi

  # ── audiomxd 蓝牙路由死循环兜底（2026-07-28 现场实测）────
  # 已知 macOS bug：audiomxd 卡在 com.apple.mediaexperience.btroutingrequestqueue
  # 反复注册同一通知观察者，占满一整个核心；关蓝牙不能根治（真实触发源未知，见
  # decisions f418f03c）。这里只做止损：CPU 持续偏高就 kill，launchd 会自动拉起干净实例。
  # 用 pgrep -x 按进程名精确匹配（避免 ps|grep 子串误命中其他命令行里带 "audiomxd" 字样的进程），
  # 遍历每个匹配到的 PID 单独判断，避免多实例场景下只取第一个漏杀真正卡死的那个。
  # 直接 kill -9（不走 SIGTERM 两段式）：这是内核态/系统框架层面的死循环，SIGTERM 大概率不会被响应。
  AUDIOMXD_CPU_THRESHOLD=80
  for audiomxd_pid in $(pgrep -x audiomxd 2>/dev/null); do
    audiomxd_cpu=$(ps -o %cpu= -p "$audiomxd_pid" 2>/dev/null | tr -d ' ' | cut -d. -f1)
    if [ -n "$audiomxd_cpu" ] && [ "$audiomxd_cpu" -ge "$AUDIOMXD_CPU_THRESHOLD" ] 2>/dev/null; then
      if sudo -n kill -9 "$audiomxd_pid" 2>/dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] killed audiomxd pid=${audiomxd_pid}（CPU ${audiomxd_cpu}%，蓝牙路由死循环兜底）"
      fi
    fi
  done

  # 已退出的 harness relay 容器每小时新增 ~13 个（2026-07-19/20 现场验证），
  # daily 单次清理频率追不上堆积速度，这里每 15 分钟顺手清一次。只 prune 已退出的，
  # 不碰 running 容器（container prune 本身语义就只清 Exited/Created 状态，不会误删运行中的）。
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    relay_prune_out=$(docker container prune -f 2>/dev/null || true)
    relay_reclaimed=$(echo "$relay_prune_out" | grep "Total reclaimed space" | awk -F': ' '{print $2}')
    [ -n "$relay_reclaimed" ] && [ "$relay_reclaimed" != "0B" ] && \
      echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] 已退出容器 prune 回收 ${relay_reclaimed}"
  fi
  exit 0
fi

# ─────────────────────────────────────────────
# daily 模式：Mac mini 磁盘清理（v2.0）
# ─────────────────────────────────────────────
LOG_FILE="/tmp/janitor-$(date +%Y%m%d).log"
BEFORE=$(df "$DISK_VOL" | tail -1 | awk '{print $3}')

log() { echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

log "=== Janitor v4.0 开始清扫 $(date '+%Y-%m-%d') ==="

# 1. Brain/Bridge LaunchDaemon 日志截断（>10M 保留最后 1000 行）
log "[1/$TOTAL_STEPS] Brain/Bridge 服务日志..."
LOGS_DIR="$CECELIA_REPO/logs"
truncated=0
for logfile in brain.log brain-error.log bridge.log bridge-error.log frontend.log frontend-error.log; do
  f="$LOGS_DIR/$logfile"
  if [ -f "$f" ]; then
    size_kb=$(du -k "$f" | awk '{print $1}')
    if [ "$size_kb" -gt 10240 ]; then
      tail -1000 "$f" > "$f.tmp" && mv "$f.tmp" "$f"
      truncated=$((truncated + 1))
      log "  ↳ $logfile 截断（原 ${size_kb}K）"
    fi
  fi
done
log "  ✓ 截断 $truncated 个日志"

# 2. /tmp/cecelia-*.log 旧运行日志（>3天删除）
log "[2/$TOTAL_STEPS] Cecelia 旧运行日志..."
deleted=$(find /tmp -maxdepth 1 -name "cecelia-*.log" -mtime +3 -delete -print 2>/dev/null | wc -l | tr -d ' ')
deleted2=$(find /tmp -maxdepth 1 \( -name "cecelia-err.*" -o -name "cecelia-out.*" \) -mtime +1 -delete -print 2>/dev/null | wc -l | tr -d ' ')
log "  ✓ 删除 $deleted 个日志 + $deleted2 个临时文件"

# 3. Claude JSONL 会话记录（>7天删除）
log "[3/$TOTAL_STEPS] Claude 会话记录..."
jsonl_deleted=0
for account_dir in /Users/administrator/.claude-account*/projects/; do
  if [ -d "$account_dir" ]; then
    count=$(find "$account_dir" -name "*.jsonl" -mtime +7 -delete -print 2>/dev/null | wc -l | tr -d ' ')
    jsonl_deleted=$((jsonl_deleted + count))
  fi
done
log "  ✓ 删除 $jsonl_deleted 个 JSONL 文件"

# 4. npm cache 清理
log "[4/$TOTAL_STEPS] npm cache..."
if command -v npm >/dev/null 2>&1; then
  npm cache clean --force 2>/dev/null && log "  ✓ npm cache 已清理" || log "  ✗ 跳过"
else
  log "  ✗ 跳过（npm 不存在）"
fi

# 5. Homebrew cache 清理（>7天）
log "[5/$TOTAL_STEPS] Homebrew cache..."
if command -v brew >/dev/null 2>&1; then
  brew cleanup --prune=7 2>/dev/null && log "  ✓ brew cache 已清理" || log "  ✗ 跳过"
else
  log "  ✗ 跳过（brew 不存在）"
fi

# 6. /tmp 旧随机临时目录（>1天）
log "[6/$TOTAL_STEPS] /tmp 旧临时目录..."
find /tmp -maxdepth 1 -type d -mtime +1 \
  ! -name "snap-private-tmp" ! -name "systemd-private-*" \
  ! -name "cecelia*" ! -name "claude*" ! -name "vscode*" \
  ! -name "puppeteer*" ! -name "playwright*" ! -name "zenithjoy*" \
  ! -name "tsx-*" ! -name "node_modules" ! -name "tmp" ! -name "." \
  2>/dev/null -exec rm -rf {} + 2>/dev/null || true
log "  ✓ 清理完"

# 7. .prd/.dod/.dev-mode 残留文件（>3天删除）
log "[7/$TOTAL_STEPS] 开发残留文件..."
residual=0
if [ -d "$CECELIA_REPO" ]; then
  for pattern in ".prd-*" ".dod-*" ".dev-mode*" ".dev-incident-log*" ".dev-feedback-report*"; do
    count=$(find "$CECELIA_REPO" -maxdepth 1 -name "$pattern" -mtime +3 -delete -print 2>/dev/null | wc -l | tr -d ' ')
    residual=$((residual + count))
  done
fi
log "  ✓ 删除 $residual 个残留文件"

# 8. Git 孤儿分支清理
log "[8/$TOTAL_STEPS] Git 孤儿分支..."
BRANCH_GC="$CECELIA_REPO/packages/engine/skills/dev/scripts/branch-gc.sh"
if [ -f "$BRANCH_GC" ] && [ -d "$CECELIA_REPO/.git" ]; then
  gc_output=$(cd "$CECELIA_REPO" && bash "$BRANCH_GC" 2>&1 || true)
  cleaned=$(echo "$gc_output" | tail -1 | tr -cd '0-9 ' | awk '{print $1}')
  [ -z "$cleaned" ] && cleaned=0
  log "  ✓ 清理 $cleaned 个孤儿分支"
else
  log "  ✗ 跳过（branch-gc.sh 或仓库不存在）"
fi

# 9. 残留 worktree 清理（>24h 且无 open PR）
log "[9/$TOTAL_STEPS] 残留 worktree..."
wt_cleaned=0
if [ -d "$CECELIA_REPO/.claude/worktrees" ]; then
  cd "$CECELIA_REPO" || true
  git worktree prune 2>/dev/null
  for wt_dir in .claude/worktrees/*/; do
    [ ! -d "$wt_dir" ] && continue
    wt_branch=$(git -C "$wt_dir" rev-parse --abbrev-ref HEAD 2>/dev/null)
    [ -z "$wt_branch" ] && continue
    last_commit=$(git -C "$wt_dir" log -1 --format=%ct 2>/dev/null || echo "0")
    now=$(date +%s)
    age_hours=$(( (now - last_commit) / 3600 ))
    if [ "$age_hours" -gt 24 ]; then
      has_pr=$(gh pr list --head "$wt_branch" --state open --json number -q '.[0].number' 2>/dev/null || echo "")
      if [ -z "$has_pr" ]; then
        git worktree remove --force "$wt_dir" 2>/dev/null && wt_cleaned=$((wt_cleaned + 1))
      fi
    fi
  done
fi
log "  ✓ 清理 $wt_cleaned 个残留 worktree"

# 10. Docker 容器/镜像清理（Exited 容器 + 未引用旧版 cecelia-brain 镜像）
log "[10/$TOTAL_STEPS] Docker 容器/镜像清理..."
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  prune_out=$(docker container prune -f 2>/dev/null || true)
  reclaimed=$(echo "$prune_out" | grep "Total reclaimed space" | awk -F': ' '{print $2}')
  [ -z "$reclaimed" ] && reclaimed="0B"

  # 当前所有容器（含 exited 之外仍保留的）引用的镜像 ID（短 12 位），这些镜像不动
  in_use_ids=$(docker ps -aq 2>/dev/null | xargs -I{} docker inspect --format '{{.Image}}' {} 2>/dev/null | sed 's/sha256://' | cut -c1-12 | sort -u)

  img_deleted=0
  for tag in $(docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep '^cecelia-brain:'); do
    case "$tag" in
      cecelia-brain:latest|cecelia-brain:blue-fallback) continue ;;
    esac
    img_id=$(docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' 2>/dev/null | awk -v t="$tag" '$1==t{print $2}')
    [ -z "$img_id" ] && continue
    if echo "$in_use_ids" | grep -q "^${img_id}$"; then
      continue
    fi
    if docker rmi "$tag" >/dev/null 2>&1; then
      img_deleted=$((img_deleted + 1))
    fi
  done
  log "  ✓ container prune 回收 ${reclaimed} | 删除 $img_deleted 个未引用旧版 cecelia-brain 镜像"
else
  log "  ✗ 跳过（docker 不可用）"
fi

# ── 结果 ──
AFTER=$(df "$DISK_VOL" | tail -1 | awk '{print $3}')
FREED_MB=$(( (BEFORE - AFTER) / 1024 ))
CURRENT=$(df -h "$DISK_VOL" | tail -1 | awk '{print $3 "/" $2 " (" $5 ")"}')
log ""
log "=== 清扫完成 ==="
log "释放: ${FREED_MB}MB | 当前: $CURRENT"

# 超70%发告警到 Cecelia Brain
USAGE_PCT=$(df "$DISK_VOL" | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$USAGE_PCT" -gt 70 ]; then
  log "⚠️  磁盘 ${USAGE_PCT}%，超警戒线！"
  curl -s -X POST http://localhost:5221/api/brain/tasks \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"🚨 磁盘告警 ${USAGE_PCT}%，需人工检查\",\"priority\":\"P0\",\"skill\":\"/janitor\"}" \
    2>/dev/null || true
fi

cat "$LOG_FILE"
