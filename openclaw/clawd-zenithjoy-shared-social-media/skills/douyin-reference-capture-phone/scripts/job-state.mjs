#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const STAGES = ['discovery', 'acquisition', 'transcription', 'delivery'];

function parse(argv) {
  const command = argv[2];
  const args = {};
  for (let i = 3; i < argv.length; i += 2) {
    if (!argv[i]?.startsWith('--') || i + 1 >= argv.length) throw new Error(`Invalid argument near ${argv[i] || '<end>'}`);
    args[argv[i].slice(2)] = argv[i + 1];
  }
  return { command, args };
}

function statePath(jobDir) {
  return path.join(path.resolve(jobDir), 'job-state.json');
}

function writeAtomic(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temp, file);
}

function read(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function nextStage(state) {
  return STAGES.find((stage) => state.stages[stage]?.status !== 'completed') || null;
}

function main() {
  const { command, args } = parse(process.argv);
  if (!args['job-dir']) throw new Error('Missing --job-dir');
  const file = statePath(args['job-dir']);
  if (command === 'init') {
    if (!args['job-id'] || !args.topic) throw new Error('init requires --job-id and --topic');
    if (!fs.existsSync(file)) {
      const now = new Date().toISOString();
      writeAtomic(file, {
        schema_version: 1,
        job_id: args['job-id'],
        topic: args.topic,
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
  if (!STAGES.includes(args.stage)) throw new Error(`Invalid --stage; expected ${STAGES.join(', ')}`);
  const allowed = new Set(['pending', 'running', 'completed', 'blocked', 'failed']);
  if (!allowed.has(args.status)) throw new Error('Invalid --status');
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

try { main(); } catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
