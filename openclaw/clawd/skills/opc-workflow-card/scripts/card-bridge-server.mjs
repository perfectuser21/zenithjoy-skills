#!/usr/bin/env node

import http from 'node:http';
import fs from 'node:fs';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const HOST = process.env.OPC_CARD_BRIDGE_HOST || '0.0.0.0';
const PORT = Number(process.env.OPC_CARD_BRIDGE_PORT || 18791);
const CONFIG = process.env.OPENCLAW_CONFIG_PATH || '/root/.openclaw/clawdbot.json';
const SCRIPT = process.env.OPC_CARD_REGISTRY_SCRIPT || '/root/clawd/skills/opc-workflow-card/scripts/card-registry.mjs';
const MAX_BODY = 1024 * 1024;
let queue = Promise.resolve();

function send(res, status, body) {
  const text = JSON.stringify(body);
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'content-length': Buffer.byteLength(text) });
  res.end(text);
}

function configuredToken() {
  const config = JSON.parse(fs.readFileSync(CONFIG, 'utf8'));
  return String(config?.gateway?.auth?.token || '');
}

function authorized(req) {
  const token = configuredToken();
  if (!token) return false;
  const authorization = String(req.headers.authorization || '');
  const direct = String(req.headers['x-openclaw-token'] || '');
  return authorization === `Bearer ${token}` || direct === token;
}

async function readBody(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_BODY) throw new Error('request body too large');
    chunks.push(chunk);
  }
  const text = Buffer.concat(chunks).toString('utf8');
  return JSON.parse(text || '{}');
}

async function runRegistry(command, payload) {
  const payloadBase64 = Buffer.from(JSON.stringify(payload)).toString('base64');
  const { stdout } = await execFileAsync('/usr/local/bin/node', [SCRIPT, command, '--payload-base64', payloadBase64], {
    cwd: '/root/clawd',
    timeout: 120000,
    maxBuffer: 2 * 1024 * 1024,
    env: { ...process.env, HOME: '/root' },
  });
  const lines = stdout.trim().split(/\r?\n/).filter(Boolean);
  const result = JSON.parse(lines.at(-1) || '{}');
  if (!result.ok) throw new Error(result.error || 'card registry returned failure');
  return result;
}

function enqueue(work) {
  const next = queue.then(work, work);
  queue = next.catch(() => {});
  return next;
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === 'GET' && req.url === '/health') {
      send(res, 200, { ok: true, service: 'opc-card-bridge', schema_version: 2 });
      return;
    }
    if (req.method !== 'POST' || !['/event', '/action'].includes(req.url)) {
      send(res, 404, { ok: false, error: 'not found' });
      return;
    }
    if (!authorized(req)) {
      send(res, 401, { ok: false, error: 'unauthorized' });
      return;
    }
    const payload = await readBody(req);
    const command = req.url === '/event' ? 'upsert' : 'action';
    const result = await enqueue(() => runRegistry(command, payload));
    send(res, 200, result);
  } catch (error) {
    const status = /too large/.test(error.message) ? 413 : 500;
    send(res, status, { ok: false, error: error.message });
  }
});

server.listen(PORT, HOST, () => {
  process.stdout.write(`${JSON.stringify({ ok: true, service: 'opc-card-bridge', host: HOST, port: PORT })}\n`);
});

for (const signal of ['SIGTERM', 'SIGINT']) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
