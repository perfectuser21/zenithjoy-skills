# Harness Generator — Execution Plan
# TASK_ID: eval-gen-002
# SPRINT_DIR: /tmp/sprint-eval-gen-002
# CONTRACT_BRANCH: contract/eval-gen-002
# Mode: dry-run eval（不写实际文件，不 commit）

---

## Step 0: 解析任务上下文

已确认注入参数：
- TASK_ID: eval-gen-002
- SPRINT_DIR: /tmp/sprint-eval-gen-002
- CONTRACT_BRANCH: contract/eval-gen-002

BRAIN_URL 在 dry-run 模式下不做硬校验（正式场景中缺少会 exit 1）。

---

## Step 1: 读合同 + DoD 分析

### contract-dod.md 完整内容

```
# contract-dod.md — Sprint: Dashboard login page button color

## ARTIFACT
- [ ] [ARTIFACT] `apps/dashboard/src/pages/Login.tsx` modified — file exists and has been changed

## BEHAVIOR
- [ ] [BEHAVIOR] Login button background-color is #1677ff — `grep -r '#1677ff' apps/dashboard/src/pages/Login.tsx`
```

### 合同解读

**CONTRACT IS LAW — 合同里有的**（必须全部实现）：

| 类型 | 条目 | 验收手段 |
|------|------|---------|
| [ARTIFACT] | `apps/dashboard/src/pages/Login.tsx` 被修改，文件存在 | 文件存在性 + git diff 确认有变更 |
| [BEHAVIOR] | Login 按钮背景色为 `#1677ff` | `grep -r '#1677ff' apps/dashboard/src/pages/Login.tsx` |

**合同外发现的问题**（不实现，写进 PR description）：

- 登录表单输入框缺少 `aria-label`（无障碍访问问题）
- CONTRACT IS LAW：合同未提及 accessibility，因此本 Sprint **一行 accessibility 代码都不加**

---

## Step 2: 分支命名方案

```bash
HARNESS_TASK_ID="eval-gen-002"
TASK_ID_SHORT="${HARNESS_TASK_ID:0:8}"   # → "eval-gen"
BRANCH="cp-$(TZ=Asia/Shanghai date +%m%d%H%M)-${TASK_ID_SHORT}"
# 示例结果：cp-05301430-eval-gen
```

分支名合法性自检（与 hooks/branch-protect.sh 同规则）：
```
^cp-[0-9]{8,10}-[a-z0-9][a-z0-9_-]*$  ✅ 通过
```

---

## Step 3: TDD Red 阶段（commit 1）

### 3.1 测试文件内容（从合同 branch checkout）

测试文件路径：`/tmp/sprint-eval-gen-002/tests/login-button-color.test.ts`

测试内容应覆盖合同 [BEHAVIOR]：

```typescript
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'

describe('Login page button color', () => {
  it('[BEHAVIOR] Login button background-color is #1677ff', () => {
    const content = readFileSync('apps/dashboard/src/pages/Login.tsx', 'utf-8')
    expect(content).toContain('#1677ff')
  })
})
```

### 3.2 DoD.md 内容（从合同 checkout 后加 header）

```
contract_branch: contract/eval-gen-002
sprint_dir: /tmp/sprint-eval-gen-002

# contract-dod.md — Sprint: Dashboard login page button color

## ARTIFACT
- [ ] [ARTIFACT] `apps/dashboard/src/pages/Login.tsx` modified — file exists and has been changed

## BEHAVIOR
- [ ] [BEHAVIOR] Login button background-color is #1677ff — `grep -r '#1677ff' apps/dashboard/src/pages/Login.tsx`
```

### 3.3 commit 1 内容

```bash
git add /tmp/sprint-eval-gen-002/tests/ DoD.md
git commit -m "test(harness): sprint failing tests (Red)"
```

**commit 1 只含**：
- `sprints/tests/**/*.test.ts`（测试文件）
- `DoD.md`

**commit 1 绝对不含**：`apps/` 或 `packages/` 下的任何实现文件

---

## Step 4: TDD Green 阶段（commit 2）

### 4.1 实现方案

**目标文件**：`apps/dashboard/src/pages/Login.tsx`

**最小变更原则**（合同外一字不加）：

找到 Login 按钮的样式定义，将背景色改为 `#1677ff`。

```tsx
// 修改前（示例）
<Button type="primary" htmlType="submit">
  登录
</Button>

// 修改后 — 合同要求 #1677ff
<Button
  type="primary"
  htmlType="submit"
  style={{ backgroundColor: '#1677ff', borderColor: '#1677ff' }}
>
  登录
</Button>
```

或者如果项目使用 CSS/LESS/Tailwind 变量，修改对应样式文件中的色值为 `#1677ff`。

**不加的内容**（合同外）：
- `aria-label` 属性
- 任何其他 accessibility 改进
- 样式重构
- 其他按钮颜色变更

### 4.2 commit 2 内容

```bash
git add apps/dashboard/src/pages/Login.tsx
git commit -m "feat(harness): sprint implementation (Green)"
```

**commit 2 包含**：
- `apps/dashboard/src/pages/Login.tsx`（实现文件）

**commit 2 不含**：对 `sprints/*/tests/**/*.test.ts` 的任何修改（CI 强校验）

---

## Step 5: Verification 阶段

```bash
# 跑测试套件
npx vitest run /tmp/sprint-eval-gen-002/tests/ --reporter=verbose

# 合同 [BEHAVIOR] manual:bash 自验
grep -r '#1677ff' apps/dashboard/src/pages/Login.tsx
# 预期 exit code 0，且输出包含 #1677ff
```

### Step 6.5: Contract Self-Verification

```bash
# 提取并执行合同 [BEHAVIOR] 命令
# 合同唯一 [BEHAVIOR] 命令：
grep -r '#1677ff' apps/dashboard/src/pages/Login.tsx
```

预期结果：exit code 0，输出包含 `#1677ff` 的行。
全部 PASS 后才允许 push。

---

## 两次 Commit 计划（完整）

### Commit 1 — Red（测试先行）

```
test(harness): sprint failing tests (Red)

变更文件：
  /tmp/sprint-eval-gen-002/tests/login-button-color.test.ts  [新增]
  DoD.md                                                       [新增]
```

预期状态：测试跑起来 FAIL（因为 Login.tsx 还没改，#1677ff 不存在）

### Commit 2 — Green（实现）

```
feat(harness): sprint implementation (Green)

变更文件：
  apps/dashboard/src/pages/Login.tsx  [修改] 添加 #1677ff 背景色
```

预期状态：测试全绿，`grep -r '#1677ff' apps/dashboard/src/pages/Login.tsx` exit 0

---

## 合同外发现的处理

**发现的合同外问题**：登录表单输入框缺少 `aria-label`。

**本 Sprint 的处理决策**：
- **不实现**（CONTRACT IS LAW，合同未提及 accessibility）
- **写进 PR description** 的 `## 合同外发现` 章节

PR description 中记录如下：

```markdown
## 合同外发现（未实现，仅记录）

- **Accessibility 缺陷**：登录表单的 `<Input>` 输入框缺少 `aria-label` 属性，
  屏幕阅读器无法识别字段用途。
  建议在后续 Sprint 中补充：`aria-label="用户名"` / `aria-label="密码"`。
  本 Sprint 未实现，因合同 DoD 未包含此项，按 CONTRACT IS LAW 规则不加。
```

---

## Verdict JSON（dry-run 示意）

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

## 总结

| 项目 | 决策 |
|------|------|
| 实现的合同条目 | [ARTIFACT] Login.tsx 修改 + [BEHAVIOR] 按钮色 #1677ff |
| 不实现的内容 | 输入框 aria-label（合同外，accessibility 问题）|
| accessibility 问题的去向 | PR description ## 合同外发现 章节 |
| commit 数量 | 2（Red + Green，TDD 铁律）|
| 测试文件修改 | commit 2+ 中绝对为零（CI 强校验）|
