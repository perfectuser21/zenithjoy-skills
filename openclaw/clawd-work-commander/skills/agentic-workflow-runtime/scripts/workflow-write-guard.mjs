#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

// 这是 work-commander 的共享账本目录，本脚本可能被别的agent工作区里的拷贝调用，
// 不能从自己所在位置反推——调用方必须显式传 --state-dir，或设置
// OPENCLAW_WORKFLOW_STATE_DIR。缺了直接报错，不要悄悄落到一个装错环境就不存在的路径。
const DEFAULT_STATE_DIR = process.env.OPENCLAW_WORKFLOW_STATE_DIR || null;
const WRITE_INTENTS = {
  artifact_write: new Set(['preflight', 'discovery', 'qualification', 'collection', 'scoring', 'delivery', 'outreach', 'cleanup', 'plan', 'contract', 'seal', 'generate', 'evaluate', 'judge', 'publish', 'merge']),
  raw_comment_insert: new Set(['collection']),
  raw_comment_update: new Set(['scoring', 'delivery']),
  final_lead_write: new Set(['delivery', 'outreach']),
  keyword_cursor_write: new Set(['delivery']),
  outreach_claim_write: new Set(['outreach']),
  outreach_account_update: new Set(['outreach']),
};

function fail(message, details = {}) {
  process.stderr.write(`${JSON.stringify({ ok: false, authorized: false, error: message, ...details })}\n`);
  process.exit(2);
}

function parse(argv) {
  const out = { _: [] };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (!value.startsWith('--')) out._.push(value);
    else {
      const key = value.slice(2);
      const next = argv[index + 1];
      if (next === undefined || next.startsWith('--')) out[key] = true;
      else {
        out[key] = next;
        index += 1;
      }
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
  if (!/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}$/.test(text)) fail(`Invalid ${field}`);
  return text;
}

function readLedger(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    fail('Cannot read Commander ledger', { state_file: file, cause: error.message });
  }
}

function transitionEvents(state) {
  const transitions = new Set(['stage_started', 'stage_accepted', 'retrying', 'blocked']);
  return (state.events || [])
    .map((entry) => entry?.payload || entry)
    .filter((payload) => payload && transitions.has(payload.event));
}

const args = parse(process.argv.slice(2));
if (args._[0] !== 'authorize') {
  fail('Usage: workflow-write-guard.mjs authorize --run-id ID --attempt-id ID --execution-id ID --lease-id ID --worker-agent-id ID --stage-id ID --stage-attempt N --intent INTENT');
}

const runId = safeId(required(args, 'run-id'), 'run_id');
const attemptId = safeId(required(args, 'attempt-id'), 'attempt_id');
const executionId = safeId(required(args, 'execution-id'), 'execution_id');
const leaseId = safeId(required(args, 'lease-id'), 'lease_id');
const workerAgentId = safeId(required(args, 'worker-agent-id'), 'worker_agent_id');
const stageId = safeId(required(args, 'stage-id'), 'stage_id');
const intent = safeId(required(args, 'intent'), 'intent');
const stageAttempt = Number(required(args, 'stage-attempt'));

if (!Number.isInteger(stageAttempt) || stageAttempt < 1) fail('Invalid stage_attempt');
if (!WRITE_INTENTS[intent]) fail('Unknown write intent', { intent });
if (!WRITE_INTENTS[intent].has(stageId)) fail('Write intent is not allowed for this stage', { intent, stage_id: stageId });

const rawStateDir = args['state-dir'] || DEFAULT_STATE_DIR;
if (!rawStateDir) fail('state-dir is required: pass --state-dir <path> or set OPENCLAW_WORKFLOW_STATE_DIR');
const stateDir = path.resolve(String(rawStateDir));
const stateFile = path.join(stateDir, `${runId}__${attemptId}.json`);
const state = readLedger(stateFile);

const expectedExecutionId = `${runId}:${attemptId}`;
if (executionId !== expectedExecutionId || state.execution_id !== executionId) {
  fail('Execution identity mismatch', { execution_id: executionId, ledger_execution_id: state.execution_id });
}
if (state.run_id !== runId || state.attempt_id !== attemptId) fail('Run identity mismatch');
if (state.worker_agent_id !== workerAgentId) {
  fail('Worker agent mismatch', { worker_agent_id: workerAgentId, ledger_worker_agent_id: state.worker_agent_id });
}
if (state.lease_id !== leaseId) fail('Commander lease mismatch');
if (state.terminal) fail('Execution is terminal and immutable', { terminal_status: state.terminal.status });
if (state.pending_relay) fail('Commander event relay is pending; writes are fenced until event state is durable');

const transitions = transitionEvents(state);
const active = transitions.at(-1);
if (!active || active.event !== 'stage_started') {
  fail('No writable stage is active', { latest_transition: active?.event || null });
}
if (active.stage_id !== stageId || Number(active.stage_attempt) !== stageAttempt) {
  fail('Stale or out-of-order worker attempt', {
    requested_stage: stageId,
    requested_stage_attempt: stageAttempt,
    active_stage: active.stage_id,
    active_stage_attempt: active.stage_attempt,
    active_event_id: active.event_id,
  });
}

const tokenSource = [executionId, leaseId, workerAgentId, stageId, stageAttempt, intent, active.event_id].join('|');
const fenceToken = crypto.createHash('sha256').update(tokenSource).digest('hex');

process.stdout.write(`${JSON.stringify({
  ok: true,
  authorized: true,
  schema_version: 2,
  run_id: runId,
  attempt_id: attemptId,
  execution_id: executionId,
  worker_agent_id: workerAgentId,
  stage_id: stageId,
  stage_attempt: stageAttempt,
  intent,
  commander_event_id: active.event_id,
  fence_token: fenceToken,
  state_file: stateFile,
})}\n`);
