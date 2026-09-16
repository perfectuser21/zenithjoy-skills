#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const LOCK = '/root/clawd-media/locks/douyin-phone.lock.json';
const LEASE_MS = 10 * 60 * 1000;

function parse(argv) {
  const command = argv[2];
  const args = {};
  for (let i = 3; i < argv.length; i += 2) {
    if (!argv[i]?.startsWith('--') || i + 1 >= argv.length) throw new Error(`Invalid argument near ${argv[i] || '<end>'}`);
    args[argv[i].slice(2)] = argv[i + 1];
  }
  return { command, args };
}

function current() {
  if (!fs.existsSync(LOCK)) return null;
  try { return JSON.parse(fs.readFileSync(LOCK, 'utf8')); } catch { return { invalid: true, acquired_at_ms: 0 }; }
}

function main() {
  const { command, args } = parse(process.argv);
  const lock = current();
  if (command === 'show') {
    process.stdout.write(`${JSON.stringify({ ok: true, lock })}\n`);
    return;
  }
  if (!args['job-id']) throw new Error('Missing --job-id');
  if (command === 'release') {
    if (!lock) return process.stdout.write(`${JSON.stringify({ ok: true, released: false, reason: 'not_locked' })}\n`);
    if (lock.job_id !== args['job-id']) throw new Error(`Lock belongs to ${lock.job_id}`);
    fs.unlinkSync(LOCK);
    process.stdout.write(`${JSON.stringify({ ok: true, released: true, job_id: args['job-id'] })}\n`);
    return;
  }
  if (command !== 'acquire') throw new Error('Command must be acquire, release, or show');
  fs.mkdirSync(path.dirname(LOCK), { recursive: true });
  const now = Date.now();
  if (lock && lock.job_id === args['job-id']) {
    process.stdout.write(`${JSON.stringify({ ok: true, acquired: true, existing: true, lock })}\n`);
    return;
  }
  if (lock && now - Number(lock.acquired_at_ms || 0) <= LEASE_MS) throw new Error(`PHONE_LOCKED by ${lock.job_id || 'unknown'} stage=${lock.stage || 'unknown'}`);
  if (lock) fs.unlinkSync(LOCK);
  const value = { job_id: args['job-id'], stage: args.stage || 'unknown', acquired_at: new Date(now).toISOString(), acquired_at_ms: now, lease_ms: LEASE_MS };
  const fd = fs.openSync(LOCK, 'wx', 0o600);
  fs.writeFileSync(fd, `${JSON.stringify(value, null, 2)}\n`);
  fs.closeSync(fd);
  process.stdout.write(`${JSON.stringify({ ok: true, acquired: true, existing: false, lock: value })}\n`);
}

try { main(); } catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
