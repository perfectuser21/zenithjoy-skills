# post-pr-create.sh rewrite/* 豁免 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** post-pr-create.sh 对 rewrite/* 分支 PR 跳过 auto-merge（停人工 review），其余分支行为不变。

**Architecture:** 在 hook 的 HARNESS_NODE 判断之后加一段 headRefName 查询 + rewrite/* 前缀判断；配 stub-gh 的 bash regression test 并接进 lint-skills CI。

**Tech Stack:** bash、gh CLI stub、GitHub Actions（lint-skills.yml）。

## Global Constraints

- TDD 两 commit：commit-1 = failing test（红）+ CI 接线，commit-2 = 实现（绿）
- commit message 用 Conventional Commits；**PR 标题**必须 `[CONFIG] fix(hooks):` 前缀（改了 workflow 文件）
- gh 查询失败 → 保守按普通分支处理（不静默放掉守卫）
- 合并后同步部署副本 `~/.claude/hooks/post-pr-create.sh`（收尾动作，不进 repo commit）

---

### Task 1: Regression test（commit-1，红）

**Files:**
- Create: `hooks/__tests__/post-pr-create-rewrite.test.sh`
- Modify: `.github/workflows/lint-skills.yml`（lint-skills job 追加一个 step）

**Interfaces:**
- Consumes: `hooks/post-pr-create.sh`（stdin 喂 PostToolUse JSON，PATH 塞 stub gh）
- Produces: 测试脚本 exit 0 = 全过；任一 case 失败 exit 1

- [ ] **Step 1: 写测试脚本**

```bash
#!/bin/bash
# post-pr-create-rewrite.test.sh — skills#127 回归：rewrite/* PR 不得被 hook 秒合
# 用 stub gh 隔离真实 GitHub；3 case：rewrite 豁免 / cp 守卫仍在 / gh 查询失败保守处理
set -u
HOOK="$(cd "$(dirname "$0")/.." && pwd)/post-pr-create.sh"
FAILS=0

run_case() {
  local name="$1" stub_branch="$2" view_exit="$3" expect_exit="$4" expect_merge="$5"
  local tmp; tmp=$(mktemp -d)
  cat > "$tmp/gh" <<STUB
#!/bin/bash
echo "\$@" >> "$tmp/calls.log"
if [ "\$1" = "pr" ] && [ "\$2" = "view" ]; then
  if [ "$view_exit" != "0" ]; then exit "$view_exit"; fi
  echo "$stub_branch"
fi
exit 0
STUB
  chmod +x "$tmp/gh"
  local input='{"tool_input":{"command":"gh pr create --title x"},"tool_response":{"stdout":"https://github.com/perfectuser21/zenithjoy-skills/pull/999\n"}}'
  PATH="$tmp:$PATH" HARNESS_NODE= bash "$HOOK" <<< "$input" >/dev/null 2>&1
  local rc=$?
  local merged=no
  grep -q "pr merge" "$tmp/calls.log" 2>/dev/null && merged=yes
  if [ "$rc" -eq "$expect_exit" ] && [ "$merged" = "$expect_merge" ]; then
    echo "OK $name (exit=$rc merge=$merged)"
  else
    echo "FAIL $name: 期望 exit=$expect_exit merge=$expect_merge，实际 exit=$rc merge=$merged"
    FAILS=$((FAILS+1))
  fi
  rm -rf "$tmp"
}

run_case "rewrite/* 跳过 auto-merge（停人工 review）" "rewrite/harness-controller-v2" 0 0 no
run_case "cp-* 守卫不变（auto-merge + exit 2）"      "cp-07110000-foo"              0 2 yes
run_case "gh pr view 失败 → 保守按普通分支"           ""                             1 2 yes

if [ "$FAILS" -gt 0 ]; then exit 1; fi
echo "all cases passed"
```

- [ ] **Step 2: 跑测试确认红（proven-to-fire）**

Run: `bash hooks/__tests__/post-pr-create-rewrite.test.sh`
Expected: case 1（rewrite）FAIL（旧实现 exit=2 merge=yes），case 2/3 OK，脚本 exit 1

- [ ] **Step 3: 接进 lint-skills.yml**

在 `lint-skills` job 的「Brain 契约一致性守卫」step 之后追加：

```yaml
      # skills#127 回归：post-pr-create hook 对 rewrite/* 必须跳过 auto-merge（人工门）
      - name: Regression — post-pr-create rewrite/* 豁免
        run: bash hooks/__tests__/post-pr-create-rewrite.test.sh
```

- [ ] **Step 4: Commit（commit-1）**

提交上述两个文件，message：`test(hooks): post-pr-create rewrite 豁免 regression（红）`

### Task 2: Hook 实现（commit-2，绿）

**Files:**
- Modify: `hooks/post-pr-create.sh:27-29`（HARNESS_NODE 块之后、auto-merge 之前插入）

**Interfaces:**
- Consumes: Task 1 的测试脚本
- Produces: rewrite/* → exit 0 无 merge；其余分支原行为

- [ ] **Step 1: 在 HARNESS_NODE 块后插入分支判断**

```bash
# rewrite/* 重写 PR 停人工 review（decision e6c57e2f，skills#127 教训）：
# 不启用 auto-merge、不强制 watchdog，等主理人批准。
# gh 查询失败（HEAD_BRANCH 为空）→ 保守按普通分支处理，守卫不因查询失败静默放掉。
HEAD_BRANCH=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json headRefName -q .headRefName 2>/dev/null)
if [[ "$HEAD_BRANCH" == rewrite/* ]]; then
  echo "[post-pr-create] rewrite/* 分支（${HEAD_BRANCH}）：跳过 auto-merge，重写 PR 停人工 review，等主理人批准。" >&2
  exit 0
fi
```

- [ ] **Step 2: 跑测试确认绿**

Run: `bash hooks/__tests__/post-pr-create-rewrite.test.sh`
Expected: 3 case 全 OK，输出 `all cases passed`，exit 0

- [ ] **Step 3: Commit（commit-2）**

提交 hooks/post-pr-create.sh，message：`fix(hooks): post-pr-create 对 rewrite 分支跳过 auto-merge，守住人工 review 门`
