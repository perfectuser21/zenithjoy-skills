#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

// 这是 work-commander 的共享账本目录，本脚本可能被别的agent工作区里的拷贝调用，
// 不能从自己所在位置反推——调用方必须显式传 --state-dir，或设置
// OPENCLAW_WORKFLOW_STATE_DIR。缺了直接报错，不要悄悄落到一个装错环境就不存在的路径。
const DEFAULT_STATE_DIR = process.env.OPENCLAW_WORKFLOW_STATE_DIR || null;
const DEFAULT_EVENT_URL = 'https://vps-hk.tailce7a8b.ts.net:8444/webhook/agentic-workflow-runner-v1/event';
let activeRelease = null;

function fail(message, code = 1) {
  if (activeRelease) { activeRelease(); activeRelease = null; }
  process.stderr.write(`${JSON.stringify({ ok: false, error: message })}\n`);
  process.exit(code);
}

function argsOf(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const value = argv[i];
    if (!value.startsWith('--')) out._.push(value);
    else {
      const key = value.slice(2);
      const next = argv[i + 1];
      if (next === undefined || next.startsWith('--')) out[key] = true;
      else { out[key] = next; i += 1; }
    }
  }
  return out;
}

function required(args, key) {
  const value = args[key];
  if (value === undefined || value === '') fail(`Missing --${key}`);
  return String(value);
}

function safeId(value, field) {
  const text = String(value);
  if (!/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(text)) fail(`Invalid ${field}`);
  return text;
}

function sha256(value, field) {
  const text = String(value);
  if (!/^[a-f0-9]{64}$/.test(text)) fail(`Invalid ${field}`);
  return text;
}

function controlTokenHash(value) {
  const token = String(value || '');
  if (!/^[A-Za-z0-9_-]{32,128}$/.test(token)) fail('Invalid control_token');
  return crypto.createHash('sha256').update(token, 'utf8').digest('hex');
}

function controlTokenMatches(expectedHash, token) {
  const actual = Buffer.from(controlTokenHash(token), 'hex');
  const expected = Buffer.from(String(expectedHash || ''), 'hex');
  return actual.length === expected.length && crypto.timingSafeEqual(actual, expected);
}

function jsonArg(args, key, fallback) {
  if (args[key] === undefined) return fallback;
  try { return JSON.parse(String(args[key])); }
  catch (error) { fail(`Invalid --${key}: ${error.message}`); }
}

function statePath(args) {
  const runId = safeId(required(args, 'run-id'), 'run_id');
  const attemptId = safeId(required(args, 'attempt-id'), 'attempt_id');
  const rawStateDir = args['state-dir'] || DEFAULT_STATE_DIR;
  if (!rawStateDir) fail('state-dir is required: pass --state-dir <path> or set OPENCLAW_WORKFLOW_STATE_DIR');
  const dir = path.resolve(String(rawStateDir));
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  return { runId, attemptId, dir, file: path.join(dir, `${runId}__${attemptId}.json`) };
}

function validateResumeSource({ args, runId, attemptId, executionId, dir }) {
  const sourceExecutionId = args['resumes-execution-id'];
  if (!sourceExecutionId) {
    if (attemptId !== 'a1') fail('Non-initial attempt requires --resumes-execution-id');
    return null;
  }

  if (attemptId === 'a1') fail('Initial attempt cannot resume another execution');
  const sourceText = String(sourceExecutionId);
  const separator = sourceText.lastIndexOf(':');
  if (separator < 1 || separator === sourceText.length - 1) fail('Invalid resumes_execution_id');
  const sourceRunId = safeId(sourceText.slice(0, separator), 'resumes_run_id');
  const sourceAttemptId = safeId(sourceText.slice(separator + 1), 'resumes_attempt_id');
  if (sourceRunId !== runId) fail('Resume source must belong to the same run_id');
  if (sourceText === executionId) fail('Execution cannot resume itself');

  const sourceFile = path.join(dir, `${sourceRunId}__${sourceAttemptId}.json`);
  if (!fs.existsSync(sourceFile)) fail('Resume source ledger not found');
  const source = readJson(sourceFile);
  if (source.execution_id !== sourceText) fail('Resume source ledger identity mismatch');
  const sourceStatus = source.terminal?.status;
  if (!sourceStatus) fail('Resume source must have a terminal status');
  if (!['blocked', 'failed'].includes(sourceStatus)) {
    fail(`Resume source status ${sourceStatus} is immutable and cannot be resumed`);
  }
  return sourceText;
}

function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (error) { fail(`Cannot read ledger ${file}: ${error.message}`); }
}

function writeAtomic(file, value) {
  const temp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temp, file);
}

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function lock(file) {
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
  fail(`Ledger lock timeout: ${lockFile}`);
}

async function relay(payload, url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-opc-event-schema': 'agentic-workflow-v2' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    const text = await response.text();
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${text.slice(0, 300)}`);
    return { ok: true, status: response.status, body: text.slice(0, 500) };
  } finally {
    clearTimeout(timer);
  }
}

function commonEvent(state, seq) {
  const now = new Date();
  return {
    schema_version: 2,
    run_id: state.run_id,
    attempt_id: state.attempt_id,
    execution_id: state.execution_id,
    resumes_execution_id: state.resumes_execution_id || null,
    object_id: state.object_id,
    workflow_id: state.workflow_id,
    worker_agent_id: state.worker_agent_id,
    task_request_hash: state.task_request_hash || null,
    event_seq: seq,
    event_id: `${state.execution_id}:${seq}`,
    dedupe_key: `${state.execution_id}:${seq}`,
    total_steps: state.total_steps,
    owner_lease: {
      owner: 'work-commander',
      lease_id: state.lease_id,
      expires_at: new Date(now.getTime() + 15 * 60 * 1000).toISOString(),
    },
    card_target: state.card_target,
    observed_at: now.toISOString(),
  };
}

async function persistAndRelay(file, state, payload, marker, eventUrl) {
  state.event_seq = payload.event_seq;
  state.updated_at = payload.observed_at || payload.finished_at;
  state.pending_relay = { marker, payload };
  state.events.push({ marker, payload, relayed: false });
  writeAtomic(file, state);

  let receipt;
  try { receipt = await relay(payload, eventUrl); }
  catch (error) {
    process.stdout.write(`${JSON.stringify({ ok: false, relayed: false, marker, payload, error: error.message, state_file: file })}\n`);
    process.exitCode = 2;
    return;
  }

  state.pending_relay = null;
  state.events.at(-1).relayed = true;
  state.events.at(-1).relay_receipt = receipt;
  if (marker === 'WORKFLOW_TERMINAL') state.terminal = payload;
  writeAtomic(file, state);
  process.stdout.write(`${JSON.stringify({ ok: true, relayed: true, marker, payload, line: `${marker} ${JSON.stringify(payload)}`, state_file: file, receipt })}\n`);
}

async function retryPending(file, state, eventUrl) {
  if (!state.pending_relay) return false;
  const { marker, payload } = state.pending_relay;
  let receipt;
  try { receipt = await relay(payload, eventUrl); }
  catch (error) {
    process.stdout.write(`${JSON.stringify({ ok: false, relayed: false, retry: true, marker, payload, error: error.message, state_file: file })}\n`);
    process.exitCode = 2;
    return true;
  }
  state.pending_relay = null;
  const item = state.events.find((entry) => entry.payload.event_id === payload.event_id);
  if (item) { item.relayed = true; item.relay_receipt = receipt; }
  if (marker === 'WORKFLOW_TERMINAL') state.terminal = payload;
  writeAtomic(file, state);
  process.stdout.write(`${JSON.stringify({ ok: true, relayed: true, retry: true, marker, payload, line: `${marker} ${JSON.stringify(payload)}`, state_file: file, receipt })}\n`);
  return true;
}

const args = argsOf(process.argv.slice(2));
const command = args._[0];
if (!['init', 'event', 'terminal', 'show', 'verify-control'].includes(command)) fail('Usage: workflow-state.mjs init|event|terminal|show|verify-control [options]');
const { runId, attemptId, file } = statePath(args);

if (command === 'show') {
  if (!fs.existsSync(file)) fail('Ledger not found');
  process.stdout.write(`${JSON.stringify(readJson(file), null, 2)}\n`);
  process.exit(0);
}

const release = lock(file);
activeRelease = release;
try {
  if (command === 'init') {
    const executionId = `${runId}:${attemptId}`;
    const suppliedControlToken = required(args, 'control-token');
    const suppliedControlTokenHash = controlTokenHash(suppliedControlToken);
    if (fs.existsSync(file)) {
      const state = readJson(file);
      if (state.execution_id !== executionId) fail('Ledger identity mismatch');
      if (!controlTokenMatches(state.control_token_hash, suppliedControlToken)) fail('Control token mismatch for existing ledger');
      if (args['task-request-hash'] && state.task_request_hash !== sha256(args['task-request-hash'], 'task_request_hash')) fail('Task request hash mismatch for existing ledger');
      process.stdout.write(`${JSON.stringify({ ok: true, idempotent: true, terminal: Boolean(state.terminal), pending_relay: Boolean(state.pending_relay), state_file: file, state })}\n`);
    } else {
      const resumesExecutionId = validateResumeSource({
        args,
        runId,
        attemptId,
        executionId,
        dir: path.dirname(file),
      });
      const state = {
        schema_version: 2,
        run_id: runId,
        attempt_id: attemptId,
        execution_id: executionId,
        resumes_execution_id: resumesExecutionId,
        object_id: safeId(required(args, 'object-id'), 'object_id'),
        workflow_id: safeId(required(args, 'workflow-id'), 'workflow_id'),
        worker_agent_id: safeId(required(args, 'worker-agent-id'), 'worker_agent_id'),
        task_request_hash: args['task-request-hash'] ? sha256(args['task-request-hash'], 'task_request_hash') : null,
        total_steps: Number(required(args, 'total-steps')),
        lease_id: `${executionId}:${Date.now().toString(36)}`,
        control_token_hash: suppliedControlTokenHash,
        card_target: {
          audience_key: safeId(required(args, 'audience-key'), 'audience_key'),
          chat_id: safeId(required(args, 'chat-id'), 'chat_id'),
          visibility: String(args.visibility || 'internal'),
        },
        event_seq: 0,
        events: [],
        pending_relay: null,
        terminal: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      if (!Number.isInteger(state.total_steps) || state.total_steps < 1) fail('Invalid total_steps');
      if (state.worker_agent_id === 'main' || state.worker_agent_id === 'work-commander') fail('Invalid worker_agent_id');
      writeAtomic(file, state);
      process.stdout.write(`${JSON.stringify({ ok: true, created: true, state_file: file, state })}\n`);
    }
  } else {
    if (!fs.existsSync(file)) fail('Initialize ledger first');
    const state = readJson(file);
    if (command === 'verify-control') {
      if (state.terminal) fail('Execution attempt is terminal and immutable');
      if (!controlTokenMatches(state.control_token_hash, required(args, 'control-token'))) fail('Control token mismatch');
      process.stdout.write(`${JSON.stringify({ ok: true, authorized: true, execution_id: state.execution_id, state_file: file })}\n`);
    } else {
      if (state.terminal) fail('Execution attempt is terminal and immutable');
      const eventUrl = String(args['event-url'] || process.env.OPC_N8N_EVENT_URL || DEFAULT_EVENT_URL);
      if (await retryPending(file, state, eventUrl)) {
        release();
        activeRelease = null;
        process.exit(process.exitCode || 0);
      }
      const seq = state.event_seq + 1;
      if (command === 'event') {
      const payload = {
        ...commonEvent(state, seq),
        event: required(args, 'event'),
        stage_id: args['stage-id'] || null,
        stage_attempt: Number(args['stage-attempt'] || 1),
        status: required(args, 'status'),
        summary: String(args.summary || ''),
        evidence: jsonArg(args, 'evidence-json', []),
        next_action: String(args['next-action'] || ''),
        current_step: Number(args['current-step'] || 0),
      };
      await persistAndRelay(file, state, payload, 'WORKFLOW_EVENT', eventUrl);
      } else {
        const status = required(args, 'status');
        if (!['completed', 'blocked', 'failed', 'stopped'].includes(status)) fail('Invalid terminal status');
        // 诚实性闸门：声称做过cleanup但没验证成功，不能报completed——防止Commander
        // 忘记/幻觉验证结果时把没收尾干净的run悄悄标成功。
        const cleanupClaim = jsonArg(args, 'cleanup-json', { attempted: false, verified: false });
        if (status === 'completed' && cleanupClaim && cleanupClaim.attempted === true && cleanupClaim.verified !== true) {
          fail('cleanup.attempted=true but cleanup.verified is not true — cannot report completed');
        }
        const base = commonEvent(state, seq);
        const payload = {
          ...base,
          status,
          accepted_stages: jsonArg(args, 'accepted-stages-json', []),
          metrics: jsonArg(args, 'metrics-json', {}),
          writes: jsonArg(args, 'writes-json', {}),
          cleanup: jsonArg(args, 'cleanup-json', { attempted: false, verified: false }),
          stop_reason: String(args['stop-reason'] || ''),
          finished_at: new Date().toISOString(),
        };
        delete payload.owner_lease;
        delete payload.observed_at;
        await persistAndRelay(file, state, payload, 'WORKFLOW_TERMINAL', eventUrl);
      }
    }
  }
} finally {
  release();
  activeRelease = null;
}
