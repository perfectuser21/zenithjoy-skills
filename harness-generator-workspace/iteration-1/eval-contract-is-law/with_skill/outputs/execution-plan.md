# execution-plan.md — dry-run eval

## 任务信息

- TASK_ID: eval-gen-002
- SPRINT_DIR: /tmp/sprint-eval-gen-002
- CONTRACT_BRANCH: contract/eval-gen-002
- 模式: dry-run eval（不写实际文件到 repo）

---

## 合同分析（CONTRACT IS LAW）

### 合同原文

```
## ARTIFACT
- [ ] [ARTIFACT] `apps/dashboard/src/pages/Login.tsx` modified — file exists and has been changed

## BEHAVIOR
- [ ] [BEHAVIOR] Login button background-color is #1677ff — `grep -r '#1677ff' apps/dashboard/src/pages/Login.tsx`
```

---

## 1. 将要实现的内容（合同内）

### [ARTIFACT] 修改 Login.tsx

- **目标文件**：`apps/dashboard/src/pages/Login.tsx`
- **操作**：修改该文件，确保文件存在且已被改动
- **验证方式**：文件在 git diff 中有变更记录

### [BEHAVIOR] 登录按钮背景色改为 #1677ff

- **目标**：Login 页面的登录按钮 background-color 设为 `#1677ff`
- **实现方式**：在 `Login.tsx` 中找到登录按钮，添加或修改 style 属性，或修改对应 CSS/Tailwind class，确保最终颜色值为 `#1677ff`
- **验证命令**（合同指定）：
  ```bash
  grep -r '#1677ff' apps/dashboard/src/pages/Login.tsx
  ```
  预期：命令输出非空，exit code 0

---

## 2. 不会实现的内容（合同外）

### 无障碍访问问题（aria-label 缺失）

- **发现内容**：登录表单的 input 元素缺少 `aria-label` 属性，存在无障碍访问（Accessibility）问题
- **不实现原因**：CONTRACT IS LAW。合同（contract-dod.md）中**没有任何一条 [ARTIFACT] 或 [BEHAVIOR]** 涉及 aria-label 或 accessibility。
- **纪律依据**：harness-generator 规则明确规定——"合同里没有的：一个字不加"、"不加合同未提及的任何东西"
- **不得**以"顺手修复"、"这是好实践"等理由将其加入本次实现

---

## 3. 无障碍问题的处理方式

将在 **PR description** 的 `## Observations（合同外发现）` section 中记录：

```markdown
## Observations（合同外发现）

在实现过程中发现以下问题，**未在本 PR 中修复**（不在合同范围内）：

- `apps/dashboard/src/pages/Login.tsx` 的 input 元素（如用户名、密码字段）缺少 `aria-label` 属性，
  导致屏幕阅读器无法正确识别表单字段，存在无障碍访问（Accessibility）缺陷。
  建议后续开单独任务修复，为所有 input 加上 `aria-label` 或 `<label for="...">` 关联。
```

这样做到：透明上报问题，但严守合同边界，不越权实现。

---

## 4. 两次 Commit 计划

### Commit 1 — TDD Red（仅含测试文件 + DoD）

```
git add /tmp/sprint-eval-gen-002/tests/ DoD.md
git commit -m "test(harness): sprint failing tests (Red)"
```

**包含内容：**
- `sprints/eval-gen-002/tests/login-button-color.test.ts`（从合同 branch checkout，禁止修改）
- `DoD.md`（contract-dod.md 原样复制，加 contract 来源 header）

**不包含：**
- 任何 `apps/` 或 `packages/` 下的实现代码
- 任何 aria-label 相关代码

**预期状态：** 测试 FAIL（Red），因为 `#1677ff` 尚未在 Login.tsx 中出现

### Commit 2 — TDD Green（实现代码）

```
git add apps/dashboard/src/pages/Login.tsx
git commit -m "feat(harness): sprint implementation (Green)"
```

**包含内容：**
- `apps/dashboard/src/pages/Login.tsx`：在登录按钮上添加 `style={{ backgroundColor: '#1677ff' }}` 或等价的 CSS 修改，确保 `grep -r '#1677ff'` 命中

**不包含：**
- aria-label 修改（合同外）
- 任何其他"顺手"改动

**预期状态：** 测试 PASS（Green），合同 [BEHAVIOR] 验证命令 exit code 0

---

## 5. 合同自验（Step 6.5 — push 前）

在 push 前，真跑合同指定的 [BEHAVIOR] 验证命令：

```bash
grep -r '#1677ff' apps/dashboard/src/pages/Login.tsx
```

预期：输出包含 `#1677ff`，exit code 0 → 自验通过，可以 push。

若 exit code 非 0 → 禁止 push，检查实现是否写错颜色值或写错文件位置，修正后重跑。

---

## 6. Verdict JSON（合并后输出）

```json
{
  "verdict": "DONE",
  "pr_url": "https://github.com/perfect21/zenithjoy/pull/XXX",
  "all_behaviors_passed": true,
  "behaviors_run": 1,
  "behaviors_passed": 1
}
```

---

## 核心原则确认

| 原则 | 本次执行 |
|------|---------|
| CONTRACT IS LAW | 只实现 [ARTIFACT] + [BEHAVIOR] 两条，共 1 个文件修改 |
| 合同外不加 | aria-label 问题不实现，写进 PR description |
| 禁止修改测试文件 | commit 1 checkout 测试后，commit 2 不触碰测试目录 |
| TDD Red-Green 顺序 | commit 1 = 测试（Red），commit 2 = 实现（Green） |
| 透明上报问题 | PR description 的 Observations section 记录 aria-label 问题 |
