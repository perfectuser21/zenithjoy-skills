#!/usr/bin/env node

import fs from 'node:fs';

const labels = {
  comprehensive: '综合排序', latest: '最新发布', most_liked: '最多点赞', most_commented: '最多评论', most_favorited: '最多收藏',
  one_day: '一天内', one_week: '一周内', six_months: '半年内',
  unlimited: '不限', under_one_minute: '1分钟以下', one_to_five_minutes: '1–5分钟', over_five_minutes: '5分钟以上',
  following: '关注的人', recently_viewed: '最近看过', not_viewed: '还未看过', same_city: '同城',
  visible_window_exhaustive: '穷尽可见窗口', top_n: '每视频限量',
  strong_intent: '强意向', weak_intent: '弱意向'
};

const file = process.argv[2];
if (!file) throw new Error('Usage: render-task-description.mjs <task_request.json>');
const request = JSON.parse(fs.readFileSync(file, 'utf8'));
const value = (key) => labels[key] || key;
const time = request.search_policy.time_layers.map(value).join(' → ');
const comments = request.comment_policy.mode === 'top_n'
  ? `每视频最多${request.comment_policy.per_video_limit}条，${request.comment_policy.batch_size}条/轮`
  : `跟随视频时间层穷尽，${request.comment_policy.batch_size}条/视频/轮`;
const defaults = request.defaults_applied.length ? request.defaults_applied.join('、') : '无（全部由任务明确指定）';
const outreach = request.outreach_policy.enabled
  ? `抖音私信｜先 claim 后发送｜本轮最多${request.outreach_policy.max_per_run}人｜审批 ${request.outreach_policy.approval_id}`
  : '关闭（零外部联系）';

process.stdout.write([
  `任务：${request.task_name}`,
  `目标人群：${request.audience}`,
  `搜索关键词：${request.keywords.join('、')}`,
  `视频筛选：${value(request.search_policy.sort)}｜时间 ${time}｜时长 ${value(request.search_policy.duration)}｜范围 ${value(request.search_policy.scope)}｜位置 ${value(request.search_policy.location)}`,
  '视频处理：可见结果穷尽并去重｜每个链接完整 ASR｜Luna 校正后一次判定',
  `评论处理：${comments}｜轮询 ${request.comment_policy.scheduler === 'round_robin' ? '公平轮转' : request.comment_policy.scheduler}`,
  `合格配送：${request.scoring_policy.deliver_categories.map(value).join(' + ')}｜按视频、评论、人员、历史运行去重`,
  `触达：${outreach}`,
  `结果卡片：${request.card_target.audience_key}｜${request.card_target.visibility}`,
  `本次默认值：${defaults}`
].join('\n') + '\n');
