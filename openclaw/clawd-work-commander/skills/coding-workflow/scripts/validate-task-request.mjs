#!/usr/bin/env node
// coding-harness task_request 校验器：输出 {ok, schema, task_request_hash}；失败输出 {ok:false,error} 并 exit 1。
import crypto from 'node:crypto';
import fs from 'node:fs';
function fail(message) { process.stderr.write(`${JSON.stringify({ ok: false, error: message })}\n`); process.exit(1); }
function string(value, name, max = 20000) {
  if (typeof value !== 'string' || !value.trim()) fail(`${name} must be a non-empty string`);
  if (value.length > max) fail(`${name} exceeds ${max} characters`);
}
function oneOf(value, name, choices) { if (!choices.includes(value)) fail(`${name} must be one of: ${choices.join(', ')}`); }
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}
const file = process.argv[2];
if (!file) fail('Usage: validate-task-request.mjs <task_request.json>');
let request;
try { request = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (error) { fail(`Invalid task request JSON: ${error.message}`); }
if (!request || typeof request !== 'object' || Array.isArray(request)) fail('task_request must be an object');
const allowed = ['task_title', 'thin_prd', 'base_repo', 'base_branch', 'target_environment', 'gp_anchor', 'change_kind', 'tenant_id'];
for (const key of Object.keys(request)) if (!allowed.includes(key)) fail(`Unknown field ${key}`);
for (const field of allowed) if (request[field] === undefined) fail(`Missing ${field}`);
string(request.task_title, 'task_title', 200);
string(request.thin_prd, 'thin_prd');
string(request.base_repo, 'base_repo', 300);
if (!/^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(\.git)?$/.test(request.base_repo)) fail('base_repo must be a full GitHub URL');
string(request.base_branch, 'base_branch', 120);
oneOf(request.target_environment, 'target_environment', ['mac_web', 'windows_cloud', 'windows_wechat', 'linux_server', 'local_api', 'playground']);
string(request.gp_anchor, 'gp_anchor', 120);
if (!/^([a-z0-9_]+\/[a-z0-9_]+(#step[0-9]+|\s+keep-green)|none\((infra|docs|config|backlog)\))$/.test(request.gp_anchor)) fail('gp_anchor must be <line>/<gp>#stepN | <line>/<gp> keep-green | none(infra|docs|config|backlog)');
oneOf(request.change_kind, 'change_kind', ['new_capability', 'capability_change', 'bugfix', 'parameter_only']);
string(request.tenant_id, 'tenant_id', 64);
const hash = crypto.createHash('sha256').update(canonical(request), 'utf8').digest('hex');
process.stdout.write(`${JSON.stringify({ ok: true, schema: 'coding-task-request-v1', task_request_hash: hash, task_title: request.task_title, tenant_id: request.tenant_id })}\n`);
