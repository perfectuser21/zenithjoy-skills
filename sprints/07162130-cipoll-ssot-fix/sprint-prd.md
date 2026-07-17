# Sprint PRD — ci-poll.sh grep -c 双行输出修复

## 背景

`scripts/ci-poll.sh` 使用 `grep -c` 统计 fail/pending 计数。当 `grep` 命中
但管道另一端已关闭时，`grep -c` 会在正常计数行之外额外输出错误信息，导致变量
赋值为两行文本，后续 `[ "${FAILED:-0}" -gt 0 ]` 整数比较报 bash 错误。
参考 cecelia 仓 #3869 同款修法：在管道末端加 `| head -1` 或改 `awk` 取单值。

## Invariant 约束

- [接口不变] ci-poll.sh 退出码语义不变：0=全绿，10=有 fail，11=BEHIND
- [调用接口不变] 脚本入参（PR_NUMBER REPO）及调用方式不变，复用方无需改动
- [职责不变] 脚本只报状态，不做 merge/rebase/fix（单一职责铁律）

## 累积 FR

- FR-1：`FAILED` 变量赋值管道末端加 `| head -1`，确保始终为单行整数
- FR-2：`PENDING` 变量赋值管道末端加 `| head -1`，确保始终为单行整数
- FR-3：修复前必须先写 failing test——模拟 gh 输出使 `grep -c` 产双行，
  验证现版本整数比较报错（exit ≠ 0 且 stderr 含 integer expression expected
  或类似错误），修复后正确判定
- FR-4：回归用例三分支：CI 全绿（pending=0 fail=0）、有 fail（fail>0）、
  BEHIND（mergeStateStatus=BEHIND）各一用例，修复后均通过

## NFR

- 修复代码行数变化 ≤ 4 行（最小改动原则）
- 测试脚本为纯 bash，无外部依赖，可在 CI runner 直接执行
- 测试文件提交至 repo，永久留在 CI 回归（不得删除）

## 范围限定

**在范围内**：
- `scripts/ci-poll.sh`：FAILED/PENDING 两处 grep -c 管道加 `| head -1`
- failing test + 三分支回归测试脚本（新建于 `tests/` 或 `scripts/tests/`）

**不在范围内**：
- 其他脚本的 grep -c 用法（本次只修 ci-poll.sh）
- 退出码逻辑、sleep 间隔、merge 判断逻辑

## 预期受影响文件

- `scripts/ci-poll.sh`：2 处管道修改
- `tests/ci-poll-grep-fix.sh`（新建）：failing test + 回归用例

## journey_type: bug_fix
## target_environment: local_api
