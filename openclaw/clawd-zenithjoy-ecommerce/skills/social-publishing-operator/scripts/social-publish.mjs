#!/usr/bin/env node

import { readFile } from 'node:fs/promises';

const IDEMPOTENCY_RE = /^[A-Za-z0-9._:-]{8,128}$/;
const ACTIONS = new Set(['validate', 'preview', 'execute', 'status']);
const PLATFORMS = new Set(['facebook', 'instagram', 'tiktok']);

function output(value, exitCode = 0) {
  process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
  process.exitCode = exitCode;
}

function fail(error, detail) {
  output({ ok: false, error, ...(detail ? { detail } : {}) }, 1);
  return null;
}

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--input' || arg === '--base-url') {
      result[arg.slice(2)] = argv[index + 1];
      index += 1;
    } else {
      throw new Error(`unknown_argument:${arg}`);
    }
  }
  return result;
}

function requiredText(input, key) {
  const value = input[key];
  if (typeof value !== 'string' || !value.trim()) throw new Error(`missing_${key}`);
  return value.trim();
}

function optionalText(input, key) {
  const value = input[key];
  return typeof value === 'string' && value.trim() ? value.trim() : undefined;
}

function assertHttps(value, key) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`${key}_must_be_https`);
  }
  if (url.protocol !== 'https:' || url.username || url.password) {
    throw new Error(`${key}_must_be_https`);
  }
  return value;
}

function buildOperation(input) {
  if (input.tenant_id !== 'zenithjoy') throw new Error('unsupported_tenant');
  const contentObjectId = requiredText(input, 'content_object_id');
  const platform = requiredText(input, 'platform');
  const action = requiredText(input, 'action');
  if (!PLATFORMS.has(platform)) throw new Error('invalid_platform');
  if (!ACTIONS.has(action)) throw new Error('invalid_action');

  const approvalId = optionalText(input, 'approval_id');
  const idempotencyKey = optionalText(input, 'idempotency_key');
  if (action === 'execute') {
    if (!approvalId) throw new Error('approval_id_required');
    if (!idempotencyKey || !IDEMPOTENCY_RE.test(idempotencyKey)) {
      throw new Error('valid_idempotency_key_required');
    }
  }

  if (action === 'status') {
    if (platform === 'tiktok' && input.publish_id) {
      return {
        contentObjectId,
        platform,
        deliveryMode: optionalText(input, 'delivery_mode') || 'draft',
        action,
        approvalId,
        idempotencyKey,
        method: 'POST',
        path: '/api/tiktok/status',
        body: { publishId: requiredText(input, 'publish_id') },
      };
    }
    return {
      contentObjectId,
      platform,
      deliveryMode: optionalText(input, 'delivery_mode') || (platform === 'tiktok' ? 'draft' : 'public'),
      action,
      approvalId,
      idempotencyKey,
      method: 'GET',
      path: platform === 'tiktok' ? '/api/tiktok/creator' : '/api/meta/status',
    };
  }

  const deliveryMode = requiredText(input, 'delivery_mode');
  if (platform !== 'tiktok') {
    if (deliveryMode !== 'public') throw new Error('meta_delivery_mode_must_be_public');
    const mediaUrl = optionalText(input, 'media_url');
    if (mediaUrl) assertHttps(mediaUrl, 'media_url');
    const message = optionalText(input, 'message');
    const caption = optionalText(input, 'caption');
    if (platform === 'facebook' && !message && !mediaUrl) {
      throw new Error('facebook_message_or_media_required');
    }
    if (platform === 'instagram' && !mediaUrl) throw new Error('instagram_media_url_required');
    return {
      contentObjectId,
      platform,
      deliveryMode,
      action,
      approvalId,
      idempotencyKey,
      method: 'POST',
      path: '/api/meta/publish',
      body: {
        platform,
        mode: action === 'execute' ? 'publish' : 'preview',
        ...(action === 'execute' ? { confirm: 'PUBLISH', idempotencyKey } : {}),
        ...(message ? { message } : {}),
        ...(caption ? { caption } : {}),
        ...(mediaUrl ? { mediaUrl } : {}),
      },
    };
  }

  if (deliveryMode === 'public') throw new Error('tiktok_public_not_available');
  if (deliveryMode !== 'draft' && deliveryMode !== 'private') {
    throw new Error('invalid_tiktok_delivery_mode');
  }
  const videoUrl = assertHttps(requiredText(input, 'video_url'), 'video_url');
  if (deliveryMode === 'draft') {
    return {
      contentObjectId,
      platform,
      deliveryMode,
      action,
      approvalId,
      idempotencyKey,
      method: 'POST',
      path: '/api/tiktok/draft',
      body: {
        mode: action === 'execute' ? 'upload' : 'preview',
        ...(action === 'execute' ? { confirm: 'UPLOAD_DRAFT', idempotencyKey } : {}),
        videoUrl,
      },
    };
  }

  const durationSeconds = Number(input.duration_seconds);
  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0 || durationSeconds > 600) {
    throw new Error('valid_duration_seconds_required');
  }
  return {
    contentObjectId,
    platform,
    deliveryMode,
    action,
    approvalId,
    idempotencyKey,
    method: 'POST',
    path: '/api/tiktok/publish',
    body: {
      mode: action === 'execute' ? 'publish' : 'preview',
      ...(action === 'execute' ? { confirm: 'PUBLISH_PRIVATE', idempotencyKey } : {}),
      videoUrl,
      durationSeconds,
      title: optionalText(input, 'title') || '',
      isAigc: input.is_aigc === true,
      promotesOwnBrand: input.promotes_own_brand === true,
      paidPartnership: input.paid_partnership === true,
    },
  };
}

async function main() {
  let args;
  let input;
  let operation;
  try {
    args = parseArgs(process.argv.slice(2));
    if (!args.input) throw new Error('input_file_required');
    input = JSON.parse(await readFile(args.input, 'utf8'));
    operation = buildOperation(input);
  } catch (error) {
    return fail(error instanceof Error ? error.message : 'invalid_input');
  }

  if (operation.action === 'validate') {
    return output({
      ok: true,
      validated: true,
      contentObjectId: operation.contentObjectId,
      platform: operation.platform,
      deliveryMode: operation.deliveryMode,
      request: { method: operation.method, path: operation.path, body: operation.body || null },
    });
  }

  const key = process.env.SOCIAL_PUBLISH_BRIDGE_KEY;
  if (!key) return fail('SOCIAL_PUBLISH_BRIDGE_KEY_required');
  const baseUrl = (args['base-url'] || process.env.SOCIAL_PUBLISH_BRIDGE_URL || 'https://www.zenithjoyai.com').replace(/\/$/, '');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30_000);
  let response;
  let remote;
  try {
    response = await fetch(`${baseUrl}${operation.path}`, {
      method: operation.method,
      headers: {
        Authorization: `Bearer ${key}`,
        Accept: 'application/json',
        ...(operation.body ? { 'Content-Type': 'application/json' } : {}),
      },
      ...(operation.body ? { body: JSON.stringify(operation.body) } : {}),
      signal: controller.signal,
    });
    const raw = await response.text();
    remote = raw ? JSON.parse(raw) : null;
  } catch (error) {
    clearTimeout(timeout);
    return fail(error instanceof Error && error.name === 'AbortError' ? 'bridge_timeout' : 'bridge_unreachable');
  }
  clearTimeout(timeout);

  const ok = response.ok && remote?.ok !== false;
  return output({
    ok,
    contentObjectId: operation.contentObjectId,
    platform: operation.platform,
    deliveryMode: operation.deliveryMode,
    action: operation.action,
    approvalId: operation.approvalId || null,
    idempotencyKey: operation.idempotencyKey || null,
    httpStatus: response.status,
    remote,
    nextCheckAt: ok && operation.action === 'execute' ? new Date(Date.now() + 60_000).toISOString() : null,
  }, ok ? 0 : 2);
}

await main();
