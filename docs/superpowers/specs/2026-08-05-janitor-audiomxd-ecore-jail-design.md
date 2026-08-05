# Janitor audiomxd E核监狱改造设计

Brain task: 42358c3d；决策 db79a1d3（v1 原始决策 f418f03c）。

## 问题
v1 兜底 kill -9 已执行 730 次且有害：launchd 秒拉起，重生进程每轮在性能核烧满 15 分钟再被杀，等效常驻烧一个 P 核。真机实验排除项：蓝牙电源循环无效、重启 bluetoothd 无效、launchctl disable 被 SIP 拦运行期（已登记，重启后永久生效）。taskpolicy -b + renice 20 已手动施加验证：死循环被钉在 E 核后台，负载下降。

## 修法
`janitor/janitor.sh` 384-399 行 audiomxd 块改为：CPU≥80 且 `ps -o nice= | tr -d ' '` ≠ "20"（幂等）→ `sudo -n /usr/sbin/taskpolicy -b -p PID` + `sudo -n /usr/bin/renice 20 -p PID`，日志 `jailed audiomxd pid=<pid>（CPU <cpu>%，已钉死E核后台nice20，蓝牙路由死循环兜底v2）`，不再 kill。
**绝对路径是硬约束**：cron PATH（第 33 行修补后）无 /usr/sbin，sudoers 无 secure_path，裸 taskpolicy 实测 command not found。

## 守卫
`janitor/__tests__/janitor_audiomxd_log_format.test.sh`：grep 标记 `killed audiomxd pid=` → `jailed audiomxd pid=`（TDD：先改测试=红），三条 eval 渲染断言复用（echo 只用既有 audiomxd_pid/audiomxd_cpu 两变量）；**顺手点名进 lint-skills.yml**（该测试此前从未进 CI）。

## 测试策略
unit：上述测试先红后绿；integration（merge 后真机）：主 checkout 拉最新，杀掉现有已施策 audiomxd 让其重生，跑一轮 frequent，验证日志出现 jailed 行、`ps -o nice=` = 20、不再出现 killed 行。
