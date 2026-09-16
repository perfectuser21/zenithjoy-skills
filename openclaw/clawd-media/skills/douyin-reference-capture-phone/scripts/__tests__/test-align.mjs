// 回归守卫：ASR 逐词时间戳 → 带时间的句子
//
// 起因（2026-09-11 实测踩了三次）：通义 qwen-audio-3.0-asr-flash 返回的
// sentence.text 标点完整，但 sentence.words[] 里只有极少数词带 punctuation
// （实测 134 词中仅 21 个带标点）。直接按 words 的 punctuation 断句，会把
// 一段 57 秒的口播切成 119 个碎片（句均 0.5 秒），拿不到可用的句子结构。
//
// 正解：以 sentence.text 的标点为准做断句，再把 words 的时间戳按字符序对齐上去。
//
// 用法: node test-align.mjs <被测脚本路径>
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const target = process.argv[2];
if (!target) {
  console.error('need script path');
  process.exit(2);
}
const mod = await import(pathToFileURL(target).href);
const { sentencesWithTiming } = mod;
if (typeof sentencesWithTiming !== 'function') {
  console.error('FATAL: sentencesWithTiming not exported from', target);
  process.exit(2);
}

let pass = 0;
let fail = 0;
const ok = (m) => {
  console.log(`  PASS: ${m}`);
  pass += 1;
};
const ng = (m) => {
  console.log(`  FAIL: ${m}`);
  fail += 1;
};
const chk = (cond, good, bad) => (cond ? ok(good) : ng(bad));

// ---- fixture：真机返回的缩样（标点分布与实测一致：多数词无 punctuation）----
const text = '大家好，今天我们聊一聊人工智能训练师。很多同学问我这个证书到底有没有用？我把资料发给你。';
const words = [
  { text: '大家好', begin_time: 80, end_time: 280, punctuation: '，' },
  { text: '今天我们', begin_time: 400, end_time: 680, punctuation: '' },
  { text: '聊一聊', begin_time: 680, end_time: 920, punctuation: '' },
  { text: '人工智能', begin_time: 920, end_time: 1200, punctuation: '' },
  { text: '训练', begin_time: 1200, end_time: 1320, punctuation: '' },
  { text: '师', begin_time: 1320, end_time: 1440, punctuation: '。' },
  { text: '很多同学', begin_time: 1500, end_time: 1900, punctuation: '' },
  { text: '问我', begin_time: 1900, end_time: 2100, punctuation: '' },
  { text: '这个', begin_time: 2100, end_time: 2300, punctuation: '' },
  { text: '证书', begin_time: 2300, end_time: 2600, punctuation: '' },
  { text: '到底', begin_time: 2600, end_time: 2800, punctuation: '' },
  { text: '有没有', begin_time: 2800, end_time: 3100, punctuation: '' },
  { text: '用', begin_time: 3100, end_time: 3200, punctuation: '' },
  { text: '我把', begin_time: 3600, end_time: 3800, punctuation: '' },
  { text: '资料', begin_time: 3800, end_time: 4000, punctuation: '' },
  { text: '发', begin_time: 4000, end_time: 4100, punctuation: '' },
  { text: '给你', begin_time: 4100, end_time: 4300, punctuation: '。' },
];

console.log('--- 断句正确性（核心：不能按 words 的稀疏标点切）---');
const s1 = sentencesWithTiming(text, words, 1);
chk(
  s1.length === 3,
  `切出 3 句（实得 ${s1.length}）`,
  `断句错误：期望 3 句、实得 ${s1.length} —— 回归到按 words.punctuation 碎切了`,
);
chk(
  s1.length === 3 && s1[0].text === '大家好，今天我们聊一聊人工智能训练师。',
  '第1句文本完整（含标点）',
  `第1句错: ${s1[0] && s1[0].text}`,
);
chk(
  s1.length === 3 && s1[2].text === '我把资料发给你。',
  '第3句文本完整',
  `第3句错: ${s1[2] && s1[2].text}`,
);

console.log('--- 时间戳对齐 ---');
chk(s1[0] && s1[0].begin === 80, '第1句起点取自首词 begin_time=80', `第1句起点错: ${s1[0] && s1[0].begin}`);
chk(s1[0] && s1[0].end === 1440, '第1句终点取自末词 end_time=1440', `第1句终点错: ${s1[0] && s1[0].end}`);
chk(s1[2] && s1[2].begin === 3600, '第3句起点=3600', `第3句起点错: ${s1[2] && s1[2].begin}`);
chk(s1[2] && s1[2].end === 4300, '第3句终点=4300', `第3句终点错: ${s1[2] && s1[2].end}`);
chk(
  s1.every((s, i) => i === 0 || s.begin >= s1[i - 1].end),
  '句子时间单调不重叠',
  '时间轴错乱：句子区间重叠',
);

console.log('--- 倍速换算（3倍速录制 → 视频真实时刻）---');
const s3 = sentencesWithTiming(text, words, 3);
chk(s3[0] && s3[0].begin === 240, '3倍速下第1句起点 80×3=240', `倍速换算错: ${s3[0] && s3[0].begin}`);
chk(s3[2] && s3[2].end === 12900, '3倍速下末句终点 4300×3=12900', `倍速换算错: ${s3[2] && s3[2].end}`);

console.log('--- 边界 ---');
chk(sentencesWithTiming('', words, 1).length === 0, '空文本返回空数组', '空文本未返回空数组');
chk(sentencesWithTiming(text, [], 1).length === 0, '无 words 返回空数组', '无 words 未返回空数组');
const noPunct = sentencesWithTiming('没有句末标点的一段话', words.slice(0, 3), 1);
chk(noPunct.length === 1, '无句末标点时整体作为一句', `无标点处理错: ${noPunct.length}`);

console.log('');
console.log(`PASS=${pass} FAIL=${fail}`);
process.exit(fail === 0 ? 0 : 1);
