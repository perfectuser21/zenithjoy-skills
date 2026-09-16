#!/usr/bin/env node
import fs from 'node:fs';
const file = process.argv[2];
if (!file) throw new Error('Usage: render-task-description.mjs <task_request.json>');
const r = JSON.parse(fs.readFileSync(file, 'utf8'));
process.stdout.write([
  `任务：${r.task_title}`,
  `仓库：${r.base_repo} @ ${r.base_branch}`,
  `环境：${r.target_environment}｜改动类型：${r.change_kind}｜GP 锚：${r.gp_anchor}`,
  `PRD：${String(r.thin_prd).slice(0, 400)}`,
].join('\n') + '\n');
