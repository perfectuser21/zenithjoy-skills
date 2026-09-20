---
name: shopify-commerce-operator
description: "Operate a Shopify store from the existing OPC/OpenClaw runtime: verify API access, validate product experiment contracts, read catalog state, and create safe draft products. Use when Zenithjoy/秋米 asks to connect Shopify, prepare or sync products, or turn a product-selection experiment into a Shopify draft."
---

# Shopify 商业运营器

把 Shopify 接入现有 OPC/OpenClaw，不新建第二套总控。Shopify 是商品、结账和订单事实源；飞书/业务对象保存实验、负责人和验收证据；OpenClaw 负责任务推进。

## 路由与所有权

- `zenithjoy-router` / 秋米：租户入口与上下文。
- `main`：把目标拆成 Work Item，维护状态、下一步和验收。
- `dev`：API、商品同步、主题和 Webhook 技术动作。
- `media` / `social-media-manager`：选品研究、素材假设、自然流和广告实验。
- `infra`：密钥引用、Webhook、日志和运行健康。

不要创建新的中央 Agent。需要专业能力时由现有 Agent 调用本 Skill。

## 凭据

只从运行时秘密管理器或进程环境读取：

- `SHOPIFY_STORE_DOMAIN`，例如 `store.myshopify.com`；
- `SHOPIFY_CLIENT_ID`；
- `SHOPIFY_CLIENT_SECRET`；
- `SHOPIFY_API_VERSION`，默认 `2026-07`。

不得把密钥写进任务卡、日志、聊天、代码、Git 或产物。不得打印访问令牌。用户曾在聊天中暴露过的 Secret 只可用于临时验证，生产前必须 Rotate。

## 商品实验合同

每个候选品先建立一个 Product Experiment，至少包含：

- `object_id`、`tenant_id`、`market`、`source_url`；
- `human_owner`、`ai_owner`、`status`；
- `next_action`、`next_check_at`、`acceptance_criteria`、`evidence_url`、`updated_at`；
- 成本、售价、履约费用、支付费率、退款准备金和目标 CPA；
- 知识产权、禁限售、产品安全、广告承诺和素材授权检查；
- 商品标题、描述、规格、价格、图片 URL 和创意假设。

结构见 [商品草稿合同](references/product-draft.schema.json)，示例见 [商品草稿示例](references/product-draft.example.json)。

## 标准流程

1. 预检：运行 `doctor`，核对店铺、API 版本和授权范围。
2. 选品：`media` 输出候选品、目标人群、痛点、差异化角度和盈亏平衡 CPA。
3. 合规：核对侵权、敏感品、功效宣称、素材权利、物流时效和退款风险。任一项未知则进入 `review`，不得公开。
4. 建草稿：先 `validate-draft`，再由 `dev` 经所有者确认后执行 `create-draft --commit`。
5. 回读：保存 Shopify Product GID、handle、状态和 Admin URL 作为 evidence；没有回读不得报告完成。
6. 装修：第一阶段使用 Shopify Online Store 主题和自有域名；无需另建一个与 Shopify 分离的网站。
7. 渠道：Meta/TikTok 首选 Shopify 官方销售渠道应用同步 Pixel/CAPI、目录和订单归因；广告创建与预算仍单独审批。
8. 实验：每个素材绑定 `creative_id`、假设、投放渠道、花费、访问、加购、发起结账、购买、CPA、退款和结论。

## 命令

在本 Skill 目录运行：

```text
node scripts/shopify-admin.mjs doctor
node scripts/shopify-admin.mjs list-products --first 20
node scripts/shopify-admin.mjs validate-draft references/product-draft.example.json
node scripts/shopify-admin.mjs create-draft references/product-draft.example.json
node scripts/shopify-admin.mjs create-draft references/product-draft.example.json --commit
```

`create-draft` 默认只输出将要发送的已脱敏预览；只有显式 `--commit` 才写入 Shopify。此版本只创建 `DRAFT`，不公开发布。

## 动作边界

- 只读查询、合同校验和草稿预览可自动执行。
- 创建 Shopify 草稿商品是外部写入，必须有当前任务的明确授权；脚本仍要求 `--commit`。
- 公开上架、域名切换、支付配置、折扣、邮件发送、社媒发布、Meta/TikTok 广告创建或改预算，必须由业务所有者逐项批准。
- 验证码、登录挑战、授权范围异常、支付/税务/合规信息不确定时停止并请求人工处理。
- 不抓取或复用无权使用的 1688、竞品或社媒素材；AI 改写或混剪不自动消除版权、商标或肖像权风险。

## 完成标准

只有以下内容都存在，才能把“Shopify 接入”标记完成：

- `doctor` 成功并回读目标店铺；
- 权限至少包含 `read_products` 与 `write_products`；
- 商品合同校验通过；
- 若执行创建，Shopify 回读到 `DRAFT` 商品及至少一个 Variant；
- 任务对象记录负责人、下一步、验收条件和 evidence；
- 生产密钥已轮换并通过安全引用注入，日志中没有 Secret 或 Token。

