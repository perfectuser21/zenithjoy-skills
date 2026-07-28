# W7 人形验收设计 — 合同 [BEHAVIOR] 剧本化 delta 实施

日期：2026-07-28 ｜ 任务：38c0c94e ｜ 设计决策：d3021871 ｜ RD：cecelia `docs/prd/2026-07-28-w7-human-evaluator-rd.md`

## 目标

evaluator 像人一样按步骤操作验收，而非跑一行命令。三层设计：L1 剧本层（必过阻塞 merge）/ L2 意外观察（嵌在剧本里）/ L3 探索层（剧本全过后带预算自由测试）。零引擎依赖，只改 skill 文本。

## 现状基线（skills#149 已合并部分）

- proposer 9.14.0：三段式（动作/预期观察/验证命令）+ until-loop within-Ns 范式 + legacy 兼容标记
- evaluator 1.26.0：按剧本执行（动作→轮询预期观察→验证命令），behavior_tests 加 action/expected 字段
- reviewer 9.7.0：**完全未动**，无剧本审查维度
- 已知隐患：#149 样例把验证命令写成多行，cecelia `harness-promote-regression.js` 的 `Test:\s*manual:(.+)$` 单行收割会取出 `cmd="bash"` 的假绿回归条目

## Delta 设计

### 1. harness-contract-proposer 9.14.0 → 9.15.0

- 三段式升级为**五行剧本**，每条新写 [BEHAVIOR] 必含：
  ```
  - [ ] [BEHAVIOR] [L1|L2|L3] B-NN: <步骤名>
    动作: <人做什么——点/发/调/等>
    预期观察: <人应该看到什么——消息到达/页面变化/DB出现记录>
    等待预算: <N>s（超时=FAIL；同步观察写 0s）
    留证: <截图路径 / 命令输出 / DB查询结果>
    Test: manual:bash <单行验证命令，长命令用 bash -c '...'>
  ```
- **Test: 保持必填且强制单行**——兼容三个机械闸：cecelia `harness-contract-lint.mjs`（MISSING_TEST 规则）、`harness-promote-regression.js` 单行收割、`harness-judge.js` 存在性正则。同时修掉 #149 多行验证命令隐患（模板明文禁止多行，until-loop 用 `bash -c` 包成单行）。
- 新增 `## 探索提示` 合同段模板（平级二级标题，禁止嵌进 `## E2E 验收` 段内部）：列高风险探索面（错输入/连点两次/中途刷新/返回重进/边界值），供 evaluator L3 使用；预算行可调（默认 10 分钟/15 动作）。
- 接缝步骤（真机/异步/第三方）在步骤名后标 `[接缝×2]`，evaluator 重复执行 2 次。
- 补 ≥2 完整正例（同步观察 + 异步等待各一）+ ≥2 禁止反例（旧命令行长相 / 缺等待预算）。

### 2. harness-contract-reviewer 9.7.0 → 9.8.0

- Golden Path 覆盖审查新增：
  - 第 20 条：新写 [BEHAVIOR] 缺 动作/预期观察/等待预算/留证 任一段 → 第 1 维 dod_machineability 打回 REVISION（`[legacy]` 标记条目豁免）。
  - 第 21 条：合同缺 `## 探索提示` 段，或探索面未覆盖高风险操作（错输入/重复提交/中途中断/边界值）→ 第 6 维低分打回，**feedback 必须给出具体探索提示内容**供 proposer 填入（"探索提示由 GAN reviewer 写进合同"的落地方式）。
- **不动 7 个维度名**（dod_machineability 等是与 Brain ReviewerOutputSchema 的接口约定）。

### 3. harness-evaluator 1.27.0 → 1.28.0

- **L1 按步执行+逐步留证**：每条剧本 执行动作 → within 等待预算轮询预期观察 → 采集留证（截图存 `SPRINT_DIR/screenshots/`、命令输出/DB 查询结果记入 behavior_tests.log_tail 或留证文件）→ 跑 Test: 命令。全过才 PASS。
- **L2 意外观察**：执行任何步骤时发现"不对劲"（卡顿/控制台报错/布局歪/慢响应）必须录入 verdict JSON 新增顶层 `findings[]` 字段（`{severity, step, observation, evidence}`）。步骤照过，观察必留。additive 字段：Brain `EvaluatorOutputSchema` 非 strict，多余字段被 strip 不报错；findings 同时落 `SPRINT_DIR/findings.md` 文件留证。
- **L3 探索层**：剧本全过后，按合同 `## 探索提示` 段自由测试，默认预算 10 分钟/15 动作（合同可调）。发现分级：P0/P1（丢数据/直接面客错误）→ verdict FAIL 阻塞 merge；P2/P3 → 记 findings 不阻塞（report 阶段/人工落 issue）。
- **FLAKY 判定**：`[接缝×2]` 步骤执行 2 次，两次不一致 → verdict FAIL，failed_step 标 `FLAKY:<步骤>`（flaky 即 bug）。
- **不动**：SEGMENT_EVAL 段级轻验收维持机械断言；legacy 条目按旧协议执行（向后兼容——存量合同 evaluator 仍能跑）。

### 4. cecelia 侧（merge 后第二个 PR）

- 跑 `scripts/sync-skills-snapshot.sh` 刷 `packages/workflows/skills/harness-*` 快照（脚本已覆盖三个目录）。
- `contract-gate.js` / `harness-contract-lint.mjs` **不改**——以本地样例过闸验证为证（RD 改动面#5 判定为"不需要则不动"）。

## 兼容性证据（Research Subagent 已核查）

| 机械闸 | 结论 | 证据 |
|---|---|---|
| harness-contract-lint MISSING_TEST | 兼容（Test: 保留单行） | `scripts/harness-contract-lint.mjs:47-99` |
| promote-regression 收割 | 兼容且修掉 #149 隐患 | `harness-promote-regression.js:54` 单行正则 |
| judge 存在性/E2E 段提取 | 兼容 | `harness-judge.js:594,194-198` |
| Brain verdict schema | findings[] 被 strip 不拒绝 | `harness-shared.js:262-277` 无 .strict() |
| ## 探索提示 段 | 平级标题不破坏 awk/regex 提取 | evaluator SKILL:322,326 |
| zenithjoy-skills CI | lint-skills.py 只查 frontmatter/version 格式 | `.github/workflows/lint-skills.yml` |

## 测试策略

文本改动档（skill 文档），四项验证：
1. **本地 lint**：`python3 .github/workflows/scripts/lint-skills.py`（frontmatter/version 合法）
2. **样例过闸（integration）**：写一份新格式样例 contract-dod 片段，跑 `node cecelia/scripts/harness-contract-lint.mjs` 断言 exit 0
3. **收割断言（integration）**：`node -e` 调 cecelia `parseBehaviorEntries` 断言新格式样例收割出完整单行命令（非 "bash"）
4. **CI 全绿**：lint-skills + check-brain-contract + learning 占位符闸

## 不做（拆出去）

- 实弹验证（新格式合同真跑一发 harness）→ 归 Phase1 验火
- Brain 代码改动（含 findings 入库消费）→ 不碰引擎
- 探索层止损/成本监控 → 观察首批实弹后再定
