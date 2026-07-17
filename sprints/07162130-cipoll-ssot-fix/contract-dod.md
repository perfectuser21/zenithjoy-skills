# Contract DoD — ci-poll.sh grep -c 双行输出修复

**TASK_ID**: 507308ae-f906-4bc0-b32c-37a182b82f97

---

## [BEHAVIOR] 条目

[ ] [BEHAVIOR] B1: 当 `grep -c` 返回多行输出时，旧版 `ci-poll.sh` 的整数比较报错 → 断言：构造含 `fail` 的双行 CHECKS 输出喂给旧版比较逻辑，bash 报 `integer expression expected` 或以非零码退出（exit ≠ 0）

[ ] [BEHAVIOR] B2: 修复后 CI 全绿场景（pending=0, fail=0, mergeStateStatus≠BEHIND）→ 断言：`ci-poll.sh` mock 版本退出码为 0，stdout 含 `CI_GREEN`

[ ] [BEHAVIOR] B3: 修复后有 fail 场景（fail>0）→ 断言：`ci-poll.sh` mock 版本退出码为 10，stderr 含 `CI_FAILED`

[ ] [BEHAVIOR] B4: 修复后 BEHIND 场景（mergeStateStatus=BEHIND, fail=0, pending=0）→ 断言：`ci-poll.sh` mock 版本退出码为 11，stderr 含 `BEHIND`

[ ] [BEHAVIOR] B5: 修复代码变化极小原则 → 断言：`git diff main -- scripts/ci-poll.sh | grep '^[+-]' | grep -v '^[+-][+-][+-]' | wc -l` 输出值 ≤ 4

---

## DoD 条目

### 代码实现

[ ] `scripts/ci-poll.sh` 第 18 行 FAILED 赋值管道末端加 `| head -1`
[ ] `scripts/ci-poll.sh` 第 19 行 PENDING 赋值管道末端加 `| head -1`
[ ] diff 行数（新增+删除）≤ 4 行

### 测试

[ ] `sprints/07162130-cipoll-ssot-fix/tests/ci-poll-grep-fix.sh` 文件存在且可执行
[ ] failing test（B1）：模拟双行 grep -c 输出，验证旧版整数比较失败
[ ] 回归用例 B2（CI 全绿）：mock 版脚本返回 exit 0
[ ] 回归用例 B3（有 fail）：mock 版脚本返回 exit 10
[ ] 回归用例 B4（BEHIND）：mock 版脚本返回 exit 11
[ ] 全部测试通过：`bash sprints/07162130-cipoll-ssot-fix/tests/ci-poll-grep-fix.sh` 退出码为 0

### 可执行验收命令

`manual:bash bash sprints/07162130-cipoll-ssot-fix/tests/ci-poll-grep-fix.sh`

### CI 集成

[ ] 测试脚本提交至 repo（不得删除）
[ ] 测试脚本为纯 bash，无外部依赖，CI runner 可直接执行

### Invariant 保护

[ ] `scripts/ci-poll.sh` 退出码语义未变（0/10/11）
[ ] 脚本入参（PR_NUMBER REPO）及调用方式未变
[ ] 脚本内无 merge/rebase/fix 操作（单一职责）

### 提交

[ ] `git commit` 含 TASK_ID `507308ae`
[ ] 测试文件与修复代码同一 PR 提交
