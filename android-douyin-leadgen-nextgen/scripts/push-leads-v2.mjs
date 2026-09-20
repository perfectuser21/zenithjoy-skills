#!/usr/bin/env node
// push-leads-v2.mjs —— 0920 目标架构：交付去重升级版，抄 social-lead-delivery 的规则，
// 不引入 n8n，纯脚本实现。跟现状 push-leads.js 的区别：
//   1. 去重优先级：稳定douyin_id > 规范化主页链接 > 只有昵称不做高置信去重(标低置信)
//   2. 同一人多条评论合并成一条线索(不新建行)，保留全部来源到"重复轨迹"，"重复命中次数"+1
//   3. 跨run去重：每次都读现存表判断是否已存在，不是只在当次batch内存Set去重(那是现状的局限)
//   4. 状态统一落"待复核"——AI判断理由环节还没校准到可用精度(实测Luna/Terra都只有55.6%)，
//      不自动放行/不自动排除，全部人工复核，不再拼"AI判断理由"这种假模板字符串
//
// 用法: node push-leads-v2.mjs <tsv路径> <搜索账号标识>
// TSV 里 LEAD 行格式(11-12列，跟harvest-keyword.sh输出一致):
//   LEAD  昵称  抖音号  账号类型  评论  评论日期  地区  视频标题  关键词  主页IP  主页链接  作品链接

import fs from "fs";
import https from "https";

const [, , TSV, SRCACC] = process.argv;
if (!TSV) { console.error("usage: push-leads-v2.mjs <tsv> <搜索账号标识>"); process.exit(2); }

const APP_ID = process.env.FEISHU_APP_ID;
const APP_SECRET = process.env.FEISHU_APP_SECRET;
const BASE = process.env.FEISHU_BASE_APP || "GNuwbzY0da8GP0sv6MGcOTu9ntd";
const TABLE = process.env.FEISHU_LEADS_TABLE || "tblTLFj69CflUqSr";

function post(path, body, token) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = "Bearer " + token;
    headers["Content-Length"] = Buffer.byteLength(data);
    const req = https.request({ hostname: "open.feishu.cn", path, method: "POST", headers }, (res) => {
      let d = ""; res.on("data", (c) => (d += c)); res.on("end", () => resolve(JSON.parse(d)));
    });
    req.on("error", reject); req.write(data); req.end();
  });
}
function get(path, token) {
  return new Promise((resolve, reject) => {
    const req = https.request({ hostname: "open.feishu.cn", path, method: "GET", headers: { Authorization: "Bearer " + token } }, (res) => {
      let d = ""; res.on("data", (c) => (d += c)); res.on("end", () => resolve(JSON.parse(d)));
    });
    req.on("error", reject); req.end();
  });
}
function put(path, body, token) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = https.request({ hostname: "open.feishu.cn", path, method: "PUT", headers: { Authorization: "Bearer " + token, "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) } }, (res) => {
      let d = ""; res.on("data", (c) => (d += c)); res.on("end", () => resolve(JSON.parse(d)));
    });
    req.on("error", reject); req.write(data); req.end();
  });
}
function txt(v) {
  if (Array.isArray(v)) return v.map((x) => (x && x.text) || x).join("");
  return v == null ? "" : String(v);
}

async function main() {
  const tokRes = await post("/open-apis/auth/v3/tenant_access_token/internal", { app_id: APP_ID, app_secret: APP_SECRET });
  const tok = tokRes.tenant_access_token;

  // 1. 读现存表，建两级索引：按抖音号(高置信)、按"昵称|主页链接"(低置信兜底)
  const byDyid = new Map();
  const byLowConf = new Map();
  let pageToken = "";
  do {
    const r = await get(`/open-apis/bitable/v1/apps/${BASE}/tables/${TABLE}/records?page_size=100${pageToken ? "&page_token=" + pageToken : ""}`, tok);
    for (const item of r.data.items || []) {
      const f = item.fields;
      const dyid = txt(f["抖音号"]);
      if (dyid && dyid !== "id待核验") byDyid.set(dyid, item.record_id);
      const lowKey = `${txt(f["抖音昵称"])}|${txt(f["主页链接"])}`;
      byLowConf.set(lowKey, item.record_id);
    }
    pageToken = r.data.has_more ? r.data.page_token : "";
  } while (pageToken);
  console.log(`现存表已读: byDyid=${byDyid.size} byLowConf=${byLowConf.size}`);

  const nowMs = Date.now();
  const now = new Date(nowMs + 8 * 3600e3).toISOString().replace("T", " ").slice(0, 16) + "(UTC+8)";
  const lines = fs.readFileSync(TSV, "utf8").trim().split("\n").filter((l) => l.startsWith("LEAD\t"));

  let created = 0, merged = 0, skipped = 0;
  // 同批次内也要合并(同一人在同一次采集里多条评论)，先按人分组
  const groups = new Map(); // key -> {nick, id, atype, comments:[{body,date,region,video,kw,vurl}], purl, pip}
  for (const ln of lines) {
    const f = ln.split("\t");
    const [, nick, id, atype, comment, cdate, region, video, kw, pip, purl, vurl] = f;
    if (atype === "organization") { console.log("跳过同行:", nick); skipped++; continue; }
    const key = (id && id !== "") ? `D:${id}` : `L:${nick}|${purl || ""}`;
    if (!groups.has(key)) groups.set(key, { nick, id, atype, purl, pip, comments: [] });
    groups.get(key).comments.push({ body: comment, date: cdate, region, video, kw, vurl });
  }

  for (const [key, g] of groups) {
    const dyid = g.id && g.id !== "" ? g.id : "";
    const existingId = (dyid && byDyid.get(dyid)) || byLowConf.get(`${g.nick}|${g.purl || ""}`);
    const primary = g.comments[0];
    const extraTrail = g.comments.slice(1).map((c) => `[${c.date}] ${c.body}`).join(" | ");

    if (existingId) {
      // 已存在：合并，不新建行。重复命中次数+1，重复轨迹追加，不改状态(人工已在处理的不打扰)
      const cur = await get(`/open-apis/bitable/v1/apps/${BASE}/tables/${TABLE}/records/${existingId}`, tok);
      const curFields = cur?.data?.record?.fields || {};
      const prevTrail = txt(curFields["重复轨迹"]);
      const prevCount = Number(txt(curFields["重复命中次数"]) || 0);
      const newTrail = [prevTrail, `[${now}] 命中同一人新评论: ${primary.body}${extraTrail ? " | " + extraTrail : ""} (来源:${primary.video.slice(0, 30)})`].filter(Boolean).join(" || ");
      await put(`/open-apis/bitable/v1/apps/${BASE}/tables/${TABLE}/records/${existingId}`, {
        fields: { "重复命中次数": prevCount + g.comments.length, "重复轨迹": newTrail.slice(0, 2000) },
      }, tok);
      console.log("MERGED", g.nick, "(", key, ") 命中次数+", g.comments.length);
      merged++;
      continue;
    }

    const keyStr = `${g.nick} / ${dyid || "id待核验"}`;
    const lowConfNote = dyid ? "" : "｜⚠️只有昵称无稳定抖音号，低置信，触达前需人工核实身份";
    const allComments = g.comments.map((c) => `[${c.date}] ${c.body}`).join(" || ");
    const body = {
      fields: {
        "抖音获客-线索表": keyStr,
        "抖音昵称": g.nick,
        "抖音号": dyid || "id待核验",
        "主页链接": g.purl || "",
        "IP属地": g.pip || "",
        "业务线": "AI人工智能训练师",
        "原始评论": allComments,
        "AI判断理由": `未自动打分(评分模型实测准确率不足，0920校准中)，人工复核${lowConfNote}`,
        "状态": "待复核",
        "发送状态": "未发送",
        "来源视频": `${primary.vurl ? primary.vurl + " ｜ " : ""}${primary.video.slice(0, 80)}`,
        "搜索账号": SRCACC,
        "搜索意图": primary.kw,
        "目标人群": "考证人群",
        "采集时间": nowMs,
        "重复命中次数": g.comments.length - 1,
        "合规核验状态": "待核验",
      },
    };
    const res = await post(`/open-apis/bitable/v1/apps/${BASE}/tables/${TABLE}/records`, body, tok);
    if (res.code === 0) { created++; console.log("CREATED(待复核)", keyStr); byDyid.set(dyid, res.data.record.record_id); }
    else console.log("FAIL", g.nick, JSON.stringify(res).slice(0, 150));
  }
  console.log(`\n汇总: 新建(待复核)=${created} 合并进已有线索=${merged} 跳过同行=${skipped}`);
}
main().catch((e) => { console.error(e); process.exit(1); });
