# 智能发布 Line 军师决策理由（eval-2 / dry-run）

## 背景
- Line: 智能发布（c019cdeb-d90b-4f8b-a658-ae333663ac35），status=active，maturity=skeleton，8 平台自动发布能力。
- 触发：run_terminal——刚失败的 run，经查失败根因是 **Brain 调度器的 worktree 分配冲突**。
- 关键性质：这是调度器层（全局基础设施）的故障，会影响**所有 line** 的任务派发，与智能发布 line 自身的业务代码无关。

## 决策：halt_and_escalate（停止本线重试，升级为全局基础设施修复）

### 理由
1. **重试无意义**。根因不在本 line 的 PRD/代码/测试，而在 Brain 调度器分配 worktree 的环节。在调度器修好之前重跑同一 run，必然再次撞上同一冲突——浪费 LLM 额度、污染本 line 的成功率统计，还可能制造更多脏 worktree 加剧冲突。
2. **根因跨 line，处置层级要升**。军师的职责边界是本 line，但当失败根因被定位为全局组件时，正确动作不是在本 line 内部"绕过/换姿势重跑"，而是把问题升级到 brain 基础设施 owner，走系统性修复（bug fix 流程：先写能复现的 failing test，再修，test 永久进 CI）。
3. **查重先于新建**。只读查询发现 Brain issues 里已有两个 In progress 的 P1 worktree 相关 issue：
   - `ec5ceda5-1cad-4c12-99e7-3d79a5d5d2cb` — worktree/node_modules 被环境清理器反复破坏 + promote bind-mount inode 断链
   - `dfc5c882-e3f2-488e-9b96-05f6cb5c06bb` — codex relay 容器把容器路径 worktree 注册进宿主共享 .git，毒化宿主所有 worktree 创建
   本次"调度器 worktree 分配冲突"很可能与其中之一同源。因此升级动作的第一步是**归并判断**：同源则把本次失败作为新证据附到已有 issue；不同源才新建 issue（sub-area=brain, P1）+ 关联 fix task。避免重复 issue / 重复 PR（正是 watchdog 刚根治过的坑）。
4. **止血优先**。在修复合并并真正部署（brain-deploy 重建镜像，reload 不算数）之前，应暂停所有 line 的新 harness run 派发，防止批量失败。修复后先用最小 run 验证 worktree 分配正常，再恢复智能发布 line 的派发。
5. **本 line 无堆积压力**。最近 200 条任务里没有归属本 line 的活跃任务，暂停派发对本 line 的即时代价很低，进一步支持"先修地基再跑车"的取舍。

### Dry-run 约束的落实
- 全程只执行了 GET 查询；未创建任务、未新建/更新 issue、未发任何通知、未 PATCH 任何状态。
- 所有写动作（新建/归并 issue、创建 fix task、暂停派发标记、恢复派发）均以 `proposal` 形式写进 result.json 的 actions，`executed=false`，标注 `blocked_by: dry_run`。

## 实际执行过的所有 curl 命令清单（全部为 GET，零写操作）

| # | 命令 | 类型 | 结果 |
|---|------|------|------|
| 1 | `curl -s "localhost:5221/api/brain/journeys/c019cdeb-d90b-4f8b-a658-ae333663ac35"` | GET | 成功，取得 line 元数据（active/skeleton） |
| 2 | `curl -s "localhost:5221/api/brain/context"` | GET | 成功，取得 OKR/最近 PR/活跃任务全景 |
| 3 | `curl -s "localhost:5221/api/brain/initiative-runs?journey_id=...&limit=5"` | GET | 404（该端点不存在） |
| 4 | `curl -s "localhost:5221/api/brain/runs?journey_id=...&limit=5"` | GET | 404（该端点不存在） |
| 5 | `curl -s "localhost:5221/api/brain/tasks?journey_id=...&status=failed&limit=5"` | GET | 成功（journey_id 过滤疑似未生效，返回其他线的失败任务） |
| 6 | `curl -s "localhost:5221/api/brain/issues?limit=50"` | GET | 成功，查重命中 2 个 In progress 的 P1 worktree issue |
| 7 | `curl -s "localhost:5221/api/brain/tasks?limit=100"`（过滤 title 含 worktree） | GET | 成功，无同名修复任务在跑 |
| 8 | `curl -s "localhost:5221/api/brain/tasks?limit=200"`（本地过滤 payload.journey_id=本 line） | GET | 成功，本 line 当前 0 条活跃任务 |

无任何 POST / PATCH / DELETE。
