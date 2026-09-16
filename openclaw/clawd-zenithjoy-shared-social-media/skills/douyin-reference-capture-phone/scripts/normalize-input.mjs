#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

function parse(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 2) {
    if (!argv[i]?.startsWith('--') || i + 1 >= argv.length) throw new Error(`Invalid argument near ${argv[i] || '<end>'}`);
    args[argv[i].slice(2)] = argv[i + 1];
  }
  return args;
}

function writeAtomic(file, value) {
  fs.mkdirSync(path.dirname(path.resolve(file)), { recursive: true });
  const target = path.resolve(file);
  const temp = `${target}.tmp-${process.pid}`;
  fs.writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temp, target);
}

function extractUrl(text) {
  const matches = String(text).match(/https?:\/\/[^\s<>"'，。；]+/giu) || [];
  return matches.find((value) => {
    try {
      const host = new URL(value).hostname.toLowerCase();
      return host === 'douyin.com' || host.endsWith('.douyin.com') || host === 'iesdouyin.com' || host.endsWith('.iesdouyin.com');
    } catch {
      return false;
    }
  }) || null;
}

function videoIdFrom(value) {
  if (!value) return null;
  const match = String(value).match(/(?:\/video\/|\/m\/video\/|aweme\/detail\/)(\d{15,22})/u);
  return match?.[1] || null;
}

async function resolveUrl(originalUrl) {
  try {
    const response = await fetch(originalUrl, {
      method: 'GET',
      redirect: 'follow',
      headers: { 'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36' },
      signal: AbortSignal.timeout(15_000)
    });
    return { url: response.url || originalUrl, status: response.ok ? 'resolved' : `http_${response.status}` };
  } catch (error) {
    return { url: originalUrl, status: 'unresolved', error: String(error?.message || error) };
  }
}

const args = parse(process.argv);
if (!args.input || !args.output) throw new Error('Required: --input <text> --output <path>');

const originalUrl = extractUrl(args.input);
if (!originalUrl) {
  writeAtomic(args.output, {
    schema_version: 1,
    mode: 'topic',
    topic: args.input.trim(),
    created_at: new Date().toISOString()
  });
  process.stdout.write(`${JSON.stringify({ ok: true, mode: 'topic', output: path.resolve(args.output) })}\n`);
} else {
  const resolved = await resolveUrl(originalUrl);
  const videoId = videoIdFrom(resolved.url) || videoIdFrom(originalUrl);
  const result = {
    schema_version: 1,
    mode: 'direct_url',
    original_input: args.input,
    original_url: originalUrl,
    resolved_url: resolved.url,
    resolution_status: resolved.status,
    video_id: videoId,
    app_uri: videoId ? `snssdk1128://aweme/detail/${videoId}` : resolved.url,
    created_at: new Date().toISOString()
  };
  if (resolved.error) result.resolution_error = resolved.error;
  writeAtomic(args.output, result);
  process.stdout.write(`${JSON.stringify({ ok: true, mode: result.mode, video_id: result.video_id, resolution_status: result.resolution_status, output: path.resolve(args.output) })}\n`);
}
