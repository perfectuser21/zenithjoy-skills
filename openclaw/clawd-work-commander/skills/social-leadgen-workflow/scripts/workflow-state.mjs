#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const STAGES = ['discovery', 'qualification', 'collection', 'scoring', 'delivery'];
const STATUSES = new Set(['pending', 'running', 'completed', 'blocked', 'failed']);

function parse(argv) {
  const command = argv[2];
  const args = {};
  for (let index = 3; index < argv.length; index += 2) {
    if (!argv[index]?.startsWith('--') || index + 1 >= argv.length) throw new Error(`Invalid argument near ${argv[index] || '<end>'}`);
    args[argv[index].slice(2)] = argv[index + 1];
  }
  return { command, args };
}

function fileFor(jobDir) {
  return path.join(path.resolve(jobDir), 'workflow-state.json');
}

function writeAtomic(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temporary, file);
}

function read(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function nextStage(state) {
  return STAGES.find((stage) => state.stages[stage]?.status !== 'completed') || null;
}

function required(args, names) {
  for (const name of names) if (!args[name]) throw new Error(`Missing --${name}`);
}

function main() {
  const { command, args } = parse(process.argv);
  required(args, ['job-dir']);
  const file = fileFor(args['job-dir']);

  if (command === 'init') {
    required(args, ['job-id', 'tenant-id', 'platform', 'window-start', 'window-end']);
    if (!fs.existsSync(file)) {
      const now = new Date().toISOString();
      writeAtomic(file, {
        schema_version: 1,
        job_id: args['job-id'],
        tenant_id: args['tenant-id'],
        platform: args.platform,
        window: { start: args['window-start'], end: args['window-end'] },
        created_at: now,
        updated_at: now,
        stages: Object.fromEntries(STAGES.map((stage) => [stage, { status: 'pending', attempts: 0, updated_at: now, note: '' }]))
      });
    }
    const state = read(file);
    process.stdout.write(`${JSON.stringify({ ok: true, state_file: file, next_stage: nextStage(state), state })}\n`);
    return;
  }

  if (!fs.existsSync(file)) throw new Error(`State does not exist: ${file}`);
  const state = read(file);
  if (command === 'show') {
    process.stdout.write(`${JSON.stringify({ ok: true, state_file: file, next_stage: nextStage(state), state })}\n`);
    return;
  }

  if (command !== 'set') throw new Error('Command must be init, show, or set');
  required(args, ['stage', 'status']);
  if (!STAGES.includes(args.stage)) throw new Error(`Invalid --stage; expected ${STAGES.join(', ')}`);
  if (!STATUSES.has(args.status)) throw new Error('Invalid --status');
  const previous = state.stages[args.stage];
  const now = new Date().toISOString();
  state.stages[args.stage] = {
    ...previous,
    status: args.status,
    attempts: previous.attempts + (args.status === 'running' ? 1 : 0),
    updated_at: now,
    note: args.note || previous.note || ''
  };
  state.updated_at = now;
  writeAtomic(file, state);
  process.stdout.write(`${JSON.stringify({ ok: true, state_file: file, stage: args.stage, status: args.status, next_stage: nextStage(state) })}\n`);
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
