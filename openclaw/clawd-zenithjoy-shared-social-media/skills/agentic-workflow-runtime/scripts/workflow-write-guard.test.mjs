#!/usr/bin/env node

import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const script = path.resolve(path.dirname(fileURLToPath(import.meta.url)), 'workflow-write-guard.mjs');
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'workflow-write-guard-'));
const runId = 'test-run';
const attemptId = 'a1';
const executionId = `${runId}:${attemptId}`;
const leaseId = `${executionId}:lease`;
const stateFile = path.join(tempDir, `${runId}__${attemptId}.json`);

const baseState = {
  schema_version: 2,
  run_id: runId,
  attempt_id: attemptId,
  execution_id: executionId,
  worker_agent_id: 'tenant-worker',
  lease_id: leaseId,
  pending_relay: null,
  terminal: null,
  events: [{
    marker: 'WORKFLOW_EVENT',
    payload: {
      event: 'stage_started',
      event_id: `${executionId}:2`,
      stage_id: 'collection',
      stage_attempt: 2,
    },
  }],
};

function writeState(value) {
  fs.writeFileSync(stateFile, `${JSON.stringify(value)}\n`);
}

function invoke(overrides = {}) {
  const values = {
    'run-id': runId,
    'attempt-id': attemptId,
    'execution-id': executionId,
    'lease-id': leaseId,
    'worker-agent-id': 'tenant-worker',
    'stage-id': 'collection',
    'stage-attempt': '2',
    intent: 'raw_comment_insert',
    'state-dir': tempDir,
    ...overrides,
  };
  const argv = ['authorize'];
  for (const [key, value] of Object.entries(values)) argv.push(`--${key}`, value);
  return spawnSync(process.execPath, [script, ...argv], { encoding: 'utf8' });
}

try {
  writeState(baseState);
  const accepted = invoke();
  assert.equal(accepted.status, 0, accepted.stderr);
  const receipt = JSON.parse(accepted.stdout);
  assert.equal(receipt.authorized, true);
  assert.equal(receipt.commander_event_id, `${executionId}:2`);
  assert.match(receipt.fence_token, /^[a-f0-9]{64}$/);

  const stale = invoke({ 'stage-attempt': '1' });
  assert.equal(stale.status, 2);
  assert.match(stale.stderr, /Stale or out-of-order worker attempt/);

  const wrongIntent = invoke({ intent: 'final_lead_write' });
  assert.equal(wrongIntent.status, 2);
  assert.match(wrongIntent.stderr, /not allowed for this stage/);

  writeState({
    ...baseState,
    events: [{ marker: 'WORKFLOW_EVENT', payload: { event: 'stage_started', event_id: `${executionId}:3`, stage_id: 'scoring', stage_attempt: 1 } }],
  });
  const scoringUpdate = invoke({ 'stage-id': 'scoring', 'stage-attempt': '1', intent: 'raw_comment_update' });
  assert.equal(scoringUpdate.status, 0, scoringUpdate.stderr);
  assert.equal(JSON.parse(scoringUpdate.stdout).authorized, true);
  const scoringFinalWrite = invoke({ 'stage-id': 'scoring', 'stage-attempt': '1', intent: 'final_lead_write' });
  assert.equal(scoringFinalWrite.status, 2);
  assert.match(scoringFinalWrite.stderr, /not allowed for this stage/);

  writeState({ ...baseState, terminal: { status: 'completed' } });
  const terminal = invoke();
  assert.equal(terminal.status, 2);
  assert.match(terminal.stderr, /terminal and immutable/);

  process.stdout.write('workflow-write-guard tests passed\n');
} finally {
  fs.rmSync(tempDir, { recursive: true, force: true });
}
