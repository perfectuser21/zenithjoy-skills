---
name: ecommerce-listing-qa
description: |
  商品上架前的成品验收——图文语言一致、数量一致、无他国文字、标价与售价一致。
  ⚠️ 刻意独立于 codex-image-cleanup：处理者不能当验收者。
  ZenithJoy 已在这里栽过两次（2026-09-11 美国站图内中文促销语；2026-09-21 捷克品
  图为西班牙语 + 图写 Five pack 而标题是 6 件套）。
  触发场景：商品要上架 / 上架前检查 / 图对不对 / 能不能发 / 验收商品 / listing QA。
---

# 上架前验收

## 为什么这是独立的一步

两次事故都不是"没处理"，是**处理完了没人验**：

| 时间 | 事故 | 谁发现的 |
|---|---|---|
| 2026-09-11 | 美国站商品图里留着中文促销语「清洁自如，高效省力」 | **主理人肉眼** |
| 2026-09-21 | 捷克品：图是西班牙语；图写 `Five pack` 而标题/变体是 6 件套 | 上架后才发现 |

栽两次说明不是偶然。**洗图的 skill 说"洗好了"不算数**——
自己批自己的作业，永远批得过。

## 铁律

1. **逐张看图,不是看文件名、不是看处理日志。**AI 图像编辑会静默失败：
   返回成功、文件也变了，但水印还在或产品被改形。
2. **验收者 ≠ 处理者。**哪怕都是 AI，也要作为独立一步重新看。
3. **有一项不过就不许上架。**上架后再改，客人可能已经看到。

## 检查清单

### A. 语言一致性

| 查什么 | 怎么查 |
|---|---|
| 标题 / 描述 / 变体名语言 == 目标市场语言 | 读 `title` `descriptionHtml` `variants.title` |
| **图内文字语言 == 目标市场语言** | 逐张看图 |
| 无第三国文字残留 | 中文、日文、以及**别的欧洲语言** |

⚠️ 第三条最容易漏。2026-09-21 那个女巫摆件，标题是捷克语，
图上却是西班牙语 `Elegante en la estantería`——货源方给的多语版本混了。

```python
import re
zh = re.findall(r'[一-鿿]+', title + desc)   # 中文
# 图内文字必须人眼看，OCR 不可靠也不必要——就几张图
```

### B. 数量 / 规格一致性

**标题、变体、图上的数字必须三者一致。**

2026-09-21 实例：

```
标题:  6-dílná sady（6 件套）
变体:  Sada 6 kusů（6 件）
图上:  Five pack（5 件）        ← 货不对板
```

客人看图以为 5 件，下单是 6 件套——**退款和差评的直接来源**。

### C. 价格一致性

| 查什么 |
|---|
| 标题里写的价（如 `590 Kč`）与变体 `price` 换算后是否对得上 |
| 目标市场的币种是否已配（见 `shopify-store-setup`）——否则客人看到的是店铺主币种 |

### D. 图片可用性

| 查什么 |
|---|
| 无水印、无他方品牌 |
| 产品主体完整，没被裁断 |
| 同一商品的图**颜色/款式一致**——单规格商品配多色图会让客人以为选错 |
| 没有"半截手柄"这种看不出是什么的废图 |

2026-09-11 实例：5 张图跨 4 种颜色（蓝/白/粉/白灰），其中 1 张只剩一截白手柄。

### E. 分类与标签

| 查什么 |
|---|
| `productType` 填到位 |
| 市场标签（如 `market:CZ`）与实际目标市场一致 |

## 取数

```bash
curl -s -X POST "https://${DOMAIN}/admin/api/2025-01/graphql.json" \
  -H "X-Shopify-Access-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"{ products(first:10, query:\"status:DRAFT\"){ nodes {
        title descriptionHtml productType tags
        variants(first:10){ nodes { title price } }
        media(first:20){ nodes { ... on MediaImage { image { url } } } } } } }"}'
```

图下载到 scratchpad 后**逐张打开看**：

```bash
curl -s -o "$SB/p1.jpg" "<image url>"
# 然后用 Read 工具真的看这张图
```

## 判定

| 结果 | 动作 |
|---|---|
| 全过 | 放行上架（见 `shopify-store-setup` §2） |
| 任一不过 | **拦下**，列出具体哪张图 / 哪个字段 / 差在哪，不含糊说"建议优化" |

## 已上架才发现问题怎么办

先改回 `DRAFT` 止血，再修。别留着边卖边改——
客人已经看到的错误信息会变成订单纠纷。

```graphql
mutation { productUpdate(input:{id:"…", status:DRAFT}) { product { status } } }
```
