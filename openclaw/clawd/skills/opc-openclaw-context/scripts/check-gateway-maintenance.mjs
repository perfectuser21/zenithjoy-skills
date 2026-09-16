#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
let stateDir = "/root/clawd-work-commander/state/workflow-runs";
const allowedRuns = new Set();

for (let index = 0; index < args.length; index += 1) {
  if (args[index] === "--state-dir") {
    stateDir = args[index + 1];
    index += 1;
  } else if (args[index] === "--allow-run") {
    allowedRuns.add(args[index + 1]);
    index += 1;
  } else {
    console.error(`Unknown argument: ${args[index]}`);
    process.exit(64);
  }
}

if (!fs.existsSync(stateDir)) {
  console.error(`Gateway maintenance guard cannot find workflow state directory: ${stateDir}`);
  process.exit(3);
}

const active = [];
const invalid = [];

// Only canonical attempt ledgers participate in the maintenance fence. Stage
// sidecars deliberately contain protocol-prefixed text and are not ledgers.
const canonicalLedgerName = /__a[1-9][0-9]*\.json$/;
for (const filename of fs.readdirSync(stateDir).filter((name) => canonicalLedgerName.test(name)).sort()) {
  const ledgerPath = path.join(stateDir, filename);
  try {
    const ledger = JSON.parse(fs.readFileSync(ledgerPath, "utf8"));
    if (!ledger.terminal && !allowedRuns.has(ledger.run_id)) {
      active.push({
        run_id: ledger.run_id ?? "unknown",
        attempt_id: ledger.attempt_id ?? "unknown",
        execution_id: ledger.execution_id ?? "unknown",
        updated_at: ledger.updated_at ?? null,
        ledger: ledgerPath,
      });
    }
  } catch (error) {
    invalid.push({ ledger: ledgerPath, error: error.message });
  }
}

if (invalid.length > 0) {
  console.error(JSON.stringify({ ok: false, reason: "invalid_ledgers", invalid }, null, 2));
  process.exit(3);
}

if (active.length > 0) {
  console.error(JSON.stringify({ ok: false, reason: "active_workflows", active }, null, 2));
  process.exit(2);
}

console.log(JSON.stringify({ ok: true, reason: "maintenance_window_clear", state_dir: stateDir }));
