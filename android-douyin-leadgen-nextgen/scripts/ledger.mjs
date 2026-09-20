#!/usr/bin/env node
// ledger.mjs —— 0920 目标架构：轻量本地账本，不用 n8n。
// 记 run_id/attempt_id/各阶段状态，支持断点续跑。存本地 JSON 文件（一个 run 一个文件）。
//
// 用法:
//   node ledger.mjs init --run-dir <dir> --run-id <id> --tenant <t> --platform <p> --keyword <kw>
//   node ledger.mjs set  --run-dir <dir> --stage <stage> --status <completed|running|blocked|failed> [--note <n>]
//   node ledger.mjs show --run-dir <dir>
//   node ledger.mjs next-attempt --run-dir <dir>   # 断点续跑时分配新 attempt_id，只导入已完成阶段

import fs from "fs";
import path from "path";

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const key = a.slice(2);
      const val = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : true;
      out[key] = val;
    } else {
      out._.push(a);
    }
  }
  return out;
}

function ledgerPath(runDir) {
  return path.join(runDir, "ledger.json");
}

function loadLedger(runDir) {
  const p = ledgerPath(runDir);
  if (!fs.existsSync(p)) throw new Error(`ledger not found at ${p}; run init first`);
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function saveLedger(runDir, ledger) {
  fs.mkdirSync(runDir, { recursive: true });
  ledger.updated_at = new Date().toISOString();
  fs.writeFileSync(ledgerPath(runDir), JSON.stringify(ledger, null, 2));
}

const STAGES = [
  "preflight", "search", "video_dedup", "own_account_filter", "comment_gate",
  "video_judge", "comment_collect", "comment_score", "delivery_dedup", "outreach", "cleanup",
];

const args = parseArgs(process.argv.slice(2));
const cmd = process.argv[2];
const runDir = args["run-dir"];
if (!runDir) { console.error("missing --run-dir"); process.exit(2); }

if (cmd === "init") {
  const runId = args["run-id"] || `run-${Date.now()}`;
  const ledger = {
    run_id: runId,
    attempt_id: "a1",
    tenant: args["tenant"] || "",
    platform: args["platform"] || "douyin",
    keyword: args["keyword"] || "",
    sort: args["sort"] || "most_liked",
    time_window: args["time-window"] || "one_week",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    stages: Object.fromEntries(STAGES.map((s) => [s, { status: "pending", note: "", updated_at: null }])),
  };
  saveLedger(runDir, ledger);
  console.log(JSON.stringify({ ok: true, run_id: ledger.run_id, attempt_id: ledger.attempt_id }));
} else if (cmd === "set") {
  const stage = args["stage"];
  const status = args["status"];
  if (!STAGES.includes(stage)) { console.error(`unknown stage: ${stage}; must be one of ${STAGES.join(",")}`); process.exit(2); }
  if (!["pending", "running", "completed", "blocked", "failed"].includes(status)) { console.error(`invalid status: ${status}`); process.exit(2); }
  const ledger = loadLedger(runDir);
  ledger.stages[stage] = { status, note: args["note"] || "", updated_at: new Date().toISOString() };
  saveLedger(runDir, ledger);
  console.log(JSON.stringify({ ok: true, stage, status }));
} else if (cmd === "show") {
  const ledger = loadLedger(runDir);
  console.log(JSON.stringify(ledger, null, 2));
} else if (cmd === "next-attempt") {
  const ledger = loadLedger(runDir);
  const n = parseInt(ledger.attempt_id.replace("a", ""), 10) + 1;
  const newAttempt = `a${n}`;
  const completedStages = Object.fromEntries(
    Object.entries(ledger.stages).filter(([, v]) => v.status === "completed")
  );
  const resumed = {
    ...ledger,
    attempt_id: newAttempt,
    resumes_attempt_id: ledger.attempt_id,
    stages: Object.fromEntries(
      STAGES.map((s) => [s, completedStages[s] || { status: "pending", note: "", updated_at: null }])
    ),
  };
  saveLedger(runDir, resumed);
  console.log(JSON.stringify({ ok: true, attempt_id: newAttempt, resumed_from: ledger.attempt_id, imported_stages: Object.keys(completedStages) }));
} else {
  console.error("usage: ledger.mjs <init|set|show|next-attempt> --run-dir <dir> ...");
  process.exit(2);
}
