# 军师决策记录 — 智能发布 Line（DRY_RUN）

- LINE_ID: `c019cdeb-d90b-4f8b-a658-ae333663ac35`（智能发布，ZenithJoy）
- TRIGGER: `idle`（产能空槽，Brain 唤醒）
- DRY_RUN: `true` —— 全程零写入：未创建任务、未 PATCH 推进项、未写 note、未发 Bark/飞书

## 最终决策

**decision = fix_bug（路径A）**，target = P0 issue `db8630b7-fa89-4fa6-8f96-033dd9d5f570`
「e2e-verify.ps1 Phase 2 在 Windows GHA runner 崩溃：ffmpeg 不在 PATH + host.docker.internal 无法解析」

## 决策理由全文

### Step 0 防抖
查 queued 任务中 task_type=strategist_decision 且 journey_id=本 line 的数量 = **0**，无重复决策在跑，继续。

### Step 1 快照事实（每条带证据来源）

1. **line 基本面**（`GET /api/brain/warroom/line/<id>`）：智能发布，status=active，maturity=skeleton。章程明确写：8 平台 × 3 类内容 dryrun+真发全链路跑通，**GHA windows-latest CI 自动验证**。
2. **能力面**（`GET /api/brain/abilities?journey_id=<id>`）：25 个条目——16 个 ability working（全部 thin）、**3 个小红书 ability broken**（图文/视频/长文）、6 个头条/视频号 ability planned、4 个 feature working。
3. **推进项账本**（`GET /api/brain/warroom/line/<id>/advancements`）：仅「微信公众号文章发布」1 个 ability 有账，4 项：2 done、1 doing（定时发布 `693c079f`, P1）、1 todo（多图文素材库 `00d57f14`, P2）。
4. **doing 项挂账**：全系统查无与「定时发布」关联的任务——in_progress=0 条；queued 5 条全是 content-pipeline（无 journey_id）；completed / failed 最近各 100 条中 payload.journey_id==本 line 均为 0，且无任何任务带 advancement_item_id。账本 2026-07-08 05:05 刚创建（done 项的 pr_url 指向落账本功能本身的 cecelia PR #3635），doing 状态疑为播种残留。
5. **open issues**（`GET /api/brain/issues?status=open&limit=50`）：共 41 条。所有 issue 的 journey_id 均为 null；sub_area 分布为 line02/agent/dashboard/harness/api/null，无一硬标 line01。其中 **P0 `db8630b7`（e2e-verify.ps1 Phase 2 Windows GHA 崩溃）** 语义上正中本 line 章程的「GHA windows-latest CI 自动验证」——e2e-verify.ps1 是发布链路的 E2E 验证脚本（ffmpeg 验视频流，符合 Contract 规则里"视频类功能 Final E2E 必须 ffprobe/ffmpeg 验证"），2026-06-10 open 至今近一个月，**无任何进行中或排队的修复任务**。
6. **无停线信号**：本 line 无历史 run 失败记录（根本没有 run 记录），TRIGGER=idle 非失败触发。

### Step 2 优先级阶梯逐级判断（不跳级）

1. **停线条件** → 不命中。无连续失败；唯一疑点（doing 挂账）可解释为当日账本播种残留，不属"无法解释的矛盾数据"。
2. **P0/P1 bug** → **命中即停**。P0 `db8630b7` open 且无修复在途 → 决策 = 修 bug（路径A）。
3. ~~刚终局 run 暴露新问题~~ → idle 触发，无终局 run，不适用。
4. ~~续推进~~ → 被第 2 级截停。附注：即便走到这级，也应先修账（doing→todo）再挑 todo「多图文素材库」（P2）；DRY_RUN 禁 PATCH，修账需求已写入 result.json 的 `ledger_repair_needed`。
5. ~~补货~~ → todo 未耗尽，不适用。另观察：3 个 broken 小红书 ability 和 6 个 planned 头条/视频号 ability 都无推进项账，是后续补货的候选，留给下轮决策。
6. ~~noop~~ → 有事可做。

**为什么不是路径B（小改动）**：该 bug 涉及 GHA runner 环境（PATH、容器网络解析）+ 有登记 issue，铁律顺序是先 Issue 后 Task 的路径A；且非"无 spec 争议的半天内小活"可轻断。

### Step 3 自审打分

```
依据:
  1) line 章程原文含「GHA windows-latest CI 自动验证」,issue 正中该验证脚本 e2e-verify.ps1
  2) P0 已 open 近一个月(2026-06-10),in_progress/queued 中均无修复任务
  3) 阶梯规则:P0/P1 bug(第2级)优先于 P2 推进项(第4级),不跳级
confidence: 0.72
质量预期: 修通 Phase 2 后本 line 的 CI 自动验证链恢复,后续所有发布 ability 推进项获得可信验收闸,
          也为修复 3 个 broken 小红书 ability 打下验证基础
风险: 该 issue 的 journey_id/sub_area 均为 null,归属本 line 是语义推断非硬关联;
      若归属判断错,浪费一次决策周期(但修 CI 验证链对发布线仍有价值,损失有限)
```

confidence 0.72 ≥ 0.6，不触发停线上报。

### Step 4 / Step 5

DRY_RUN=true → 跳过执行与留痕落库。拟建任务草案与留痕全文（`decision_note_draft`）均在 `result.json` 中。

### 浮给晨报的附注（登记不执行）

- **元数据卫生（cross-line 观察）**：41 条 open issue 的 journey_id 全为 null，军师按 skill 规定"过滤属于本 line 的 issue"只能靠语义推断，归属置信度被系统性压低。建议给 issues 回填 journey_id。
- **账本修账**：推进项「定时发布」doing 挂账，非 DRY_RUN 时应先 `PATCH status: doing→todo`。

---

## 实际执行过的所有 curl 命令清单

全部为 **GET（只读）**，零写操作（无任何 POST/PATCH/DELETE 被执行）：

| # | 命令 | 方法 | 用途 |
|---|------|------|------|
| 1 | `curl -s "localhost:5221/api/brain/tasks?status=queued&limit=50"` | GET | Step 0 防抖：查排队中的 strategist_decision |
| 2 | `curl -s "localhost:5221/api/brain/warroom/line/c019cdeb-d90b-4f8b-a658-ae333663ac35"` | GET | Step 1：line 基本面 |
| 3 | `curl -s "localhost:5221/api/brain/warroom/line/c019cdeb-d90b-4f8b-a658-ae333663ac35/advancements"` | GET | Step 1：推进项账本 |
| 4 | `curl -s "localhost:5221/api/brain/issues?status=open&limit=50"` | GET | Step 1：open issues |
| 5 | `curl -s "localhost:5221/api/brain/tasks?limit=100"` | GET | Step 1：最近任务过滤本 line |
| 6 | `curl -s "localhost:5221/api/brain/tasks?status=in_progress&limit=50"` | GET | 查本 line 进行中任务（=0） |
| 7 | `curl -s "localhost:5221/api/brain/tasks?status=queued&limit=50"` | GET | 查排队任务详情（5 条均 content-pipeline） |
| 8 | `curl -s "localhost:5221/api/brain/harness/initiative-runs?journey_id=<id>&limit=10"` | GET | 尝试查 run 记录（端点 404，Cannot GET） |
| 9 | `curl -s "localhost:5221/api/brain/journeys/<id>/features"` | GET | 尝试查 features（端点 404） |
| 10 | `curl -s "localhost:5221/api/brain/journey-features?journey_id=<id>"` | GET | 尝试查 features（端点 404） |
| 11 | `curl -s "localhost:5221/api/brain/abilities?journey_id=<id>"` | GET | 本 line 全部 ability/feature 及状态（25 条） |
| 12 | `curl -s "localhost:5221/api/brain/features?journey_id=<id>"` | GET | 误入 feature-registry 端点（返回全局 registry，未采用） |
| 13 | `curl -s "localhost:5221/api/brain/tasks?status=completed&limit=100"` | GET | 查本 line 已完成任务（=0） |
| 14 | `curl -s "localhost:5221/api/brain/tasks?status=failed&limit=100"` | GET | 查本 line 失败任务（=0，停线条件排除） |
