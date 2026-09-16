#!/usr/bin/env node

import fs from "node:fs";

const CONFIG_PATH = process.env.OPENCLAW_CONFIG_PATH || "/root/.openclaw/clawdbot.json";

function usage() {
  console.error("Usage: feishu-bitable.mjs list APP_TOKEN TABLE_ID | create APP_TOKEN TABLE_ID FIELDS_JSON | update APP_TOKEN TABLE_ID RECORD_ID FIELDS_JSON");
  process.exit(2);
}

function loadAccount() {
  const config = JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
  const account = config?.channels?.feishu?.accounts?.main;
  if (!account?.appId || !account?.appSecret) {
    throw new Error("Feishu main account credentials are missing from OpenClaw config");
  }
  return account;
}

async function request(method, url, token, body) {
  const response = await fetch(url, {
    method,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let payload;
  try {
    payload = JSON.parse(text);
  } catch {
    throw new Error(`Feishu returned non-JSON response (${response.status})`);
  }
  if (!response.ok || payload.code !== 0) {
    throw new Error(`Feishu API failed (${response.status}): ${payload.code ?? "unknown"} ${payload.msg ?? "unknown"}`);
  }
  return payload;
}

async function tenantToken(account) {
  const payload = await request(
    "POST",
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    null,
    { app_id: account.appId, app_secret: account.appSecret },
  );
  if (!payload.tenant_access_token) throw new Error("Feishu response did not include tenant_access_token");
  return payload.tenant_access_token;
}

async function listRecords(token, appToken, tableId) {
  const items = [];
  let pageToken = "";
  do {
    const url = new URL(`https://open.feishu.cn/open-apis/bitable/v1/apps/${encodeURIComponent(appToken)}/tables/${encodeURIComponent(tableId)}/records`);
    url.searchParams.set("page_size", "500");
    if (pageToken) url.searchParams.set("page_token", pageToken);
    const payload = await request("GET", url.toString(), token);
    items.push(...(payload.data?.items || []));
    pageToken = payload.data?.has_more ? payload.data?.page_token || "" : "";
  } while (pageToken);
  return { code: 0, data: { items, total: items.length } };
}

const [command, appToken, tableId, arg4, arg5] = process.argv.slice(2);
if (!command || !appToken || !tableId) usage();

try {
  const token = await tenantToken(loadAccount());
  let result;
  if (command === "list") {
    result = await listRecords(token, appToken, tableId);
  } else if (command === "create") {
    if (!arg4) usage();
    result = await request(
      "POST",
      `https://open.feishu.cn/open-apis/bitable/v1/apps/${encodeURIComponent(appToken)}/tables/${encodeURIComponent(tableId)}/records`,
      token,
      { fields: JSON.parse(arg4) },
    );
  } else if (command === "update") {
    if (!arg4 || !arg5) usage();
    result = await request(
      "PUT",
      `https://open.feishu.cn/open-apis/bitable/v1/apps/${encodeURIComponent(appToken)}/tables/${encodeURIComponent(tableId)}/records/${encodeURIComponent(arg4)}`,
      token,
      { fields: JSON.parse(arg5) },
    );
  } else {
    usage();
  }
  process.stdout.write(`${JSON.stringify(result)}\n`);
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
