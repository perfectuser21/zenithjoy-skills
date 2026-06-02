---
name: engine-worktree
version: 16.0.1
updated: 2026-06-02
description: Cecelia /dev 接力链 1/2。确保工作在独立 git worktree 的 cp-* 分支。Engine 独有（Superpowers using-git-worktrees 是交互式的，不适合 autonomous）。
trigger: /dev SKILL.md 的 TERMINAL IMPERATIVE 点火
---

> **CRITICAL LANGUAGE RULE**: 所有输出简体中文。

## 运行

```bash
bash packages/engine/skills/dev/scripts/worktree-manage.sh init-or-check "$TASK_NAME"
```

该子命令：
- 已在 worktree → 补齐 `.dev-lock.<branch>`（含 session_id + owner_session），自检通过
- 在主仓库 → `worktree add` 创 cp-* 分支 + 新 worktree + 写 .dev-lock，**echo 出 worktree 路径**。脚本是子进程，**无法 cd 调用方进程的 cwd**——cd 是调用方（你）的责任。

> ⚠️ **必须 cd**：脚本在主仓库创建 worktree 后只能打印路径，不会（也不能）把你带进去。**收到路径后你必须 `cd <worktree_path>`，后续所有操作（含 git checkout/commit/push）都在该 worktree 内进行**。绝不在主仓库 checkout cp-* 分支开发——会与其它任务争用主仓库工作目录、踩踏 git 状态（cecelia 侧已加 worktree-checkout-guard hook 拦截此行为）。

## 完成标志

- `git rev-parse --git-dir` 含 `worktrees`
- 分支 `cp-*`
- `.dev-lock.<branch>` 存在且含 `owner_session`

---

## TERMINAL IMPERATIVE

engine-worktree 完成。**你的下一个 tool call 必须是**：

```
Skill({"skill":"superpowers:brainstorming"})
```

不要 Read。不要 Bash。不要 inline brainstorm。brainstorming 启动前按 /dev SKILL.md Tier 1 规则派 Research Subagent 判 PRD 是否 thin、查历史决策。
