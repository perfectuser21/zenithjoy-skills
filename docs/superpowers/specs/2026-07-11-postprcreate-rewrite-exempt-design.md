# 设计：post-pr-create.sh 对 rewrite/* 分支跳过 auto-merge

日期：2026-07-11 ｜ Brain task：0f268ba1 ｜ decision：b687ff46（bug-fix）

## 问题
`hooks/post-pr-create.sh` 第 30 行对所有非 HARNESS_NODE 新建 PR 无条件 `gh pr merge --auto --squash` + exit 2，
导致 rewrite/* 重写 PR（decision e6c57e2f 要求停人工 review）创建 11 秒被秒合（skills#127 实锤）。
CI 侧 lint-skills.yml auto-merge job 本有 cp-* 过滤——只有本地 hook 这道闸缺分支判断。

## 修法
在 HARNESS_NODE 判断之后、enable auto-merge 之前加分支判断：
1. `gh pr view "$PR_NUMBER" --repo "$REPO" --json headRefName -q .headRefName` 取 head 分支
2. `rewrite/*` 前缀 → 跳过 auto-merge，stderr 提示「重写 PR 停人工 review，等主理人批准」，exit 0（不强制 watchdog）
3. 其余分支 → 行为完全不变（auto-merge + exit 2 强制 engine-pr-watchdog）
4. `gh pr view` 查询失败/空值 → 保守按普通分支处理（守卫不因查询失败静默放掉）

## Regression Test（proven-to-fire）
`hooks/__tests__/post-pr-create-rewrite.test.sh`：
- PATH 塞 stub `gh`（记录调用参数到日志；`pr view ... headRefName` 按 STUB_BRANCH 环境变量返回分支名）
- stdin 喂模拟 `gh pr create` 的 PostToolUse hook 输入 JSON
- case 1 rewrite/*：断言未调 `pr merge`、exit 0（旧实现下红 = proven-to-fire）
- case 2 cp-*：断言调了 `pr merge --auto`、exit 2（防守卫被误删）
- case 3 pr view 失败：断言按普通分支处理（调 merge、exit 2）
接进 lint-skills.yml 新 step（改 workflow → PR 标题带 [CONFIG] 前缀）。

## 范围外（勘察记录）
- `hooks/watch-pr.sh:78` 也 enable auto-merge，但为 legacy（现版 post-pr-create 已不调用它），不动
- `hooks/stop-dev.sh:933` 直接 merge，走 /dev dev-mode 文件路径（cp-* worktree 专用），rewrite 流程不经过，不动

## 收尾
合并后 `cp hooks/post-pr-create.sh ~/.claude/hooks/` 同步部署副本；回写 task 0f268ba1。
