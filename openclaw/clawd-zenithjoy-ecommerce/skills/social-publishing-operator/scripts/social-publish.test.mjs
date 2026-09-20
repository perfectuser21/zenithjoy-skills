import assert from 'node:assert/strict';
import { mkdtemp, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const script = fileURLToPath(new URL('./social-publish.mjs', import.meta.url));

async function inputFile(value) {
  const directory = await mkdtemp(join(tmpdir(), 'social-publish-test-'));
  const path = join(directory, 'input.json');
  await writeFile(path, JSON.stringify(value));
  return path;
}

function run(path, env = {}, baseUrl) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [script, '--input', path, ...(baseUrl ? ['--base-url', baseUrl] : [])], {
      env: { ...process.env, ...env },
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    child.on('close', (code) => resolve({ code, stdout, stderr, json: JSON.parse(stdout) }));
  });
}

test('validates an Instagram preview without a secret', async () => {
  const path = await inputFile({
    tenant_id: 'zenithjoy',
    content_object_id: 'content-001',
    platform: 'instagram',
    delivery_mode: 'public',
    action: 'validate',
    media_url: 'https://www.zenithjoyai.com/media/one.jpg',
    caption: 'hello',
  });
  const result = await run(path, { SOCIAL_PUBLISH_BRIDGE_KEY: '' });
  assert.equal(result.code, 0);
  assert.equal(result.json.validated, true);
  assert.equal(result.json.request.body.mode, 'preview');
});

test('requires approval for an external write', async () => {
  const path = await inputFile({
    tenant_id: 'zenithjoy',
    content_object_id: 'content-002',
    platform: 'facebook',
    delivery_mode: 'public',
    action: 'execute',
    idempotency_key: 'content-002-facebook-v1',
    message: 'hello',
  });
  const result = await run(path);
  assert.equal(result.code, 1);
  assert.equal(result.json.error, 'approval_id_required');
});

test('blocks unsupported public TikTok posting', async () => {
  const path = await inputFile({
    tenant_id: 'zenithjoy',
    content_object_id: 'content-003',
    platform: 'tiktok',
    delivery_mode: 'public',
    action: 'validate',
    video_url: 'https://www.zenithjoyai.com/media/one.mp4',
  });
  const result = await run(path);
  assert.equal(result.code, 1);
  assert.equal(result.json.error, 'tiktok_public_not_available');
});

test('maps an approved TikTok draft upload to the bridge contract', async (t) => {
  let observed;
  const server = createServer((request, response) => {
    let body = '';
    request.on('data', (chunk) => { body += chunk; });
    request.on('end', () => {
      observed = { url: request.url, authorization: request.headers.authorization, body: JSON.parse(body) };
      response.writeHead(200, { 'Content-Type': 'application/json' });
      response.end(JSON.stringify({ ok: true, result: { publishId: 'publish-123' } }));
    });
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(() => server.close());
  const address = server.address();
  const baseUrl = `http://127.0.0.1:${address.port}`;
  const path = await inputFile({
    tenant_id: 'zenithjoy',
    content_object_id: 'content-004',
    platform: 'tiktok',
    delivery_mode: 'draft',
    action: 'execute',
    approval_id: 'approval-004',
    idempotency_key: 'content-004-tiktok-v1',
    video_url: 'https://www.zenithjoyai.com/media/one.mp4',
  });
  const result = await run(path, { SOCIAL_PUBLISH_BRIDGE_KEY: 'test-only-key' }, baseUrl);
  assert.equal(result.code, 0);
  assert.equal(observed.url, '/api/tiktok/draft');
  assert.equal(observed.authorization, 'Bearer test-only-key');
  assert.equal(observed.body.confirm, 'UPLOAD_DRAFT');
  assert.equal(observed.body.mode, 'upload');
});

test('reads Meta status through the authenticated bridge', async (t) => {
  const server = createServer((request, response) => {
    assert.equal(request.url, '/api/meta/status');
    assert.equal(request.headers.authorization, 'Bearer test-only-key');
    response.writeHead(200, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify({ ok: true, publishingEnabled: false }));
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(() => server.close());
  const address = server.address();
  const path = await inputFile({
    tenant_id: 'zenithjoy',
    content_object_id: 'content-005',
    platform: 'facebook',
    delivery_mode: 'public',
    action: 'status',
  });
  const result = await run(path, { SOCIAL_PUBLISH_BRIDGE_KEY: 'test-only-key' }, `http://127.0.0.1:${address.port}`);
  assert.equal(result.code, 0);
  assert.equal(result.json.remote.publishingEnabled, false);
});
