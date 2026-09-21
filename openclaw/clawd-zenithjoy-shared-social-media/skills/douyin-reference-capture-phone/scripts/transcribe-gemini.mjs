#!/usr/bin/env node
// transcribe-gemini.mjs — ASR via toapis(OpenAI 兼容),wav 大音频自动分片版。
// 09-03 案卷(issue ed2886f3):44.8s 音频整段发 363s 全超时;按 20s 切片后 129s 全转成功。
// marker=segment-seconds(默认 20);非 wav 或短音频走原单发路径,调用方接口不变。
// 09-05 重建:原热补丁未进 git 被 workspace migration 抹掉,本版必须 commit 进 workspace 仓。

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    if (!key.startsWith('--')) throw new Error(`Unexpected argument: ${key}`);
    const name = key.slice(2);
    if (name === 'dry-run') out[name] = true;
    else {
      if (i + 1 >= argv.length) throw new Error(`Missing value for ${key}`);
      out[name] = argv[++i];
    }
  }
  return out;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function audioFormat(input) {
  const ext = path.extname(input).slice(1).toLowerCase();
  const supported = new Set(['wav', 'mp3', 'm4a', 'aac', 'flac', 'ogg']);
  if (!supported.has(ext)) throw new Error(`Unsupported audio extension: .${ext}`);
  return ext;
}

// ---------- wav RIFF 解析(遍历 chunk 找 data,禁止假设 44 字节头) ----------
function parseWav(buf) {
  if (buf.length < 12 || buf.toString('ascii', 0, 4) !== 'RIFF' || buf.toString('ascii', 8, 12) !== 'WAVE') return null;
  let off = 12;
  let fmt = null;
  let dataOffset = -1;
  let dataLength = 0;
  while (off + 8 <= buf.length) {
    const id = buf.toString('ascii', off, off + 4);
    const size = buf.readUInt32LE(off + 4);
    const body = off + 8;
    if (id === 'fmt ' && body + 16 <= buf.length) {
      fmt = {
        audioFormat: buf.readUInt16LE(body),
        channels: buf.readUInt16LE(body + 2),
        sampleRate: buf.readUInt32LE(body + 4),
        byteRate: buf.readUInt32LE(body + 8),
        blockAlign: buf.readUInt16LE(body + 12),
        bitsPerSample: buf.readUInt16LE(body + 14),
      };
    } else if (id === 'data') {
      dataOffset = body;
      dataLength = Math.min(size, buf.length - body);
    }
    off = body + size + (size % 2); // chunk 按 2 字节对齐
  }
  if (!fmt || dataOffset < 0 || dataLength <= 0) return null;
  if (fmt.audioFormat !== 1) return null; // 只切 PCM;压缩 wav 走单发
  return { fmt, dataOffset, dataLength };
}

function buildWavHeader(fmt, dataLen) {
  const h = Buffer.alloc(44);
  h.write('RIFF', 0, 'ascii');
  h.writeUInt32LE(36 + dataLen, 4);
  h.write('WAVE', 8, 'ascii');
  h.write('fmt ', 12, 'ascii');
  h.writeUInt32LE(16, 16);
  h.writeUInt16LE(fmt.audioFormat, 20);
  h.writeUInt16LE(fmt.channels, 22);
  h.writeUInt32LE(fmt.sampleRate, 24);
  h.writeUInt32LE(fmt.byteRate, 28);
  h.writeUInt16LE(fmt.blockAlign, 32);
  h.writeUInt16LE(fmt.bitsPerSample, 34);
  h.write('data', 36, 'ascii');
  h.writeUInt32LE(dataLen, 40);
  return h;
}

function sliceWav(buf, wav, segmentSeconds) {
  const bytesPerSecond = wav.fmt.byteRate || (wav.fmt.sampleRate * wav.fmt.blockAlign);
  let segBytes = Math.max(wav.fmt.blockAlign, Math.floor(bytesPerSecond * segmentSeconds));
  segBytes -= segBytes % wav.fmt.blockAlign; // 对齐 block,防半帧 400
  const out = [];
  for (let start = 0; start < wav.dataLength; start += segBytes) {
    const len = Math.min(segBytes, wav.dataLength - start);
    const pcm = buf.subarray(wav.dataOffset + start, wav.dataOffset + start + len);
    out.push({
      buffer: Buffer.concat([buildWavHeader(wav.fmt, len), pcm]),
      startSec: start / bytesPerSecond,
    });
  }
  return out;
}

// ---------- 复读退化清理(3 倍速尾部吐重复标点;实测 47299 字垃圾 → 454 字) ----------
function sanitizeTranscript(text) {
  let t = text;
  // 1) 单字符(标点/空白为主)连打 >3 → 保留 1 个
  t = t.replace(/([。，、！？!?.,\s])\1{3,}/g, '$1');
  // 2) 短片段(≤20 字)连续重复 ≥3 次 → 保留 1 次;迭代到不动点(上限 5 轮防病态)
  for (let i = 0; i < 5; i += 1) {
    const next = t.replace(/(.{2,20}?)\1{2,}/g, '$1');
    if (next === t) break;
    t = next;
  }
  return t.trim();
}

function repetitionSignals(text) {
  const compact = text.replace(/\s+/g, ' ').trim();
  const signals = [];
  const sentences = compact.split(/(?<=[。！？!?])/).map((x) => x.trim()).filter(Boolean);
  for (let width = 1; width <= Math.min(3, Math.floor(sentences.length / 2)); width += 1) {
    const tail = sentences.slice(-width).join('');
    const previous = sentences.slice(-2 * width, -width).join('');
    if (tail.length >= 8 && tail === previous) signals.push(`repeated_tail_${width}_sentences`);
  }
  return [...new Set(signals)];
}

// ---------- 逐词时间戳 -> 带时间的句子（2026-09-11 踩坑三次后固化）----------
// 通义 qwen-audio-3.0-asr-flash 的 sentence.text 标点完整，但 words[] 里绝大多数词的
// punctuation 为空（实测 134 词仅 21 个带标点）。按 words.punctuation 断句会把 57 秒
// 口播切成 119 个碎片（句均 0.5 秒），不可用。
// 正解：以 text 的标点断句，再按字符序把 words 的时间戳对齐上去。
// speed = 录制倍速（3 倍速录制传 3），输出即视频真实时刻（ms）。
export function sentencesWithTiming(text, words, speed = 1) {
  if (!text || !Array.isArray(words) || words.length === 0) return [];
  const mult = Number(speed) > 0 ? Number(speed) : 1;
  const chars = [];
  words.forEach((w, wi) => { for (const ch of String(w.text || "")) chars.push({ ch, wi }); });
  const out = [];
  let ci = 0, buf = "", firstWi = null, lastWi = null;
  const flush = () => {
    if (!buf.trim() || firstWi === null) { buf = ""; firstWi = null; lastWi = null; return; }
    const a = words[firstWi], b = words[lastWi === null ? firstWi : lastWi];
    out.push({ text: buf,
      begin: Math.round(Number(a.begin_time || 0) * mult),
      end: Math.round(Number(b.end_time || 0) * mult) });
    buf = ""; firstWi = null; lastWi = null;
  };
  for (const ch of String(text)) {
    buf += ch;
    if ("。！？!?".includes(ch)) { flush(); continue; }
    if (ci < chars.length && chars[ci].ch === ch) {
      if (firstWi === null) firstWi = chars[ci].wi;
      lastWi = chars[ci].wi; ci += 1;
    } else if (firstWi === null && ci < chars.length) {
      // text 与 words 出现偏移（漏字/多字）时，仍把当前词位置作为句起点，
      // 避免整句因对不齐而被丢弃——尤其是结尾没有句末标点的残句。
      firstWi = chars[ci].wi; lastWi = chars[ci].wi;
    }
  }
  flush();
  return out;
}

// ---------- 通义 DashScope 通道（2026-09-11 起为默认）----------
// 实测（TTS ground truth 对照，见 __tests__/asr-benchmark）：
//   3 倍速录制音频下，gemini-2.5-flash-lite 字级准确率 70.7%、业务关键词 2/9，
//   且会整段改写题材（把"人工智能训练师考证"听成"职场生存/数据报表"）；
//   qwen-audio-3.0-asr-flash 同一份音频 100%、9/9；6.3 分钟长稿 89.8%、
//   中文专有名词/数字/钩子零失误。故默认切通义，gemini 保留为 fallback。
// 额外收益：返回带逐词毫秒时间戳（words[]），可做钩子定位与结构拆解。
async function transcribeDashscope({ base64Audio, format, apiKey, model }) {
  const body = {
    model,
    input: { messages: [{ role: 'user', content: [{ audio: `data:audio/${format};base64,${base64Audio}` }] }] },
    parameters: { format },  // 必填，缺了报 UNSUPPORTED_FORMAT: format is empty
  };
  const res = await fetch('https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation', {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`DashScope ${res.status}: ${(await res.text()).slice(0, 200)}`);
  const payload = await res.json();
  const out = payload?.output?.output;
  const sentence = out?.sentence || {};
  return {
    transcript: String(sentence.text || out?.text || '').trim(),
    words: Array.isArray(sentence.words) ? sentence.words : [],
    durationSeconds: payload?.usage?.duration ?? null,
    raw: payload,
  };
}

function redactResponse(payload) {
  const copy = structuredClone(payload);
  if (copy?.request) delete copy.request;
  return copy;
}

async function transcribeOnce({ base64, format, apiBase, apiKey, model, prompt }) {
  const body = {
    model,
    temperature: 0,
    messages: [{
      role: 'user',
      content: [
        { type: 'text', text: prompt },
        { type: 'input_audio', input_audio: { data: base64, format } },
      ],
    }],
  };
  let responsePayload;
  let status = 0;
  let lastError;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      const response = await fetch(`${apiBase}/chat/completions`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(120_000),
      });
      status = response.status;
      const text = await response.text();
      try { responsePayload = JSON.parse(text); } catch { responsePayload = { error: { message: text.slice(0, 1000) } }; }
      if (response.ok) break;
      const retryable = response.status === 408 || response.status === 429 || response.status >= 500;
      lastError = new Error(`ASR HTTP ${response.status}: ${responsePayload?.error?.message || 'unknown error'}`);
      if (!retryable || attempt === 3) throw lastError;
    } catch (error) {
      lastError = error;
      if (attempt === 3) throw error;
    }
    await sleep(750 * (2 ** (attempt - 1)));
  }
  const transcript = responsePayload?.choices?.[0]?.message?.content?.trim();
  if (!transcript) throw lastError || new Error('ASR returned no transcript');
  return { transcript, responsePayload, status };
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.input || !args['output-dir']) {
    throw new Error('Usage: transcribe-gemini.mjs --input FILE --output-dir DIR [--segment-id ID] [--source-start SEC] [--segment-seconds N] [--dry-run]');
  }
  const input = path.resolve(args.input);
  const outputDir = path.resolve(args['output-dir']);
  // provider: dashscope(默认,通义) | gemini(旧通道,fallback)
  const provider = args.provider || 'dashscope';
  const isDash = provider === 'dashscope';
  const model = args.model || (isDash ? 'qwen-audio-3.0-asr-flash' : 'gemini-2.5-flash-lite-official');
  const apiBase = (args['api-base'] || 'https://toapis.com/v1').replace(/\/$/, '');
  const defaultKeyFile = isDash
    ? '/Users/administrator/.openclaw/credentials/dashscope-api-key'
    : '/Users/administrator/.openclaw/credentials/toapis-api-key';
  const keyFile = args['api-key-file'] || defaultKeyFile;
  // 录制倍速：3 倍速录制时传 3，时间戳换算成视频真实时刻
  const speed = Number(args.speed || 1);
  const segmentId = args['segment-id'] || path.basename(input, path.extname(input));
  const sourceStart = Number(args['source-start'] || 0);
  const segmentSeconds = Math.max(5, Number(args['segment-seconds'] || 20));
  const stat = fs.statSync(input);
  if (!stat.isFile() || stat.size === 0) throw new Error(`Input is empty or not a file: ${input}`);
  if (stat.size > 20 * 1024 * 1024) throw new Error('Audio segment exceeds 20 MiB; split it before inline upload');
  fs.mkdirSync(outputDir, { recursive: true });

  const format = audioFormat(input);
  const raw = fs.readFileSync(input);
  // 分片决策:wav + PCM + 时长超过一片 → 切;否则单发(mp3 等压缩格式无法纯 JS 切)
  let segments = null;
  if (format === 'wav') {
    const wav = parseWav(raw);
    if (wav) {
      const bytesPerSecond = wav.fmt.byteRate || (wav.fmt.sampleRate * wav.fmt.blockAlign);
      const durationSec = wav.dataLength / bytesPerSecond;
      if (durationSec > segmentSeconds * 1.25) segments = sliceWav(raw, wav, segmentSeconds);
    }
  }

  if (args['dry-run']) {
    const result = {
      ok: true, dry_run: true, input, bytes: stat.size, model,
      segment_id: segmentId, source_start: sourceStart,
      segment_seconds: segmentSeconds, planned_segments: segments ? segments.length : 1,
    };
    fs.writeFileSync(path.join(outputDir, 'result.json'), `${JSON.stringify(result, null, 2)}\n`);
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return;
  }

  let apiKey = (isDash ? process.env.DASHSCOPE_API_KEY : process.env.TOAPIS_API_KEY)?.trim();
  if (!apiKey && fs.existsSync(keyFile)) apiKey = fs.readFileSync(keyFile, 'utf8').trim();
  if (!apiKey) {
    throw new Error(isDash
      ? `Missing DASHSCOPE_API_KEY and key file ${keyFile}`
      : 'Missing TOAPIS_API_KEY and API key file');
  }

  // 通义通道：整段直发，不分片（实测 126 秒音频单发即可，且分片会破坏时间戳连续性）
  if (isDash) {
    const started = Date.now();
    const r = await transcribeDashscope({
      base64Audio: raw.toString('base64'), format, apiKey, model,
    });
    const sentences = sentencesWithTiming(r.transcript, r.words, speed);
    const result = {
      ok: true, provider: 'dashscope', model,
      segment_id: segmentId, source_start: sourceStart,
      chars: r.transcript.length,
      duration_ms: Date.now() - started,
      billed_seconds: r.durationSeconds,
      speed,
      transcript: r.transcript,
      words: r.words,           // 逐词毫秒时间戳（原始，未乘倍速）
      sentences,                // 断句 + 已按 speed 换算成视频真实时刻
      transcript_preview: r.transcript.slice(0, 120),
    };
    fs.writeFileSync(path.join(outputDir, 'raw-response.json'), `${JSON.stringify(r.raw, null, 2)}\n`);
    fs.writeFileSync(path.join(outputDir, 'result.json'), `${JSON.stringify(result, null, 2)}\n`);
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return;
  }

  const prompt = args.prompt || [
    '请逐字转写这段中文短视频音频。',
    '只输出实际听到的口语，不总结、不续写、不翻译。',
    '保留自然分段和标点；专名不确定时写[听不清]。',
    '静音或结束后不要重复前文，也不要输出说明。',
  ].join('');

  const started = Date.now();
  let transcript;
  let lastPayload;
  let lastStatus = 0;
  let segmentResults = null;

  if (segments) {
    const parts = [];
    segmentResults = [];
    for (let i = 0; i < segments.length; i += 1) {
      const seg = segments[i];
      const r = await transcribeOnce({
        base64: seg.buffer.toString('base64'), format: 'wav', apiBase, apiKey, model, prompt,
      });
      parts.push(sanitizeTranscript(r.transcript));
      segmentResults.push({
        index: i, start_sec: Math.round(seg.startSec * 10) / 10,
        bytes: seg.buffer.length, http_status: r.status,
        finish_reason: r.responsePayload?.choices?.[0]?.finish_reason || null,
      });
      lastPayload = r.responsePayload;
      lastStatus = r.status;
    }
    transcript = sanitizeTranscript(parts.filter(Boolean).join('\n'));
  } else {
    const r = await transcribeOnce({ base64: raw.toString('base64'), format, apiBase, apiKey, model, prompt });
    transcript = sanitizeTranscript(r.transcript);
    lastPayload = r.responsePayload;
    lastStatus = r.status;
  }

  if (!transcript) throw new Error('ASR returned empty transcript after sanitize');
  const signals = repetitionSignals(transcript);
  const result = {
    ok: true,
    segment_id: segmentId,
    source_start: sourceStart,
    input,
    bytes: stat.size,
    model,
    provider: 'toapis-openai-compatible',
    http_status: lastStatus,
    elapsed_ms: Date.now() - started,
    usage: lastPayload?.usage || null,
    finish_reason: lastPayload?.choices?.[0]?.finish_reason || null,
    segment_seconds: segmentSeconds,
    segments: segmentResults,
    repetition_signals: signals,
    needs_review: signals.length > 0,
  };
  fs.writeFileSync(path.join(outputDir, 'transcript.txt'), `${transcript}\n`);
  fs.writeFileSync(path.join(outputDir, 'raw-response.json'), `${JSON.stringify(redactResponse(lastPayload), null, 2)}\n`);
  fs.writeFileSync(path.join(outputDir, 'result.json'), `${JSON.stringify(result, null, 2)}\n`);
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

const isDirectRun = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isDirectRun) main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
