# W7 人形验收（合同 [BEHAVIOR] 剧本化）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **禁令（本 worktree 共享，违者事故）**：实施 subagent 只允许改文件+commit，**禁止 push / 开 PR / merge / 删 worktree / 切分支**——收尾由主 session 的 finishing → engine-ship 链统一做。

**Goal:** 把 harness 合同 [BEHAVIOR] 升级为五行人形剧本（动作/预期观察/等待预算/留证/Test:），evaluator 按步操作逐步留证 + 意外观察 findings + 探索层，reviewer 审剧本完整性与探索提示。

**Architecture:** 纯 skill 文本改动（zenithjoy-skills SSOT 三个 SKILL.md），零引擎依赖。Test: 保持必填单行以兼容 cecelia 三个机械闸（harness-contract-lint / promote-regression 收割 / judge 存在性正则）。verdict JSON 新增 findings[] 为 additive 字段（Brain Zod 非 strict，先例：unverifiable[]）。

**Tech Stack:** Markdown（SKILL.md）、本地验证用 node（cecelia 闸脚本）+ python3（lint-skills.py）。

**版本 bump:** proposer 9.16.0→9.17.0 / reviewer 9.7.0→9.8.0 / evaluator 1.32.2→1.33.0（各自 frontmatter `version:` + `updated: 2026-07-28` + changelog 顶部插一条）。

**Spec:** `docs/superpowers/specs/2026-07-28-w7-human-evaluator-design.md`

---

### Task 1: proposer 9.17.0 — 五行剧本格式 + 探索提示段 + 接缝标注 + 正反例

**Files:**
- Modify: `harness-contract-proposer/SKILL.md`（frontmatter 第 7 行 version、第 9 行 updated、changelog 顶部、`## ⚡ 三段式 [BEHAVIOR] 剧本格式（v9.14 新增）` 整段，约 317-370 行）

- [ ] **Step 1: 改 frontmatter + changelog**

`version: 9.16.0` → `version: 9.17.0`；`updated: 2026-07-17` → `updated: 2026-07-28`；changelog 列表最顶部（`- 9.16.0:` 之前）插入：

```yaml
  - 9.17.0: W7 人形验收（RD 2026-07-28，决策 d3021871）——三段式升级五行剧本：每条新写 [BEHAVIOR] 必含 动作/预期观察/等待预算/留证/Test: 五行；Test: 强制单行（长命令 bash -c 包裹，修 #149 多行验证命令被 promote-regression 收割成 cmd="bash" 隐患）；新增 ## 探索提示 合同段模板（L3 探索层输入，默认预算 10 分钟/15 动作）；接缝步骤（真机/异步/第三方）标 [接缝×2] 由 evaluator 重复执行判 FLAKY；补同步/异步正例各一 + 旧命令行长相/缺等待预算反例各一；legacy 标记条目继续豁免
```

- [ ] **Step 2: 用下面全文替换 `## ⚡ 三段式 [BEHAVIOR] 剧本格式（v9.14 新增）` 整段**

替换范围：从 `## ⚡ 三段式 [BEHAVIOR] 剧本格式（v9.14 新增）` 标题行起，到 `## ⚡ 锚定父路声明（硬规则 — v9.13 新增）` 标题行之前（含原 until-loop、样例剧本、legacy 小节及末尾 `---` 分隔线）。替换为：

````markdown
## ⚡ 五行剧本 [BEHAVIOR] 格式（v9.17 — W7 人形验收，替代 v9.14 三段式）

**每条新写 [BEHAVIOR] 必须是五行剧本，缺任一行 Reviewer 打回（[legacy] 标记条目豁免）：**

```
- [ ] [BEHAVIOR] [L1|L2|L3] B-NN: <步骤名>（接缝步骤加标注 [接缝×2]）
  动作: <人做什么——点/发/调/等>
  预期观察: <人应该看到什么——消息到达/页面变化/DB出现记录>
  等待预算: <N>s（超时=FAIL；同步观察写 0s）
  留证: <截图路径 / 命令输出 / DB查询结果>
  Test: manual:bash <单行验证命令>
```

| 行 | 说明 |
|---|---|
| 动作 | 用户/系统执行的操作步骤（点击/发送/调用等），evaluator 照此真实执行 |
| 预期观察 | 用户或系统可见的状态变化，evaluator 在预算内轮询观察 |
| 等待预算 | 最多等多久（如 `30s`）；超时未观察到 = 该条 FAIL；同步观察写 `0s` |
| 留证 | evaluator 必须采集的证据：截图存 `${SPRINT_DIR}/screenshots/`，命令输出/DB 查询结果进 behavior_tests.log_tail |
| Test | 机器可跑断言，**必须单行完整命令**（见下）|

### Test: 单行铁律（机械闸兼容）

**Test: 行必须是单行完整命令**——三个机械闸都按单行解析：
- cecelia `harness-contract-lint.mjs`：缺 Test: = MISSING_TEST 红
- cecelia `harness-promote-regression.js`：`Test:\s*manual:(.+)$` 单行收割进回归合同——多行写法只收割到首词（如 `bash`），产出假绿回归条目（#149 实证隐患）
- until-loop 等长命令用 `bash -c '...'` 包成单行

```bash
# ✅ 异步 until-loop 单行范式（within 60s 等待预算）
Test: manual:bash bash -c 'DEADLINE=$((SECONDS+60)); until psql "$DB_URL" -tAc "SELECT 1 FROM messages WHERE type='"'"'settings_notify'"'"' AND created_at > NOW()-INTERVAL '"'"'5m'"'"'" | grep -q 1; do [ $SECONDS -lt $DEADLINE ] || { echo "FAIL: within 60s 未收到消息"; exit 1; }; sleep 2; done; echo "OK: within 60s 收到消息确认"'
```

### 正例（两条完整剧本）

**正例 1 — 同步观察（UI 交互类）：**

```
- [ ] [BEHAVIOR] [L2] B-01: 保存设置后页面出现成功提示
  动作: 在设置页填写通知开关=开，点击「保存」按钮
  预期观察: 页面立即出现「保存成功」toast，且设置项保持为开
  等待预算: 0s
  留证: ${SPRINT_DIR}/screenshots/b01-save-toast.png + DB 查询输出
  Test: manual:bash bash -c 'curl -sf localhost:5221/api/settings | jq -e ".notify_enabled==true"'
```

**正例 2 — 异步等待（消息推送类）：**

```
- [ ] [BEHAVIOR] [L2] B-02: 点设置触发消息推送，within 60s 收到确认 [接缝×2]
  动作: 调用 POST /api/settings/save 保存配置
  预期观察: within 60s 消息表出现 settings_notify 新条目，用户侧收到推送确认
  等待预算: 60s
  留证: until-loop 命令输出末 5 行（含 OK 行）
  Test: manual:bash bash -c 'DEADLINE=$((SECONDS+60)); until psql "$DB_URL" -tAc "SELECT 1 FROM messages WHERE type='"'"'settings_notify'"'"'" | grep -q 1; do [ $SECONDS -lt $DEADLINE ] || { echo FAIL; exit 1; }; sleep 2; done; echo OK'
```

### 反例（禁止写法）

**反例 1 — 旧命令行长相（缺全部剧本行）→ Reviewer 第 1 维打回：**

```
- [ ] [BEHAVIOR] [L2] 检查接口响应 Test: manual:bash curl -sf localhost:5221/api/ping | jq -e '.ok==true'
```

（无 动作/预期观察/等待预算/留证——这是把验收塑造回脚本级的病根。存量合同里这种写法必须带 `[legacy]` 标记才豁免。）

**反例 2 — 异步观察缺等待预算 → Reviewer 第 1 维打回：**

```
- [ ] [BEHAVIOR] [L2] B-03: 任务完成后收到通知
  动作: 触发任务执行
  预期观察: 收到完成通知
  留证: 命令输出
  Test: manual:bash bash -c 'psql "$DB_URL" -tAc "SELECT 1 FROM notifications" | grep -q 1'
```

（异步观察没写等多久 = evaluator 无法判超时，FAIL 语义不确定。）

### 接缝步骤标注 [接缝×2]

步骤碰真实世界接缝（真机 UIA/RPA、异步消息、第三方 API）→ 步骤名后标 `[接缝×2]`，evaluator 将重复执行 2 次，两次不一致 → 直接判 FLAKY 上报（flaky 即 bug）。**只标可重复执行的步骤**：动作不幂等且合同写不出重置方式的，不标（单次执行），并在留证行写明原因。

### legacy 兼容标记

存量纯命令写法（未含剧本行）保留有效，但标 `[legacy]`，不强制迁移——新写条目必须五行剧本：

```
- [ ] [BEHAVIOR] [L2] [legacy] 检查接口响应 Test: manual:bash curl -sf localhost:5221/api/ping | jq -e '.ok==true'
```

---

## ⚡ 探索提示合同段（v9.17 — L3 探索层输入）

**contract-draft.md 必须含独立二级段 `## 探索提示`**（平级标题，**禁止塞进 `## E2E 验收` 段内部**——会截断 evaluator 的 E2E 脚本提取）。evaluator 在剧本全过后按此段做带预算的自由测试。模板：

```markdown
## 探索提示（L3 探索层 — evaluator 剧本全过后执行）

探索预算: 10 分钟 / 15 动作（默认；高风险 sprint 可调大，写明理由）
高风险面:
- 错输入: <具体字段/接口 + 非法值，如 POST /api/settings 传 notify_enabled="abc">
- 重复提交: <可连点/重发的入口，如 连点两次「保存」>
- 中途中断: <刷新/返回重进/杀进程的位置，如 保存进行中刷新页面>
- 边界值: <数值/长度/时间边界，如 标题 0 字符 / 10000 字符>
发现分级: P0/P1（丢数据/直接面客错误）→ 阻塞 merge；P2/P3 → 记 findings 不阻塞
```

高风险面条目由 Proposer 起草、GAN Reviewer 审查补充（Reviewer 发现缺口时在 feedback 里直接给出条目文本）。

---
````

- [ ] **Step 3: 本地验证**

```bash
cd /Users/administrator/worktrees/zenithjoy-skills/w7-human-evaluator
python3 .github/workflows/scripts/lint-skills.py
grep -c "五行剧本" harness-contract-proposer/SKILL.md   # 期望 ≥2
grep -n "接缝×2" harness-contract-proposer/SKILL.md | head -3   # 期望有命中
grep -n "## 探索提示" harness-contract-proposer/SKILL.md | head -2   # 期望有命中
```

Expected: lint 输出无 error；三个 grep 均有命中。

- [ ] **Step 4: Commit**

```bash
git add harness-contract-proposer/SKILL.md
git commit -m "feat(proposer): 9.17.0 五行剧本 [BEHAVIOR] + 探索提示段 + 接缝×2 标注 [38c0c94e]"
```

---

### Task 2: reviewer 9.8.0 — 剧本完整性 + 探索提示覆盖两条审查规则

**Files:**
- Modify: `harness-contract-reviewer/SKILL.md`（frontmatter version/updated、changelog 顶部、「Golden Path 覆盖审查」段末尾追加第 20/21 条）

- [ ] **Step 1: 改 frontmatter + changelog**

`version: 9.7.0` → `version: 9.8.0`；`updated:` 改 `2026-07-28`；changelog 顶部（`- 9.7.0:` 之前）插入：

```yaml
  - 9.8.0: W7 人形验收（RD 2026-07-28，决策 d3021871，与 proposer 9.17.0 配套）——Golden Path 覆盖审查新增第 20 条（新写 [BEHAVIOR] 缺 动作/预期观察/等待预算/留证 任一行或 Test: 非单行完整命令 → 第 1 维 dod_machineability 打回；[legacy] 标记条目豁免）+ 第 21 条（合同缺 ## 探索提示 段，或错输入/重复提交/中途中断/边界值明显适用却未覆盖 → 第 6 维低分打回，feedback 必须直接给出建议的探索提示条目文本供 proposer 原样填入）；7 个维度名不动（ReviewerOutputSchema 接口约定）
```

- [ ] **Step 2: 定位「Golden Path 覆盖审查」段的第 19 条（grep -n "第 19 条\|(19)" 找锚点），在该条之后、下一个二级标题之前追加：**

```markdown
20. **五行剧本完整性（W7 人形验收 — proposer 9.17.0 五行剧本格式）**：每条**新写** [BEHAVIOR]（无 `[legacy]` 标记）缺 `动作:`/`预期观察:`/`等待预算:`/`留证:` 任一行，或 `Test:` 不是单行完整命令（命令体折到后续行 = promote-regression 只收割到首词，产出假绿回归条目）→ 第 1 维 dod_machineability 打回 REVISION，feedback 指明缺哪行。异步观察类（预期观察含"收到/出现/推送/完成"等异步语义）等待预算写 `0s` 或缺失 → 同样打回。

21. **探索提示覆盖（W7 L3 探索层）**：合同缺独立二级段 `## 探索提示`，或其高风险面对本 sprint 明显适用却未覆盖（错输入/重复提交/中途中断/边界值四类逐一核对）→ 第 6 维低分打回。**feedback 必须直接给出建议的探索提示条目文本**（如"补：错输入 — POST /api/xxx 传非法枚举值"），供 proposer 原样填入——这是"探索提示由 GAN reviewer 写进合同"的落地方式，不许只说"覆盖不足"。
```

- [ ] **Step 3: 本地验证**

```bash
cd /Users/administrator/worktrees/zenithjoy-skills/w7-human-evaluator
python3 .github/workflows/scripts/lint-skills.py
grep -n "五行剧本完整性\|探索提示覆盖" harness-contract-reviewer/SKILL.md
grep -c "dod_machineability" harness-contract-reviewer/SKILL.md   # 期望比改前多 1（新增条引用了维度名但没改维度定义）
```

Expected: lint 无 error；两条新规则可 grep 到。

- [ ] **Step 4: Commit**

```bash
git add harness-contract-reviewer/SKILL.md
git commit -m "feat(reviewer): 9.8.0 剧本完整性+探索提示覆盖审查（W7 配套） [38c0c94e]"
```

---

### Task 3: evaluator 1.33.0 — 按步留证 + 意外观察 findings + 探索层 + FLAKY

**Files:**
- Modify: `harness-evaluator/SKILL.md`（frontmatter version/updated、changelog 顶部、约 1107-1130 行「behavior_tests 三段式剧本字段（v1.26 新增…）」小节整体升级、其后新增三个小节）

- [ ] **Step 1: 改 frontmatter + changelog**

`version: 1.32.2` → `version: 1.33.0`；`updated: 2026-07-26` → `updated: 2026-07-28`；changelog 顶部（`- 1.32.2:` 之前）插入：

```yaml
  - 1.33.0: W7 人形验收（RD 2026-07-28，决策 d3021871，与 proposer 9.17.0 配套）——L1 按步执行逐步留证（每条剧本：执行动作 → within 等待预算轮询预期观察 → 采集留证（截图/命令输出/DB结果）→ 跑 Test: 单行命令；behavior_tests 条目新增 wait_budget/evidence 字段）；L2 意外观察（执行中发现卡顿/报错/布局歪/慢响应必录 verdict 顶层 findings[] additive 字段 + SPRINT_DIR/findings.md，P0/P1 即使断言全绿也 FAIL）；L3 探索层（剧本全过后按合同 ## 探索提示 段自由测试，默认 10 分钟/15 动作，legacy 合同无此段则跳过）；[接缝×2] 步骤重复执行 2 次不一致 → FAIL 且 failed_step="FLAKY:<步骤名>"；SEGMENT_EVAL 段验与 [legacy] 条目按旧协议不变
```

- [ ] **Step 2: 把「behavior_tests 三段式剧本字段（v1.26 新增，与 proposer 9.14 配套）」小节（从该加粗行起、到「非三段式（legacy 格式）条目…」行止）替换为：**

````markdown
**behavior_tests 五行剧本字段（v1.33 — W7 人形验收，与 proposer 9.17 配套；v1.26 三段式的超集）**：合同条目含剧本格式时，behavior_tests 条目在 `command`/`exit_code`/`log_tail` 之上新增：

- `action`：剧本「动作」行，evaluator 实际执行的操作步骤（字符串）
- `expected`：剧本「预期观察」行，期望状态描述
- `wait_budget`：剧本「等待预算」行（如 `"60s"`；同步 `"0s"`）
- `evidence`：剧本「留证」行的实际产物（截图相对路径 或 命令输出/DB 查询结果摘要）

**L1 按步执行逐步留证（人形执行协议）**——每条剧本依序做四件事，全部条目过才 PASS：

1. **执行「动作」**：照动作行真实操作（调 API / Playwright 点击 / 发消息）
2. **在「等待预算」内轮询「预期观察」**：until-loop 轮询，预算耗尽未观察到 → 该条 FAIL（failed_step 写步骤名 + "等待预算 <N>s 超时"）
3. **采集「留证」**：截图存 `${SPRINT_DIR}/screenshots/`（mac_web 沿用 Step B-2.5 视觉自验），命令输出/DB 查询结果记入该条 `log_tail` 与 `evidence`
4. **跑 `Test:` 单行命令**：记录真实 `exit_code` + `log_tail`（EVA v2 E1 硬要求不变）

五行剧本示例条目：

```json
{
  "command": "bash -c 'until psql \"$DB_URL\" -tAc \"SELECT 1 FROM messages WHERE type='settings_notify'\" | grep -q 1; do sleep 2; done; echo OK'",
  "exit_code": 0,
  "log_tail": "OK: within 60s 收到消息确认",
  "verification_level": "L2",
  "action": "POST /api/settings/save",
  "expected": "within 60s 消息队列出现新条目",
  "wait_budget": "60s",
  "evidence": "screenshots/b02-notify.png"
}
```

三段式（v1.26）条目省略 `wait_budget`/`evidence`；`[legacy]` 条目只需 `command`/`exit_code`/`log_tail`——**存量合同按旧协议原样执行，不因缺剧本行 FAIL**（向后兼容）。

**FLAKY 判定（接缝步骤 ×2）**：步骤名带 `[接缝×2]` 标注的条目重复执行 2 次（动作+观察+Test 全流程）。两次结果不一致（exit_code 或关键观察不同）→ 整体 verdict FAIL，`failed_step` 写 `FLAKY:<步骤名>`，log_excerpt 附两次差异。flaky 即 bug，禁止取"较好的一次"。

**L2 意外观察（findings[] — 断言只回答问的问题，人还报告没人问的问题）**：执行任何步骤（含 L3 探索）时凡"不对劲"——卡顿、控制台报错、布局歪、慢响应、日志异常——**步骤照过，观察必留**：记入 verdict JSON 顶层 `findings[]` 数组（additive 字段，v1 消费方忽略未知字段无害，先例 `unverifiable[]`），同时落 `${SPRINT_DIR}/findings.md` 文件留证：

```json
{"verdict":"PASS","task_id":"$TASK_ID","attempt_id":"${HARNESS_ATTEMPT_ID:-}","findings":[{"severity":"P2","step":"B-01","observation":"保存按钮点击后 3s 才出 toast，页面无 loading 态","evidence":"screenshots/b01-save-toast.png"}], ...}
```

分级分流：`P0/P1`（丢数据/直接面客错误）→ **即使剧本断言全绿也整体 FAIL**（feedback 写明 finding）；`P2/P3` → 只记录不阻塞（report 阶段/人工落 issue）。

**L3 探索层（剧本全过后，带预算自由测试）**：剧本全部 PASS 后，读合同 `## 探索提示` 段执行自由测试——错输入/连点两次/中途刷新/返回重进/边界值，按段内高风险面逐条来，预算默认 **10 分钟/15 动作**（合同段内可调，以合同为准）。发现全部进 `findings[]`，分级分流同上（P0/P1 → FAIL 阻塞 merge）。合同无 `## 探索提示` 段（legacy 合同）→ 跳过 L3，verdict notes 注明"legacy 合同无探索提示段，L3 未执行"。**SEGMENT_EVAL 段级轻验收不跑 L2/L3**（段验维持机械断言，三层只作用于终验/总验——设计如此）。
````

- [ ] **Step 3: 本地验证**

```bash
cd /Users/administrator/worktrees/zenithjoy-skills/w7-human-evaluator
python3 .github/workflows/scripts/lint-skills.py
grep -n "findings\[\]\|FLAKY:\|L3 探索层\|wait_budget" harness-evaluator/SKILL.md | head -8
bash .github/workflows/scripts/check-brain-contract.sh
```

Expected: lint 无 error；四个关键词均命中；Brain 契约检查全 ✅。

- [ ] **Step 4: Commit**

```bash
git add harness-evaluator/SKILL.md
git commit -m "feat(evaluator): 1.33.0 按步留证+findings 意外观察+L3 探索层+FLAKY 判定（W7） [38c0c94e]"
```

---

### Task 4: 机械闸样例验证（不 commit 产物，结果记录进 PR body）

**Files:**
- Create（scratchpad，不入库）: `/private/tmp/claude-501/-Users-administrator-worktrees-cecelia-session-af85a991/268e7902-82ed-478c-af81-6452dd2198dc/scratchpad/w7-sample-dod.md`

- [ ] **Step 1: 写新格式样例 contract-dod**

```bash
cat > /private/tmp/claude-501/-Users-administrator-worktrees-cecelia-session-af85a991/268e7902-82ed-478c-af81-6452dd2198dc/scratchpad/w7-sample-dod.md << 'EOF'
# Contract DoD（W7 五行剧本样例）

- [x] [BEHAVIOR] [L2] B-01: 保存设置后页面出现成功提示
  动作: 在设置页点击「保存」按钮
  预期观察: 页面立即出现「保存成功」toast
  等待预算: 0s
  留证: screenshots/b01-save-toast.png
  Test: manual:bash bash -c 'curl -sf localhost:5221/api/settings | jq -e ".notify_enabled==true"'
- [x] [BEHAVIOR] [L2] B-02: 点设置触发推送 within 60s 收到确认 [接缝×2]
  动作: 调用 POST /api/settings/save
  预期观察: within 60s 消息表出现新条目
  等待预算: 60s
  留证: until-loop 输出末 5 行
  Test: manual:bash bash -c 'until psql "$DB_URL" -tAc "SELECT 1 FROM messages" | grep -q 1; do sleep 2; done; echo OK'
- [x] [ARTIFACT] 探索提示段存在
  Test: bash -c 'grep -q "## 探索提示" contract-draft.md'
EOF
```

- [ ] **Step 2: 跑 harness-contract-lint（期望 exit 0）**

```bash
node /Users/administrator/perfect21/cecelia/scripts/harness-contract-lint.mjs /private/tmp/claude-501/-Users-administrator-worktrees-cecelia-session-af85a991/268e7902-82ed-478c-af81-6452dd2198dc/scratchpad/w7-sample-dod.md; echo "exit=$?"
```

Expected: `✅ harness-contract-lint: ... 合规，无违规条目`，exit=0。

- [ ] **Step 3: 跑 promote-regression 收割断言（期望收割出完整单行命令，非 "bash"）**

```bash
cd /Users/administrator/perfect21/cecelia && node --input-type=module -e "
import { parseBehaviorEntries } from './packages/brain/src/harness-promote-regression.js';
import { readFileSync } from 'fs';
const t = readFileSync('/private/tmp/claude-501/-Users-administrator-worktrees-cecelia-session-af85a991/268e7902-82ed-478c-af81-6452dd2198dc/scratchpad/w7-sample-dod.md','utf8');
const e = parseBehaviorEntries(t);
console.log(JSON.stringify(e, null, 2));
if (e.length !== 2) { console.error('FAIL: 期望收割 2 条 BEHAVIOR，得到 ' + e.length); process.exit(1); }
for (const x of e) { if (x.cmd.length < 20) { console.error('FAIL: 收割命令过短（多行隐患复现）: ' + x.cmd); process.exit(1); } }
console.log('OK: 收割 2 条完整单行命令');
"
```

Expected: 打印 2 条 entries，每条 cmd 是完整 `bash bash -c '...'` 命令，末行 `OK`。

- [ ] **Step 4: 全量 skill lint + 契约守卫最终确认**

```bash
cd /Users/administrator/worktrees/zenithjoy-skills/w7-human-evaluator
python3 .github/workflows/scripts/lint-skills.py && bash .github/workflows/scripts/check-brain-contract.sh && python3 .github/workflows/scripts/test/test_lint_skills.py
```

Expected: 三个脚本全部通过。

- [ ] **Step 5: 无需 commit（样例在 scratchpad）**，验证输出摘要留给 PR body 用。

---

## 合并后跟进（主 session 做，不在本 plan 的 subagent 范围）

1. cecelia 主仓跑 `bash scripts/sync-skills-snapshot.sh` → 刷 `packages/workflows/skills/harness-*` 快照 → 开 cecelia PR（第二个 PR）
2. PATCH 任务 38c0c94e completed + handoff
3. 实弹验证不做（归 Phase1 验火，RD 明确拆出）

## Self-Review 结论

- Spec 覆盖：五行剧本→Task1；单行 Test: 铁律→Task1+Task4 Step3；探索提示段→Task1；reviewer 20/21→Task2；L1 留证/L2 findings/L3 探索/FLAKY/SEGMENT_EVAL 不动/legacy 兼容→Task3；样例过闸→Task4；快照同步→合并后跟进。无缺口。
- 无占位符；版本号/字段名（wait_budget/evidence/findings/FLAKY:）跨任务一致。
