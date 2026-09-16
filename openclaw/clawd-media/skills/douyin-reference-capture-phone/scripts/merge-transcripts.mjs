#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

function argsOf(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 2) out[argv[i]?.replace(/^--/, '')] = argv[i + 1];
  return out;
}

function normalize(text) {
  return text.replace(/\r/g, '').replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim();
}

function overlapLength(left, right) {
  const max = Math.min(120, left.length, right.length);
  for (let n = max; n >= 6; n -= 1) if (left.slice(-n) === right.slice(0, n)) return n;
  return 0;
}

function removeConsecutiveRepeats(text) {
  let output = text;
  let changed = false;
  for (let pass = 0; pass < 3; pass += 1) {
    const next = output.replace(/([^。！？!?\n]{8,80}[。！？!?])(?:\s*\1){1,}/gu, '$1');
    if (next === output) break;
    output = next;
    changed = true;
  }
  return { text: output, changed };
}

function main() {
  const args = argsOf(process.argv);
  if (!args.manifest || !args['output-dir']) throw new Error('Usage: merge-transcripts.mjs --manifest segments.json --output-dir DIR');
  const manifestPath = path.resolve(args.manifest);
  const outputDir = path.resolve(args['output-dir']);
  const parsed = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const segments = Array.isArray(parsed) ? parsed : parsed.segments;
  if (!Array.isArray(segments) || segments.length === 0) throw new Error('Manifest has no segments');
  fs.mkdirSync(outputDir, { recursive: true });
  const loaded = segments.map((segment, index) => {
    let transcript = segment.transcript;
    if (!transcript && segment.transcript_path) transcript = fs.readFileSync(path.resolve(path.dirname(manifestPath), segment.transcript_path), 'utf8');
    if (!transcript) throw new Error(`Missing transcript for segment ${segment.segment_id || index}`);
    return { ...segment, order: index, text: normalize(transcript), source_start: Number(segment.source_start || 0) };
  }).sort((a, b) => a.source_start - b.source_start || a.order - b.order);
  const raw = loaded.map((s) => `[${s.segment_id || s.order} @ ${s.source_start.toFixed(1)}s]\n${s.text}`).join('\n\n');
  let clean = '';
  const boundaries = [];
  for (const segment of loaded) {
    const n = overlapLength(clean, segment.text);
    boundaries.push({ segment_id: segment.segment_id || segment.order, removed_overlap_chars: n });
    clean += (clean ? '\n' : '') + segment.text.slice(n);
  }
  const deduped = removeConsecutiveRepeats(normalize(clean));
  clean = normalize(deduped.text);
  const reviewSegments = loaded.filter((s) => s.needs_review || s.repetition_signals?.length).map((s) => s.segment_id || s.order);
  const result = { ok: true, segments: loaded.length, boundaries, consecutive_repetition_removed: deduped.changed, review_segments: reviewSegments, needs_review: deduped.changed || reviewSegments.length > 0 };
  fs.writeFileSync(path.join(outputDir, 'raw-transcript.txt'), `${raw}\n`);
  fs.writeFileSync(path.join(outputDir, 'clean-transcript.txt'), `${clean}\n`);
  fs.writeFileSync(path.join(outputDir, 'merge-result.json'), `${JSON.stringify(result, null, 2)}\n`);
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

try { main(); } catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
