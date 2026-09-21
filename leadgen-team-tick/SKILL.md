---
name: leadgen-team-tick
description: 智能获客「团队层」两个可重跑脚本——看板员（从工件算平台×能力矩阵与新鲜度，不手填）和熟化员（findings/escalation 归一化后同判例≥3次自动开 Brain 任务，本地账本幂等）。0921 首次真实点火：开出 task e10dd2b8。触发场景：获客矩阵现状 / 熟化四态闭环 / 团队 tick / 判例开单。
---

# 智能获客团队层 tick（看板员 + 熟化员）

> 0921 主理人拍板：单次 run 由 Commander 四只手盯，**跨 run 的"哪个格子在哪、下一趟跑什么、判例攒够没"由团队层管**，两者只通过工件说话。
> 本 skill 是团队层里可机械化的两块；排程员用现成的 `triage-officer`，司令部=有头+主理人。

## 为什么是脚本不是表

0921 落地核实：三个状态载体（SKILL.md 熟化计数 / `journeys.maturity` / `golden_paths.status`）**全部已被实证为没人更新的死字段**。状态必须从工件**算出来**，凡要人记得填的都会死。

## 看板员 `scripts/board_v0.sh`

探针→格子 S 阶段（每条探针可重跑）：原语数（S2）/ 合同 run 工件（S3）/ cron+近7天 LEAD（S4）/ 触达 cron（S5）/ 脚本 git 最后改动≥28天（S6 候选）；新平台看判定树日期与 runtime 存在性。末行=**团队自身新鲜度**——团队静默死时这里变红。

0921 实测：`抖音×获客 S5（原语50，触达cron在跑，近7天LEAD 837，脚本5天前改过未到S6）`；快手/小红书/视频号均 S0，`runtime=缺(硬前提)`；合同 run 最后 09-13（n8n 路径已死 7 天）。

## 熟化员 `scripts/maturation_v2.py`

自由文本 → 归一化（去时间/批次/数字，同义词折叠）→ group by → ≥2 候选 / ≥3 开单；`--ledger` 本地账本保证同判例不重复开（先 GET 任务状态，查不到按 open）。默认演练，`--fire` 才 POST。

**0921 首次真实点火**：308 行 findings + 332 行 escalation。
- `--key stem`（主干60字）：185 判例，38 条 ≥3——同根因按尾巴措辞拆成 ~5 条，**不能拿来自动开单**
- `--key cause`（原因子句，默认）：93 判例，**18 条 ≥3**；最顶「指定节点 xian-m4 不可达」**396 次（占全部 640 行的 62%）**，自 0917 起从未开单、0921 13:41 仍在报
- 已为它开 Brain 任务 `e10dd2b8-9a24-453a-b463-e39988b6d2ae`（P0 queued，Brain 自动标 harness_initiative）；重跑演练确认账本幂等（跳过 1，不重复）

**⚠️ 放开 `--fire` 的前提**：只用 `--key cause`；首轮先人工过一遍 18 条清单再点火。
**⚠️ 账本债风险**：有头建的 harness_initiative 曾被 watchdog 判 failed（memory 账本债第四次发作），建完必须回查状态。

## 接线

- 两个脚本挂 Manager 巡检 cron（每日）；账本放 `/opt/openclaw/state/maturation-opened.json`（与 findings 同机）
- POST 字段照 memory `brain_task_creation_field_gotchas`：顶层 `change_kind/repo_hint=zenithjoy-workspace/map_scope_hint=[keyword_acquisition]/base_sha`，`payload.gp_anchor` 合法形式
- 健康度双曲线（COMMANDER.md）：SOP 侧 `cmdr-stream/escort.txt` 各 6 条自 0916 未变；分身侧 escalation 日计数 48/130/71/27/55/1——SOP 不降、升级被单一未修判例占满 = **未在熟化**；0921 的 1 次是节点不可达导致的沉默，不是好转
