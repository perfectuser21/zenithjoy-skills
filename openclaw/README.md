# OpenClaw 自研 Skill（源码归集）

> 首次并入：2026-09-16。主理人拍板进本 repo 的 `openclaw/` 子目录，而非新建 repo——少一个地方要记。

## 这是什么

**OpenClaw gateway 用的 skill，与本 repo 其余 ~127 个 Claude Code skill 是两套不同的运行时。**

| | 本 repo 根目录下的 skill | `openclaw/` 下的 skill |
|---|---|---|
| 运行时 | Claude Code harness（`~/.claude/skills`） | OpenClaw gateway |
| 数量 | ~127 | 37 个唯一（64 份文件，跨 9 个 workspace） |
| 交集 | `notion`、`skill-creator` 两个重名，但**不是同一个东西** | 同左 |

## 为什么并进来

并入前，这 37 个 skill **只活在 us-vps 一台机器的本地 git 里**：

- 每个 `clawd-*` workspace 各是一个本地 git 仓库，`git remote -v` 全空——**没有任何远端**
- 唯一有远端的是 `clawd-dev/openclaw-src`，那指向上游 `github.com/openclaw/openclaw`，不是我们的代码
- 本机 `~/openclaw-migration/workspaces-root/` 那份是 2026-09-05 的 rsync 快照，已过期

**那台机器没了，这些 skill 就全没了。**

## 目录结构

```
openclaw/<workspace>/skills/<skill-name>/SKILL.md
```

保留 workspace 归属，不做去重。因为跨 workspace 副本是真实存在的部署事实——同一个 skill 被多个 agent workspace 各存一份，内容**未必一致**。合并成一份会把分叉藏起来，而藏起来的分叉正是这套系统反复出问题的根源。

12 个 skill 存在跨 workspace 副本：

| skill | 份数 |
|---|---:|
| `social-leadgen-workflow` / `douyin-reference-capture-phone` / `douyin-leadgen-phone` / `agentic-workflow-runtime` | 4 |
| `social-video-qualifier` / `social-video-discovery` / `social-lead-delivery` / `social-comment-lead-scorer` / `social-comment-lead-collector` / `enterprise-context-loader` / `douyin-phone-runtime` | 3 |
| `social-lead-outreach` | 2 |

## 并入时排除了什么

| 排除项 | 数量 | 原因 |
|---|---:|---|
| `clawd-dev/openclaw-src/**` | 123 份 SKILL.md | OpenClaw 上游自带（weather / spotify-player / tmux / 1password 那类工具），属 `github.com/openclaw/openclaw`，不是我们的代码 |
| `.xxx-backup-YYYYMMDD/` 隐藏目录 | 8 份 | 手工备份目录（如 `.attachment-routing-backup-20260903-1000`）。git 本身就是版本控制，不需要这类快照 |
| `node_modules/` `dist/` `build/` `.venv/` | 1074+1012+38 个文件 | 依赖与构建产物（首次打包 81MB，其中 pdfjs-dist 的字体资源占大头） |
| `*.bak` | 7 份 | 临时文件 |

排除后：314 个文件 / 2.9MB。

## ⚠️ 当前状态：一次性快照，尚未接自动同步

**这份代码不会自己更新。** 现在的同步方向是单向手工的：

```
us-vps:/opt/openclaw/workspaces-root/clawd-*/skills/   ← 真身，改动发生在这里
        │
        │  ✋ 手工，无自动化
        ↓
本 repo openclaw/                                       ← 你正在看的这份
```

**如果不接上自动同步，它会重演 `~/openclaw-migration/workspaces-root/` 的命运——那份 2026-09-05 的快照现在已经过期 11 天，而且没人发现。**

接同步的两条路（未实施）：

1. **us-vps 定时 push**：在 us-vps 上加 cron，检测 `clawd-*/skills/` 有变更就 commit 并 push 到本 repo 的分支。好处是真身变了立刻有记录；代价是要给 us-vps 配 GitHub 凭据。
2. **本机定时 pull + PR**：本机 cron 定时从 us-vps rsync 下来，有 diff 就开 PR。好处是凭据不下放到 us-vps，且改动经 PR 可见；代价是延迟一个 cron 周期。

在接上之前，**任何 skill 改动仍须以 us-vps 上的版本为准**，本目录只是灾备副本。

## 相关

- Brain 账本：`skill_registry`（真身表）、`ops_skills`（ops-collector 每 5min 从 `clawdbot.json` 现算的派生投影）
- 守夜断言：`promise-map-nightly.js` 的 A6 `skill_ledger_consistency` 每日对账 Brain 侧两处计数
- 四处落脚全清单见 cecelia repo 的 handoff（task `419c25c5`）
