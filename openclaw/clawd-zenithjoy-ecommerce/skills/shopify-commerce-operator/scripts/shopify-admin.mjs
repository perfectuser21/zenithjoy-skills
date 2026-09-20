#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import process from "node:process";

const API_VERSION = process.env.SHOPIFY_API_VERSION || "2026-07";

function fail(message, details = undefined, code = 1) {
  const payload = { ok: false, error: message };
  if (details !== undefined) payload.details = details;
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  process.exit(code);
}

function output(payload) {
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
}

function normalizedStoreDomain() {
  const raw = (process.env.SHOPIFY_STORE_DOMAIN || "").trim();
  if (!raw) fail("Missing SHOPIFY_STORE_DOMAIN");
  let value = raw.replace(/^https?:\/\//i, "").replace(/\/$/, "");
  if (value.includes("/")) fail("SHOPIFY_STORE_DOMAIN must be a hostname only");
  if (!/^[a-z0-9][a-z0-9.-]+$/i.test(value)) fail("Invalid SHOPIFY_STORE_DOMAIN");
  return value.toLowerCase();
}

function credentials() {
  const clientId = process.env.SHOPIFY_CLIENT_ID;
  const clientSecret = process.env.SHOPIFY_CLIENT_SECRET;
  if (!clientId || !clientSecret) fail("Missing SHOPIFY_CLIENT_ID or SHOPIFY_CLIENT_SECRET");
  return { clientId, clientSecret };
}

async function requestToken(store) {
  const { clientId, clientSecret } = credentials();
  const response = await fetch(`https://${store}/admin/oauth/access_token`, {
    method: "POST",
    headers: { "content-type": "application/json", "accept": "application/json" },
    body: JSON.stringify({
      client_id: clientId,
      client_secret: clientSecret,
      grant_type: "client_credentials"
    })
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || !body.access_token) {
    fail("Shopify token request failed", { status: response.status, error: body.error || body.error_description || "unknown" });
  }
  return body.access_token;
}

async function graphql(query, variables = {}) {
  const store = normalizedStoreDomain();
  const token = await requestToken(store);
  const response = await fetch(`https://${store}/admin/api/${API_VERSION}/graphql.json`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "accept": "application/json",
      "x-shopify-access-token": token
    },
    body: JSON.stringify({ query, variables })
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) fail("Shopify GraphQL request failed", { status: response.status, errors: body.errors });
  if (body.errors?.length) fail("Shopify GraphQL returned errors", body.errors);
  return { store, data: body.data, extensions: body.extensions };
}

function isHttpUrl(value) {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}

function validateDraft(draft) {
  const errors = [];
  const requiredStrings = [
    "object_id", "tenant_id", "market", "source_url", "human_owner", "ai_owner",
    "status", "next_action", "next_check_at", "acceptance_criteria", "updated_at"
  ];
  for (const key of requiredStrings) {
    if (typeof draft?.[key] !== "string" || !draft[key].trim()) errors.push(`${key} must be a non-empty string`);
  }
  if (draft?.tenant_id !== "zenithjoy") errors.push("tenant_id must be zenithjoy");
  if (draft?.source_url && !isHttpUrl(draft.source_url)) errors.push("source_url must be an HTTP(S) URL");
  if (!draft?.economics || typeof draft.economics !== "object") errors.push("economics is required");
  const numericEconomics = ["unit_cost", "shipping_cost", "sale_price", "payment_fee_rate", "refund_reserve_rate", "target_cpa"];
  for (const key of numericEconomics) {
    if (!Number.isFinite(draft?.economics?.[key]) || draft.economics[key] < 0) errors.push(`economics.${key} must be a non-negative number`);
  }
  const checks = ["ip_review", "product_safety_review", "claims_review", "asset_rights_review"];
  for (const key of checks) {
    if (!["pass", "review", "fail"].includes(draft?.compliance?.[key])) errors.push(`compliance.${key} must be pass, review, or fail`);
  }
  const product = draft?.product;
  if (!product || typeof product !== "object") errors.push("product is required");
  if (typeof product?.title !== "string" || !product.title.trim()) errors.push("product.title is required");
  if (!Array.isArray(product?.variants) || product.variants.length === 0) errors.push("product.variants must contain at least one variant");
  for (const [index, variant] of (product?.variants || []).entries()) {
    if (!Number.isFinite(variant.price) || variant.price < 0) errors.push(`product.variants[${index}].price must be a non-negative number`);
    if (variant.compare_at_price !== undefined && (!Number.isFinite(variant.compare_at_price) || variant.compare_at_price < variant.price)) {
      errors.push(`product.variants[${index}].compare_at_price must be at least price`);
    }
  }
  for (const [index, file] of (product?.files || []).entries()) {
    if (!isHttpUrl(file.url)) errors.push(`product.files[${index}].url must be an HTTP(S) URL reachable by Shopify`);
  }
  return errors;
}

async function readDraft(path) {
  if (!path) fail("A product draft JSON path is required");
  let draft;
  try {
    draft = JSON.parse(await readFile(path, "utf8"));
  } catch (error) {
    fail("Unable to read product draft JSON", error.message);
  }
  const errors = validateDraft(draft);
  if (errors.length) fail("Product draft validation failed", errors);
  return draft;
}

function productSetInput(draft) {
  const product = draft.product;
  const input = {
    title: product.title.trim(),
    descriptionHtml: product.description_html || "",
    vendor: product.vendor || "",
    productType: product.product_type || "",
    tags: [...new Set([...(product.tags || []), `experiment:${draft.object_id}`, `market:${draft.market}`])],
    status: "DRAFT",
    variants: product.variants.map((variant) => {
      const mapped = {
        price: variant.price,
        optionValues: Object.entries(variant.option_values || {}).map(([optionName, name]) => ({ optionName, name }))
      };
      if (variant.compare_at_price !== undefined) mapped.compareAtPrice = variant.compare_at_price;
      if (variant.sku) mapped.sku = variant.sku;
      return mapped;
    })
  };
  if (Array.isArray(product.options) && product.options.length) {
    input.productOptions = product.options.map((option, index) => ({
      name: option.name,
      position: index + 1,
      values: (option.values || []).map((name) => ({ name }))
    }));
  }
  if (Array.isArray(product.files) && product.files.length) {
    input.files = product.files.map((file) => ({
      originalSource: file.url,
      alt: file.alt || product.title,
      ...(file.filename ? { filename: file.filename } : {}),
      contentType: file.content_type || "IMAGE"
    }));
  }
  return input;
}

async function doctor() {
  const result = await graphql(`query ShopifyOperatorDoctor {
    shop { name myshopifyDomain currencyCode primaryDomain { url host } }
    currentAppInstallation { accessScopes { handle } }
  }`);
  const scopes = result.data.currentAppInstallation?.accessScopes?.map((item) => item.handle).sort() || [];
  const required = ["read_products", "write_products"];
  output({
    ok: required.every((scope) => scopes.includes(scope)),
    api_version: API_VERSION,
    shop: result.data.shop,
    scopes,
    required_scopes_present: Object.fromEntries(required.map((scope) => [scope, scopes.includes(scope)]))
  });
}

async function listProducts(first) {
  const result = await graphql(`query ListProducts($first: Int!) {
    products(first: $first, sortKey: UPDATED_AT, reverse: true) {
      nodes {
        id title handle status updatedAt onlineStoreUrl
        variants(first: 20) { nodes { id title sku price compareAtPrice } }
      }
    }
  }`, { first });
  output({ ok: true, store: result.store, products: result.data.products.nodes });
}

async function createDraft(path, commit) {
  const draft = await readDraft(path);
  const input = productSetInput(draft);
  if (!commit) {
    output({ ok: true, mode: "dry-run", object_id: draft.object_id, input, next: "Re-run with --commit after owner approval" });
    return;
  }
  const result = await graphql(`mutation CreateDraft($input: ProductSetInput!) {
    productSet(synchronous: true, input: $input) {
      product {
        id title handle status updatedAt onlineStoreUrl
        variants(first: 20) { nodes { id title sku price compareAtPrice } }
      }
      userErrors { code field message }
    }
  }`, { input });
  const payload = result.data.productSet;
  if (payload.userErrors?.length) fail("Shopify rejected the draft product", payload.userErrors);
  if (!payload.product || payload.product.status !== "DRAFT") fail("Draft write could not be verified", payload.product);
  output({ ok: true, mode: "committed", object_id: draft.object_id, store: result.store, product: payload.product });
}

function optionValue(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

const [command, path] = process.argv.slice(2).filter((arg) => !arg.startsWith("--") && arg !== optionValue("--first"));

try {
  if (command === "doctor") await doctor();
  else if (command === "list-products") {
    const first = Number(optionValue("--first") || 20);
    if (!Number.isInteger(first) || first < 1 || first > 100) fail("--first must be an integer from 1 to 100");
    await listProducts(first);
  } else if (command === "validate-draft") {
    const draft = await readDraft(path);
    output({ ok: true, object_id: draft.object_id, title: draft.product.title, variants: draft.product.variants.length });
  } else if (command === "create-draft") {
    await createDraft(path, process.argv.includes("--commit"));
  } else {
    fail("Unknown command", "Use doctor, list-products, validate-draft, or create-draft", 2);
  }
} catch (error) {
  fail("Unhandled error", error instanceof Error ? error.message : String(error));
}

