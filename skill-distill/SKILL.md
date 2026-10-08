---
name: skill-distill
description: |
  沉淀：把验证阶段连续通过 K 次的冻结整流程 skill vN，按探索摸到的边界拆成 activity 链，并产出给 Commander 的 wf-<能力> 陪跑 skill——先查重引用，再逐个 activity 写说明书和步骤 skill（每步 DoD、故障处置、成功判定、契约），声明拆完须重新连续通过 K 次。技能工厂五阶段（试跑→探索→验证→沉淀→固化）的第④步，决策 5826ddd7 / 1b469079。
  触发：任务里写「阶段：沉淀」「使用 skill：skill-distill」、把这个跑稳的整流程拆成 activity、写成 skill。
  与 Claude Code 的 skill-creator 关系：本 skill 是「写什么」的规范（两边通用）；skill-creator 负责 Claude Code 侧的评测与发布流程，其 ZenithJoy 规则引用本规范。
  不适用：验证没达标的整流程 skill（不沉淀，只记坑）；验收已写好的 skill（用 contract-reviewer / skill-evaluator）。
---

> **语言规则：所有输出简体中文。**

# 沉淀 skill-distill

输入是一个**验证阶段已达标的冻结整流程 skill vN**，加上探索期摸出的**边界清单**和**故障处置表**；输出两样东西：

1. **activity 链**：每个 activity 一份说明书 + 一份步骤 skill 草稿；
2. **`wf-<能力>`**：给 Commander（work-commander）陪跑这条流程用的 skill 草稿。

你不上架、不合并、不登记，只交草稿。

**为什么第一次沉淀就拆**：先证明整流程稳定（验证阶段连续通过），再拆；拆完以后出问题，才能归因于"拆分"本身。所以这里不再有"第一次默认不拆"。

**副作用**：本 skill 只读、只输出 JSON，**不写任何文件、不提 PR**；落盘、提 PR、把 Activity / Step 登记进树与仓库，都由上架阶段（skill-publish）完成。注意 `patch` 可被下游直接应用，上架阶段必须先过验收（contract-reviewer 无致命项）才能应用。

## 第 0 步：核对输入（不过就停）

| 检查 | 不通过时 |
|---|---|
| 验证记录：Brain 交给你的 run-verify 独立会话产出的 `verdict=pass` 记录，连续条数 ≥ K（K 以 Brain 任务给的值为准；决策 6ec463c3：验证阶段 K=10），且每条的 `skill` 都是**同一个冻结版本** vN、`input` 互不相同、`slice_digest`（加载的处置表片指纹）一致 | 停止，`status=rejected`，写明「验证未达标 / 版本不一致 / 输入重复 / 处置表变过」 |
| 验证结论不是你在本会话里自己得出的 | 停止，`status=rejected`，写明「验证结论不独立」 |
| 探索交付物：边界清单逐项都有结论（输入类、故障类必须有结论；平台惩罚类不主动触发，可记「未遇到」） | 停止，`status=rejected`，写明哪项没结论 |
| 查重要用的目录能访问 | 部分不可访问：继续，在 `dedup.unreachable` 列出，并加一条 open_question「可能与未查到的位置重复」；**技能库根目录不可访问或三处全不可访问：停止，`status=rejected`** |

## 你拿到的材料

| 材料 | 来源 |
|---|---|
| 冻结整流程 skill vN | 验证阶段一直在跑的那个版本（含「依赖对象」与「故障处置」两节） |
| 验证记录 | K 条 run-verify 的 JSON（`verdict=pass`） |
| 探索交付物 | 摸边界的交付物：边界清单、处置表候选行、平台发现、手册素材、候选改进 |
| 试跑交付物 | skill-explore 输出的 JSON（`trajectory` / `final_evidence` / `findings`） |
| 工坊提案（可能有） | OpenClaw Skill 工坊针对这次运行自动写的 PROPOSAL.md |

## 第 1 步：查重引用——能引用就不新建

依次搜，找同一件事或同一段动作：

1. 技能库 `zenithjoy-skills` 根目录的 skill（name / description / 正文关键词）
2. 技能库 `openclaw/*/skills/` 与各 OpenClaw agent 工位里的 skill
3. OpenClaw 工坊提案目录里的同类提案

| 查到 | 处理 |
|---|---|
| 已有 skill 做的就是这件事 | **不新建**，产出对它的修改（补步骤、补坑、更新熟化计数），**以补丁形式交付**，不整篇重写 |
| 已有 skill 覆盖其中一段 | 新 skill 引用它，不复制那一段 |
| 都没有 | 新建；`skill_name` 必须与所有已查位置里的 skill 名都不相同（同名不同实现也算冲突，换名） |

## 第 2 步：归层与拆成 activity 链

**归层**（写进 frontmatter 的 `layer`，每个 activity 各自归层）：

| 层 | 放什么 |
|---|---|
| 底座 base | 所有平台、所有业务都要守的规矩（锁、拟人、定位三层） |
| 平台 platform | 某个平台上的动作，与业务无关（抖音搜索、打开评论区、朋友圈点赞动作本身） |
| 业务 business | 一个业务结果的阶段与业务判断（获客：哪条评论算有意向） |

**怎么拆成 activity**（第一次沉淀就拆）：

1. **切分依据**：探索摸到的边界，加上树的统一标准。Activity 的认定只用 `/tree`（决策 0cee5452），不另立一套：
   - ①交接：换执行者，或要等待，就是边界；
   - ②结果：有业务可见、可读回验收的结果，是 Activity；否则是 Step；
   - ③重试：能单独重跑，是 Activity。

   拿不准时用问题二：做到这里，有没有明确输入、交出能验收的结果，且后面失败可以从这里重来？有 → Activity 终点；没有 → Step。
2. **风险等级不同的段不放进同一个 activity**（只读 vs 对外可见 / 不可撤回）。
3. **不要把 Step 抬成 Activity**：不为"每一段都能单独管"而拆；颗粒度更细的留在 Step 层（第 3 步）。activity 内部切步骤时，可用四个问题自查：出问题要不要知道是它、会不会改变外部世界、会不会单独关掉或重试、是不是交接点。
4. 每个 activity 产出两份东西：**说明书**（`activity_spec`，对应树上 Activity 的列）和**步骤 skill 草稿**（对应树上的 Step）。

**抽成跨流程共用件**（这是另一件事，别和上面混）：只有**已经存在**≥2 个流程用到同一段，才抽成共用的；只算已发生的，不算预测。第一次出现的段留在本流程里，等第二个流程用到时再搬进仓库。

## 第 3 步：提炼步骤（每个 activity 内部）

- 一步 = **一次页面状态变化**，不是一次点击。
- 从试跑的 `trajectory` 里删掉 `detour: true` 的绕路与重试，只留成功路径；以冻结 vN 的步骤为准。
- 必须切出一步的地方：进入新页面；对外动作**之前**（确认对象选对）；对外动作**之后**（确认生效）。

## 第 4 步：每一步写 DoD 五个字段

| 字段 | 规矩 |
|---|---|
| 前置 | 这一步开始时应在哪个页面；不在就先回退，不硬点 |
| 动作 | 找哪个控件（写文字 / content-desc），做什么；**禁止写坐标** |
| 完成判据 | 写**状态**不写动作（「出现『朋友圈』标题」，不是「点了发现」）；必须可观察（前台包名 / 页面标题 / 控件文字 / 截图特征）；对外动作那一步加**反向检查**（如「菜单显示『赞』而不是『取消』」） |
| 证据 | 截图或控件树，证据 ID 带步号与时间 |
| 失败处理 | **引用故障处置表的行**，不在步骤里写死次数和秒数；**对外动作失败一律停止，不重试** |

## 第 5 步：故障处置拆进链里

整流程 skill 里的「故障处置」一节，按归属拆开，格式沿用树上 Activity `failure` 已有的四分类：

| 四分类 | 含义 | 例子 |
|---|---|---|
| `empty_ok` | 本来就没有，正常结束，不算失败 | 页面明确写着「暂无结果」 |
| `retryable` | 可重试，带参数：等多久、重试几次、重试前做什么、还不行怎么办 | 目标暂时没出来：等 5 秒、重试 3 次 |
| `fatal` | 致命，立即停 | 账号不对；对外动作失败 |
| `needs_human` | 要人介入 | 没见过的弹窗；风控 |

| 行属于 | 拆到 |
|---|---|
| 只和某个 activity 有关 | 该 activity 的 `activity_spec.failure` |
| 只和某一步有关 | 该步的 `on_fail` |
| 和平台或通用对象有关（网络、设备锁、抖音搜索…） | 不拆进本流程，写进 `platform_findings`，由上架阶段登记到仓库对应物件的 `failure_semantics`；本流程只引用 |

探索里的其余边界结论：经验、判断依据写进 `handbook_seed`，不塞进步骤 skill。

## 第 6 步：成功判定（必写）

- 每个 activity 一份：成功长什么样（一到三条可观察断言）、哪张截图 / 哪条记录能证明、由谁判（run-verify 独立判定，不由执行者自报）。
- 整条链再写一份端到端的成功判定，与冻结版本 vN 的成功判定一致。

**写不出可观察断言的 skill 不允许交稿。**

## 第 7 步：契约

每个 activity 的 SKILL.md 里写「契约」一节，四项都要有，缺项写「无」并说明为什么：
前置条件（环境态：App 在前台、已登录、网络通；输入合法性）/ 后置条件（= 成功判定）/ 副作用（对外可见的改变、写了哪些数据）/ 失败模式（引用第 5 步的四分类）。另列**依赖对象**：本 activity 用到的通用与平台对象（网络、设备锁、adb、抖音搜索…），运行时按这张清单加载处置表的相关行。

## 第 8 步：写给 Commander 的 wf-<能力>

`<能力>` 用树上该能力的 key。内容只服务陪跑，不重复步骤细节：

| 节 | 写什么 |
|---|---|
| 链路 | activity 顺序；每个 activity 的正常状态长什么样、时长预算、交接物 |
| 诊断 | 每次失败归哪一类，决定计数怎么走：外部原因（作废，不计数不清零）／错误（改版，清零）／拆分本身的问题（回沉淀修拆分）／优化（记入候选改进）／表外故障（停下截图上报，登记候选行） |
| 处置权限 | 按 COMMANDER.md 三档：自动做／Bark 请示／只报不做 |
| 流程手册 | 由 `handbook_seed` 整理：经验、踩坑、判断依据 |
| 回流 | 某个 activity 坏了（平台改版、页面变）→ 只回流该 activity 到探索；整条走法变了 → 回试跑（决策 9b3b027b） |

## 第 9 步：熟化状态块

每个步骤 skill 标题下第一段，按「熟化四态」（发现 → 蒸馏 → 固化候选 → 代码化）：

```
> **熟化：蒸馏**（首次沉淀 · 来源 冻结版本 <skill>@<vN> · 更新 MMDD）
> 判例计数：<坑的简称> ×1；……　（同一判例第 2 次标「固化候选」，第 3 次必须开开发任务写成代码并从本 skill 删掉该条）
```

把试跑与探索里的 `findings` 逐条写进「坑」一节，并登记到判例计数。

## 第 10 步：声明重新验证

activity 链拆开后，视为一个新版本，**必须重新连续通过 K 次**才进固化阶段（决策 6ec463c3：固化前 K=30；以 Brain 任务给的值为准）。这 K 次在上架登记完成后，由 work-commander 加载 `workflow-commander` + 本流程的 `wf-<能力>` 陪跑，在测试账号、测试手机上跑。

本 skill 只在交付物 `rerun` 里声明，不负责跑。

## 交付物（最后只输出这一个 JSON）

```json
{
  "stage": "distill",
  "flow_name": "整流程名",
  "capability_key": "树上该能力的 key",
  "status": "ok | rejected",
  "source": {
    "frozen_skill": "<skill>@<vN>",
    "verify_run_ids": ["验证记录里的 run_id"],
    "slice_digest": "验证时加载的处置表片指纹"
  },
  "dedup": {"checked": ["查过的位置"], "unreachable": [], "reuses": ["引用的已有 skill"]},
  "chain": ["activity_key，按流程顺序"],
  "activities": [
    {
      "activity_key": "kebab-case，链内唯一",
      "activity_spec": {
        "promise": "一句话承诺",
        "inputs": "明确的输入",
        "outputs": "交出的、能验收的结果",
        "preconditions": "开始前必须成立的环境态",
        "failure": {"empty_ok": [], "retryable": [], "fatal": [], "needs_human": []},
        "readback": "怎么读回验收（与草稿「成功判定」一致）",
        "uses": ["依赖的仓库对象 key"]
      },
      "split_basis": "按交接 / 结果 / 重试哪几条认定为 activity；拿不准时问题二的答案",
      "action": "new | update",
      "skill_name": "kebab-case 名，与已有 skill 不重名",
      "target_path": "zenithjoy-skills 里的目标路径",
      "layer": "base | platform | business",
      "success_criteria": [{"claim": "可观察断言，与草稿「成功判定」逐字一致", "evidence": "来源运行里能证明它的证据ID"}],
      "draft_markdown": "action=new 时：完整 SKILL.md 文本；action=update 时：留空",
      "patch": "action=update 时：对目标文件的 unified diff；action=new 时：留空"
    }
  ],
  "end_to_end_success_criteria": [{"claim": "整条链的可观察断言", "evidence": "证据ID"}],
  "wf_skill": {"skill_name": "wf-<能力>", "draft_markdown": "给 Commander 的陪跑 skill 全文"},
  "handbook_seed": ["流程手册种子：经验、踩坑、判断依据"],
  "platform_findings": [{"object": "仓库对象 key", "row": "处置表候选行", "evidence": "证据ID"}],
  "rerun": {"k": 30, "against": "拆分后的整条 activity 链", "basis": "决策 6ec463c3；以 Brain 任务给的值为准"},
  "open_questions": ["需要人或下一步确认的点"]
}
```

任一 activity 的 `success_criteria` 为空、`end_to_end_success_criteria` 为空，或 `wf_skill.draft_markdown` 为空 → 不得交稿（`status=rejected`）。判例计数由上架阶段写入、熟化阶段按计数开任务；本 skill 只负责把 findings 如实登记为 ×1 或在原计数上 +1。

## 本 skill 自身的失败模式

| 情况 | 处理 |
|---|---|
| 第 0 步任一检查不过 | `status=rejected`，不产出草稿 |
| 试跑 trajectory 里除了绕路没有有效步骤 | `status=rejected`，写明「无可提炼的成功路径」 |
| 查到多个都像是同一件事的已有 skill | `action=update` 指向最接近的一个，其余写进 open_questions |
| 写不出任何可观察的成功判定 | `status=rejected` |
| 按三测试 / 问题二切不出一个以上 activity（整条流程就是一个 Activity） | 不硬拆：`chain` 只放一个 activity，`split_basis` 写明依据；`wf_skill` 照写 |

## 步骤 skill 草稿骨架（每个 activity 一份）

```
---
name: <名字>
layer: <base|platform|business>
description: |
  <做什么；触发场景；不适用场景>
---
> **熟化：…**（见第 9 步）

# <标题>

## 说明书
承诺 / 输入 / 输出 / 前置 / 读回 / 依赖对象
## 前置与设备
## 步骤
| # | 前置 | 动作 | 完成判据 | 证据 | 失败处理（引用处置表行） |
## 故障处置
| 四分类 | 现象 | 参数 / 处置 |
## 成功判定
## 契约
## 坑
```
