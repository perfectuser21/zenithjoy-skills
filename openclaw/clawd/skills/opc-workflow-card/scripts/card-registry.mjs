#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const DEFAULT_REGISTRY = '/root/clawd/state/opc-card-registry-v2.json';
const DEFAULT_PROFILE = 'opc-main';
const DEFAULT_CONTROL_URL = 'https://vps-hk.tailce7a8b.ts.net:8444/webhook/agentic-workflow-runner-v1/control';
let activeRelease = null;

function fail(message, code = 1) {
  if (activeRelease) { activeRelease(); activeRelease = null; }
  process.stderr.write(`${JSON.stringify({ ok: false, error: message })}\n`);
  process.exit(code);
}

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    if (!argv[i].startsWith('--')) out._.push(argv[i]);
    else {
      const key = argv[i].slice(2);
      if (argv[i + 1] === undefined || argv[i + 1].startsWith('--')) out[key] = true;
      else { out[key] = argv[++i]; }
    }
  }
  return out;
}

function decodePayload(args) {
  const raw = args['payload-base64'];
  if (!raw) fail('Missing --payload-base64');
  try { return JSON.parse(Buffer.from(String(raw), 'base64').toString('utf8')); }
  catch (error) { fail(`Invalid payload: ${error.message}`); }
}

function safeText(value, max = 1200) {
  return String(value ?? '').replace(/[\u0000-\u001f]/g, ' ').slice(0, max);
}

function safeId(value, field) {
  const text = String(value ?? '');
  if (!/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}$/.test(text)) fail(`Invalid ${field}`);
  return text;
}

function initialRegistry() {
  return { schema_version: 2, cards: {}, event_ids: {}, callback_ids: {}, updated_at: new Date().toISOString() };
}

function readRegistry(file) {
  if (!fs.existsSync(file)) return initialRegistry();
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (error) { fail(`Invalid registry: ${error.message}`); }
}

function writeAtomic(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  const temp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temp, file);
}

function sleep(ms) { Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms); }

function lock(file) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  const lockFile = `${file}.lock`;
  for (let i = 0; i < 80; i += 1) {
    try {
      const fd = fs.openSync(lockFile, 'wx', 0o600);
      return () => { try { fs.closeSync(fd); } finally { fs.rmSync(lockFile, { force: true }); } };
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
      try {
        if (Date.now() - fs.statSync(lockFile).mtimeMs > 60000) { fs.rmSync(lockFile, { force: true }); continue; }
      } catch {}
      sleep(50);
    }
  }
  fail('Card Registry lock timeout');
}

function cardKey(event) {
  return [safeId(event.run_id, 'run_id'), safeId(event.object_id, 'object_id'), safeId(event.card_target?.audience_key, 'audience_key')].join('|');
}

function statusMeta(status) {
  const map = {
    running: ['orange', '执行中', '🔄'],
    waiting: ['yellow', '等待中', '⏳'],
    blocked: ['red', '已阻塞', '⛔'],
    completed: ['green', '已完成', '✅'],
    failed: ['red', '失败', '❌'],
    stopped: ['grey', '已停止', '⏹️'],
  };
  return map[status] || ['blue', safeText(status || '未知'), 'ℹ️'];
}

function progressBar(current, total) {
  const safeTotal = Math.max(1, Number(total) || 1);
  const safeCurrent = Math.min(safeTotal, Math.max(0, Number(current) || 0));
  const filled = Math.round((safeCurrent / safeTotal) * 10);
  return `${'■'.repeat(filled)}${'□'.repeat(10 - filled)}  ${safeCurrent}/${safeTotal}`;
}

function callbackText(action, entry) {
  return `OPC_CALLBACK ${JSON.stringify({ action, workflow_run_id: entry.run_id, attempt_id: entry.attempt_id, execution_id: entry.execution_id, object_id: entry.object_id, step_run_id: entry.latest?.stage_id || null, audience_key: entry.audience_key })}`;
}

function render(entry) {
  const latest = entry.latest || {};
  const [template, statusLabel, icon] = statusMeta(latest.status);
  const titleKind = entry.view === 'task' ? '任务详情' : entry.view === 'evidence' ? '证据' : 'Workflow';
  const current = latest.current_step ?? 0;
  const total = latest.total_steps ?? entry.total_steps ?? 1;
  const stage = safeText(latest.stage_id || '准备运行');
  const summary = safeText(latest.summary || latest.stop_reason || '已登记，等待首个状态事件');
  const next = safeText(latest.next_action || (latest.status === 'completed' ? '无' : '等待 Work Commander 更新'));
  const evidence = Array.isArray(latest.evidence) ? latest.evidence : [];
  const timeline = (entry.timeline || []).slice(-6).map((item) => `- ${safeText(item.at, 40)} · ${safeText(item.event || item.status, 40)} · ${safeText(item.stage_id || '-', 40)}`).join('\n') || '- 暂无';

  let main;
  if (entry.view === 'evidence') {
    main = `**${icon} ${statusLabel}**\n\n**已登记证据**\n${evidence.length ? evidence.map((item) => `- ${safeText(typeof item === 'string' ? item : JSON.stringify(item), 300)}`).join('\n') : '- 当前步骤尚未登记证据'}\n\n**最近事实**\n${summary}`;
  } else if (entry.view === 'task') {
    main = `**${icon} ${statusLabel} · ${stage}**\n\n${progressBar(current, total)}\n\n**当前结果**\n${summary}\n\n**下一步**\n${next}\n\n**执行身份**\nAttempt ${safeText(entry.attempt_id)} · Worker ${safeText(entry.worker_agent_id)}`;
  } else {
    main = `**${icon} ${statusLabel}**\n\n${progressBar(current, total)}\n\n**当前阶段**\n${stage}\n\n**最新进展**\n${summary}\n\n**下一步**\n${next}`;
  }

  if (entry.control_notice) main += `\n\n**控制请求**\n${safeText(entry.control_notice)}`;

  const actions = entry.view === 'workflow'
    ? [
        ['查看任务详情', 'primary', 'open_task_detail'],
        ['查看证据', 'default', 'open_evidence'],
        ['标记阻塞', 'danger', 'mark_blocked'],
      ]
    : [
        ['返回 Workflow', 'primary', 'open_workflow_summary'],
        ['查看证据', 'default', 'open_evidence'],
        ['标记阻塞', 'danger', 'mark_blocked'],
      ];

  return {
    schema: '2.0',
    config: { update_multi: true, width_mode: 'fill' },
    header: {
      title: { tag: 'plain_text', content: `🎛️ OPC | ${titleKind}` },
      subtitle: { tag: 'plain_text', content: `${safeText(entry.workflow_id)} · ${safeText(entry.attempt_id)}` },
      template,
    },
    body: {
      direction: 'vertical',
      padding: '12px 12px 12px 12px',
      elements: [
        { tag: 'markdown', content: main, text_size: 'normal' },
        { tag: 'hr' },
        { tag: 'markdown', content: `**时间线**\n${timeline}`, text_size: 'notation' },
        ...actions.map(([content, type, action]) => ({
          tag: 'button',
          text: { tag: 'plain_text', content },
          type,
          width: 'fill',
          value: { text: callbackText(action, entry) },
        })),
        { tag: 'markdown', content: `Run ${safeText(entry.run_id)} · v${entry.version}`, text_size: 'notation' },
      ],
    },
  };
}

function runCli(args, dryRun) {
  if (dryRun) return { dry_run: true, args };
  const result = spawnSync('lark-cli', ['--profile', process.env.OPC_LARK_PROFILE || DEFAULT_PROFILE, ...args, '--format', 'json'], { encoding: 'utf8', timeout: 30000 });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`lark-cli exit ${result.status}: ${(result.stderr || result.stdout).slice(0, 800)}`);
  try { return JSON.parse(result.stdout); }
  catch { throw new Error(`Invalid lark-cli JSON: ${result.stdout.slice(0, 500)}`); }
}

function findMessageId(value) {
  if (!value || typeof value !== 'object') return null;
  if (typeof value.message_id === 'string' && value.message_id) return value.message_id;
  for (const child of Object.values(value)) {
    const found = findMessageId(child);
    if (found) return found;
  }
  return null;
}

function publish(entry, dryRun) {
  const card = render(entry);
  if (entry.message_id) {
    const response = runCli(['im', 'messages', 'patch', '--message-id', entry.message_id, '--data', JSON.stringify({ content: JSON.stringify(card) })], dryRun);
    return { operation: 'patch', message_id: entry.message_id, response, card };
  }
  const idempotency = crypto.createHash('sha256').update(`${entry.key}:create`).digest('hex').slice(0, 48);
  const response = runCli(['im', '+messages-send', '--chat-id', entry.chat_id, '--msg-type', 'interactive', '--content', JSON.stringify(card), '--idempotency-key', idempotency], dryRun);
  const messageId = dryRun ? 'dry-run-message-id' : findMessageId(response);
  if (!messageId) throw new Error(`Send response missing message_id: ${JSON.stringify(response).slice(0, 500)}`);
  entry.message_id = messageId;
  return { operation: 'create', message_id: messageId, response, card };
}

async function postControl(payload, dryRun) {
  if (dryRun) return { dry_run: true };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(process.env.OPC_N8N_CONTROL_URL || DEFAULT_CONTROL_URL, {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload), signal: controller.signal,
    });
    const body = await response.text();
    if (!response.ok) throw new Error(`Control HTTP ${response.status}: ${body.slice(0, 300)}`);
    return { status: response.status, body: body.slice(0, 500) };
  } finally { clearTimeout(timer); }
}

const args = parseArgs(process.argv.slice(2));
const command = args._[0];
if (!['upsert', 'action', 'show'].includes(command)) fail('Usage: card-registry.mjs upsert|action|show');
const registryFile = path.resolve(String(args.registry || DEFAULT_REGISTRY));
if (command === 'show') {
  process.stdout.write(`${JSON.stringify(readRegistry(registryFile), null, 2)}\n`);
  process.exit(0);
}

const payload = decodePayload(args);
const dryRun = Boolean(args['dry-run'] || process.env.OPC_CARD_DRY_RUN === '1');
const release = lock(registryFile);
activeRelease = release;
try {
  const registry = readRegistry(registryFile);
  if (command === 'upsert') {
    if (Number(payload.schema_version) !== 2) fail('Unsupported event schema');
    const eventId = safeId(payload.event_id, 'event_id');
    if (registry.event_ids[eventId]) {
      process.stdout.write(`${JSON.stringify({ ok: true, deduped: true, event_id: eventId, registry: registry.event_ids[eventId] })}\n`);
      release();
      activeRelease = null;
      process.exit(0);
    }
    const key = cardKey(payload);
    const entry = registry.cards[key] || {
      key,
      run_id: payload.run_id,
      attempt_id: payload.attempt_id,
      execution_id: payload.execution_id,
      object_id: payload.object_id,
      workflow_id: payload.workflow_id,
      worker_agent_id: payload.worker_agent_id,
      audience_key: payload.card_target.audience_key,
      chat_id: payload.card_target.chat_id,
      visibility: payload.card_target.visibility,
      sender_profile: process.env.OPC_LARK_PROFILE || DEFAULT_PROFILE,
      view: 'workflow',
      version: 0,
      timeline: [],
      created_at: new Date().toISOString(),
    };
    if (entry.chat_id !== payload.card_target.chat_id) fail('Card chat identity mismatch');
    if (entry.execution_id !== payload.execution_id) {
      const resumableStatuses = new Set(['blocked', 'failed']);
      const priorStatus = String(entry.latest?.status || '');
      if (payload.resumes_execution_id !== entry.execution_id) fail('Card resume source mismatch');
      if (!resumableStatuses.has(priorStatus)) fail(`Card cannot resume from status ${priorStatus || 'unknown'}`);
      if (entry.workflow_id !== payload.workflow_id || entry.worker_agent_id !== payload.worker_agent_id) fail('Card resume workflow identity mismatch');
      entry.resumed_from_execution_id = entry.execution_id;
      entry.attempt_id = payload.attempt_id;
      entry.execution_id = payload.execution_id;
    }
    entry.latest = payload;
    entry.total_steps = payload.total_steps || entry.total_steps;
    entry.timeline.push({ event_id: eventId, event: payload.event || 'terminal', status: payload.status, stage_id: payload.stage_id || null, at: payload.observed_at || payload.finished_at || new Date().toISOString() });
    entry.timeline = entry.timeline.slice(-30);
    entry.version += 1;
    entry.updated_at = new Date().toISOString();
    entry.control_notice = null;
    const published = publish(entry, dryRun);
    registry.cards[key] = entry;
    registry.event_ids[eventId] = { key, message_id: entry.message_id, version: entry.version, at: entry.updated_at };
    registry.updated_at = entry.updated_at;
    if (!dryRun) writeAtomic(registryFile, registry);
    process.stdout.write(`${JSON.stringify({ ok: true, deduped: false, key, version: entry.version, ...published })}\n`);
  } else {
    const action = safeText(payload.action, 80);
    if (!['open_task_detail', 'open_workflow_summary', 'open_evidence', 'mark_blocked'].includes(action)) fail('Unsupported action');
    const callbackId = safeText(payload.event_id || payload.callback_event_id || '', 180);
    if (callbackId && registry.callback_ids[callbackId]) {
      process.stdout.write(`${JSON.stringify({ ok: true, deduped: true, callback_id: callbackId, result: registry.callback_ids[callbackId] })}\n`);
      release();
      activeRelease = null;
      process.exit(0);
    }
    const candidates = Object.values(registry.cards).filter((entry) => entry.run_id === payload.workflow_run_id && (!payload.object_id || entry.object_id === payload.object_id) && (!payload.audience_key || entry.audience_key === payload.audience_key));
    if (candidates.length !== 1) fail(`Expected one registered card, found ${candidates.length}`);
    const entry = candidates[0];
    if (action === 'open_task_detail') entry.view = 'task';
    if (action === 'open_workflow_summary') entry.view = 'workflow';
    if (action === 'open_evidence') entry.view = 'evidence';
    let control = null;
    if (action === 'mark_blocked') {
      control = await postControl({ schema_version: 2, action, run_id: entry.run_id, attempt_id: entry.attempt_id, execution_id: entry.execution_id, object_id: entry.object_id, requested_by: payload.sender_id || null, callback_event_id: callbackId || null, requested_at: new Date().toISOString() }, dryRun);
      entry.control_notice = '已提交“标记阻塞”请求，等待 Work Commander 回写正式状态。';
    }
    entry.version += 1;
    entry.updated_at = new Date().toISOString();
    const published = publish(entry, dryRun);
    registry.cards[entry.key] = entry;
    const result = { key: entry.key, action, version: entry.version, message_id: entry.message_id, control };
    if (callbackId) registry.callback_ids[callbackId] = result;
    registry.updated_at = entry.updated_at;
    if (!dryRun) writeAtomic(registryFile, registry);
    process.stdout.write(`${JSON.stringify({ ok: true, deduped: false, ...result, ...published })}\n`);
  }
} catch (error) {
  fail(error.message);
} finally {
  release();
  activeRelease = null;
}
