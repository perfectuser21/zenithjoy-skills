---
name: skill-distill
description: |
  沉淀：把一次核验通过的运行（探路轨迹 + 证据）提炼成一份合格的 skill 草稿——先查重合并，再定归层与拆分，每一步写 DoD，必写成功判定与契约。技能工厂七阶段的第③步。
  触发：任务里写「阶段：沉淀」「使用 skill：skill-distill」、把这次跑通的沉淀成 skill、写成 skill。
  与 Claude Code 的 skill-creator 关系：本 skill 是「写什么」的规范（两边通用）；skill-creator 负责 Claude Code 侧的评测与发布流程，其 ZenithJoy 规则引用本规范。
  不适用：核验没通过的运行（不沉淀，只记坑）；验收已写好的 skill（用 contract-reviewer / skill-evaluator）。
---

> **语言规则：所有输出简体中文。**

# 沉淀 skill-distill

输入是一次**已核验通过**的运行；输出是一份 SKILL.md 草稿。你不上架、不合并，只交草稿。

**副作用**：本 skill 只读、只输出 JSON，**不写任何文件、不提 PR**；落盘与提 PR 由上架阶段完成。注意 `patch` 可被下游直接应用，上架阶段必须先过验收（contract-reviewer 无致命项）才能应用。

## 第 0 步：核对输入（不过就停）

| 检查 | 不通过时 |
|---|---|
| 核验结论 `verdict=pass`，且其 `run_id` 与探路交付物的 `run_id` 相同；核验结论必须是 Brain 交给你的 run-verify 独立会话产出，**不能是你在本会话里自己得出的** | 停止，`status=rejected`，写明「核验结论缺失、不独立或不属于本次运行」 |
| 探路交付物 `trajectory` 非空、`final_evidence` 非空 | 停止，`status=rejected`，写明缺哪项 |
| 查重要用的目录能访问 | 部分不可访问：继续，在 `dedup.unreachable` 列出，并加一条 open_question「可能与未查到的位置重复」；**技能库根目录不可访问或三处全不可访问：停止，`status=rejected`** |

## 你拿到的材料

| 材料 | 来源 |
|---|---|
| 探路交付物 | skill-explore 输出的 JSON（trajectory / final_evidence / findings） |
| 核验结论 | run-verify 的 `verdict=pass` |
| 工坊提案（可能有） | OpenClaw Skill 工坊针对这次运行自动写的 PROPOSAL.md |

## 第 1 步：查重——能合并就不新建

依次搜，找同一件事或同一段动作：

1. 技能库 `zenithjoy-skills` 根目录的 skill（name / description / 正文关键词）
2. 技能库 `openclaw/*/skills/` 与各 OpenClaw agent 工位里的 skill
3. OpenClaw 工坊提案目录里的同类提案

| 查到 | 处理 |
|---|---|
| 已有 skill 做的就是这件事 | **不新建**，产出对它的修改（补步骤、补坑、更新熟化计数），**以补丁形式交付**，不整篇重写 |
| 已有 skill 覆盖其中一段 | 新 skill 引用它，不复制那一段 |
| 都没有 | 新建；`skill_name` 必须与所有已查位置里的 skill 名都不相同（同名不同实现也算冲突，换名） |

## 第 2 步：归层与拆分

**归层**（写进 frontmatter 的 `layer`）：

| 层 | 放什么 |
|---|---|
| 底座 base | 所有平台、所有业务都要守的规矩（锁、拟人、定位三层） |
| 平台 platform | 某个平台上的动作，与业务无关（抖音搜索、打开评论区、朋友圈点赞动作本身） |
| 业务 business | 一个业务结果的阶段与业务判断（获客：哪条评论算有意向） |

**拆分**：满足任一条才把一段单独拆成 skill，否则留在当前 skill 里：
1. **已经存在** ≥2 个 skill 用到这一段（只算已发生的，不算预测）；
2. 这一段自己有明确可观察的成功判定；
3. 风险等级不同（只读 vs 对外可见 / 不可撤回）。
第一次沉淀默认**不拆**，等第二个 skill 要用同一段时再抽。

## 第 3 步：提炼步骤

- 一步 = **一次页面状态变化**，不是一次点击。
- 从 trajectory 里删掉 `detour: true` 的绕路与重试，只留成功路径。
- 必须切出一步的地方：进入新页面；对外动作**之前**（确认对象选对）；对外动作**之后**（确认生效）。

## 第 4 步：每一步写 DoD 五个字段

| 字段 | 规矩 |
|---|---|
| 前置 | 这一步开始时应在哪个页面；不在就先回退，不硬点 |
| 动作 | 找哪个控件（写文字 / content-desc），做什么；**禁止写坐标** |
| 完成判据 | 写**状态**不写动作（「出现『朋友圈』标题」，不是「点了发现」）；必须可观察（前台包名 / 页面标题 / 控件文字 / 截图特征）；对外动作那一步加**反向检查**（如「菜单显示『赞』而不是『取消』」） |
| 证据 | 截图或控件树，证据 ID 带步号与时间 |
| 失败处理 | 重试一次 / 退回上一步 / 停止上报；**对外动作失败一律停止，不重试** |

## 第 5 步：成功判定（必写）

- 成功长什么样：一到三条可观察断言。
- 证据：哪一张截图 / 哪条记录能证明。
- 由谁判：run-verify 独立判定，不由执行者自报。
**写不出可观察断言的 skill 不允许交稿。**

## 第 6 步：契约

写在 SKILL.md 的「契约」一节，四项都要有，缺项写「无」并说明为什么：
前置条件（环境态：App 在前台、已登录、网络通；输入合法性）/ 后置条件（= 成功判定）/ 副作用（对外可见的改变、写了哪些数据）/ 失败模式（无匹配、多义匹配、风控限流、已做过、坐标漂移）。

## 第 7 步：熟化状态块

放在标题下第一段，按「熟化四态」（发现 → 蒸馏 → 固化候选 → 代码化）：

```
> **熟化：蒸馏**（首次沉淀 · 来源 run <run_id> · 更新 MMDD）
> 判例计数：<坑的简称> ×1；……　（同一判例第 2 次标「固化候选」，第 3 次必须开开发任务写成代码并从本 skill 删掉该条）
```

把探路交付物里的 `findings` 逐条写进「坑」一节，并登记到判例计数。

## 交付物（最后只输出这一个 JSON）

```json
{
  "stage": "distill",
  "action": "new | update",
  "skill_name": "kebab-case 名，与已有 skill 不重名",
  "target_path": "zenithjoy-skills 里的目标路径",
  "layer": "base | platform | business",
  "dedup": {"checked": ["查过的位置"], "unreachable": [], "merged_into": null, "reuses": ["引用的已有 skill"]},
  "split_decision": "不拆 / 拆出了什么，依据哪一条",
  "status": "ok | rejected",
  "run_id": "来源运行的 run_id",
  "success_criteria": [{"claim": "可观察断言，与草稿「成功判定」逐字一致", "evidence": "来源运行里能证明它的证据ID"}],
  "draft_markdown": "action=new 时：完整 SKILL.md 文本；action=update 时：留空",
  "patch": "action=update 时：对目标文件的 unified diff；action=new 时：留空",
  "open_questions": ["需要人或下一步确认的点"]
}
```

`success_criteria` 为空 → 不得交稿（`status=rejected`）。判例计数由上架阶段写入、熟化阶段按计数开任务；本 skill 只负责把 findings 如实登记为 ×1 或在原计数上 +1。

## 本 skill 自身的失败模式

| 情况 | 处理 |
|---|---|
| 第 0 步任一检查不过 | `status=rejected`，不产出草稿 |
| 轨迹里除了绕路没有有效步骤 | `status=rejected`，写明「无可提炼的成功路径」 |
| 查到多个都像是同一件事的已有 skill | `action=update` 指向最接近的一个，其余写进 open_questions |
| 写不出任何可观察的成功判定 | `status=rejected` |

## SKILL.md 草稿骨架

```
---
name: <名字>
layer: <base|platform|business>
description: |
  <做什么；触发场景；不适用场景>
---
> **熟化：…**（见第 7 步）

# <标题>

## 前置与设备
## 步骤
| # | 前置 | 动作 | 完成判据 | 证据 | 失败处理 |
## 成功判定
## 契约
## 坑
```
