# Contract DoD: Janitor 有头 Agent 保护

**Task ID**: ca2492bb-5f5e-4fea-9e27-125efd156aac
**Sprint Dir**: sprints/07222128-janitor-headed-agent-protection
**Date**: 2026-07-22

---

## [BEHAVIOR] 行为断言（≥4 条，必须全部通过）

[BEHAVIOR-01] 有 TTY 的进程（tty != ??）调用 `is_orphan()` 必须返回 1（不判定为孤儿）。
验证：T-01、T-02、T-03

[BEHAVIOR-02] 祖先链中含 tmux/screen/sshd/login 的进程调用 `is_orphan()` 必须返回 1（交互会话保护）。
验证：T-04

[BEHAVIOR-03] TTY=??、直接或间接 PPID=1、命令行不含白名单关键词的进程，`is_orphan()` 必须返回 0（允许清理）。
验证：T-05

[BEHAVIOR-04] 命令行含 `brain/server.js`、`cecelia-bridge.cjs`、`n8n` 之一的进程，`is_orphan()` 必须返回 1（服务白名单保护）。
验证：T-06

[BEHAVIOR-05] 祖先链中含 `claude` 进程（现有保护）调用 `is_orphan()` 必须返回 1（回归不破坏）。
验证：T-07

[BEHAVIOR-06] 修改后 `janitor/__tests__/janitor_orphan.test.sh` 全部静态验证项（含 TTY 保护、白名单、Brain API 查询等）必须全绿（0 FAIL）。
验证：运行 `bash janitor/__tests__/janitor_orphan.test.sh`

---

## 完成标准检查清单

### 代码变更

- [ ] `janitor/janitor.sh` 中 `is_orphan()` 函数体（第 187–209 行范围）已替换为含三层保护的新实现
- [ ] 新 `is_orphan()` 中存在 `tty=$(ps -o tty= -p "$pid"` 调用
- [ ] 新 `is_orphan()` 中存在 `[ "$tty" != "??" ] && return 1` 保护
- [ ] 新 `is_orphan()` 中存在 `tmux|screen|sshd|login` 祖先链匹配
- [ ] 新 `is_orphan()` 中存在 `brain/server\.js|cecelia-bridge\.cjs|n8n` 白名单检查
- [ ] daily 模式代码未被修改（`TOTAL_STEPS=10` 等 daily 步骤不变）

### 测试

- [ ] `janitor/__tests__/janitor_orphan.test.sh` 全绿（0 FAIL）
- [ ] `janitor/tests/test-cron-path-and-diskvol.sh` 全绿（0 FAIL）
- [ ] `sprints/07222128-janitor-headed-agent-protection/tests/janitor_protection.test.sh` 全绿（T-01～T-07 均 PASS）

### 推送与 PR

- [ ] 变更已推送到分支 `cp-07222226-ws-ca2492bb`
- [ ] PR 已开（目标 main），CI 全绿

---

## manual:bash 验收命令

```bash
# 1. 静态代码审计——验证 is_orphan() 含三层保护
grep -A 30 'is_orphan()' /workspace/janitor/janitor.sh | grep -E 'tty.*ps|tty.*\?\?|tmux.*screen|brain.*server'

# 2. 运行现有静态验证套件
cd /workspace && bash janitor/__tests__/janitor_orphan.test.sh

# 3. 运行现有回归套件
cd /workspace && bash janitor/tests/test-cron-path-and-diskvol.sh

# 4. 运行新行为级合同测试（T-01~T-07）
cd /workspace && bash sprints/07222128-janitor-headed-agent-protection/tests/janitor_protection.test.sh

# 5. [merge 后] 生产日志观察（30 分钟，两个 frequent 周期）
grep -E "kill|KILL|orphan" ~/logs/janitor-frequent.log | tail -50
# 期望：无 Codex/node_modules 路径进程被 kill 的记录
```

---

## 风险备注

- macOS 上 `setsid` 可用（T-05 fixture），但若环境无 `setsid`，回退使用 `nohup sleep 9999 & disown $!`
- TTY 检查基于 `ps -o tty=`，在 Docker 容器内 TTY 可能为空字符串而非 `??`，已在 `is_orphan()` 中用 `[ -z "$tty" ] && return 1` 处理（进程已消失 → 不杀）
