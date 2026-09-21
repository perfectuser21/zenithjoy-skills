#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);

// 脚本固定躺在 <workspace>/skills/<skill名>/scripts/ 下，往上跳3层就是 workspace 根——
// 用这个反推部署根目录，不写死具体机器/客户的绝对路径，跨环境可移植。
const WORKSPACE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");

// jszip 是 openclaw 自己的依赖，不是本技能的依赖，本机装在哪个前缀（/opt/homebrew、
// /usr/local、/usr 等）因操作系统/安装方式而异，不能写死一个。优先允许环境变量直接指定
// （客户环境路径特殊时无需改代码），否则按常见 npm 全局前缀逐个尝试，找到第一个真实存在的。
function resolveJSZip() {
  if (process.env.OPENCLAW_JSZIP_PATH) {
    return require(process.env.OPENCLAW_JSZIP_PATH);
  }
  try {
    return require("jszip");
  } catch {
    // 走不到全局解析路径时，退回常见 npm 全局安装前缀逐个探测
  }
  const candidatePrefixes = [
    "/opt/homebrew/lib/node_modules",
    "/usr/local/lib/node_modules",
    "/usr/lib/node_modules",
  ];
  for (const prefix of candidatePrefixes) {
    const candidate = path.join(prefix, "openclaw/node_modules/jszip/lib/index.js");
    if (fs.existsSync(candidate)) return require(candidate);
  }
  throw new Error(
    "jszip not found: 设置环境变量 OPENCLAW_JSZIP_PATH 指向 jszip 的 lib/index.js，或确认 openclaw 全局安装路径",
  );
}
const JSZip = resolveJSZip();
const input = process.argv[2];
const maxInputMb = 200;
const maxInputBytes = maxInputMb * 1024 * 1024;
const maxOutputChars = 120_000;
const defaultRoot = path.join(WORKSPACE_ROOT, "media/inbound");
const allowedRoots = (process.env.OFFICE_READER_ALLOWED_ROOTS || defaultRoot)
  .split(path.delimiter)
  .map((item) => path.resolve(item))
  .filter(Boolean);

function fail(message) {
  process.stderr.write(`office-reader: ${message}\n`);
  process.exit(2);
}

function decodeXml(text) {
  return text
    .replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(Number.parseInt(n, 16)))
    .replace(/&#([0-9]+);/g, (_, n) => String.fromCodePoint(Number.parseInt(n, 10)))
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, "&");
}

function cleanText(text) {
  return decodeXml(text)
    .replace(/\r/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function truncate(text) {
  if (text.length <= maxOutputChars) return { text, truncated: false };
  return {
    text: `${text.slice(0, maxOutputChars)}\n\n[内容已在 ${maxOutputChars} 字符处截断]`,
    truncated: true,
  };
}

function columnIndex(ref) {
  const letters = String(ref || "").match(/^[A-Z]+/i)?.[0]?.toUpperCase() || "A";
  let value = 0;
  for (const ch of letters) value = value * 26 + ch.charCodeAt(0) - 64;
  return Math.max(0, value - 1);
}

async function readZipEntry(zip, name, limit = 20 * 1024 * 1024) {
  const entry = zip.file(name);
  if (!entry) return "";
  const value = await entry.async("string");
  if (Buffer.byteLength(value, "utf8") > limit) fail(`压缩包条目过大: ${name}`);
  return value;
}

async function extractDocx(buffer) {
  const zip = await JSZip.loadAsync(buffer, { checkCRC32: true });
  const names = [
    "word/document.xml",
    "word/footnotes.xml",
    ...Object.keys(zip.files)
      .filter((name) => /^word\/(header|footer)\d+\.xml$/i.test(name))
      .sort(),
  ];
  const sections = [];
  for (const name of names) {
    const xml = await readZipEntry(zip, name);
    if (!xml) continue;
    const text = cleanText(
      xml
        .replace(/<w:tab\b[^>]*\/?\s*>/gi, "\t")
        .replace(/<w:br\b[^>]*\/?\s*>/gi, "\n")
        .replace(/<\/w:tc>/gi, "\t")
        .replace(/<\/w:tr>/gi, "\n")
        .replace(/<\/w:p>/gi, "\n")
        .replace(/<[^>]+>/g, ""),
    );
    if (text) sections.push(name === "word/document.xml" ? text : `[${name}]\n${text}`);
  }
  if (!sections.length) fail("DOCX 中没有可读取文字");
  return sections.join("\n\n");
}

function parseSharedStrings(xml) {
  const values = [];
  for (const match of xml.matchAll(/<si\b[^>]*>([\s\S]*?)<\/si>/gi)) {
    const parts = [...match[1].matchAll(/<t\b[^>]*>([\s\S]*?)<\/t>/gi)].map((item) => decodeXml(item[1]));
    values.push(parts.join(""));
  }
  return values;
}

function parseRelationships(xml) {
  const map = new Map();
  for (const match of xml.matchAll(/<Relationship\b([^>]*)\/?\s*>/gi)) {
    const attrs = match[1];
    const id = attrs.match(/\bId="([^"]+)"/i)?.[1];
    const target = attrs.match(/\bTarget="([^"]+)"/i)?.[1];
    if (id && target) map.set(id, target);
  }
  return map;
}

function parseWorkbookSheets(xml) {
  const sheets = [];
  for (const match of xml.matchAll(/<sheet\b([^>]*)\/?\s*>/gi)) {
    const attrs = match[1];
    const name = decodeXml(attrs.match(/\bname="([^"]*)"/i)?.[1] || "Sheet");
    const relId = attrs.match(/\br:id="([^"]+)"/i)?.[1];
    if (relId) sheets.push({ name, relId });
  }
  return sheets;
}

function cellValue(cellXml, type, sharedStrings) {
  if (type === "inlineStr") {
    return [...cellXml.matchAll(/<t\b[^>]*>([\s\S]*?)<\/t>/gi)]
      .map((match) => decodeXml(match[1]))
      .join("");
  }
  const raw = cellXml.match(/<v\b[^>]*>([\s\S]*?)<\/v>/i)?.[1] ?? "";
  if (type === "s") return sharedStrings[Number.parseInt(raw, 10)] ?? raw;
  if (type === "b") return raw === "1" ? "TRUE" : "FALSE";
  if (type === "str") return decodeXml(raw);
  const formula = cellXml.match(/<f\b[^>]*>([\s\S]*?)<\/f>/i)?.[1];
  return formula ? `=${decodeXml(formula)}${raw ? ` [${decodeXml(raw)}]` : ""}` : decodeXml(raw);
}

function parseSheet(xml, sharedStrings) {
  const rows = [];
  for (const rowMatch of xml.matchAll(/<row\b[^>]*>([\s\S]*?)<\/row>/gi)) {
    const values = [];
    for (const cellMatch of rowMatch[1].matchAll(/<c\b([^>]*)>([\s\S]*?)<\/c>/gi)) {
      const attrs = cellMatch[1];
      const ref = attrs.match(/\br="([^"]+)"/i)?.[1] || "A1";
      const type = attrs.match(/\bt="([^"]+)"/i)?.[1] || "n";
      const index = Math.min(columnIndex(ref), 199);
      values[index] = cellValue(cellMatch[2], type, sharedStrings);
    }
    while (values.length && values.at(-1) === undefined) values.pop();
    rows.push(values.map((value) => String(value ?? "").replace(/[\t\r\n]+/g, " ")).join("\t"));
    if (rows.length >= 10_000) {
      rows.push("[工作表已在 10000 行处截断]");
      break;
    }
  }
  return rows.join("\n");
}

async function extractXlsx(buffer) {
  const zip = await JSZip.loadAsync(buffer, { checkCRC32: true });
  const sharedStrings = parseSharedStrings(await readZipEntry(zip, "xl/sharedStrings.xml"));
  const workbook = await readZipEntry(zip, "xl/workbook.xml");
  const relationships = parseRelationships(await readZipEntry(zip, "xl/_rels/workbook.xml.rels"));
  const sheets = parseWorkbookSheets(workbook);
  const output = [];
  for (const [index, sheet] of sheets.entries()) {
    let target = relationships.get(sheet.relId) || `worksheets/sheet${index + 1}.xml`;
    target = target.replace(/^\//, "").replace(/^xl\//, "");
    const xml = await readZipEntry(zip, `xl/${target}`);
    output.push(`## 工作表：${sheet.name}\n${xml ? parseSheet(xml, sharedStrings) : "[无法读取工作表内容]"}`);
  }
  if (!output.length) fail("XLSX 中没有可读取工作表");
  return output.join("\n\n");
}

async function extractLegacyXls(buffer) {
  const XLSX = await import("xlsx");
  const workbook = XLSX.read(buffer, {
    type: "buffer",
    cellDates: true,
    cellFormula: true,
    dense: true,
  });
  const output = workbook.SheetNames.map((sheetName) => {
    const sheet = workbook.Sheets[sheetName];
    const text = XLSX.utils.sheet_to_csv(sheet, {
      FS: "\t",
      RS: "\n",
      blankrows: false,
      strip: true,
    });
    return `## 工作表：${sheetName}\n${text || "[空工作表]"}`;
  });
  if (!output.length) fail("XLS 中没有可读取工作表");
  return output.join("\n\n");
}

async function extractPdf(buffer) {
  const { PDFParse } = await import("pdf-parse");
  const parser = new PDFParse({ data: buffer });
  try {
    const result = await parser.getText();
    if (!result.text?.trim()) fail("PDF 中没有可提取文字，可能是扫描件");
    return result.text;
  } finally {
    await parser.destroy();
  }
}

if (!input) fail("缺少附件路径");
let realPath;
try {
  realPath = fs.realpathSync(input);
} catch {
  fail("附件不存在");
}
if (!allowedRoots.some((root) => realPath === root || realPath.startsWith(`${root}${path.sep}`))) {
  fail("拒绝读取非入站附件路径");
}
const stat = fs.statSync(realPath);
if (!stat.isFile()) fail("目标不是文件");
if (stat.size > maxInputBytes) fail(`附件超过 ${maxInputMb} MB 限制`);

const ext = path.extname(realPath).toLowerCase();
const buffer = fs.readFileSync(realPath);
let extracted;
if (ext === ".docx") extracted = await extractDocx(buffer);
else if (ext === ".xlsx") extracted = await extractXlsx(buffer);
else if (ext === ".xls") extracted = await extractLegacyXls(buffer);
else if (ext === ".pdf") extracted = await extractPdf(buffer);
else if ([".csv", ".txt", ".md"].includes(ext)) extracted = buffer.toString("utf8");
else if (ext === ".doc") fail("暂不支持旧格式 .doc，请另存为 .docx");
else fail(`不支持的文件类型: ${ext || "无扩展名"}`);

const result = truncate(cleanText(extracted));
process.stdout.write(
  `# 文件：${path.basename(realPath)}\n# 类型：${ext}\n# 截断：${result.truncated ? "是" : "否"}\n\n${result.text}\n`,
);
