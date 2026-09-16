#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

function argsOf(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (!argv[i].startsWith("--")) continue;
    out[argv[i].slice(2)] = argv[i + 1];
    i += 1;
  }
  return out;
}

function readJsonYaml(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function requiredMissing(company, products, segments) {
  const missing = [];
  for (const key of ["company_name", "industry", "description", "geographies"]) {
    const value = company[key];
    if (value === undefined || value === null || value === "" || (Array.isArray(value) && value.length === 0)) missing.push(`company.${key}`);
  }
  if (!Array.isArray(products.items) || products.items.length === 0) missing.push("products.items");
  if (!Array.isArray(segments.items) || segments.items.length < 3) missing.push("customer_segments.items(minimum=3)");
  return missing;
}

const args = argsOf(process.argv);
const root = args.root || process.env.OPENCLAW_COMPANY_DATA_ROOT || "/root/clawd/company-data";
const registryPath = args.registry || process.env.OPENCLAW_TENANT_REGISTRY || "/root/clawd/config/enterprise-context/tenant-registry.json";
const tenant = args.tenant;
const task = args.task || "general";
if (!tenant || !/^[a-z0-9][a-z0-9_-]{1,63}$/.test(tenant)) {
  console.error("--tenant is required and must be a safe tenant_id");
  process.exit(2);
}

const dir = path.join(root, tenant, "current");
try {
  const registry = readJsonYaml(registryPath);
  if (registry.cross_tenant_fallback !== false) throw new Error("tenant registry must disable cross-tenant fallback");
  const tenantRoute = registry.tenants?.[tenant];
  if (!tenantRoute) throw new Error(`tenant ${tenant} is not registered`);
  const manifest = readJsonYaml(path.join(dir, "manifest.yaml"));
  const company = readJsonYaml(path.join(dir, "company-profile.yaml"));
  const products = readJsonYaml(path.join(dir, "products.yaml"));
  const segments = readJsonYaml(path.join(dir, "customer-segments.yaml"));
  const keywords = readJsonYaml(path.join(dir, "keywords.yaml"));
  for (const [name, value] of [["manifest", manifest], ["company", company], ["products", products], ["customer_segments", segments], ["keywords", keywords]]) {
    if (value?.tenant_id !== tenant) throw new Error(`${name}.tenant_id mismatch; refusing cross-tenant data`);
  }
  if (manifest.source_app_id && manifest.source_app_id !== tenantRoute.feishu?.app_id) {
    throw new Error("manifest Feishu app does not match tenant registry");
  }
  const masterPath = path.join(dir, "enterprise-master.md");
  const masterDocument = fs.existsSync(masterPath) ? fs.readFileSync(masterPath, "utf8") : null;
  const missing = requiredMissing(company, products, segments);
  const completeness = Math.max(0, Math.round(100 - (missing.length / 7) * 100));

  const common = {
    tenant_id: tenant,
    task_type: task,
    version: manifest.version,
    last_synced_at: manifest.last_synced_at,
    source: manifest.source,
    status: missing.length ? "incomplete" : "ready",
    completeness,
    missing_required: missing,
    tenant_route: {
      feishu_app_id: tenantRoute.feishu?.app_id || null,
      feishu_bot_name: tenantRoute.feishu?.bot_name || null,
      feishu_account_id: tenantRoute.feishu?.account_id || null,
      openclaw_router: tenantRoute.openclaw?.router_agent || null,
      cross_tenant_fallback: false
    },
    company,
    master_document: {
      path: masterPath,
      source_url: company.master_document_url || null,
      available: Boolean(masterDocument),
      content: masterDocument
    }
  };
  const taskData = {
    hot_news: { products: products.items, customer_segments: segments.items, keywords },
    keyword_radar: { products: products.items, customer_segments: segments.items, keywords },
    content: { products: products.items, customer_segments: segments.items, keywords },
    leadgen: { customer_segments: segments.items, geographies: company.geographies, keywords },
    fde: { products: products.items, customer_segments: segments.items, delivery_boundaries: company.delivery_boundaries || [] },
    general: { products: products.items, customer_segments: segments.items, keywords }
  };
  console.log(JSON.stringify({ ...common, ...(taskData[task] || taskData.general) }, null, 2));
} catch (error) {
  console.error(JSON.stringify({ tenant_id: tenant, task_type: task, status: "invalid", error: error.message }, null, 2));
  process.exit(1);
}
