# Contract Draft — ci-poll.sh grep -c 双行输出修复

**TASK_ID**: 507308ae-f906-4bc0-b32c-37a182b82f97
**Sprint**: sprints/07162130-cipoll-ssot-fix
**Journey Type**: bug_fix
**Base Repo**: zenithjoy-skills
**起草轮次**: 第 1 轮（无上轮 reviewer feedback）

---

## 问题陈述

`scripts/ci-poll.sh` 第 18–19 行：

```bash
FAILED=$(echo "$CHECKS" | grep -c "fail" 2>/dev/null || echo 0)
PENDING=$(echo "$CHECKS" | grep -cE "pending|in_progress|queued" 2>/dev/null || echo 0)
```

当 `grep -c` 在管道破裂（broken pipe）场景下触发时，会在正常计数行之外额外写入错误信息到 stdout（某些 bash 版本／环境下 `2>/dev/null` 不能完全屏蔽），导致变量被赋值为多行文本，后续 `[ "${FAILED:-0}" -gt 0 ]` 整数比较报 `integer expression expected` 并以非零码退出，掩盖真实 CI 状态。

---

## 修复方案

在 `FAILED` 和 `PENDING` 赋值管道末端各加 `| head -1`，确保变量始终为单行整数：

```bash
FAILED=$(echo "$CHECKS" | grep -c "fail" 2>/dev/null | head -1 || echo 0)
PENDING=$(echo "$CHECKS" | grep -cE "pending|in_progress|queued" 2>/dev/null | head -1 || echo 0)
```

代码行数变化：≤ 4 行（满足 NFR）。

---

## Invariant 约束（不得破坏）

| 约束 | 验证方式 |
|------|---------|
| 退出码语义不变：0=全绿，10=有 fail，11=BEHIND | 三分支回归测试覆盖 |
| 入参（PR_NUMBER REPO）及调用方式不变 | 接口签名未动 |
| 脚本只报状态，不做 merge/rebase/fix | 代码 diff 审查 |

---

## Test Contract 表

| # | [BEHAVIOR] 条目 | 测试用例 | 测试类型 |
|---|----------------|---------|---------|
| B1 | `grep -c` 产双行时，旧版整数比较报错 | `test_failing_grep_c_multiline` | failing test（记录当前 bug） |
| B2 | 修复后 CI 全绿场景正确返回 exit 0 | `test_all_green` | regression |
| B3 | 修复后有 fail 场景正确返回 exit 10 | `test_has_fail` | regression |
| B4 | 修复后 BEHIND 场景正确返回 exit 11 | `test_behind` | regression |

---

## E2E 验收

以下命令在仓库根目录可直接执行：

```bash
# 运行全套测试（failing test + 三分支回归）
bash sprints/07162130-cipoll-ssot-fix/tests/ci-poll-grep-fix.sh

# 预期输出：所有用例 PASS，exit 0
# 修复前：test_failing_grep_c_multiline 应当 PASS（证明 bug 存在），回归用例 FAIL
# 修复后：所有用例均 PASS
```

验收断言：
1. `bash sprints/07162130-cipoll-ssot-fix/tests/ci-poll-grep-fix.sh` 退出码为 0
2. stdout 中出现 `ALL TESTS PASSED` 字样
3. 无 `integer expression expected` 错误
4. `scripts/ci-poll.sh` diff 仅改动 FAILED/PENDING 两行（`| head -1` 插入），diff 行数 ≤ 4

---

## 未覆盖真实链路清单

| 场景 | 覆盖状态 | 说明 |
|------|---------|------|
| 真实 `gh pr checks` 调用 | Mock | 测试用 echo 模拟 gh 输出，无需真实 GitHub token |
| 真实 broken pipe 触发 | 部分 Mock | 用构造双行字符串模拟 grep -c 双行输出；真实 broken pipe 较难在 CI runner 中复现 |
| 多 repo / 多 PR 组合 | N/A | 本次修复为字符串处理逻辑，与 repo/PR 无关 |
| sleep 30 轮询行为 | N/A | 不在本次修复范围 |

---

## 覆盖率要求

- 测试脚本为纯 bash，无外部依赖（仅用 bash 内建 + echo + grep）
- 测试文件提交至 repo，永久留在 CI 回归（不得删除）
- 所有测试用例需在 macOS bash 3.x 和 Linux bash 5.x 环境均可运行

---

## DoD 引用

详见 `contract-dod.md`。
