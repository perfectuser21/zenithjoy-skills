## post-pr-create.sh 对 rewrite/* 跳过 auto-merge（2026-07-11）

### 根本原因
本地 PostToolUse hook `hooks/post-pr-create.sh` 对所有非 HARNESS_NODE 新建 PR 无条件 `gh pr merge --auto --squash`，完全不看分支名。CI 侧 lint-skills auto-merge job 本来就只合 cp-*（有正确过滤），两道闸只有本地 hook 缺分支判断——rewrite/* 重写 PR（decision e6c57e2f 要求停人工 review）因此在创建 11 秒后被秒合（skills#127 实锤）。守卫类逻辑在多道闸并存时，每道闸都必须独立带完整判断条件，不能默认"另一道会拦"。

### 下次预防
- [x] regression test `hooks/__tests__/post-pr-create-rewrite.test.sh`（stub gh，3 case：rewrite 豁免 / cp-* 守卫不变 / gh 查询失败保守处理）已接进 lint-skills CI，旧实现下亲验报红（proven-to-fire）
- [x] 若有人删掉豁免逻辑，该 step 红 → lint-skills 红 → auto-merge job 不跑（自指安全闭环）
- [ ] 后续候选刀（最终审查 Important）：gh pr view 查询失败时 rewrite PR 会 fail-open 落回 auto-merge；可用本地 `git branch --show-current` 兜底或失败时只 exit 2 不 enable auto-merge。已批 PrepPRD 第 4 条显式拍板当前取舍，非疏漏
- [ ] 新增会 merge/enable auto-merge 的 hook 或脚本时，必须先列全分支类型（cp-*/rewrite/*/其他）并写明每类的合并策略
