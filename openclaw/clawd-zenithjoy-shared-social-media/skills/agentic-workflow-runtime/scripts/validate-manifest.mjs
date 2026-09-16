#!/usr/bin/env node

import fs from 'node:fs';

function fail(message) {
  process.stderr.write(`${message}\n`);
  process.exit(1);
}

const file = process.argv[2];
if (!file) fail('Usage: validate-manifest.mjs <manifest.json>');

let manifest;
try {
  manifest = JSON.parse(fs.readFileSync(file, 'utf8'));
} catch (error) {
  fail(`Invalid JSON: ${error.message}`);
}

const required = ['schema_version', 'workflow_id', 'version', 'objective', 'tenant_requirements', 'stages', 'cleanup'];
for (const key of required) if (manifest[key] === undefined) fail(`Missing ${key}`);
if (manifest.schema_version !== 1) fail('schema_version must be 1');
if (!/^[a-z][a-z0-9-]{2,63}$/.test(manifest.workflow_id)) fail('Invalid workflow_id');
if (!Array.isArray(manifest.tenant_requirements) || manifest.tenant_requirements.length === 0) fail('tenant_requirements must be non-empty');
if (!Array.isArray(manifest.stages) || manifest.stages.length === 0) fail('stages must be non-empty');
if (!manifest.orchestrator && !manifest.commander) fail('Manifest requires orchestrator or commander');
if (manifest.orchestrator) {
  if (manifest.orchestrator.type !== 'n8n') fail('orchestrator.type must be n8n');
  if (!manifest.orchestrator.workflow_id) fail('orchestrator.workflow_id is required');
  if (manifest.orchestrator.event_protocol !== 'n8n-agent-node-v1') fail('Unsupported orchestrator.event_protocol');
  if (manifest.orchestrator.worker_may_spawn_agents !== false) fail('n8n workers must not spawn agents');
} else {
  if (manifest.commander?.agent_id !== 'work-commander') fail('commander.agent_id must be work-commander');
  if (manifest.commander?.event_protocol !== 'agentic-workflow-v2') fail('Unsupported commander.event_protocol');
}
if (manifest.worker_agent_id !== undefined && (!manifest.worker_agent_id || manifest.worker_agent_id === 'main')) fail('Invalid worker_agent_id');
if (manifest.worker_agent_id === undefined && manifest.worker_agent_binding !== 'trusted_tenant_context.agent_id') {
  fail('Generic manifest must bind worker through trusted_tenant_context.agent_id');
}
if (manifest.dedicated_tenant === true && manifest.worker_agent_id === undefined) {
  fail('Dedicated tenant manifest requires worker_agent_id');
}

const ids = new Set();
for (const stage of manifest.stages) {
  for (const key of ['id', 'skill', 'objective', 'depends_on', 'acceptance', 'retry', 'safety']) if (stage[key] === undefined) fail(`Stage is missing ${key}`);
  if (!/^[a-z][a-z0-9_-]{1,63}$/.test(stage.id)) fail(`Invalid stage id: ${stage.id}`);
  if (ids.has(stage.id)) fail(`Duplicate stage id: ${stage.id}`);
  ids.add(stage.id);
  if (!Array.isArray(stage.depends_on) || !Array.isArray(stage.acceptance) || stage.acceptance.length === 0) fail(`Invalid arrays in stage ${stage.id}`);
  if (!Number.isInteger(stage.retry?.max_attempts) || stage.retry.max_attempts < 1 || stage.retry.max_attempts > 5) fail(`Invalid retry.max_attempts in ${stage.id}`);
  if (!Array.isArray(stage.retry?.retry_on) || !Array.isArray(stage.safety?.stop_on)) fail(`Invalid retry/safety in ${stage.id}`);
}

for (const stage of manifest.stages) {
  for (const dependency of stage.depends_on) {
    if (!ids.has(dependency)) fail(`Unknown dependency ${dependency} in ${stage.id}`);
    if (dependency === stage.id) fail(`Stage ${stage.id} depends on itself`);
  }
}

const visited = new Set();
const active = new Set();
const byId = new Map(manifest.stages.map((stage) => [stage.id, stage]));
function visit(id) {
  if (active.has(id)) fail(`Dependency cycle at ${id}`);
  if (visited.has(id)) return;
  active.add(id);
  for (const dependency of byId.get(id).depends_on) visit(dependency);
  active.delete(id);
  visited.add(id);
}
for (const id of ids) visit(id);

if (manifest.cleanup?.always !== true || !Array.isArray(manifest.cleanup?.acceptance) || manifest.cleanup.acceptance.length === 0) fail('cleanup must always run and have acceptance criteria');
process.stdout.write(`${JSON.stringify({ ok: true, workflow_id: manifest.workflow_id, version: manifest.version, stages: manifest.stages.map((stage) => stage.id) })}\n`);
