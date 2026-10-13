---
name: arch-review
version: 1.2.0
created: 2026-03-10
updated: 2026-07-14
changelog:
  - 1.2.0: 部署配置漂移探针（decision be038f9e 铁律配套 — 「运行时对但持久化没改，下次部署冲掉」已复发5+次根治）— 4A 新增第 9 项探针C：对生产运行时（docker 容器 / LaunchDaemon）取实际 env，对比持久化源（repo .env.docker/compose、deploy-lib.sh 默认值、GitHub 仓库变量），关键变量运行时≠持久化推导值 🔴 开 Issue；持久化源互相矛盾 ⚠️。探针C 与 A/B 同为非代码类检查，「无 packages/brain/src」时照常执行；输出表加一行
  - 1.1.0: 台账-现实一致性双探针（handoff 0714 刀4 — 台账漂移无人察觉根治）— 4A 新增第 7/8 项：探针A【台账新鲜度】active journey 的 journeys.updated_at 落后该线最近 merged PR >7 天 ⚠️ / >21 天 🔴 开 followup；探针B【smoke 一致性】journey.e2e_test_path 脚本 grep 近 60 天 decisions「废弃/去X」关键词，命中 🔴 开 Issue。两探针查 Brain DB 不依赖 repo 代码，「无 packages/brain/src 则跳过」前置改为只跳 4A 1-6 与 4B，探针照常执行；输出表同步加两行
  - 1.0.0: 初始版本 - 从 /architect Mode 3 迁移 + 新增 Mode 4 架构巡检
description: |
  架构审查官。负责验证、巡检、发现偏离与结构退化，不承担新架构设计职责（那是 /architect 的事）。

  两个模式：
  - verify：Initiative 完成后验收（Brain 自动触发 task_type=initiative_verify）
  - review：每日架构健康巡检（Brain 定时触发 task_type=arch_review）

  触发词：验收 initiative、架构巡检、检查架构漂移、arch-review、检查结构健康、/arch-review
---

# /arch-review - 架构审查官

**角色定位**：审查而非设计。发现问题、记录发现、决定是否升级到 /architect。

**模型**：Sonnet（评估型任务，不需要 Opus 的创造力）

**核心分工**：
```
/architect   → 提出设计、产出架构方案
/arch-review → 验收成果、巡检健康、守住边界
```

---

## 触发方式

```bash
/arch-review verify --initiative-id <id>   # Mode 3: Initiative 验收
/arch-review review                        # Mode 4: 每日巡检（默认）
/arch-review review --full                 # Mode 4: 完整版（每周）
/arch-review review --scope=drift          # 仅漂移检查
/arch-review review --scope=health         # 仅结构健康
/arch-review --task-id <id>               # Brain 自动派发
```

---

## Mode 3：Initiative 验收（verify）

### 目标

Initiative 所有 dev tasks 完成、code_review PASS 后，验收功能 DoD + 架构对齐 + 标记完成。

Brain 自动触发：`task_type = 'initiative_verify'`

### Phase 1：前置条件检查

```bash
INITIATIVE_ID="<id>"
PENDING=$(curl -s "http://localhost:5221/api/brain/tasks?project_id=$INITIATIVE_ID" | \
  jq '[.[] | select(.task_type=="dev" and (.status | IN("queued","in_progress","blocked")))] | length')
[ "$PENDING" -gt 0 ] && echo "BLOCK: $PENDING dev tasks 未完成" && exit 1

CR=$(curl -s "http://localhost:5221/api/brain/tasks?project_id=$INITIATIVE_ID" | \
  jq -r '[.[] | select(.task_type=="code_review" and .payload.scope=="initiative")] | last | .status')
[ "$CR" != "completed" ] && echo "BLOCK: initiative code_review 未通过" && exit 1
```

### Phase 2：功能 DoD 验收

读取 `initiative-dod.md`，逐条验证 F1/F2/... 条件，记录 PASS / FAIL。

### Phase 3：架构对齐校验

对照 `architecture.md` 逐条验证：
- **数据模型**：查询实际 DB schema，确认新增字段/表存在
- **API 端点**：grep routes.js 确认新增端点存在
- **关键决策**：代码是否符合选定方案（不可自动校验的标注"需人工确认"）

### Phase 4：输出验收报告

```markdown
## Initiative 验收报告

### 功能 DoD
- ✅/❌ F1: ...

### 架构对齐
- ✅/❌ 数据模型 — [字段] 存在
- ✅/❌ API — [端点] 存在
- ⚠️  需人工确认 — [决策描述]

### 总体裁决：APPROVED / NEEDS_REVISION / REJECTED
```

### Phase 5：标记完成（仅 APPROVED）

```bash
curl -s -X PATCH http://localhost:5221/api/brain/projects/$INITIATIVE_ID \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'
```

### Machine-Readable Verdict

```json
{
  "verdict": "APPROVED",
  "summary": "Initiative 验收通过",
  "dod_results": [{"id": "F1", "status": "PASS", "note": "..."}],
  "architecture_alignment": "aligned"
}
```

| verdict | Brain 行为 |
|---------|-----------|
| `APPROVED` | project status → completed |
| `NEEDS_REVISION` | 创建修订 dev task（最多 3 轮） |
| `REJECTED` | cecelia_events P0 告警 |

完成后创建 `.arch-review-verify-done`。

---

## Mode 4：架构巡检（review）

### 前置检查

若 `packages/brain/src/` 不存在，跳过**代码类检查（4A 第 1-6 项 + 4B）**（该仓库无 Cecelia Brain 模块）。**但 4A 第 7/8/9 项探针查的是 Brain DB 与生产运行时（localhost:5221 / psql cecelia / docker / launchctl），不依赖 repo 代码，必须照常执行**——不允许因此前置返回 HEALTHY 直接退出。

```bash
SKIP_CODE_REVIEW=0
[ ! -d "packages/brain/src" ] && SKIP_CODE_REVIEW=1 && echo "无 Cecelia Brain 模块：跳过 4A 1-6 与 4B，仅跑 4A 7/8/9 探针"
```

### 执行节奏

| 模式 | 频率 | 4A Drift | 4B Health |
|------|------|---------|----------|
| 默认（daily） | 每日 | 完整 6 项 | 轻量（core modules 只） |
| `--full` | 每周 | 完整 | 完整全库扫描 |
| `--scope=drift` | 按需 | 完整 | 跳过 |
| `--scope=health` | 按需 | 跳过 | 完整 |

---

### 4A：Architecture Drift Review（防漂移）

检查实现是否偏离 `architecture.md` / ADR / SYSTEM_MAP。

**每日 9 项检查**（第 7/8/9 项为探针，查 Brain DB 与生产运行时，不受「无 packages/brain/src」前置影响）：

**1. Boundary Drift**
L0/L1/L2/Planner/Skill 职责边界是否被侵蚀，有无跨层直接调用。

**2. Undocumented Architectural Changes**
```bash
git log --since="24 hours ago" --name-only --pretty=format:"" | sort -u
```
近期结构性改动是否同步到 architecture.md / SYSTEM_MAP。

**3. Routing Integrity**
task_type → skill 映射是否清晰；fallback 是否被滥用（如 dev→talk 静默降级）。

**4. Core Module Complexity**
```bash
wc -l packages/brain/src/{tick,executor,planner,thalamus,cortex}.js
```
5 个核心文件行数趋势，是否有大块新增逻辑没有对应测试。

**5. Concurrency & State Safety**
近期改动是否涉及 task 状态机、worktree 管理、cleanup 逻辑，是否引入新竞态。

**6. Temp Patch 永久化**
```bash
grep -rn "TODO\|FIXME\|HACK\|temp\|temporary" packages/brain/src/ --include="*.js" | \
  grep -v node_modules | grep -v ".test."
```
超过 7 天的 TODO 标记为结构债。

**7. 台账新鲜度探针（v1.1 — 探针A）**

> 实证（handoff 0714）：journeys 表 Path2/Path4 updated_at 停在 2026-05-22，与该线持续 merge 的 PR 脱节 46+ 天无人察觉。harness-report 6.7.0 的翻牌义务是写入侧，本探针是巡检侧第二道闸。

对每条 active journey（排除名称含 smoke/test 的污染条目），比较 `journeys.updated_at` 与该线最近 merged PR 时间：

```bash
psql -h localhost -p 5432 -U postgres -d cecelia -tc \
  "SELECT id, name, updated_at FROM journeys WHERE status='active' AND name !~* 'smoke|test';"
# 该线最近 merged PR 时间：按 journey 名/line 关键词匹配 PR 标题
# gh pr list --repo <base_repo> --state merged --search "<line关键词>" --limit 1 --json mergedAt,title
# 匹配不到 PR 时，以 tasks 表该 journey_id 最近 completed 任务的 updated_at 兜底
```

判据：`journeys.updated_at` 落后该线最近 merged PR 时间 **> 7 天 → ⚠️**；**> 21 天 → 🔴 开 `arch_review_followup` task**（写明 journey id、落后天数、最近 PR）。

**8. smoke 一致性探针（v1.1 — 探针B）**

> 实证：golden-path-2-smoke.sh 停在 05-26 还在测已删除的飞书流程，与用户 07-07「去飞书改本地」决策（431acd2c）打架 46 天。

对每条 active journey 的 `e2e_test_path` 指向的 smoke 脚本，grep 已废弃方案关键词。关键词来源：decisions 表近 60 天「废弃/去X/弃用/改用」类决策：

```bash
psql -h localhost -p 5432 -U postgres -d cecelia -tc \
  "SELECT id, topic, decision FROM decisions WHERE created_at > NOW() - interval '60 days' AND (topic || ' ' || decision) ~ '废弃|弃用|去飞书|不再用|改用|替换为';"
# 从命中决策提取被废弃的方案关键词（如：飞书 / Bitable / LangGraph），逐个 grep smoke 脚本：
grep -nE '<废弃关键词>' <repo>/<e2e_test_path> && echo "🔴 该 smoke 在测已废弃方案"
```

命中 → **🔴 开 Issue**（POST /api/brain/issues，body 写明脚本路径、命中行、冲突 decision id）。脚本文件不存在 → ⚠️（journey 声明了 e2e_test_path 但脚本缺失，同样是台账-现实断裂）。

**9. 部署配置漂移探针（v1.2 — 探针C）**

> 实证（decision be038f9e，2026-07-14 Alex 拍板铁律的巡检侧配套）：同一漏洞复发 5+ 次——每轮"完成"只验证运行时当下状态（容器 env 对、进程连对库），没人验证下次正常部署/重启会不会把状态冲掉。持久化配置（.env.docker、deploy-lib.sh 默认值、GitHub 仓库变量）与运行时状态之间的缝每次都从这里漏。本探针的问题只有一个：**"如果现在重新部署/重启，这个服务还会得到和当前一样的配置吗？"**

对每个生产运行时，取**实际运行时 env**，对比**持久化源推导出的期望值**：

```bash
# ① Docker 容器（cecelia prod/staging）：运行时实际 env
docker inspect cecelia-node-brain --format '{{json .Config.Env}}' | jq -r '.[]' | sort
# 持久化源有两份 .env.docker，必须两份都比、且两份互 diff（实证坑：容器实际由
# CD 专用仓 ~/perfect21/cecelia-deploy-main/.env.docker 启动，主仓那份被 gitignore
# 且可能领先/落后——只比其中一份会产生假🔴或漏真🔴）：
diff ~/perfect21/cecelia/.env.docker ~/perfect21/cecelia-deploy-main/.env.docker
# 再加 docker-compose.yml / docker-compose.staging.yml 的 environment 段默认值。
# 部署脚本默认值：看实际存在的 scripts/deploy-local.sh、scripts/brain-deploy.sh 等；
# 引用了不存在的脚本名时跳过并在报告注明，不要卡住。

# ② launchd 服务：扫 /Library/LaunchDaemons/*.plist 全量（排除 *.bak*），
# 不要只按 launchd-patrol manifest 清单——manifest 只含 cecelia 系 label，
# 会漏掉 zenithjoy 系（实证：首跑抓到的🔴恰在 com.zenithjoy.api）：
for p in /Library/LaunchDaemons/com.*.plist; do
  label=$(basename "$p" .plist)
  launchctl print "system/$label" 2>/dev/null | sed -n '/environment = {/,/}/p'   # 运行时（勿用 grep -A20，50+ 变量会截断）
  /usr/libexec/PlistBuddy -c "Print :EnvironmentVariables" "$p" 2>/dev/null        # 持久化
done

# ③ GitHub 仓库变量（CI/CD 部署时注入的）——空列表和权限失败长得一样，必须验证 exit code：
gh variable list --repo perfectuser21/cecelia; echo "exit=$?"
```

比对方法：只比**关键变量**（DB 连接、端口、API base、feature flag、部署目标），不逐字节比对全量 env。对每个关键变量回答：持久化源推导值 == 运行时实际值？

判据：
- 关键变量**运行时值 ≠ 持久化推导值** → **🔴 开 Issue**（POST /api/brain/issues，写明服务名、变量名、运行时值 vs 持久化值、哪个持久化文件要改）——这正是"下次部署会冲掉"的活漏洞
- **持久化源之间互相矛盾**（.env.docker 说 A、deploy-lib.sh 默认值说 B、GitHub 变量说 C）→ **⚠️**（当前可能碰巧对，但取值优先级一变就漂移）
- 容器/服务不在跑导致取不到运行时 env → ⚠️ 记录（那是 launchd-patrol 的辖区，但要写进报告）

**探针裁决联动**：第 7/8/9 项任一 🔴 → 本次巡检 verdict 不得为 HEALTHY（至少 NEEDS_ATTENTION）。

---

### 4B：Structural Health Review（防腐化）

**轻量模式（每日，仅 core modules）**：
- packages/brain/src/ 文件数量变化
- 核心 5 文件 import 数量（依赖是否增加）
- 新文件是否有对应测试文件

**完整模式（`--full`，每周）**：

```bash
# 孤岛/僵尸模块
for f in packages/brain/src/*.js; do
  name=$(basename $f)
  count=$(grep -rl "$name" packages/brain/src/ --include="*.js" | grep -v "$name" | wc -l)
  [ "$count" -eq 0 ] && echo "ORPHAN: $name"
done

# God Module（>500行 且 import>10）
for f in packages/brain/src/*.js; do
  lines=$(wc -l < $f)
  imports=$(grep -c "^import" $f 2>/dev/null || echo 0)
  [ "$lines" -gt 500 ] && [ "$imports" -gt 10 ] && echo "GOD: $(basename $f) (${lines}L, ${imports}imports)"
done

# 近 30 天热点文件
git log --since="30 days ago" --name-only --pretty=format:"" | \
  grep "packages/brain/src/" | sort | uniq -c | sort -rn | head -10
```

---

### 输出格式（固定）

```markdown
## Architecture Review — {日期} {daily|weekly}

### Executive Summary
[2-3 句总体判断]

### 4A Drift Findings
| 检查项 | 状态 | 发现 |
|--------|------|------|
| Boundary Drift | ✅/⚠️/🔴 | ... |
| Undocumented Changes | ✅/⚠️/🔴 | ... |
| Routing Integrity | ✅/⚠️/🔴 | ... |
| Core Module Complexity | ✅/⚠️/🔴 | ... |
| Concurrency Safety | ✅/⚠️/🔴 | ... |
| Temp Patch Accumulation | ✅/⚠️/🔴 | ... |
| Ledger Freshness (探针A) | ✅/⚠️/🔴 | ... |
| Smoke Consistency (探针B) | ✅/⚠️/🔴 | ... |
| Deploy Config Drift (探针C) | ✅/⚠️/🔴 | ... |

### 4B Structural Health Findings
[轻量/完整] — 孤岛、God Module、结构债信号

### Severity
- 🔴 High: N 项
- ⚠️  Medium: N 项
- ✅ Clean: N 项

### Required Actions
- [ ] [具体行动，带优先级]

### ADR Needed? [是/否]
### Escalate to /architect? [是/否 + 理由]
```

### execution-callback 输出

```json
{
  "verdict": "HEALTHY|NEEDS_ATTENTION|CRITICAL",
  "drift_findings": 0,
  "health_findings": 1,
  "high_severity": 0,
  "escalate_to_architect": false,
  "summary": "6 项检查通过 5 项，发现 1 项 temp patch 积累"
}
```

| verdict | Brain 行为 |
|---------|-----------|
| `HEALTHY` | 记录日志，继续正常运转 |
| `NEEDS_ATTENTION` | 创建 `arch_review_followup` task |
| `CRITICAL` | 创建 P0 followup + cecelia_events 告警 |

完成后创建 `.arch-review-review-done`。

---

## Brain 注册

| task_type | skill 参数 | 触发方式 |
|-----------|-----------|---------|
| `initiative_verify` | `/arch-review verify --initiative-id <id>` | Initiative 完成后自动 |
| `arch_review` | `/arch-review review` | 每日 recurring_task |
| `arch_review` | `/arch-review review --full` | 每周 recurring_task |

---

## 禁止行为

- 不主动修改代码（发现问题 → 记录 → 创建 followup task，让 /dev 去改）
- 每条发现必须有具体文件/行号/证据，不写泛泛结论
- `CRITICAL` 时不自动标记任何 initiative completed
- 不替代 /architect 做架构设计决策
