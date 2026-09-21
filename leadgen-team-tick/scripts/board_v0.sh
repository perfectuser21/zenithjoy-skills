#!/bin/zsh
# 看板员 v0：格子矩阵从工件算出来，不手填。每行=一个格子，证据全是可重跑的探针。
set -u
now=$(date +%s)
age(){ local t=$1; [[ -z "$t" ]] && { echo "无"; return; }; echo "$(( (now - t) / 86400 ))天前"; }
D=/Users/administrator/openclaw-root/workspaces-root/clawd-work-commander/state/workflow-runs
REPO=/Users/administrator/perfect21/zenithjoy-skills
# —— 抖音×获客 ——
cmds=$(ssh xian-m4 'grep -cE "^  [a-z][a-z0-9-]+\)" ~/.local/bin/douyin-phone-adb' 2>/dev/null || echo 0)
cron=$(ssh xian-m4 'crontab -l 2>/dev/null | grep -c harvest-cron' 2>/dev/null || echo 0)
outreach=$(ssh xian-m4 'crontab -l 2>/dev/null | grep -c outreach-tick' 2>/dev/null || echo 0)
leads7=$(ssh xian-m4 'n=0; for f in $(find ~ -maxdepth 1 -name "night-*.tsv" -mtime -7 2>/dev/null); do n=$((n+$(grep -c "^LEAD" "$f"))); done; echo $n' 2>/dev/null || echo 0)
lastrun=$(ls "$D" 2>/dev/null | grep -oE 'leadgen-[0-9]{8}' | sort | tail -1 | grep -oE '[0-9]{8}')
lastrun_ts=$(date -j -f %Y%m%d "$lastrun" +%s 2>/dev/null || echo "")
scr_last=$(git -C "$REPO" log -1 --format=%ct origin/main -- openclaw/clawd-media/skills/douyin-leadgen-phone/scripts/douyin-phone-adb.zsh)
stage="S0"; [[ $cmds -ge 10 ]] && stage="S2"; [[ -n "$lastrun" ]] && stage="S3"; [[ $cron -ge 1 && $leads7 -ge 1 ]] && stage="S4"; [[ $outreach -ge 1 ]] && stage="S5"
frozen=$(( (now - scr_last) / 86400 ))
printf "%-10s %-4s  原语=%s  合同run最后=%s(%s)  cron=%s 触达cron=%s  近7天LEAD=%s  脚本最后改动=%s天前%s\n" \
  "抖音×获客" "$stage" "$cmds" "${lastrun:-无}" "$(age "$lastrun_ts")" "$cron" "$outreach" "$leads7" "$frozen" "$([[ $frozen -ge 28 ]] && echo '(S6候选)' || echo '(未到S6)')"
# —— 三个新平台 ——
for p in kuaishou xiaohongshu shipinhao; do
  doc=$(git -C "$REPO" log -1 --format=%cs origin/main -- android-$p-leadgen/SKILL.md 2>/dev/null)
  rt=$(ssh xian-m4 "ls ~/.local/bin/${p}-phone-adb ~/.local/bin/${p}-phone-runtime 2>/dev/null | head -1")
  printf "%-10s %-4s  判定树=%s  runtime=%s\n" "${p}×获客" "$([[ -n "$rt" ]] && echo S2 || echo S0)" "${doc:-无}" "${rt:-缺(硬前提)}"
done
# —— 团队自身的新鲜度（谁看团队）——
printf "\n[新鲜度] 合同run最后=%s  findings最后=%s  escalation最后=%s\n" \
  "$(age "$lastrun_ts")" \
  "$(age $(ssh us-vps 'stat -c %Y /opt/openclaw/state/escort-findings.md'))" \
  "$(age $(ssh us-vps 'stat -c %Y /opt/openclaw/state/m4-logs/escalation.log'))"
