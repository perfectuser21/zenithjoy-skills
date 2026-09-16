#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

function argsOf(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 2) out[argv[i]?.replace(/^--/, '')] = argv[i + 1];
  return out;
}

function readMaybe(file, fallback = '') {
  return file && fs.existsSync(file) ? fs.readFileSync(file, 'utf8').trim() : fallback;
}

function main() {
  const args = argsOf(process.argv);
  if (!args.metadata || !args.raw || !args.clean || !args.output) throw new Error('Usage: build-delivery.mjs --metadata meta.json --raw raw.txt --clean clean.txt --output delivery.md');
  const meta = JSON.parse(fs.readFileSync(args.metadata, 'utf8'));
  const raw = readMaybe(args.raw, '[缺失]');
  const clean = readMaybe(args.clean, '[缺失]');
  const lines = [
    `# ${meta.title || '抖音视频 ASR 全文'}`, '',
    '> 本文档是 ASR 转写产物，不包含模型校对、内容分析或业务判定。', '',
    '## 来源信息', '',
    `- 作者：${meta.author || '未知'}`,
    `- 来源：${meta.source_url || meta.source_reference || '未取得链接'}`,
    `- 发布时间：${meta.published_at || '未知'}`,
    `- 时长：${meta.duration_seconds ?? '未知'} 秒`,
    `- 采集时间：${meta.captured_at || new Date().toISOString()}`,
    `- ASR：${meta.asr_model || 'gemini-2.5-flash-lite-official'}`,
    `- Job：${meta.job_id || '未知'}`, '',
    '## ASR 全文', '', clean, '',
    '<details>', '<summary>原始机器转写（审计证据）</summary>', '', raw, '', '</details>', ''
  ];
  fs.mkdirSync(path.dirname(path.resolve(args.output)), { recursive: true });
  fs.writeFileSync(args.output, lines.join('\n'));
  process.stdout.write(`${JSON.stringify({ ok: true, output: path.resolve(args.output) })}\n`);
}

try { main(); } catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
