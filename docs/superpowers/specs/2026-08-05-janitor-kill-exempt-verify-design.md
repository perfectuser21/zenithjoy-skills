# Janitor 误伤豁免 + kill 复查设计

Brain task: ec5d00e7；决策 e8427238；issue ab1da1d7。

## 问题（真机实证）
fleet-worker（`/usr/local/libexec/cecelia/toolchain/bin/node …/fleet-worker.cjs`，用户 _cecelia）被 kill_if_orphan 的 node 孤儿判据捞中（排除串不含它），janitor 无权限杀 root/_cecelia 进程，kill EPERM 静默失败，仍 KILLED+1 并打 killed 日志——同 pid etime 连涨数十轮，日志说谎数周。

## 修法（janitor/janitor.sh，行号基于 #180 后 main）
1. **路径豁免**：kill_if_orphan（282 行 is_orphan 判断前）与 kill_if_claude_orphan（340 行判断前）各加：
   `local cmd; cmd=$(ps -o command= -p "$pid" 2>/dev/null); case "$cmd" in *"/usr/local/libexec/cecelia/"*) return ;; esac`
   全路径子串匹配（覆盖外部解释器拉起形态）；**禁用裸 `*cecelia*`**（会误豁免 ~/perfect21/cecelia* 开发目录进程——那些正是该管的）。
2. **kill 复查**：两函数 `kill -0 && kill -9` 行之后插入：
   `sleep 1; if kill -0 "$pid" 2>/dev/null; then echo "... kill-failed pid=$pid 仍存活（疑似权限不足），不计数" ; return; fi`
   复查失败分支同时跳过 KILLED+1、killed 日志、notify_brain_orphan_killed（claude 变体 352 行）。
3. **CI**：新测试 `janitor/__tests__/janitor_kill_exempt.test.sh` 点名进 lint-skills.yml（audiomxd step 之后）；顺手把从未接入 CI 的存量 `janitor_orphan.test.sh` 一并点名（现状 30/30 绿）。

## 守卫
新测试静态断言：两函数各含豁免 case（`/usr/local/libexec/cecelia/` 字面）、各含 kill-failed 分支、KILLED 自增出现在复查 return 之后（行序断言）。commit-1 对旧实现红。

## 测试策略
unit：上述断言先红后绿 + 既有 etime/audiomxd/orphan 三测试回归绿；integration（merge 后真机）：拉最新跑一轮 frequent，fleet-worker 不再出现 killed 行（可 grep 日志验证）。
