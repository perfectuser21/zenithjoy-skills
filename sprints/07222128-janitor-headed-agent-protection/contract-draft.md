# Contract Draft: Janitor 有头 Agent 保护

**Task ID**: ca2492bb-5f5e-4fea-9e27-125efd156aac
**Sprint Dir**: sprints/07222128-janitor-headed-agent-protection
**Date**: 2026-07-22
**Branch**: cp-07222226-ws-ca2492bb

---

## 背景与范围

janitor.sh 的 `is_orphan()` 函数无 TTY 感知，导致 Codex 等有头（有 TTY）交互进程因命令行路径含 `node_modules` 被 `grep node` 命中后被误杀。修复目标：在 `is_orphan()` 加入三层保护（TTY 检查、祖先链检查、服务白名单），使有头进程绝对不被 kill，同时保留对真实无头孤儿的清理能力。

**修改文件（仅两处）**：
- `janitor/janitor.sh`：替换第 187–209 行的 `is_orphan()` 函数
- `janitor/__tests__/janitor_orphan.test.sh`：新增行为级测试 T-01～T-07

---

## 功能需求（FR）

| # | 需求 | 来源 |
|---|---|---|
| FR-01 | `is_orphan()` 对 TTY != `??` 的进程返回 1（不杀） | GP-1/GP-2/GP-3 |
| FR-02 | `is_orphan()` 对祖先链中含 tmux/screen/sshd/login 的进程返回 1 | GP-2 |
| FR-03 | `is_orphan()` 对 claude 祖先保护继续生效（回归） | GP-4 |
| FR-04 | `is_orphan()` 对命令行含 `brain/server.js`、`cecelia-bridge.cjs`、`n8n` 的进程返回 1 | 服务白名单 |
| FR-05 | TTY=`??` + PPID=1 + 非白名单的真实无头孤儿，`is_orphan()` 返回 0（允许 kill） | GP-5 |
| FR-06 | `is_orphan()` 修改不影响 daily 模式（仅 frequent 扫描路径使用） | NFR-01 |

---

## 非功能需求（NFR）

- NFR-01: 修改不触碰 daily 模式逻辑
- NFR-02: T-05 孤儿 fixture 覆盖 TTY=??+PPID=1，确保清理能力不退化
- NFR-03: 测试幂等——每个 fixture 进程在 test trap 中 `kill`，不依赖真实生产进程

---

## E2E 验收

### 合同测试（自动化，TDD，必须全绿）

**测试文件**：`sprints/07222128-janitor-headed-agent-protection/tests/janitor_protection.test.sh`

| 测试 ID | 场景 | 技术断言 |
|---|---|---|
| T-01 | Codex 有 TTY 进程 → 不杀 | 用 `script -q -c 'sleep 9999 &'` 或 bash -i 构造有 TTY 进程；调用 `is_orphan $PID`；断言返回值为 1 |
| T-02 | 命令行含 node_modules 路径但有 TTY → 不杀 | 构造进程使 `ps -o tty=` 返回非 `??`；调用 `is_orphan`；断言返回 1 |
| T-03 | 模拟 Grok（非 node 命名，有 TTY）→ 不杀 | 任意有 TTY 后台进程；调用 `is_orphan`；断言返回 1 |
| T-04 | tmux 祖先链 → 不杀 | mock `ps` 使祖先 comm 含 `tmux`；调用 `is_orphan`；断言返回 1 |
| T-05 | TTY=??、PPID=1、非白名单真实孤儿 → 必须选中 | `setsid bash -c 'exec sleep 9999'` 创建无 TTY 进程；调用 `is_orphan`；断言返回 0 |
| T-06 | 白名单进程 brain/server.js → 不杀 | 进程 cmdline 含 `brain/server.js`；调用 `is_orphan`；断言返回 1 |
| T-07 | claude 祖先保护（回归）→ 不杀 | 祖先链中有 `claude` 进程；调用 `is_orphan`；断言返回 1 |

### 静态验证（代码审计，自动化）

通过 grep 检查 `janitor/janitor.sh` 中 `is_orphan()` 函数体必须包含：
1. `tty=$(ps -o tty=` 调用（TTY 读取）
2. `"$tty" != "??"` 判断（有头保护）
3. `tmux` 关键词（祖先链保护）
4. `brain/server\.js` 关键词（白名单）

### 已有回归（不得红）

- `janitor/__tests__/janitor_orphan.test.sh`：全部 20 个验证项保持通过
- `janitor/tests/test-cron-path-and-diskvol.sh`：PATH 导出、磁盘卷、frequent docker prune 保持通过

### 生产观察（merge 后手动，30 分钟内）

下一次 frequent cron 周期（15 分钟）×2 周期：
```bash
grep -E "kill|KILL|orphan" ~/logs/janitor-frequent.log | tail -50
# 断言：无 Codex 相关 PID 被 kill 的记录
```

---

## 范围边界（Out of Scope）

- 不加 `grep -v codex` 等字符串白名单
- 不改 daily 模式
- 不改 cecelia 仓库的 launcher/supervisor/executor 代码
