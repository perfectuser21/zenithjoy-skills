# Design: janitor frequent 模式 audiomxd 死循环兜底清理

## 背景

2026-07-28 排查 us-mac 变卡时确认：`audiomxd`（macOS 系统音频守护进程）会卡在
`com.apple.mediaexperience.btroutingrequestqueue` 死循环里反复调用同一个通知注册
函数（两次独立 `sample` 采样，调用栈完全一致，778/778 与 790/790 命中同一帧），
占满一整个 CPU 核心，持续数小时。已验证关闭蓝牙硬件**不能根治**（关闭后仍复发），
真实触发源尚未查明（decisions `f418f03c`）。

在根因未查明前，需要一个止损手段：定期检测并 kill 掉卡死的实例，让 launchd
自动拉起干净实例。janitor 已有 `frequent` 模式（每 15 分钟跑一次，负责僵尸/孤儿
进程清理 + 资源压力响应），是这个止损逻辑的自然归宿——不新建独立机制。

## 方案

在 `janitor/janitor.sh` 的 `frequent` 分支里，紧跟在现有孤儿进程清理小结日志
（"清理完成：killed $KILLED 个孤儿进程..."）之后、docker 容器 prune 之前，加一段：

1. `ps aux | grep '[a]udiomxd'` 取当前 audiomxd 进程（PID + %CPU）
2. CPU 占用 ≥80%（`AUDIOMXD_CPU_THRESHOLD`）→ `sudo -n kill -9 <pid>`
3. kill 成功则打印一行时间戳日志（沿用文件内既有日志格式）
4. `sudo -n` 保证没有免密 sudo 时静默失败退出，不阻塞 cron

不做的事：不追查真实触发源（超出本次范围，留给后续排查）、不改阈值之外的
调度频率、不新建独立 launchd job（复用 janitor 现有 15 分钟节奏足够及时）。

## 影响范围

只新增一段独立代码块，不改动 janitor.sh 其余任何清理项的行为。`sudo -n` 失败
时静默跳过，不影响脚本退出码（沿用 `exit 0`）。

## 测试

纯 bash 脚本，无 LLM 依赖。验收：
- `bash -n janitor.sh` 语法检查通过
- 单测脚本模拟一个高 CPU 场景（构造/mock `ps aux` 输出）验证 kill 分支被触发，
  以及低 CPU 场景验证不触发
