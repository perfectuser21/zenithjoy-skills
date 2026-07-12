#!/bin/bash
set -u
HOOK="$(cd "$(dirname "$0")/.." && pwd)/post-pr-create.sh"
FAILS=0
REAL_GIT=$(command -v git 2>/dev/null)

# run_case <name> <gh_branch> <gh_view_exit> <expect_exit> <expect_merge> [git_branch] [git_exit]
run_case() {
  local name="$1" stub_branch="$2" view_exit="$3" expect_exit="$4" expect_merge="$5"
  local git_branch="${6:-}" git_exit="${7:-0}"
  local tmp; tmp=$(mktemp -d)
  cat > "$tmp/gh" <<STUB
#!/bin/bash
echo "\$@" >> "$tmp/calls.log"
if [ "\$1" = "pr" ] && [ "\$2" = "view" ]; then
  if [ "$view_exit" != "0" ]; then exit $view_exit; fi
  echo "$stub_branch"
fi
exit 0
STUB
  chmod +x "$tmp/gh"
  cat > "$tmp/git" <<GITSTUB
#!/bin/bash
if [ "\$1" = "branch" ] && [ "\$2" = "--show-current" ]; then
  if [ $git_exit -ne 0 ]; then exit $git_exit; fi
  echo "$git_branch"
  exit 0
fi
$REAL_GIT "\$@"
GITSTUB
  chmod +x "$tmp/git"
  local input='{"tool_input":{"command":"gh pr create --title x"},"tool_response":{"stdout":"https://github.com/perfectuser21/zenithjoy-skills/pull/999\n"}}'
  PATH="$tmp:$PATH" HARNESS_NODE= bash "$HOOK" <<< "$input" >/dev/null 2>&1
  local rc=$?
  local merged=no
  grep -q "pr merge" "$tmp/calls.log" 2>/dev/null && merged=yes
  if [ "$rc" -eq "$expect_exit" ] && [ "$merged" = "$expect_merge" ]; then
    echo "OK $name (exit=$rc merge=$merged)"
  else
    echo "FAIL $name: 期望 exit=$expect_exit merge=$expect_merge, 实际 exit=$rc merge=$merged"
    FAILS=$((FAILS+1))
  fi
  rm -rf "$tmp"
}

# 正常路径：gh 成功
run_case "rewrite/* 跳过 auto-merge（停人工 review）" "rewrite/harness-controller-v2" 0 0 no
run_case "cp-* 守卫不变（auto-merge + exit 2）" "cp-07110000-foo" 0 2 yes

# gh 失败场景（regression，skills#129 残留修复）：
# gh 偶发失败 + git 兜底 rewrite/* → 必须跳过，不得 fail-open
run_case "gh失败+git兜底rewrite/*→跳过auto-merge" "" 1 0 no "rewrite/harness-v3" 0
# gh 失败 + git 兜底普通分支 → 信息充足，正常 auto-merge
run_case "gh失败+git兜底cp-*→正常auto-merge" "" 1 2 yes "cp-07120000-foo" 0
# gh 失败 + git 也失败 → fail-closed：保守跳过，不能静默放行
run_case "gh失败+git也失败→fail-closed跳过" "" 1 0 no "" 1

if [ "$FAILS" -gt 0 ]; then exit 1; fi
echo "all cases passed"
