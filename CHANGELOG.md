## [2026-06-18] dev — updated (PrepPRD 新增步骤0.5 对抗深挖)
**症状**: /dev 流水线只围绕用户说出口的 golden path（FR）建，系统性漏掉"理所应当但没人写"的横切铁律和 NFR——生产里连续暴露 AI 回复自己、误回群聊、客服数据不按租户隔离三类弱智 bug，全是用户肉眼发现，流程没有任何环节负责挖
**根因**: PrepPRD 阶段只有"展示 Golden Path 草稿"，没有对抗深挖步骤；缺少横切不变量登记表当逼问清单；单租户测试让隔离漏洞看不见
**修改**: PrepPRD 新增「步骤0.5 对抗深挖」——5 轮换镜头（顺利路径/失败边界/横切铁律/NFR/知识记忆），按 /dev 路径缩放深度，先喂横切不变量登记表（decisions category=invariant）+ 历史 learnings，产出分【要用户拍的 policy】与【机器铁律自动标注】两流，并把生产新坑回灌登记表形成闭环；配套已种 10 条铁律（5 系统级 + 5 Line04 级）

## [2026-06-18] dashboard-deploy — updated（合并 upgrade-dashboard，删重复）
**症状**: 同一件事（部署 dashboard / 给页面一个能打开的地址）存在两个 skill——`upgrade-dashboard`（旧）和 `dashboard-deploy`（#34 已是合并版）。生效目录里挂的偏偏是过时的 `upgrade-dashboard`，正确的 `dashboard-deploy` 没接软链、从不触发；还有个死链 `zenithjoy-deploy` 残留。
**根因**: `dashboard-deploy` 建好后没接进 `~/.claude/skills` / `~/.claude-account1/skills`；`upgrade-dashboard` 架构描述已过时（520/521 nginx + deploy-hk.sh + /home/xx 路径），与现实（hk-vps + autopilot-dashboard + Cloudflare Tunnel + perfect21:5211）不符。
**修改**: 以 dashboard-deploy 为唯一 skill，从 upgrade-dashboard 捞两段有用内容补入（SW 注销 console 脚本 + nginx no-cache 配置）；删除 upgrade-dashboard 目录与软链、清死链 zenithjoy-deploy、把 dashboard-deploy 接进两个生效目录；新增 eval-4（单页预览给地址场景）。iteration-3 eval：合并版 20/20 (100%) vs 旧 upgrade-dashboard 12/20 (60%)。

## [2026-06-08] device-transfer — updated (eval iteration-1 + 触发词补全)
**症状**: skill 存在但触发不稳定——Claude 在国内机器遇到下载失败/超时时不会自动调用，每次需要用户手动提醒
**根因**: description 触发词只覆盖主动发起传输的场景，没有覆盖"中途遇到下载失败"的报错词；CLAUDE.md 也没有全局规则兜底
**修改**: 补充 13 个触发词（下载失败、timeout、Connection refused、apt/pip/npm/curl 慢等）；CLAUDE.md 新增"国内外网下载失败"全局规则；新建 evals 3 条，iteration-1 结果 with_skill=12/12 (100%) vs without_skill=1/12 (8.3%)

## [2026-06-08] dev/db-update/feature-update/feature-map — updated
概念对齐到 Ability/Feature/GoldenPath 新模型；feature-update 标废弃。

## [2026-06-08] wechat-uia-silent-send — updated (eval iteration-1 + 2 bug fixes)
**症状**: 实际使用中发现 2 个 bug：(1) skill 里写命令文件的示例用 `cmd /c echo` 遇中文乱码；(2) IPC 代码在 json.load 异常时 os.remove 不执行，带 BOM 的文件导致每 3 秒死循环刷屏
**根因**: (1) `cmd /c echo` 无法处理中文/引号，正确做法是 pure ASCII JSON + `\uXXXX` 转义；(2) `os.remove` 放在 `json.load` 之后，parse 失败时文件未删，需改 `encoding='utf-8-sig'` + 读完立即删
**修改**: 修复写命令文件章节（改为 ASCII+`\uXXXX` 方案），修复 IPC 代码示例（utf-8-sig + 先删后解析），补充"联系人找不到时 dump 会话列表"调试指引；新建 evals 3 条，iteration-1 结果 with_skill=100% vs without_skill=75%

## [2026-06-08] wechat-uia-silent-send — created
**症状**: 无文档说明微信后台 UIA 发送机制，每次开发重复踩坑（等待时间/版本限制/前台路径无效）
**根因**: 经过多轮调试才摸清 `Invoke()` 后需 2s 等待、UIA SetValue+PostMessageW 才是唯一可靠路径
**修改**: 新建 skill，记录静默发送架构、命令文件 IPC、成功验证方法、禁止使用的死路

## [2026-06-03] zenithjoy-deploy — removed
**症状**: zenithjoy-deploy 和 dashboard-deploy 并存，功能重复
**根因**: 应直接替换而不是新建
**修改**: 删除 zenithjoy-deploy，由 dashboard-deploy 完全替代

## [2026-06-03] dashboard-deploy — created
**症状**: zenithjoy-deploy skill 只覆盖 ZenithJoy，Cecelia dashboard 无 skill；旧 skill 缺公网验证步骤
**根因**: 两个 dashboard 架构差异大，需统一入口；旧 skill 不含 Cloudflare tunnel ingress 知识
**修改**: 新建 dashboard-deploy 覆盖 ZenithJoy（rsync+HK VPS）和 Cecelia（本地 bind mount），含公网验证和 502 排查

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
