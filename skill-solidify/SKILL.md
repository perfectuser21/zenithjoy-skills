---
name: skill-solidify
version: 1.1.0
updated: 2026-10-14
description: |
  固化判定：沉淀后连续通过 K 次（固化前 K=30）的 activity 链，逐步判定「写成代码」还是「留给 AI」，给出优先级、探针和开发任务草稿。只判不写代码——代码由 Claude Code /dev 写，上线前按独立代码核验契约，由另一会话用 run-verify 核验。技能工厂五阶段第⑤步「固化」的判定段，决策 ca9f3d7b / 28ca1f69 / 5826ddd7 / 6ec463c3。
  触发：任务里写「阶段：固化判定」「使用 skill：skill-solidify」、哪些步骤该写成代码、固化判定。
  不适用：没跑满 K 次的链（先跑满）；写代码本身（/dev）；独立核验代码（另开 run-verify 会话）。
---

> **语言规则：所有输出简体中文。**

# 固化判定 skill-solidify

固化不是把整条链改成代码，而是**逐步**判断：哪些步写成代码，哪些步永远留给 AI。代码写完后 AI 兜底路径**永不删除**。

Brain 地址：`BRAIN=${BRAIN_URL:-http://100.79.41.61:5221}`。本 skill 只读、只输出 JSON。

## 第 0 步：核对输入（不过就停）

| 检查 | 不通过时 |
|---|---|
| 沉淀后重跑的阶段任务：`python3 bin/count_streak.py --stage-task <阶段任务 id>` 输出 `reached=true`（固化前 K=30，以任务给的值为准） | `status=rejected`，贴计数输出 |
| 能逐张读到这些运行的执行单交付（每步的动作、到达页面、证据、成败）和审计单判定 | 读不到的运行列进 `unreadable`；可读的不足 K 条 → `status=rejected` |
| 拿到 activity 链（每个 activity 的步骤 skill 与 Steps 表） | `status=rejected` |

## 证据归集（执行规则 v1）

使用正式运行账的 `activity_definition_version_id`、`implementation {kind,id,version,digest}`、`environment {id,fingerprint}` 归集；保留 `execution_role=primary/fallback/rescue` 与真实 `observed`。`verification_ref` 仅指向正式独立核验任务，禁止自填PASS。Skill独立成功、Code独立成功、救场与失败分开；只改B不得清掉A/C证据。次数仅作证据，缺观测、混版本、救场不得自动晋级Code。

需求变化先更新并验证配套Skill，再固化Code；同业务要求的已验证Skill可先用。原Skill、判据与AI兜底路径保留；代码失败可交当前环境验收过的配套Skill，禁止无依据换不兼容旧业务版本。运行救场只完成本次任务，代码改进另建开发任务。

## 第 1 步：逐步统计

对链里每一步，从 K 次运行里数出：

| 指标 | 怎么数 |
|---|---|
| 频率 | 这一步在 K 次里出现了几次 |
| 失败率 | 这一步失败（含重试后才过）的次数 ÷ 出现次数 |
| 形状 | 每次走的「前置页面 → 动作（控件文字）→ 到达页面」是否一致；不一致的列出有几种 |
| 最近有没有新分支 | 最近 10 次里是否出现前面没出现过的形状 |
| 完成判据能否机械观测 | 判据是否只靠前台包名 / 页面标题 / 控件文字 / 数据记录就能判，不需要看图理解或语义判断 |
| 是不是不可逆写入 | 点赞、发送、发布、私信、写生产表、花钱 |

## 第 2 步：贴标签

| 标签 | 条件（决策 ca9f3d7b / 28ca1f69） |
|---|---|
| `code` | **三条同时满足**：①形状跨多次重复（K 次只有一种形状）；②变体已探明（最近 10 次无新分支）；③坏了能当场发现（完成判据能机械观测，能写成探针） |
| `code_required` | 不可逆写入的动作本身：永远走代码（序列写进代码，定位按 registry 现场取），并且 ①②③ 也要满足；不满足就标 `blocked` 写清差哪条，**不得留给 AI 临场点** |
| `ai` | 判断「这一步干成没有」而事实观测不到的；需要看图、理解语义的；形状每次不一样的 |
| `ai_for_now` | 本可写代码但 ①②③ 有一条不满足（写明差哪条，下一轮 K 次后再判） |

两条硬规矩：

- **判定层永远不写死**：只有事实能机械观测时，后置条件才是纯代码；观测不到的永远走视觉 / AI。
- **代码里不写坐标**：序列固化进代码，定位存 registry（键 = 机型 | App 版本 | 屏幕密度），registry 是数据不是代码。

## 第 3 步：排优先级

`code` / `code_required` 的步骤按 **频率 × 失败率** 从高到低排——最该先固化的是 AI 最容易点飞、又跑得多的那段，不是最常跑的那段。前后相连的几步可以合成一个开发任务，前半段先固化、后半段仍留 AI 是正常的。

## 第 4 步：每个要写代码的步，给出探针与开发任务草稿

| 字段 | 写什么 |
|---|---|
| 探针（后置条件） | 可机械检查的一条断言，就是该步完成判据的代码版；**没有探针不许固化** |
| 反向退化 | 代码上线后，同一段 N 天内碎 K 次就退回 AI（建议 7 天内 3 次，写进任务） |
| AI 兜底 | 代码判不了 / 失败时退回哪个步骤 skill 的哪一步，必须写明，兜底路径永不删 |
| 判据进契约 | 判据不从步骤 skill 里删，同时写进契约 |
| 开发任务草稿 | 标题、要改的仓库与文件（如 zenithjoy-workspace 的控制器 / 脚本）、验收（探针报红一次再变绿）、转码核验（上线前按独立代码核验契约另开 run-verify 会话） |

## 交付物（最后只输出这一个 JSON）

```json
{
  "stage": "solidify",
  "status": "ok | rejected",
  "flow_name": "",
  "capability_key": "",
  "streak": {"stage_task": "", "k": 30, "reached": true},
  "runs_read": 30,
  "unreadable": [],
  "steps": [
    {"activity_key": "", "step_key": "", "frequency": 30, "failure_rate": 0.0, "shapes": 1, "new_branch_recent10": false,
     "mechanically_observable": true, "irreversible_write": false,
     "tag": "code | code_required | ai | ai_for_now | blocked", "reason": "满足 / 不满足 ①②③ 中哪几条，依据",
     "priority_score": 0.0, "probe": "后置条件断言（code / code_required 必填）", "ai_fallback": "退回哪个步骤 skill 哪一步"}
  ],
  "dev_task_drafts": [
    {"title": "", "repo": "zenithjoy-workspace", "steps": ["activity_key.step_key"], "files": [], "probe": "",
     "degrade_rule": "7 天内碎 3 次退回 AI", "acceptance": ["探针先报红一次再变绿", "上线前 run-verify 独立代码核验通过"]}
  ],
  "handover": ["开发任务由有头会话走 /dev 建单执行；写代码的会话不得自己核验"],
  "open_questions": []
}
```

`dev_task_drafts` 只出草稿；本 skill 不建任务、不写代码。

## 独立代码核验契约（替代退役入口，v1）

1. `/dev` 完成代码与永久回归；另建独立运行/核验任务，核验会话使用现有 `run-verify`，不加载已退役的转码核验入口，不读取开发会话，不修改代码或直接部署。
2. 固定材料必须包含业务要求与配套Skill版本、Activity定义、实现源码SHA及字节摘要、输入哈希、当前环境与依赖、run/attempt、验收标准、原始产物、动作记录、清理证据，以及同一永久回归故意破坏时报红、恢复时报绿的独立证据。
3. 独立核验逐项读原始来源和真实产出，确认合同中的判据实际执行，按固定task/run/attempt/definition摘要输出断言与证据；缺证据判INCONCLUSIVE，真实业务失败保持FAIL。缺观测或只有文件名/进程退出码/执行者自报不得PASS。
4. Code独立成功才能获得Code晋级证据；配套Skill成功或Commander救场不替代Code验收。结果未知先读回，不能重放对外动作；清理另列断言。
5. 开发检查通过、PR合并、部署读回与独立业务PASS分开留痕；具备该核验合同不表示某版本已通过，更不授予修改生产稳定指针的权限。

## 之后

- 有头会话按草稿走 `/dev` 写代码与探针；上线前本工位另开会话用 `run-verify` 按下方独立代码核验契约核验判据确实被执行。
- 步骤写成代码后 Commander 能否从这一步退场、整条流程何时降为异常召唤，按决策 0eb64294（待拍板）执行；拍板前 Commander 仍按 `wf-<能力>` 陪跑。
