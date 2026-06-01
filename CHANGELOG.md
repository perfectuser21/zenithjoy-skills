# ZenithJoy Skills Changelog

每次通过 skill-creator 创建或更新 skill 后，在此文件顶部追加一条记录。

格式（必须含三段）：
```
## [YYYY-MM-DD] <skill-name> — <created|updated>
**症状**: 触发本次修改的现象（什么行为失效、什么 CI 报错、什么用户反馈）
**根因**: 造成症状的根本原因
**修改**: 本次做了什么改动
```

---

## [2026-06-01] db-update — created
**症状**: 无统一数据写入规范，Feature 表被测试数据污染，截图存 COS 费用高
**根因**: notion-sync 名称误导（以为目的是同步 Notion），缺少所有表的 Output Template，截图路径未规范
**修改**: renamed notion-sync → db-update，补全 10 张表 + 5 种 Notes Type 的 Output Template，harness-report 截图改 VPS scp

## [2026-06-01] harness-report — updated
**症状**: Report 格式冗长，缺 Usage 表、DOD 对齐、截图证明
**根因**: Step 6 report 模板无结构，截图走 COS 未规范
**修改**: 新增紧凑 Report 模板，截图改 scp 到 us-vps，Phase B 调用 db-update skill

## [2026-05-30] dev + harness-planner — updated (eval 修复)
**症状**: (1) dev eval：三条路径（Bug/小改动/大功能）写 decision 时用 `type: bug_fix` 而非 `category: bug-fix`，Brain API 只认 category 字段，数据写入失效；(2) harness-planner eval：thin-slice-size 断言以 ≤50 行为标准，但含 smoke script 的真实 PRD 常见 80-110 行，eval 持续误报
**根因**: (1) dev SKILL.md bash snippet 注释说"换成实际值后执行"，Claude 自行重写 JSON 时忽略 category 写成 type；(2) ≤50 行限制是 2026-05-12 防 254 行 PRD 临时设的，未考虑 smoke script 正常占 20-40 行
**修改**: (1) dev v19.4.0: 三条路径 decision bash snippet 加 ⚠️ 注释 + 加粗强调 `category` 不能写 `type`；(2) harness-planner v8.7.0: ≤50 行改为 ≤100 行，evals.json thin-slice-size 断言同步更新为 <=100

## [2026-05-30] harness-report — updated (v6.0.0, merged harness-sprint-state)
**症状**: harness-report 和 harness-sprint-state 是两个独立 skill 但职责重叠（都是 Sprint 完成后的收尾工作），造成混乱
**根因**: 历史上 sprint-state 从 evaluator 拆出后未与 report 合并
**修改**: 将 harness-sprint-state 全部内容合并入 harness-report（Phase A=交付报告 6步，Phase B=Sprint状态同步8个DB）；harness-sprint-state 目录和 symlink 已删除；sprint-state 详细实现移入 harness-report/references/sprint-state-sync.md

## [2026-05-30] harness-evaluator + harness-contract-proposer + harness-contract-reviewer — updated + eval iteration-1
**症状**: (1) harness-evaluator v1.11.0 的空壳 workflow 检测正则漏掉 `npm test`/`npm ci` 和 PowerShell 业务命令，导致真实 `agent-qr-windows-verify.yml`（含 `npm test`）会被误判为空壳，Evaluator 提前 FAIL 而不触发 workflow；(2) harness-contract-proposer 没有 windows_cloud workflow 内容审查规则，直接按假设写 BEHAVIOR 不验证 CI 真实内容；(3) harness-contract-reviewer 缺少 ci_workflow_alignment 维度评审
**根因**: (1) 正则只覆盖 `npm run` 未覆盖 `npm test`/`npm ci`，PowerShell 命令完全未收录；(2)(3) v8.0 上线时只更新了 proposer 描述未添加强制读取 workflow 文件规则，reviewer 未对应增加第 7 维评分
**修改**: (1) evaluator v1.11.1: 正则加入 `npm test|npm ci|Set-Content|New-Item|ConvertTo-Json|Write-Host.*PASS`；(2) proposer v8.1.0: 新增 windows_cloud BEHAVIOR 1:1 映射强制规则 — 必须 cat workflow 读实际内容后对比用户路径；(3) reviewer v8.0.0: 新增第 7 维 ci_workflow_alignment；三个 skill eval iteration-1 完成，with-skill pass rate: evaluator 100%、reviewer 100%、proposer 100%

## [2026-05-29] engine-pr-watchdog — updated
**症状**: PR BEHIND，watchdog 检测到需要 rebase，rebase 完成后 push 用了 run_in_background=true，bash tool 立刻返回，Claude 输出文字结束 turn，轮询循环断裂，PR 永远卡在 BEHIND 未合并
**根因**: run_in_background=true 让 push 异步执行，bash call 立刻返回控制权给 Claude，Claude 自然结束 turn
**修改**: 禁止 run_in_background，Step 4 rebase/push 全部改为同步执行

## [2026-05-29] harness-contract-reviewer + harness-report — updated
**症状**: harness pipeline 在单 Sprint 单 PR 模式下，reviewer 第 7/8 维依赖多 Workstream 前提，评审无意义；report 创建多个 Sprint Task 与单 Sprint 模型矛盾
**根因**: 早期多 Workstream 设计残留，与 Anthropic 官方 v2（一 Sprint = 一 PR）冲突
**修改**: reviewer 删第 7/8 维，report 改为单 Sprint Task 创建

## [2026-05-29] harness-contract-proposer + harness-generator — updated
**症状**: proposer/generator 仍按多 Workstream 逻辑分配任务，产生冗余分支，与 pipeline 整体方向冲突
**根因**: 多 WS 拆分概念在 skill 里未清除，与官方 v2 单 Sprint 设计不兼容
**修改**: 移除 Workstream 拆分概念，对齐官方 v2（一个 Sprint = 一个 Generator = 一个 PR）

## [2026-05-29] hooks/ — created
**症状**: 全局 hooks 散落在 ~/.claude/hooks/，每次修改无版本记录，无法 review，出问题无法回溯
**根因**: hooks 不在 git 管理下，缺乏变更追踪
**修改**: 迁移到 zenithjoy-skills/hooks/，统一版本控制

## [2026-05-29] harness-generator — updated
**症状**: generator 开完 PR 后立刻退出，CI 未等待，PR 长期 open 无人跟进，需要人工手动合并
**根因**: generator 把"开 PR"视为任务终点，没有后续监控机制
**修改**: Step 7.5 PR 创建后轮询 CI 直到合并（后被独立 engine-pr-watchdog skill 接管）

## [2026-05-29] engine-pr-watchdog — updated v3.0.0
**症状**: watchdog 只监控当前 repo，跨 repo PR（cecelia / zenithjoy-workspace / zenithjoy-skills）被漏掉；WTBASE 路径错导致 worktree 找不到
**根因**: scope 设计过窄，只检查当前目录的 repo；路径变量赋值有误
**修改**: 改为查询所有三个 repo 的 open PR，修复 WTBASE 路径错误，放宽 trigger 条件

## [2026-05-29] engine-pr-watchdog — updated
**症状**: watchdog bash loop 运行超 600s（Bash tool 上限）后超时退出，Claude 自然输出文字结束 turn，轮询断裂，PR 被遗忘
**根因**: Bash tool 有 10 分钟硬上限，超时后控制权回到 Claude，Claude 不会自动继续轮询
**修改**: 超时后必须立刻重新发起 Bash 调用，不得输出任何文字，不得结束 turn

## [2026-05-29] skill-creator — updated
**症状**: skill 改动时有人绕过 skill-creator 直接编辑文件，CHANGELOG 未更新，zenithjoy-skills 同步状态不一致
**根因**: 缺少强制约束，AI 可以直接修改 skill 文件跳过流程
**修改**: 加入 ZenithJoy 强制规则（所有改动必须经过 skill-creator）；Post-Creation 步骤新增 zenithjoy-skills 同步 + CHANGELOG 更新
