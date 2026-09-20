# Zenithjoy 美国市场最小启动手册

## 一句话架构

```text
TikTok / Facebook / Instagram / SEO
                ↓
       Shopify Online Store
商品页 → 购物车 → Checkout → 支付 → 订单 → 履约
                ↓
 Pixel / Events API / Shopify API / Webhook
                ↓
OpenClaw Product Experiment → 复盘 → 保留、迭代或停止
```

Shopify Online Store 本身就是独立站。第一阶段不要再建一套 Headless 前端；用自有 `.com` 域名、Shopify 免费主题和标准 Checkout 即可。

## 当前接入状态与缺口

- 已验证店铺 API 可访问，现有范围覆盖商品、库存和文件读写。
- 当前商品目录为空，尚未创建商品。
- 要让 OpenClaw 自动回收订单和退款结果，下一版 App 增加 `read_orders`，并订阅 `orders/create`、`orders/paid`、`orders/cancelled`、`refunds/create` Webhook。
- Meta/TikTok 广告第一阶段不走自建 Marketing API，先安装官方渠道应用完成目录、Pixel 和服务端事件连接。
- 主题装修优先用 Shopify 主题编辑器；需要批量版本化后再用 Shopify CLI/GitHub。

## 上线前的六个闸门

1. **真实主体与收款**：商店国家、公司/个人主体、身份证明、地址、银行账户和税务资料必须相互一致。不能仅把后台国家改成美国来替代真实美国业务材料。
2. **物流**：明确发货地、可追踪物流、美国预计送达窗口、丢件/破损处理和退货地址。
3. **毛利**：计算盈亏平衡 CPA：`售价 - 货品 - 头程/尾程 - 支付费 - 履约费 - 退款准备金 - 其他变动成本`。
4. **合规**：禁限售、商标/专利/版权、产品安全、功效宣称、图片/视频/音乐授权全部有结论。
5. **网站信任**：自有域名、品牌邮箱、Contact、Shipping、Returns、Privacy、Terms、FAQ、订单查询与明确时效。
6. **事件验收**：View Content、Add to Cart、Initiate Checkout、Purchase/Complete Payment 在测试订单中只触发一次，币种和金额正确。

## 最快启动顺序

### 第 1 天：店铺底座

- 目标市场只开美国，币种 USD，语言 English。
- 选 Shopify 免费主题，先做单一视觉系统：Logo、两种主色、一种正文字体。
- 连接自有域名；正式开放前保持密码页或主题草稿预览。
- 配好支付、美国运费、税务判断、政策页和客服邮箱。
- 创建一次测试订单并走完整退款演练。

### 第 2 天：三个候选品

- 同时只跑 1 个主品和最多 2 个备选品。
- 每个品先形成 Product Experiment，再生成 Shopify `DRAFT`。
- 商品页结构：问题场景 → 演示 → 三个可证实利益点 → 规格/尺寸 → 包含物 → 时效/退货 → FAQ → CTA。
- 不直接复制供应商标题和详情；不要使用未经授权的商标、图片、视频或夸大承诺。

### 第 3 天：渠道连接

- Shopify Admin → Settings → Sales channels → 安装 **Facebook & Instagram**，连接 Business、Page、Instagram、Ad Account、Catalog、Pixel。
- 在该渠道的 Share data settings 选择合适的数据共享级别；检查隐私政策和适用地区的同意管理。
- 安装 **TikTok** 渠道，连接 TikTok for Business、Business Center、Ads Manager，启用 Pixel + Events API，并同步 Catalog。
- TikTok Shop 是额外的站内店铺能力，不等于 TikTok 广告；是否能开取决于店铺、地址、主体和目标地区资格。即使暂时不开 TikTok Shop，也可在可用地区用广告把流量送到 Shopify。
- 所有素材链接加 UTM：`utm_source`、`utm_medium`、`utm_campaign`、`utm_content=creative_id`。

### 第 4–7 天：素材与实验

- 一个品先做 20–30 条**不同假设**的素材，不做 200 条仅换字幕/镜像的近重复内容。
- 推荐矩阵：5 个角度 × 3 个开头 Hook × 2 个演示/证据 = 30 条。
- 自然流可以先筛 Hook、停留、评论问题和人群语言；它不能单独验证付费获客成本和购买经济性。
- 付费首轮只选一个主渠道。新店建议先按团队更熟悉的平台；若 Facebook 投放能力成熟，先跑 Meta Sales/Purchase；若短视频账号和达人素材更强，先跑 TikTok Website Conversions。
- 广告预算按该品盈亏平衡 CPA 设计，不使用跨品统一固定预算。公开发布、创建广告和改预算必须由所有者确认。

## 诊断顺序

| 现象 | 先看什么 | 常见动作 |
|---|---|---|
| 展示有、点击少 | Hook、首帧、受众与承诺 | 换角度，不急着改站 |
| 点击有、加购少 | 商品页一致性、价格、证据、时效 | 改 Offer/页面/受众匹配 |
| 加购有、结账少 | 运费、信任、移动端、强制字段 | 检查购物车和政策表达 |
| 结账有、付款少 | 支付方式、失败率、总价突增 | 检查支付与 Checkout |
| 有单但亏损 | CPA、毛利、退款、履约 | 提价/组合装/降成本/停品 |

## 早期决策口径（团队启发式，不是平台硬规则）

- 自然流：看素材方向，不直接宣判商品能否规模化。
- 100–200 个合格商品页访问仍几乎无加购时，先修受众/页面/Offer，不继续堆相似素材。
- 5–10 个真实付费订单可判断早期信号；20–30 个在盈亏平衡 CPA 内的付费订单，并且物流、退款和客服可控，才进入下一轮扩量。
- 任何侵权、安全、虚假宣传或收款验证风险优先于转化数据，立即停止并人工复核。

## OpenClaw 回写对象

每次实验至少回写：

- `object_id`、`shopify_product_gid`、`creative_id`、渠道、市场；
- `status`、human/AI owner、下一动作、下次检查时间；
- 展示、三秒观看、点击、商品页访问、加购、结账、购买、花费、收入、CPA、退款；
- 结论 `iterate / scale / stop / review`、原因和证据 URL。

完成不是“发出 API 请求”，而是 Shopify/渠道回读成功、业务对象有证据、下一步明确。

## 官方参考

- Shopify ProductSet: https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet
- Shopify Online Store: https://help.shopify.com/en/manual/online-store/pages/webpages
- Shopify Themes: https://help.shopify.com/en/manual/online-store/themes/adding-themes
- Shopify Domains: https://help.shopify.com/en/manual/domains/custom-domains/about-custom-domains
- Facebook & Instagram by Meta: https://help.shopify.com/en/manual/online-sales-channels/social-commerce/facebook-instagram-by-meta/setup
- Meta Pixel: https://help.shopify.com/en/manual/promoting-marketing/analyze-marketing/meta-pixel
- TikTok on Shopify: https://ads.tiktok.com/resources/help/article/tiktok-app-shopify
- TikTok Shop requirements: https://help.shopify.com/en/manual/online-sales-channels/social-commerce/tiktok/setup
- Shopify Payments country requirements: https://help.shopify.com/en/manual/payments/shopify-payments/supported-countries

