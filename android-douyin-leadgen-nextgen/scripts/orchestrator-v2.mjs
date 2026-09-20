#!/usr/bin/env node
// orchestrator-v2.mjs --- 0920 修正版：判定依据 = 结构化schema校验，不是置信度阈值。
// 照抄 protocol.md 硬性契约：status(3选1)/next_action(4选1)/4个通用metrics键+
// 各stage附加必填键+evidence非空数组(completed时)。Jev只负责把log归一化填进schema
// 该填的字段；真正放行/升级的判断是纯代码做结构校验，跟n8n原本if/else精神一致。

import { execSync } from "child_process";
import fs from "fs";
import https from "https";

const JEV_KEY = fs.readFileSync(process.env.HOME + "/.credentials/jev.env", "utf8").match(/JEV_API_KEY=(.+)/)[1].trim();

const REQUIRED_COMMON = ["external_interactions", "business_reads", "business_writes", "artifact_writes"];
const REQUIRED_BY_STAGE = {
  search: ["candidates", "screens_scanned"],
  comment_collect: ["comments_collected", "videos_processed", "cursor_updates"],
  video_judge: ["candidates_judged", "qualified"],
  delivery_dedup: ["leads_written", "duplicates_skipped"],
};
const STATUS_ENUM = ["completed", "blocked", "failed"];
const ACTION_ENUM = ["accept", "retry", "stop", "request_approval"];

function deterministicExtract(stage, log) {
  const out = { metrics: {}, evidence: [] };
  for (const k of REQUIRED_COMMON) out.metrics[k] = 0;
  if (stage === "search") {
    const m = log.match(/\u5361\u7247\u6570[:\uff1a]\s*(\d+)/);
    if (m) { out.metrics.candidates = Number(m[1]); out.evidence.push({ type: "search_results", cards_found: Number(m[1]) }); }
    out.metrics.screens_scanned = 1;
  } else if (stage === "comment_collect") {
    const m = log.match(/\u89c6\u9891\u603b\u8ba1\u91c7\u5230\u8bc4\u8bba[:\uff1a]\s*(\d+)\s*\(\u6279\u6b21\u6570=(\d+)/);
    if (m) {
      out.metrics.comments_collected = Number(m[1]);
      out.metrics.videos_processed = 1;
      out.metrics.cursor_updates = Number(m[2]);
      out.evidence.push({ type: "comment_batch", comments: Number(m[1]), batches: Number(m[2]) });
    }
  } else if (stage === "video_judge") {
    try {
      const j = JSON.parse(log);
      out.metrics.candidates_judged = 1;
      out.metrics.qualified = j.verdict === "qualified" ? 1 : 0;
      if (j.transcript) out.evidence.push({ type: "asr_transcript", chars: j.transcript.length });
    } catch {}
  } else if (stage === "delivery_dedup") {
    const c = log.match(/\u65b0\u5efa\(\u5f85\u590d\u6838\)=(\d+)/);
    const d = log.match(/\u5408\u5e76\u8fdb\u5df2\u6709\u7ebf\u7d22=(\d+)/);
    if (c) out.metrics.leads_written = Number(c[1]);
    if (d) out.metrics.duplicates_skipped = Number(d[1]);
    if (c || d) out.evidence.push({ type: "delivery_write", created: c ? Number(c[1]) : 0, merged: d ? Number(d[1]) : 0 });
  }
  return out;
}

function callJevChoice(state) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      state, model: "jev-latest",
      questions: {
        status: { type: "choice", instructions: "\u6839\u636e\u8fd9\u6bb5\u6267\u884c\u65e5\u5fd7\uff0c\u672c\u9636\u6bb5\u771f\u5b9e\u5b8c\u6210\u72b6\u6001\u662f\u4ec0\u4e48\uff1f",
          criteria: { completed: "\u4efb\u52a1\u786e\u5b9e\u5b8c\u6210\uff0c\u6709\u5177\u4f53\u8bc1\u636e", blocked: "\u56e0\u5b89\u5168\u539f\u56e0\u4e3b\u52a8\u505c\u6b62", failed: "\u786e\u5b9a\u6027\u5931\u8d25" } },
        next_action: { type: "choice", instructions: "\u4e0b\u4e00\u6b65\u8be5\u600e\u4e48\u5904\u7406\uff1f",
          criteria: { accept: "\u63a5\u53d7\uff0c\u8fdb\u5165\u4e0b\u4e00\u9636\u6bb5", retry: "\u91cd\u8bd5\u672c\u9636\u6bb5", stop: "\u7ec8\u6b62\u4efb\u52a1", request_approval: "\u9700\u4eba\u5de5\u5ba1\u6279" } },
      },
    });
    const req = https.request({ hostname: "api.typesafe.ai", path: "/v1/systemone", method: "POST",
      headers: { Authorization: "Bearer " + JEV_KEY, "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) } },
      (res) => { let d = ""; res.on("data", (c) => (d += c)); res.on("end", () => resolve(JSON.parse(d))); });
    req.on("error", reject); req.write(body); req.end();
  });
}

function validateSchema(stage, candidate) {
  const problems = [];
  if (!STATUS_ENUM.includes(candidate.status)) problems.push(`status="${candidate.status}"\u4e0d\u5728\u5141\u8bb8\u679a\u4e3e\u5185`);
  if (!ACTION_ENUM.includes(candidate.next_action)) problems.push(`next_action="${candidate.next_action}"\u4e0d\u5728\u5141\u8bb8\u679a\u4e3e\u5185`);
  for (const k of REQUIRED_COMMON) if (typeof candidate.metrics[k] !== "number") problems.push(`\u7f3a\u901a\u7528\u5fc5\u586b\u952e metrics.${k}`);
  for (const k of REQUIRED_BY_STAGE[stage] || []) if (typeof candidate.metrics[k] !== "number") problems.push(`\u7f3a${stage}\u9636\u6bb5\u5fc5\u586b\u952e metrics.${k}`);
  if (candidate.status === "completed" && candidate.evidence.length === 0) problems.push("status=completed\u4f46evidence\u4e3a\u7a7a\u6570\u7ec4");
  return problems;
}

function escalateToCommander(stage, problems) {
  console.log(`  [\u5347\u7ea7Commander] \u9636\u6bb5=${stage}`);
  console.log(`  \u5177\u4f53\u7f3a\u9677: ${problems.join("; ")}`);
  console.log(`  (\u771f\u5b9e\u5b9e\u73b0: openclaw cron add --agent media --session escort-${stage} ...)`);
}

const RUNDIR = process.argv[2] || "/tmp/orch-v2-demo";
const LEDGER = new URL("./ledger.mjs", import.meta.url).pathname;
execSync(`node ${LEDGER} init --run-dir ${RUNDIR} --run-id demo-v2-$(date +%s) --tenant jinuo --platform douyin --keyword \u4eba\u5de5\u667a\u80fd\u8bad\u7ec3\u5e08\u8bc1\u4e66`, { shell: "/bin/zsh" });

const STAGES = [
  { name: "search", log: "\u5361\u7247\u6570: 2\n\u89c6\u98911: \u4e00\u4e2a\u6708\u62ff\u4e0b\u4eba\u793e\u7684\u4eba\u5de5\u667a\u80fd\u8bad\u7ec3\u5e08\u8bc1\u4e66\uff0c\u62a5\u8003\u5168\u6d41\u7a0b\u5206\u4eab\n  \u4f5c\u54c1\u94fe\u63a5: https://v.douyin.com/5dH9hnhzj2Y/" },
  { name: "comment_collect", log: "\u6279\u63711 \u672c\u5c4f\u8bc4\u8bba\u6570: 2\nLEAD\t\u5355\u7eaf\u9756\u4ed4\t162884597...\n\u6279\u63712 \u65e0\u65b0\u589e\uff0c\u89c6\u4e3a\u53d6\u5149\n\u89c6\u9891\u603b\u8ba1\u91c7\u5230\u8bc4\u8bba: 2 (\u6279\u6b21\u6570=2 exhausted=0)" },
  { name: "video_judge", log: JSON.stringify({ verdict: "review", transcript: "...\u56fd\u5bb6\u7533\u9886\u8865\u8d34...\u6309\u9700\u62a5\u8003\u4e0d\u662f\u8d8a\u591a\u8d8a\u597d...".repeat(3), reason: "\u63d0\u53ca\u4eba\u5de5\u667a\u80fd\u8bc1\u4e66\u62a5\u8003\u8865\u8d34\uff0c\u4f46\u672a\u660e\u786e\u4eba\u5de5\u667a\u80fd\u8bad\u7ec3\u5e08" }) },
  { name: "delivery_dedup", log: "\u73b0\u5b58\u8868\u5df2\u8bfb: byDyid=2 byLowConf=3\nMERGED \u5355\u7eaf\u9756\u4ed4 ( D:162884597 ) \u547d\u4e2d\u6b21\u6570+ 1\nMERGED \u559c\u4e50 ( D:shagu90908 ) \u547d\u4e2d\u6b21\u6570+ 1\n\u6c47\u603b: \u65b0\u5efa(\u5f85\u590d\u6838)=0 \u5408\u5e76\u8fdb\u5df2\u6709\u7ebf\u7d22=2 \u8df3\u8fc7\u540c\u884c=0" },
];

for (const s of STAGES) {
  console.log(`\n=== \u9636\u6bb5: ${s.name} ===`);
  execSync(`node ${LEDGER} set --run-dir ${RUNDIR} --stage ${s.name} --status running`, { shell: "/bin/zsh" });

  const det = deterministicExtract(s.name, s.log);
  const jev = await callJevChoice(s.log);
  const candidate = { status: jev.answers.status.choice, next_action: jev.answers.next_action.choice, metrics: det.metrics, evidence: det.evidence };
  console.log("  \u7eaf\u4ee3\u7801\u62bd\u53d6metrics:", JSON.stringify(det.metrics));
  console.log("  Jev\u5f52\u4e00\u5316status/action:", candidate.status, "/", candidate.next_action, `(conf=${jev.answers.status.confidence.toFixed(2)})`);

  const problems = validateSchema(s.name, candidate);
  if (problems.length === 0) {
    execSync(`node ${LEDGER} set --run-dir ${RUNDIR} --stage ${s.name} --status ${candidate.status} --note schema_ok`, { shell: "/bin/zsh" });
    console.log("  \u2192 schema\u6821\u9a8c\u901a\u8fc7\uff0c\u8d26\u672c\u5199\u5165\uff0c\u63a8\u8fdb\u4e0b\u4e00\u9636\u6bb5");
  } else {
    escalateToCommander(s.name, problems);
    execSync(`node ${LEDGER} set --run-dir ${RUNDIR} --stage ${s.name} --status blocked --note "schema_fail"`, { shell: "/bin/zsh" });
  }
}
console.log("\n=== \u6700\u7ec8\u8d26\u672c ===");
console.log(execSync(`node ${LEDGER} show --run-dir ${RUNDIR}`, { shell: "/bin/zsh" }).toString());
