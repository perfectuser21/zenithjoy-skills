---
name: shopify-store-setup
description: "配置 Shopify 店铺的 API 权限、国家市场、语言和币种，核验前台实际显示。用于扩权限、开市场、价格币种或语言不一致；单个商品编辑查 shopify-product-ops。"
---

# Shopify 店铺配置

## 0. 先判断你卡在哪

| 症状 | 去哪一节 |
|---|---|
| `Access denied for X. Required access: read_Y` | §1 扩权 |
| 商品 ACTIVE 了但 `onlineStoreUrl` 是 null | §2 上线到渠道 |
| 客人看到的币种/语言不对 | §3 市场配置 |

---

## 1. 扩 API 权限（唯一需要人点的一步）

**Shopify 不提供"应用给自己加权限"的 API。**这是设计上的安全边界，不是能力缺失。
别浪费时间找 API，也别用浏览器 RPA 自动化它——让 agent 自己扩自己的权限，
这个口子开了不好收。

### 两个地址，缺一不可

| 步 | 地址 | 做什么 |
|---|---|---|
| 1 | `https://dev.shopify.com/dashboard/<org_id>/apps/<app_id>` | 改 Scopes → **Release** 新版本 |
| 2 | `https://<shop>.myshopify.com/admin/settings/apps` → 应用 → **Update** | 接受新权限 |

ZenithJoy 实例：org `234977440`，app `422011240449`，shop `xean5g-s8`。

⚠️ **只做第 1 步不生效**。Release 只是"声明"，店铺侧的安装记录不会自动更新——
2026-09-24 实测：发布 v1.0.3 后 token 仍只有旧的 6 项，点完 Update 才变 59 项。

⚠️ **别用 partners.shopify.com**。ZenithJoy 用的是新版 `dev.shopify.com/dashboard`，
去 partners 会找不到这个应用。

⚠️ **Scopes 框是整体替换不是追加**。只填新的，旧的会全丢，上架功能当场废掉。
每次都要把已有的一起写进去。

### 找不到 Update 按钮时的兜底

直接走授权链接（client_id 不是密钥，OAuth URL 里本来就公开）：

```
https://<shop>.myshopify.com/admin/oauth/authorize?client_id=<client_id>&scope=<逗号分隔的完整 scope 串>&redirect_uri=https://example.com
```

跳到 `example.com` 打不开是正常的——那是应用配置里的占位地址，
**只要前一页点了同意，权限就已经写进去了**。

若报 `redirect_uri is not whitelisted`，先去 §1 第 1 步把 `https://example.com`
填进 **Allowed redirection URL(s)** 再 Release。

### 验证：两个都要看，只看一个会误判

```bash
# ① 安装记录的权限
curl -s "https://${DOMAIN}/admin/oauth/access_scopes.json" \
  -H "X-Shopify-Access-Token: $TOKEN" | jq -r '.access_scopes[].handle' | sort

# ② token 自己报的 scope（取 token 的响应里就有）
curl -s -X POST "https://${DOMAIN}/admin/oauth/access_token" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"$CID\",\"client_secret\":\"$CSEC\",\"grant_type\":\"client_credentials\"}" \
  | jq -r '.scope'
```

②返回的是**实际生效**的写权限清单，比①更能说明问题。
2026-09-24 诊断就是靠它定位到"Release 了但没 Update"。

**最后一定要实调一次受限接口**，schema 上有 ≠ 你调得动：

```graphql
{ publications(first:3){ nodes { id name } } }
```

---

## 2. 上线到销售渠道（ACTIVE ≠ 能卖）

**这是最容易误判的一条。**`status: ACTIVE` 只表示"商品状态正常"，
和"客人能不能看到"是两回事。判据是 `onlineStoreUrl` 是否为 null。

```bash
# 取 Online Store 渠道 id（需 read_publications）
{ publications(first:10){ nodes { id name } } }
#   → "Online Store" / "Shop" / "Point of Sale" / "Facebook & Instagram"

# 发布
mutation {
  publishablePublish(id:"gid://shopify/Product/…",
                     input:{publicationId:"gid://shopify/Publication/…"}) {
    userErrors { field message }
  }
}
```

回读 `onlineStoreUrl` 非 null 才算成。**再真去抓一次前台页面**——
mutation 返回无错不等于客人打得开。

---

## 3. 市场 / 语言 / 币种

### 顺序不能反

```
加语言(shopLocaleEnable + shopLocaleUpdate published:true)
  → 建市场(marketCreate)
  → 配币种(marketUpdate)
  → 建 webPresence 并挂到市场
  → 抓前台验
```

市场的 webPresence 要引用语言，语言没先加会挂。

### unified markets 的坑

新店默认开 unified markets，此时：

```
marketCurrencySettingsUpdate → ❌ "This action is restricted if unified markets is enabled."
marketUpdate(input:{currencySettings:{baseCurrency:CZK}}) → ✅
```

不确定用哪个就自省 schema，别猜：

```graphql
{ __schema { mutationType { fields { name } } } }
{ __type(name:"MarketUpdateInput"){ inputFields { name type { name kind ofType { name } } } } }
```

### webPresence 要先建再挂

`marketUpdate` 的 `webPresencesToAdd` 要的是**已存在的 ID**，不是内联对象：

```
webPresencesToAdd: LIST→NON_NULL→ID     ← 传对象会报 "Invalid global id"
```

正确两步：

```graphql
mutation { webPresenceCreate(input:{defaultLocale:"cs", subfolderSuffix:"cs"}) {
  webPresence { id } userErrors { field message } } }

mutation { marketUpdate(id:"<marketId>", input:{webPresencesToAdd:["<webPresenceId>"]}) {
  market { name webPresence { subfolderSuffix } } userErrors { field message } } }
```

### ⚠️ subfolderSuffix 不等于最终路径

填 `cs`，Shopify 实际生成的是 **`/cs-cs/`**（市场 handle + 语言）。
按填进去的值去验会拿到 404，容易误判成"没配成"。

**永远从 `webPresence.rootUrls` 读真实 URL**：

```graphql
{ market(id:"…"){ webPresence { rootUrls { locale url } } } }
```

---

## 4. 验收：抓前台，不看 API

API 说成功 ≠ 客人看到的是对的。对照两个站点的同一个商品：

```bash
curl -sL -A "Mozilla/5.0" "<rootUrl>/products/<handle>" -o /tmp/a.html
grep -oE '"price":[0-9]+' /tmp/a.html | sort -u        # 价格（分为单位）
grep -oE 'CZK|"USD"|Kč' /tmp/a.html | sort | uniq -c   # 币种出现次数
grep -oiE 'Přidat do košíku|Add to cart' /tmp/a.html   # 界面语言
```

2026-09-24 实测对照（同一商品）：

| | 捷克站 `/cs-cs/` | 美国站 `/` |
|---|---|---|
| 价格 | `51500` = 515 Kč | `2354` = $23.54 |
| 币种 | CZK ×23 | USD ×18 |
| 按钮 | `přidat do košíku` | Add to cart |

**三项都对上才算配通。**

---

## 5. 别做的事

- 别只在后台点一次就认为配好了——**没抓前台等于没验**
- 别把店铺配置和商品操作混在一起做：改错一个商品影响一个商品，改错市场影响全店
- 别自动化扩权步骤

## 触发范围与原运行约束

Shopify 店铺级配置：扩 API 权限、开新国家市场、配语言与币种、验前台真显示
（✅ 2026-09-24 实测：xean5g-s8 从纯美国单市场 → 捷克市场 CZK/cs 上线）。
与 shopify-product-ops 的分界：那个改商品，这个改整店——爆炸半径差一个量级。
触发场景：Shopify 权限不够 / access denied scope / 开新国家 / 加语言 / 改币种 /
商品上架了但前台看不到 / 标价币种和客人看到的对不上。
