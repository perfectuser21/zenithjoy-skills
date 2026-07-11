#!/bin/bash
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
    echo "FAIL $name: 期望 exit=$expect_exit merge=$expect_merge, 实际 exit=$rc merge=$merged"
    FAILS=$((FAILS+1))
  fi
  rm -rf "$tmp"
}

run_case "rewrite/* 跳过 auto-merge（停人工 review）" "rewrite/harness-controller-v2" 0 0 no
run_case "cp-* 守卫不变（auto-merge + exit 2）" "cp-07110000-foo" 0 2 yes
run_case "gh pr view 失败 → 保守按普通分支" "" 1 2 yes

if [ "$FAILS" -gt 0 ]; then exit 1; fi
echo "all cases passed"
