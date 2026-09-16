#!/bin/zsh
# 回归守卫：评论采集（关11）+ 搜索视频卡片抽取（关8）
#
# 起因（2026-09-11 真机探雷）：这条获客链 18 轮报告「评论数」全是 0，从来没采到过
# 一条评论。真机走查发现两个结构性断点：
#
#  1. 关11「采评论」**根本没有命令**。skill 只写记账协议（批次/游标/哈希），
#     没有任何设备命令负责把评论从屏幕上读出来 ⇒ 交给 LLM 看截图自由发挥。
#     真机实测：评论面板无障碍树里昵称/正文/赞数/翻页终点全是结构化的，
#     能确定性抽取，根本不需要视觉。
#
#  2. 关8「读搜索结果」在**综合 tab** 上 uiautomator dump 永远 `could not get idle
#     state`（内嵌视频自动播放，keyevent 85 媒体键对它无效，实测连抓 3 次全 0 节点）。
#     切到**视频 tab** 后是静态缩略图网格，同一台机同一秒 dump 出 182 节点。
#     ⇒ 搜索阶段必须先切视频 tab 再读树。
#
# 用法：test-collect-comments.zsh <被测脚本路径>
set -u
SCRIPT="${1:?need script path}"
pass=0; fail=0
ok(){ print -- "  PASS: $1"; pass=$((pass+1)); }
ng(){ print -- "  FAIL: $1"; fail=$((fail+1)); }
chk(){ if eval "$1"; then ok "$2"; else ng "$3"; fi }

for fn in comments_from_xml comments_exhausted video_cards_from_xml; do
  src="$(/usr/bin/awk -v f="^${fn}\\\\(\\\\) \\\\{" '$0 ~ f{s=1} s{print} s&&/^\}/{exit}' "$SCRIPT")"
  [[ -n "$src" ]] || { print -- "FATAL: $fn not found in $SCRIPT"; exit 2; }
  eval "$src"
done

W=1200
FIXDIR="${0:A:h}/fixtures"
PANEL="$FIXDIR/comments-panel-1-real.xml"
GRID="$FIXDIR/search-video-grid-real.xml"

print -- "--- 关11 评论抽取（真机面板 fixture）---"
out="$(comments_from_xml "$PANEL" $W)"
chk '[[ "$(print -- "$out" | /usr/bin/wc -l | tr -d " ")" == 1 ]]' \
    "真机面板抽出恰好 1 条评论" \
    "评论条数不对：期望 1，实得 $(print -- "$out" | /usr/bin/wc -l | tr -d ' ')"
chk '[[ "$out" == *"程琢技能提升指南"* ]]' \
    "抽到评论者昵称" "没抽到昵称"
chk '[[ "$out" == *"7月6日首批名额已满"* ]]' \
    "抽到评论正文" "没抽到正文"

print -- "--- 变异测试：干扰项必须被排除 ---"
chk '[[ "$out" != *"发条评论"* ]]' \
    "底部输入框占位符「发条评论，和大家一起讨论」未被当成评论" \
    "回归！把输入框占位符当成了评论 —— 会污染线索池"
chk '[[ "$out" != *"优惠团购"* ]]' \
    "团购卡「查看地址/用户评价/优惠团购」未被当成评论" \
    "回归！把团购卡当成了评论"
chk '[[ "$out" != *"未选中"* ]]' \
    "点赞控件「赞1,未选中」（含逗号）未被当成评论" \
    "回归！含逗号的点赞控件被误判为评论"
chk '[[ "$out" != *"的头像"* ]]' \
    "头像节点未被当成评论" "回归！头像被当成了评论"

print -- "--- 翻页终点判据 ---"
chk 'comments_exhausted "$PANEL"' \
    "「暂时没有更多了」被识别为已取光" \
    "取光信号没识别到 —— 会无限翻页"

print -- "--- 关8 视频卡片抽取（真机视频tab网格 fixture）---"
cards="$(video_cards_from_xml "$GRID")"
n=$(print -- "$cards" | /usr/bin/grep -c . || true)
chk '(( n >= 4 ))' \
    "视频网格抽出 >=4 条卡片（实得 $n）" \
    "视频卡片抽取不足：期望>=4，实得 $n"
chk '[[ "$cards" == *"AI训练师进大厂秘诀"* ]]' \
    "抽到视频标题" "没抽到视频标题"
chk '[[ "$cards" != *"相关搜索"* ]]' \
    "「相关搜索」区块未被当成视频卡片" \
    "回归！把相关搜索当成了视频"

print -- "--- 关11 第二份真机 fixture（MM-DD 日期 + 作者评论）---"
P2="$FIXDIR/comments-panel-2-author-real.xml"
out2="$(comments_from_xml "$P2" $W)"
chk '[[ "$(print -- "$out2" | /usr/bin/grep -c .)" == 2 ]]' \
    "抽出 2 条评论" "条数不对：实得 $(print -- "$out2" | /usr/bin/grep -c .)"
chk '[[ "$out2" == *"零基础可以报考几级？"* ]]' \
    "抽到真实意向评论「零基础可以报考几级？」" "没抽到意向评论"
chk '[[ "$(print -- "$out2" | /usr/bin/grep "零基础" | /usr/bin/cut -f2)" == "零基础可以报考几级？" ]]' \
    "正文干净：MM-DD 日期与地区已从正文剥离" \
    "回归！正文里残留了尾部字段(日期/地区/回复按钮) —— 会污染线索文本"
chk '[[ "$(print -- "$out2" | /usr/bin/grep "零基础" | /usr/bin/cut -f3)" == "08-14" ]]' \
    "MM-DD 日期被正确抽出" "MM-DD 日期没抽到"
chk '[[ "$(print -- "$out2" | /usr/bin/grep "零基础" | /usr/bin/cut -f4)" == "陕西" ]]' \
    "地区被正确抽出" "地区没抽到"
chk '[[ "$(print -- "$out2" | /usr/bin/grep "你觉得人工智能训练师证书" | /usr/bin/cut -f5)" == "author" ]]' \
    "视频作者本人的评论被标记为 author（不得进线索池）" \
    "回归！作者评论没被标记 —— 会把视频作者本人当成客户线索"
chk '[[ "$(print -- "$out2" | /usr/bin/grep "零基础" | /usr/bin/cut -f5)" != "author" ]]' \
    "普通评论者未被误标为 author" "普通评论者被误标成 author"

print -- "--- 关8 视频时长（ASR 判定要靠它选短视频）---"
chk '[[ "$cards" == *"04:01"* && "$cards" == *"01:25"* ]]' \
    "视频卡片带出时长（04:01 / 01:25）" \
    "缺时长列 —— agent 无法优先选短视频，全片 ASR 会撑爆时间预算"
chk '[[ "$(print -- "$cards" | /usr/bin/grep "简历还是写不出来" | /usr/bin/cut -f3)" == "01:25" ]]' \
    "时长与标题正确配对（右下角时长标签归属其上方标题）" \
    "时长配对错位 —— 会按错误时长选视频"
chk '[[ "$(print -- "$cards" | /usr/bin/cut -f4 | /usr/bin/grep -c .)" -ge 4 ]]' \
    "第4列是标题（时长插在第3列后标题仍在）" "列序错乱"

print -- ""
print -- "PASS=$pass FAIL=$fail"
(( fail == 0 )) || exit 1
