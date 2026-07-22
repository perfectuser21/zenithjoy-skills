# Sprint PRD: Janitor 误杀有头 Codex（及未来 Grok）交互进程修复

**Task ID**: ca2492bb-5f5e-4fea-9e27-125efd156aac
**Sprint Dir**: sprints/07222128-janitor-headed-agent-protection
**Base Repo**: zenithjoy-skills
**Branch**: cp-07222226-ws-ca2492bb
**Created**: 2026-07-22

---

## 一、问题定位（已完成代码审计）

### 1.1 根因分析

**当前 janitor.sh 的 `is_orphan()` 函数（第 187–209 行）仅有一个保护：**
```bash
has_live_claude_ancestor "$pid"   # 祖先链中有 claude 进程 → 跳过
```
但 **对 TTY 状态完全无感知**。Codex 进程路径含 `node_modules`（形如 `.../@openai/codex/node_modules/.../bin/codex`），被以下扫描语句命中：
```bash
ps aux | grep "node" | grep -v grep | grep -v "brain\|server\|n8n\|vscode\|bridge"
```
因为进程命令行字符串含 `node`（来自路径中的 `node_modules`），且不含被排除的关键词，落入 `kill_if_orphan` 路径，而 `is_orphan()` 只查祖先链有无 claude 进程，没有 Codex 父进程，直接判定为孤儿并 kill。

**claude 专有的 `is_claude_orphan()` 函数（第 212–241 行）已有 TTY 保护：**
```bash
[ "$tty" != "??" ] && return 1   # 有 TTY → 不杀
```
但该函数仅用于 claude 进程扫描，`is_orphan()` 完全没有此逻辑。

### 1.2 受影响的扫描路径

| 扫描语句（janitor.sh 第 329–340 行） | 现状 | Codex 是否命中 |
|---|---|---|
| `grep -E "node.*vitest\|node.*jest"` | 扫 vitest/jest | 否（不含这些词）|
| `grep "node" \| grep -v "brain\|server\|n8n\|vscode\|bridge"` | 扫普通 node | **是**（命令行含 node_modules 字符串）|

### 1.3 核心修复方向

**必须修正 `is_orphan()` 本身的孤儿判定逻辑**，加入：
1. TTY 检查（TTY != `??` → 不杀；有头进程绝对不动）
2. tmux/screen/ssh 祖先保护（进程处于交互会话中 → 不杀）
3. 服务白名单（`brain/server.js`、`cecelia-bridge.cjs`、`n8n` 等）

**不做**：针对 Codex/Grok 的字符串白名单（如 `grep -v codex`）。

---

## 二、Golden Path（验收场景）

| # | 场景 | 期望结果 |
|---|---|---|
| GP-1 | `cd ~/perfect21/cecelia && CODEX_HOME=~/.codex-team1 codex` 起有头 TUI，持续运行 >600s | janitor frequent 扫描不得 kill |
| GP-2 | tmux 里跑交互式 node 程序（有 TTY） | 不得 kill |
| GP-3 | 未来 Grok 原生二进制（有 TTY，非 node 命名，但命令行含 `node_modules` 路径）| 不得 kill |
| GP-4 | Claude Code 现有保护不回归 | 继续生效 |
| GP-5 | TTY=`??`、PPID=1、超时、非白名单的真实 node 孤儿 | 必须被 kill |

---

## 三、实现计划

### 3.1 修改文件
- `janitor/janitor.sh`：修改 `is_orphan()` 函数
- `janitor/__tests__/janitor_orphan.test.sh`：补充行为级测试

### 3.2 `is_orphan()` 新逻辑（替换第 187–209 行）

```bash
is_orphan() {
  local pid=$1

  # 保护层 A: 有 TTY（有头进程）→ 绝不杀
  local tty
  tty=$(ps -o tty= -p "$pid" 2>/dev/null | tr -d ' ')
  [ -z "$tty" ] && return 1          # 进程已消失
  [ "$tty" != "??" ] && return 1     # 有终端 = 有头会话

  # 保护层 B: 祖先链中有 tmux/screen/sshd/login → 交互会话，不杀
  local current=$pid depth=0
  while [ $depth -lt 20 ]; do
    local ppid comm
    ppid=$(ps -o ppid= -p "$current" 2>/dev/null | tr -d ' ')
    [ -z "$ppid" ] || [ "$ppid" = "0" ] && break
    [ "$ppid" = "1" ] && break
    comm=$(ps -o comm= -p "$ppid" 2>/dev/null | tr -d ' ')
    case "$comm" in
      *tmux*|*screen*|*sshd*|*login*|*claude*) return 1 ;;
    esac
    current=$ppid
    depth=$((depth + 1))
  done

  # 保护层 C: 服务白名单（命令行匹配）
  local cmdline
  cmdline=$(ps -o command= -p "$pid" 2>/dev/null || echo "")
  if echo "$cmdline" | grep -qE "brain/server\.js|cecelia-bridge\.cjs|n8n"; then
    return 1
  fi

  # 孤儿判定：TTY=?? + 最终祖先是 PID 1
  local ppid_direct
  ppid_direct=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
  [ "$ppid_direct" = "1" ] && return 0   # 孤儿

  # 遍历链找到 PPID=1
  current=$pid; depth=0
  while [ $depth -lt 20 ]; do
    local ppid
    ppid=$(ps -o ppid= -p "$current" 2>/dev/null | tr -d ' ')
    [ -z "$ppid" ] || [ "$ppid" = "0" ] && return 1
    [ "$ppid" = "1" ] && return 0    # 孤儿
    current=$ppid
    depth=$((depth + 1))
  done
  return 1
}
```

### 3.3 测试用例矩阵（TDD 先行，需覆盖的新 case）

以下测试补充到 `janitor/__tests__/janitor_orphan.test.sh`：

| # | 测试名 | fixture 构造方式 | 断言 |
|---|---|---|---|
| T-01 | Codex 有 TTY → 不杀 | `bash -i -c 'sleep 9999 &'`（有 TTY），检查 is_orphan | return 1 |
| T-02 | node_modules 路径 + 有 TTY → 不杀 | 进程路径含 node_modules，TTY != ?? | return 1 |
| T-03 | 模拟 Grok（非 node 名，有 TTY）→ 不杀 | 任意有 TTY 进程 | return 1 |
| T-04 | tmux 祖先链 → 不杀 | 祖先有 tmux comm | return 1 |
| T-05 | TTY=??、PPID=1、非白名单 → 杀 | 真实孤儿 fixture（`setsid bash -c 'exec sleep 9999'`） | return 0 |
| T-06 | 白名单进程 brain/server.js → 不杀 | cmdline 含 brain/server.js | return 1 |
| T-07 | claude 祖先保护（回归）→ 不杀 | 祖先有 claude comm | return 1 |

**行为级测试实现要点**：
- T-01～T-04、T-06、T-07：spawn 真实后台进程（或 mock `ps` 输出），调用 `is_orphan`，断言不 kill。
- T-05：`setsid` 创建无终端、PPID 为 1 的进程，断言被选中（`is_orphan` return 0）。
- 测试隔离：不依赖真实生产进程。每个 fixture 进程在 test trap 中 `kill`。

---

## 四、测试全绿标准

以下两个文件必须全绿：

1. `janitor/__tests__/janitor_orphan.test.sh` — 含新 T-01～T-07
2. `janitor/tests/test-cron-path-and-diskvol.sh` — 现有回归（PATH导出、磁盘卷、frequent docker prune）

---

## 五、铁律（范围边界）

- 只改 `is_orphan()` 和配套测试，**不改 daily 模式**。
- **不加字符串白名单**（`grep -v codex` 等），必须修正判定本身。
- 不碰 cecelia 仓库的 launcher/supervisor/executor 代码（并行任务）。
- SKILL.md 如需更新，走 PR 正确顺序；cecelia dist 快照由 sync-skills-snapshot.sh 后续同步。

---

## 六、验收流程

1. **RED 阶段**：先在 `janitor/__tests__/janitor_orphan.test.sh` 写 T-01～T-07，运行确认失败（针对当前代码）。
2. **GREEN 阶段**：修改 `janitor/janitor.sh` 的 `is_orphan()` 函数，运行两个测试文件均通过。
3. **合并后观察**：下一次真实 cron frequent 周期（15 分钟），跨至少两个周期（30 分钟）确认日志中不再出现 Codex 相关 pid 被 kill。

---

## 七、不确定性与风险

| 风险 | 概率 | 对策 |
|---|---|---|
| `setsid` 在 macOS 不可用（BSD 差异） | 低（macOS 有 setsid） | 改用 `nohup` + `disown` 构造无 TTY 进程 |
| 修改后真实孤儿遗漏（清理能力退化） | 低（TTY=?? 判定不变） | T-05 孤儿 fixture 回归 |
| Grok 未来路径含特殊字符影响 grep | 低 | TTY 判定不依赖字符串匹配，天然覆盖 |

---

## 八、产物清单

| 文件 | 变更类型 |
|---|---|
| `janitor/janitor.sh` | 修改：`is_orphan()` 新增 TTY + tmux/ssh 祖先 + 白名单保护 |
| `janitor/__tests__/janitor_orphan.test.sh` | 修改：新增 T-01～T-07 行为级测试 |
| `sprints/07222128-janitor-headed-agent-protection/sprint-prd.md` | 新增：本文件 |
