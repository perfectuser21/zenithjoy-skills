---
name: social-bridge-ops
description: |
  ZenithJoy 社媒发布桥的内部机制与排障（zenithjoyai.com 上的 Pages Functions）：
  为什么幂等必须 D1 不能 KV、TikTok token 如何自愈、健康探针为何会说谎、闸门语义。
  与 social-publishing-operator 的分界：那个是"怎么调用桥"，这个是"桥内部怎么回事、坏了怎么修"。
  触发场景：发布桥报错 / access_token_invalid / idempotency_store_not_configured /
  重复发帖 / 幂等 / 发布闸 / TikTok token 过期 / 桥部署。
---

# 社媒发布桥运维

## 桥的构成

```
/api/meta/{publish,status,draft}            Facebook / Instagram
/api/tiktok/{creator,draft,publish,status}  TikTok
```

跑在 Cloudflare Pages Functions（Workers 运行时，只有 Web Platform API，无 Node）。
主机侧运维见 `cloudflare-pages-ops`。

## 1. 幂等：为什么必须 D1

**KV 不能用于生产。**KV 只有 `get` / `put`，没有条件写，
「先读再写」之间的窗口会让并发请求各自调一次上游发布接口 = **重复发帖**。

D1 的主键约束让声明成为一次原子操作：

```sql
INSERT INTO <table> (…) VALUES (…)
ON CONFLICT(<pk>) DO NOTHING
-- 只有 meta.changes === 1 的那个调用者拿到 claimed:true
```

三张表都在同一个 D1 库 `zenithjoy-meta-publish`：

| 表 | 主键 | 用途 |
|---|---|---|
| `meta_publish_attempts` | `idempotency_key` | Meta 发布幂等 |
| `tiktok_publish_attempts` | `(operation, idempotency_key)` | TikTok 发布幂等 |
| `tiktok_oauth_tokens` | `id`（恒 `default`） | TikTok 令牌 |

⚠️ **TikTok 主键必须含 `operation`**。同一份内容「先传草稿、再私密发布」
复用同一个 idempotencyKey 是合法的；只按 key 做主键，草稿记录会把随后的发布
误判成重放而**静默跳过**——丢动作比重复发布更难发现。

### 绑定必须写在 wrangler.toml

后台 PATCH 出来的 `d1_databases` 会在下一次 `wrangler pages deploy` 后变成 null。
**本地配置是部署的唯一真相。**同理 `[vars]` 里必须囊括**全部**非机密运行变量——
漏一个就会被部署抹掉。

2026-09-21 实测：`TIKTOK_MEDIA_HOSTS` 没写进 wrangler.toml，
差点在部署时被抹掉——那是 draft 的 host 白名单，失效后草稿上传全拒。

⚠️ **「plain_text 会被抹掉、secret_text 不会」这个区分不成立。**
2026-09-21 实测 secret 类型的 `META_GRAPH_API_VERSION` 同样在部署后消失。

## 2. TikTok token 自愈

| | 有效期 |
|---|---|
| access token | **24 小时** |
| refresh token | 约 365 天 |

桥自己换票，不需要人工重新授权：

```
D1 记录 → 无记录则用 env 种子落库 → 过期则刷新并回写
上游回 access_token_invalid → 强制刷新 + 只重试一次
```

⚠️ **TikTok 会轮换 refresh_token**，响应里带回的那个才是下次能用的。
不回写就等于把下一次刷新的钥匙丢了，届时只能人工重新授权——问题绕一圈回到原点。

⚠️ **表未就绪时退回 env 种子票**，不要硬失败。部署与建表之间有窗口，
这段时间发布链不该整条挂掉。

## 3. 健康探针会说谎

`/api/meta/status` 和 `/api/tiktok/creator` 都报 `idempotencyConfigured`。
**它必须与 publish 路径的 store 解析用同一套优先级**（D1 优先、KV 兜底）。

两次都犯过同一个错：探针只看 KV，线上绑了 D1 却报 `false`。

**误报比没有探针更糟**——它会诱使运维把无原子声明的 KV 加回来，
而那正是重复发帖的来源。

现在两个探针都带 `idempotencyBackend` 字段（`d1` / `kv` / `null`），别再靠猜。

## 4. 发布闸

| 变量 | 默认 | 含义 |
|---|---|---|
| `META_PUBLISH_ENABLED` | `false` | Meta 真实发布 |
| `TIKTOK_PUBLISH_ENABLED` | `false` | TikTok 私密直发 |
| `META_DRAFT_ENABLED` | `true` | Meta 草稿 |
| `TIKTOK_DRAFT_UPLOAD_ENABLED` | `true` | TikTok 收件箱草稿 |

**真实发帖必须逐次经主理人批准具体内容和账号。**不得自行开闸。

调用方还要带 `confirm`（Meta `PUBLISH` / TikTok `PUBLISH_PRIVATE` / 草稿 `UPLOAD_DRAFT`），
双闸都满足才会真发。

## 5. 排障对照表

| 返回 | 含义 | 怎么办 |
|---|---|---|
| `401 unauthorized` | 桥的 Bearer key 不对 | 取 1Password CS `Social Publish Bridge (zenithjoyai)` |
| `503 not_configured` + `missing:[…]` | 列出的环境变量缺失 | 补进 `wrangler.toml` 后重新部署，别只在后台加 |
| `503 idempotency_store_not_configured` | D1 绑定丢了 | 检查 `wrangler.toml` 的 `[[d1_databases]]`，重新部署 |
| `403 publishing_not_confirmed` | 闸门关着或 confirm 没带 | 正常行为，需主理人批准后才开 |
| `409 idempotency_key_conflict` | 同 key 不同内容 | 换 key，别复用 |
| `409 *_outcome_requires_review` | 已被声明但未收敛 | **人工复核，绝不盲目重试**——重试会重复发帖 |
| `tiktok_error / access_token_invalid` | 票失效 | 正常，桥会自动刷新重试一次；持续报错说明 refresh token 也失效，需重新授权 |

## 6. 验收铁律

**成功的 HTTP 响应不算发布成功。**必须回读平台侧证据：

```bash
# Facebook
GET https://graph.facebook.com/v26.0/<page_id>/posts?fields=id,created_time,message,permalink_url
# Instagram
GET https://graph.facebook.com/v26.0/<ig_business_id>/media?fields=id,timestamp,caption,permalink
# TikTok
POST /api/tiktok/status  { "publish_id": "…" }
```

拿到平台 content id + permalink 才算 `Published`，否则记
`Publish submitted / verification pending`。
