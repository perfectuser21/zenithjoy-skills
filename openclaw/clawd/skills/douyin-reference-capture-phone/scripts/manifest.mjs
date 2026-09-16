#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

function parse(argv) {
  const command = argv[2];
  const args = {};
  for (let i = 3; i < argv.length; i += 2) {
    const key = argv[i];
    if (!key?.startsWith('--') || i + 1 >= argv.length) throw new Error(`Invalid argument near ${key || '<end>'}`);
    args[key.slice(2)] = argv[i + 1];
  }
  return { command, args };
}

function atomicWrite(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temporary, file);
}

function main() {
  const { command, args } = parse(process.argv);
  if (!args.manifest) throw new Error('Missing --manifest');
  const manifest = path.resolve(args.manifest);
  if (command === 'init') {
    if (!args['job-id']) throw new Error('Missing --job-id');
    if (fs.existsSync(manifest)) {
      process.stdout.write(`${JSON.stringify({ ok: true, existing: true, manifest })}\n`);
      return;
    }
    atomicWrite(manifest, { schema_version: 1, job_id: args['job-id'], created_at: new Date().toISOString(), updated_at: new Date().toISOString(), segments: [] });
    process.stdout.write(`${JSON.stringify({ ok: true, created: true, manifest })}\n`);
    return;
  }
  if (command !== 'upsert') throw new Error('Command must be init or upsert');
  if (!args['segment-id']) throw new Error('Missing --segment-id');
  const data = JSON.parse(fs.readFileSync(manifest, 'utf8'));
  if (!Array.isArray(data.segments)) data.segments = [];
  let result = {};
  if (args['result-path'] && fs.existsSync(args['result-path'])) result = JSON.parse(fs.readFileSync(args['result-path'], 'utf8'));
  const item = {
    segment_id: args['segment-id'],
    source_start: Number(args['source-start'] || result.source_start || 0),
    source_end: args['source-end'] === undefined ? null : Number(args['source-end']),
    status: args.status || 'pending',
    attempt_count: Number(args['attempt-count'] || 1),
    transcript_path: args['transcript-path'] || null,
    result_path: args['result-path'] || null,
    needs_review: Boolean(result.needs_review),
    repetition_signals: result.repetition_signals || [],
    updated_at: new Date().toISOString()
  };
  const index = data.segments.findIndex((entry) => entry.segment_id === item.segment_id);
  if (index >= 0) data.segments[index] = { ...data.segments[index], ...item };
  else data.segments.push(item);
  data.updated_at = new Date().toISOString();
  atomicWrite(manifest, data);
  process.stdout.write(`${JSON.stringify({ ok: true, manifest, segment_id: item.segment_id, replaced: index >= 0 })}\n`);
}

try { main(); } catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
