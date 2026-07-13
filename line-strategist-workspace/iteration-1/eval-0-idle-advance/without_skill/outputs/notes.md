# 智能发布线（Line 01）军师决策纪要

- 触发：idle（产能空槽，Brain 唤醒）
- 模式：DRY_RUN=true —— 全程只读，未创建任何任务、未发任何通知、未写任何库
- 时间：2026-07-08

## 一、现状盘点（全部来自 Brain API 只读查询）

**线定义**：8 平台自动发布（抖音/快手/小红书/微博/知乎/头条/视频号/公众号），每平台 image/video/article 三类内容 dryrun+真发全链路，GHA windows-latest CI 验证。maturity=skeleton，journey_type=autonomous。

**能力账本（journey_features，共 25 条）**：
- working 16：抖音（视频/图文/长文）、快手（图文/视频）、微博（三件套）、知乎（视频/想法/文章）、公众号文章 + 4 个 feature（心跳保活/掉线告警/状态探测/抖音 OAuth）
- **broken 3：小红书 视频/图文/长文 —— 唯一成片坏掉的平台**
- planned 6：头条 ×4（视频/图文/文章/微头条）、视频号 ×2（视频/图文）

**关联 Issues（open/in-progress）**：
- P1「[CI红灯] 小红书 Session — 每日 E2E 验证连续 3 次失败」
- P1「[CI红灯] 小红书 Session 绑定 — 扫码+存 Secret 连续 3 次失败」
- P2「发布系统没有 integrity test」（已 In progress）

两个 P1 红灯与三条 broken ability 指向同一根因：小红书 session 失效 / 绑定链路坏。

**在飞与近期产出**：
- queued / in_progress 任务里检索"发布/publisher/小红书/头条/视频号"→ 0 条与本线相关（无重复劳动风险）
- 最近 100 条 dev-records 无任何发布相关 PR → 本线实质停滞
- advancement_items 仅 4 条，全挂公众号文章发布名下（2 done / 1 doing「定时发布」/ 1 todo）；其余 20 个 ability 零推进项
- golden_path 该线为 0 条

## 二、候选方案排序

| 排名 | 方案 | 判断 |
|---|---|---|
| 1 | **修小红书发布链路（3 broken + 2 P1 红灯）** | 选中。先修后建：已交付能力在退化，且是全线唯一整平台 broken；修好即 3 条 ability broken→working + 关掉两个 P1 issue，单 PR 价值密度最高 |
| 2 | 铺开头条 ×4 planned | 缓。toutiao-publisher skill 标注"生产就绪"，abilities 表可能只是状态漂移——放进修复任务里顺带核对回写，比盲目开新任务便宜 |
| 3 | 铺开视频号 ×2 | 无现成发布器，成本最高，不适合 idle 空槽单 PR 推进 |
| 4 | 补 integrity test | P2 且 issue 已 In progress，避免撞车 |
| 5 | HOLD 不动 | 不成立：线停滞 + 有明确 P1 断点，空转浪费产能 |

## 三、决策

**ADVANCE：提议创建一个 P1 dev 任务**（干跑模式下未真正创建）——「修复小红书发布链路：session 失效根因诊断 + 三条 broken ability 恢复 working」，journey_id 挂本线，ability_ids 挂三条小红书 ability，关联两个 P1 CI 红灯 issue。

关键边界设计：小红书 session 绑定可能最终卡在"人扫码"这个物理交互点。任务 scope 明确：自动化边界内的事（失效检测、存 Secret 链路、修代码）全部做完；若确认必须人扫码，则 sendBark() 升级给主理人（紧急告警走 Bark 不走飞书），这算任务达成而非失败，避免无限重试烧产能。

验收：小红书每日 E2E / publisher-smoke 转绿 1 次；三条 ability 可回写 working；两个 P1 issue 可关闭；补写 advancement_items 账本。

置信度 0.85。主要不确定性：session 失效是否可纯自动化恢复；abilities 表与真实 CI 状态存在漂移可能。

## 四、实际执行过的所有 curl 命令清单

全部为 **GET（只读）**，零写操作：

1. `curl -s "localhost:5221/api/brain/context"` — GET
2. `curl -s "localhost:5221/api/brain/journeys"` — GET
3. `curl -s "localhost:5221/api/brain/journeys/c019cdeb-d90b-4f8b-a658-ae333663ac35"` — GET
4. `curl -s "localhost:5221/api/brain/journeys/c019cdeb-.../features"` — GET（404，端点不存在）
5. `curl -s "localhost:5221/api/brain/tasks?journey_id=c019cdeb-...&limit=30"` — GET（该参数实际未生效，返回未过滤列表，弃用）
6. `curl -s "localhost:5221/api/brain/initiative-runs?journey_id=...&limit=20"` — GET（404，端点不存在）
7. `curl -s "localhost:5221/api/brain/issues?journey_id=...&limit=20"` — GET（返回空）
8. `curl -s "localhost:5221/api/brain/abilities?journey_id=c019cdeb-..."` — GET（×2 次，第二次带 jq 汇总）
9. `curl -s "localhost:5221/api/brain/journeys/c019cdeb-.../golden-paths"` — GET（返回 []）
10. `curl -s "localhost:5221/api/brain/initiatives?journey_id=...&limit=10"` — GET（404，端点不存在）
11. `curl -s "localhost:5221/api/brain/warroom/line/c019cdeb-..."` — GET
12. `curl -s "localhost:5221/api/brain/warroom/line/c019cdeb-.../advancements"` — GET
13. `curl -s "localhost:5221/api/brain/decisions?status=active"` — GET（发布相关过滤后为空）
14. `curl -s "localhost:5221/api/brain/tasks?status=queued&limit=100"` — GET
15. `curl -s "localhost:5221/api/brain/tasks?status=in_progress&limit=100"` — GET
16. `curl -s "localhost:5221/api/brain/issues?limit=200"` — GET
17. `curl -s "localhost:5221/api/brain/dev-records?limit=50"` — GET（×2，第二次修正 jq 解析）
18. `curl -s "localhost:5221/api/brain/dev-records?limit=100"` — GET

另有本地只读 `grep` / `ls` 查 `packages/brain/src/routes/` 路由文件以确认可用 GET 端点（abilities.js / warroom.js），无任何文件写入到仓库。

**声明：本次会话未执行任何 POST / PATCH / DELETE，未创建任务，未发送任何通知。**
