---
name: shopify-product-ops
description: Shopify 商品操作实战手册（✅ 2026-09-11 全链路实测：建草稿→传图→改文案→删图）。
  覆盖 OAuth client_credentials 取 token、GraphQL productSet 建草稿商品、stagedUploadsCreate 三步传图、
  productUpdate 改标题描述、productDeleteMedia 删图。
  触发场景：Shopify 上架 / 建商品 / 传商品图 / 改商品文案 / 调 Shopify Admin API / 独立站商品管理。
---

# Shopify 商品操作

店铺：`xean5g-s8.myshopify.com`（US / USD / trial）。凭据在 1Password CS vault 条目 **`Shopify API`**。

## 0. 取 access_token（每次调用前）

⚠️ **中国大陆不能用 Shopify Payments 那套，但 Admin API 完全可用**。走 OAuth client_credentials：

```bash
source ~/.credentials/1password.env && export OP_SERVICE_ACCOUNT_TOKEN
DOMAIN="xean5g-s8.myshopify.com"
CID=$(op item get "Shopify API" --vault CS --fields username --reveal)
CSEC=$(op item get "Shopify API" --vault CS --fields credential --reveal)
curl -s -o /tmp/tok.json -X POST "https://${DOMAIN}/admin/oauth/access_token" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d "{\"client_id\":\"${CID}\",\"client_secret\":\"${CSEC}\",\"grant_type\":\"client_credentials\"}"
TOKEN=$(python3 -c "import json;print(json.load(open('/tmp/tok.json'))['access_token'])")
rm -f /tmp/tok.json; unset CID CSEC
```

条目字段对照（**名字有坑，不是直觉的那样**）：

| 1Password 字段 | 实际含义 |
|---|---|
| `username` | Client ID（32 位 hex） |
| `credential` | Client Secret（`shpss_` 开头） |

另有条目 `Shopify automation token`（`atkn_` 开头）——**实测不能直接当 `X-Shopify-Access-Token` 用**（401），用途不明，别浪费时间。

当前 scope：`write_files,write_inventory,write_products`。**没有 `read_legal_policies`**，政策页读写不了，只能人工在后台操作。

## 1. 建草稿商品

`ProductSetInput` **没有** `price` / `compareAtPrice` / `sku` 顶层字段——必须走 `productOptions` + `variants`：

```graphql
mutation productSet($input: ProductSetInput!, $synchronous: Boolean) {
  productSet(input: $input, synchronous: $synchronous) {
    product { id title handle status }
    userErrors { field message }
  }
}
```

```json
{
  "synchronous": true,
  "input": {
    "title": "...", "descriptionHtml": "<p>...</p>",
    "vendor": "...", "productType": "...", "tags": ["..."],
    "status": "DRAFT",
    "productOptions": [{ "name": "Title", "values": [{ "name": "Default Title" }] }],
    "variants": [{
      "optionValues": [{ "optionName": "Title", "name": "Default Title" }],
      "price": "12.99", "compareAtPrice": "24.99", "sku": "..."
    }]
  }
}
```

端点：`POST https://$DOMAIN/admin/api/2026-01/graphql.json`，头 `X-Shopify-Access-Token: $TOKEN`。

## 2. 传图（三步，缺一不可）

```
stagedUploadsCreate  →  multipart POST 到返回的 url  →  productCreateMedia
```

要点：
- `stagedUploadsCreate` 入参 `{resource:"IMAGE", filename, mimeType, fileSize:"<字符串>", httpMethod:"POST"}`
- multipart body 必须**先按顺序拼完返回的所有 `parameters`，再拼 `file` 字段**，顺序错会被 S3 拒
- `productCreateMedia` 用上一步返回的 `resourceUrl` 作 `originalSource`
- 内容相同的文件 Cloudflare/Shopify 会按 hash 去重，显示 "0 files uploaded" 属正常，不是失败

## 3. 改标题/描述

```graphql
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) { product { id title } userErrors { field message } }
}
```

## 4. 删图（❗最容易踩的坑）

**REST `/products/{id}/images.json` 返回的 `id` 不能直接用于 GraphQL 删除。**

- REST 返回：`41483962449974`
- GraphQL 要的：`gid://shopify/MediaImage/32578202730550` —— **两者是不同的数字**

必须先用 GraphQL 查真实 MediaImage GID：

```graphql
query { product(id: "gid://shopify/Product/<id>") {
  media(first: 20) { edges { node { id ... on MediaImage { image { url } } } } } } }
```

再 `productDeleteMedia(productId, mediaIds)`。用错 ID 会报 `Media ids ... do not exist`。

## 4.5 上线到销售渠道（❗ACTIVE 不等于能卖）

建完的商品即使 `status` 是 `ACTIVE`，客人也可能看不到——
**「商品状态正常」和「已上架到店面」是两回事。**

判据是 `onlineStoreUrl`：

```bash
{ products(first:20){ nodes { title status onlineStoreUrl } } }
```

`onlineStoreUrl` 为 null = 没上线。2026-09-24 实测：5 个商品全部 ACTIVE，
前台可见数 1/6，差的就是这一步。

发布方法（需 `read_publications` + `write_publications`）：

```graphql
# ① 取 Online Store 渠道 id
{ publications(first:10){ nodes { id name } } }
#   → Online Store / Shop / Point of Sale / Facebook & Instagram

# ② 发布
mutation {
  publishablePublish(id:"gid://shopify/Product/…",
                     input:{publicationId:"gid://shopify/Publication/…"}) {
    userErrors { field message }
  }
}
```

回读 `onlineStoreUrl` 非 null 才算成，**并且真去抓一次前台页面**——
mutation 无错不等于客人打得开。

> 权限不够、开新国家市场、配语言币种 → 见 `shopify-store-setup`。
> 上架前的成品验收（图文语言/数量/价格一致性）→ 见 `ecommerce-listing-qa`。

## 5. 验收查询

```bash
curl -s "https://${DOMAIN}/admin/api/2026-01/products/<id>.json" -H "X-Shopify-Access-Token: ${TOKEN}"
curl -s "https://${DOMAIN}/admin/api/2026-01/shop.json"          -H "X-Shopify-Access-Token: ${TOKEN}"
```

`shop.json` 里几个关键字段：`password_enabled`（true=店铺锁着外人进不来）、`plan_name`、`eligible_for_payments`。

## 6. 安全策略（P0 已实现）

`zenithjoy-shopify-bridge` 有 `SHOPIFY_MCP_TOOL_ACCESS_MODE=p0-draft-only`：工具面收窄到只读白名单 + `create-product`，且 status **服务端强制 DRAFT**（不管调用方传什么）。给 AI/agent 调用时用这个模式，别开全权限。

## 7. 必填字段缺失时禁止编造（金丝雀实测：price 缺失场景会被编造）

`price`、`compareAtPrice`、`sku`、`vendor` 这类商品必填字段，调用方没有给出真实值时：
**禁止填一个"看起来合理"的数字或占位文本去凑齐请求**。正确处理：
- 能确定该字段本次不需要写入（如仅改标题）→ 不带这个字段。
- 该字段是本次操作必须的、但调用方没提供 → 不发起 mutation，报告"缺少 <字段名>，需要调用方提供"，等待补充。
- 绝不用同类商品的历史价格、行业均价或任意数字替代真实值——草稿即使标了 DRAFT，编造的价格一旦被后台人工放行发布，就是真实的错误定价。
