#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs';

function fail(message) {
  process.stderr.write(`${JSON.stringify({ ok: false, error: message })}\n`);
  process.exit(1);
}

function read(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (error) { fail(`Invalid task request JSON: ${error.message}`); }
}

function requiredObject(value, name, fields) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${name} must be an object`);
  for (const field of fields) if (value[field] === undefined) fail(`Missing ${name}.${field}`);
}

function string(value, name) {
  if (typeof value !== 'string' || !value.trim()) fail(`${name} must be a non-empty string`);
}

function oneOf(value, name, choices) {
  if (!choices.includes(value)) fail(`${name} must be one of: ${choices.join(', ')}`);
}

function uniqueStrings(value, name, allowed = null) {
  if (!Array.isArray(value) || value.length === 0) fail(`${name} must be a non-empty array`);
  const normalized = value.map((item) => {
    string(item, `${name}[]`);
    return item.trim();
  });
  if (new Set(normalized).size !== normalized.length) fail(`${name} must not contain duplicates`);
  if (allowed) for (const item of normalized) oneOf(item, `${name}[]`, allowed);
  return normalized;
}

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

const file = process.argv[2];
if (!file) fail('Usage: validate-task-request.mjs <task_request.json>');
const request = read(file);

for (const field of ['task_name', 'tenant_id', 'audience']) string(request[field], field);
uniqueStrings(request.keywords, 'keywords');
if (!Array.isArray(request.defaults_applied)) fail('defaults_applied must be an array');

requiredObject(request.search_policy, 'search_policy', ['sort', 'time_layers', 'duration', 'scope', 'location', 'exhaust_visible_results']);
oneOf(request.search_policy.sort, 'search_policy.sort', ['comprehensive', 'latest', 'most_liked', 'most_commented', 'most_favorited']);
uniqueStrings(request.search_policy.time_layers, 'search_policy.time_layers', ['one_day', 'one_week', 'six_months']);
oneOf(request.search_policy.duration, 'search_policy.duration', ['unlimited', 'under_one_minute', 'one_to_five_minutes', 'over_five_minutes']);
oneOf(request.search_policy.scope, 'search_policy.scope', ['unlimited', 'following', 'recently_viewed', 'not_viewed']);
oneOf(request.search_policy.location, 'search_policy.location', ['unlimited', 'same_city']);
if (request.search_policy.exhaust_visible_results !== true) fail('search_policy.exhaust_visible_results must be true');

requiredObject(request.qualification_policy, 'qualification_policy', ['transcript_coverage', 'verdict_mode', 'low_confidence']);
if (request.qualification_policy.transcript_coverage !== 'full') fail('qualification_policy.transcript_coverage must be full');
if (request.qualification_policy.verdict_mode !== 'single_full_transcript') fail('qualification_policy.verdict_mode must be single_full_transcript');
if (request.qualification_policy.low_confidence !== 'review') fail('qualification_policy.low_confidence must be review');

requiredObject(request.comment_policy, 'comment_policy', ['mode', 'window', 'batch_size', 'scheduler', 'per_video_limit']);
oneOf(request.comment_policy.mode, 'comment_policy.mode', ['visible_window_exhaustive', 'top_n']);
if (request.comment_policy.window !== 'follow_video_layer') fail('comment_policy.window must be follow_video_layer');
if (!Number.isInteger(request.comment_policy.batch_size) || request.comment_policy.batch_size < 1 || request.comment_policy.batch_size > 100) fail('comment_policy.batch_size must be an integer from 1 to 100');
if (request.comment_policy.scheduler !== 'round_robin') fail('comment_policy.scheduler must be round_robin');
if (request.comment_policy.mode === 'visible_window_exhaustive' && request.comment_policy.per_video_limit !== null) fail('Exhaustive mode requires per_video_limit=null');
if (request.comment_policy.mode === 'top_n' && (!Number.isInteger(request.comment_policy.per_video_limit) || request.comment_policy.per_video_limit < 1)) fail('top_n mode requires a positive per_video_limit');

requiredObject(request.scoring_policy, 'scoring_policy', ['deliver_categories', 'low_confidence']);
uniqueStrings(request.scoring_policy.deliver_categories, 'scoring_policy.deliver_categories', ['strong_intent', 'weak_intent']);
if (request.scoring_policy.low_confidence !== 'review') fail('scoring_policy.low_confidence must be review');

requiredObject(request.delivery_policy, 'delivery_policy', ['destination', 'dedupe', 'external_outreach']);
if (request.delivery_policy.destination !== 'tenant_final_leads') fail('delivery_policy.destination must be tenant_final_leads');
const dedupe = uniqueStrings(request.delivery_policy.dedupe, 'delivery_policy.dedupe', ['video', 'comment', 'person', 'prior_runs']);
for (const key of ['video', 'comment', 'person', 'prior_runs']) if (!dedupe.includes(key)) fail(`delivery_policy.dedupe is missing ${key}`);
if (request.delivery_policy.external_outreach !== false) fail('delivery_policy.external_outreach must be false');

requiredObject(request.card_target, 'card_target', ['audience_key', 'chat_id', 'visibility']);
string(request.card_target.audience_key, 'card_target.audience_key');
string(request.card_target.chat_id, 'card_target.chat_id');
oneOf(request.card_target.visibility, 'card_target.visibility', ['internal', 'external']);

const hash = crypto.createHash('sha256').update(canonical(request), 'utf8').digest('hex');
process.stdout.write(`${JSON.stringify({ ok: true, schema: 'social-leadgen-task-request-v1', task_request_hash: hash, task_name: request.task_name, tenant_id: request.tenant_id })}\n`);
