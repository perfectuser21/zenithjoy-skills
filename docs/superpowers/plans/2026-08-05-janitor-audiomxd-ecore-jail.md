# Janitor audiomxd E核监狱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** janitor.sh audiomxd 兜底从 kill-respawn 循环改为 taskpolicy E核监狱（幂等），守卫测试反转并点名进 CI。

**Architecture:** 单文件 bash 改动 + 既有日志格式测试改 grep 标记（TDD 红→绿）+ lint-skills.yml 点名。

**Tech Stack:** bash（macOS /bin/bash 3.2 兼容）、GitHub Actions。

## Global Constraints

- 工作目录：`/Users/administrator/worktrees/zenithjoy-skills/janitor-audiomxd-ecore-jail`
- TDD：commit-1 = 测试改标记（红）+ CI 点名；commit-2 = janitor.sh 实现（绿）
- **taskpolicy/renice 必须绝对路径**（`/usr/sbin/taskpolicy`、`/usr/bin/renice`）——cron PATH 无 /usr/sbin 且 sudoers 无 secure_path，裸命令实测 command not found
- 幂等判断：`ps -o nice= -p PID | tr -d ' '` 与字符串 `"20"` 比较（macOS 实测落 20 非 19）
- 新日志行只使用既有变量 `audiomxd_pid`/`audiomxd_cpu`（测试 eval 渲染依赖）
- 注释简体中文；commit message 结尾：`Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: 全部改动（红→绿两个 commit）

**Files:**
- Modify: `janitor/__tests__/janitor_audiomxd_log_format.test.sh`（第 24 行 grep 标记）
- Modify: `.github/workflows/lint-skills.yml`（etime regression step 之后点名本测试）
- Modify: `janitor/janitor.sh:384-399`（audiomxd 块）

- [ ] **Step 1（commit-1 红）: 测试改标记 + CI 点名**

a) `janitor/__tests__/janitor_audiomxd_log_format.test.sh` 第 24 行：

```bash
ECHO_LINE=$(grep -m1 "killed audiomxd pid=" "$JANITOR")
```

改为：

```bash
ECHO_LINE=$(grep -m1 "jailed audiomxd pid=" "$JANITOR")
```

（其余断言不动——新日志行保持 `pid=${audiomxd_pid}（CPU ${audiomxd_cpu}%` 形态，三条断言直接复用。）

b) `.github/workflows/lint-skills.yml` 在 `Regression — janitor etime 八进制换算` step 之后追加：

```yaml
      # 回归守卫：janitor audiomxd E核监狱日志格式（决策 db79a1d3）
      - name: Regression — janitor audiomxd 日志格式
        run: bash janitor/__tests__/janitor_audiomxd_log_format.test.sh
```

- [ ] **Step 2: 跑测试确认红**

Run: `bash janitor/__tests__/janitor_audiomxd_log_format.test.sh`
Expected: FAIL/ERROR（现 janitor.sh 无 `jailed audiomxd pid=` 行，grep 抽空即红）。亲见红，输出记报告。

- [ ] **Step 3: Commit（红）**

```bash
git add janitor/__tests__/janitor_audiomxd_log_format.test.sh .github/workflows/lint-skills.yml
git commit -m "fix(janitor): audiomxd 守卫测试改 jailed 标记并点名进 CI（红）"
```

- [ ] **Step 4（commit-2 绿）: janitor.sh audiomxd 块替换**

将第 384-399 行（`# ── audiomxd 蓝牙路由死循环兜底` 注释起、到 audiomxd for 循环的 `done` 止）整体替换为：

```bash
  # ── audiomxd 蓝牙路由死循环兜底 v2：E核监狱（2026-08-05，决策 db79a1d3）────
  # 已知 macOS bug：audiomxd 卡在 com.apple.mediaexperience.btroutingrequestqueue。
  # v1 的 kill -9 兜底实测有害无效：launchd 秒拉起，重生进程每轮在性能核烧满 15 分钟
  # 再被杀（730 次循环）。蓝牙电源循环 / 重启 bluetoothd / launchctl disable（SIP 拦
  # 运行期）均无法阻止重生。v2 改为钉死到 E 核后台：taskpolicy -b + nice 20，死循环
  # 继续转但抢不到性能核。幂等：nice 已是 20 视为已施加，跳过。
  # taskpolicy/renice 必须绝对路径：cron PATH（上方第 33 行修补后）不含 /usr/sbin，
  # 且本机 sudoers 无 secure_path，裸命令实测 command not found。
  AUDIOMXD_CPU_THRESHOLD=80
  for audiomxd_pid in $(pgrep -x audiomxd 2>/dev/null); do
    audiomxd_cpu=$(ps -o %cpu= -p "$audiomxd_pid" 2>/dev/null | tr -d ' ' | cut -d. -f1)
    if [ -n "$audiomxd_cpu" ] && [ "$audiomxd_cpu" -ge "$AUDIOMXD_CPU_THRESHOLD" ] 2>/dev/null; then
      audiomxd_nice=$(ps -o nice= -p "$audiomxd_pid" 2>/dev/null | tr -d ' ')
      if [ "$audiomxd_nice" != "20" ]; then
        if sudo -n /usr/sbin/taskpolicy -b -p "$audiomxd_pid" 2>/dev/null && \
           sudo -n /usr/bin/renice 20 -p "$audiomxd_pid" >/dev/null 2>&1; then
          echo "$(date '+%Y-%m-%d %H:%M:%S') [frequent] jailed audiomxd pid=${audiomxd_pid}（CPU ${audiomxd_cpu}%，已钉死E核后台nice20，蓝牙路由死循环兜底v2）"
        fi
      fi
    fi
  done
```

- [ ] **Step 5: 验证绿**

```bash
bash janitor/__tests__/janitor_audiomxd_log_format.test.sh
bash janitor/__tests__/janitor_etime_octal.test.sh
bash -n janitor/janitor.sh
```
Expected: 两测试全 PASS、语法检查通过。

- [ ] **Step 6: Commit（绿）**

```bash
git add janitor/janitor.sh
git commit -m "fix(janitor): audiomxd 兜底改 taskpolicy E核监狱，不再 kill-respawn（绿）"
```
