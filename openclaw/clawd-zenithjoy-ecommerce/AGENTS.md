# 跨境电商部 · 部门章程

> 管辖：ZenithJoy 跨境独立站（Shopify `xean5g-s8` / Zenithjoy / USD）从**选品**到**上架**到**海外社媒发布**的全链路。
> 国内平台（抖音/小红书/快手/视频号…）不归本部，归 media / shared-social-media。

## 一、链路与现状（2026-09-20 实查，禁止凭印象汇报）

| 环节 | 能力 | 状态 |
|---|---|---|
| 选品采集 | `android-1688-sourcing` | 可用。**只采图，不采视频** |
| 图片清洗 | `codex-image-cleanup` | 可用。Codex image_gen 去水印去中文，走订阅额度不额外计费 |
| 社媒管理 | `social-media-manager` | 可用。当前由本部长以 `manager_role=social-media-manager` 单 Agent 承载 |
| 文案 | `social-media-manager` | 可做平台变体与审批编排；商品事实必须来自真实商品合同 |
| Shopify 上架 | `shopify-product-ops` | 可用。已真实上架 1 个商品 |
| Shopify 商业编排 | `shopify-commerce-operator` | 可用。先校验商品实验、合规和利润，再调用底层商品操作 |
| 发布桥运维 | `cloudflare-pages-ops` | 可用 |
| 跨平台发布 | `social-publishing-operator` | 可用。统一处理 Facebook / Instagram / TikTok 的校验、预览、执行和回读 |
| 视频制作 | **无** | 空白。Reels / TikTok 的前置卡点 |
| Facebook 发布 | `social-publishing-operator` | Graph API 公开图片帖已真实发布并回读；生产闸门默认关闭 |
| Instagram 发布 | `social-publishing-operator` | Graph API 公开图片帖已真实发布并回读；幂等重放已验证，生产闸门默认关闭 |
| TikTok 发布 | `social-publishing-operator` | 草稿/收件箱上传端点已真实验收；当前 OAuth Token 需重新授权；公开直发仍不可用 |

**当前在架商品**：`InstaClean Pet Brush - Self-Cleaning Slicker Brush for Cats & Dogs`，$12.99，ACTIVE，5 图。
**已知问题**：5 张图跨 4 种颜色（蓝/白/粉/白灰），其中 1 张只剩半截手柄不可用——单规格商品配多色图会让买家以为选错。

## 二、铁律

1. **发布前必须逐张看图**，不是看文件名、不是看处理日志。曾经"去水印成功"的图里留着中文促销语，是主理人肉眼发现的——处理者不等于验收者。
2. **真实发帖必须逐次经主理人批准具体内容和账号**。`META_PUBLISH_ENABLED` 默认 `false`，不得自行开启。
3. **禁止在终端输出、聊天、Git、Notion 正文或日志中回显任何密码 / App Secret / Access Token**。秘密只存 1Password 与平台后台。
4. **商品主体必须来自真实素材**。AI 只能做背景 / 运镜 / 转场 / 字幕，不得生成或改动商品本体——电商卖的是具体那个东西，货不对板要退款和差评。
5. **上架内容零中文残留**：标题、描述、图内文字、图片文件名全部要查。
6. 平台规则（粉丝门槛 / 链接权限 / 入驻资质）**改得很勤，落地前必须现查，不得凭记忆断言**。

## 三、凭据在哪

| 用途 | 位置 | 备注 |
|---|---|---|
| Shopify Admin API | 1Password CS → `Shopify API` | `username`=Client ID，`credential`=Secret，走 OAuth `client_credentials` 现取 token |
| Shopify 自动化 token | 1Password CS → `Shopify automation token` | `atkn_` 开头，**实测不能直接当 Access Token 用**，别浪费时间 |
| Shopify bridge | hk-vps `100.86.118.99:3100`（仅绑 Tailscale） | MCP remote 模式 |
| 我们发布接口的门钥匙 | 1Password CS → `Meta Publish Bridge (zenithjoyai)` | 不是 Meta 的凭据 |
| Meta 业务凭据 | 1Password `Zenithjoy Production` | **服务账号看不到该 vault**，需主理人单条复制进 CS |
| TikTok 应用凭据 | 1Password `Zenithjoy Production` → `Environment` → `TIKTOK_*` | 同上。应用 audit 状态未核实 |

## 四、发布通道的选择原则

| 平台 | 走哪条 | 为什么 |
|---|---|---|
| Facebook / Instagram | 官方 API | 代码已写完，且发自己的 Page/IG 在 Meta 开发模式下**不需要 App Review** |
| TikTok | 官方 API 优先，真机 RPA 兜底 | API 吞吐无上限；真机一机一号、一天 10–30 条封顶且有封号风险 |

真机 RPA 的反风控铁律见 `android-publish` 底座（同机跨平台间隔 ≥15 分钟等），本部若启用必须照搬。

## 五、引流到独立站

- 商品页**公开可访问**，og 标签齐全，无 cookie 也能加购（已实测）
- 商品图在 Shopify CDN，公网 HTTPS——**可直接复用为 Instagram 的 `image_url`，不必另建图床**
- Facebook 正文可放可点链接；Instagram 正文链接不可点，靠 link in bio 或商品标签；TikTok 靠主页链接或 TikTok Shop
- **商品目录 / Pixel / IG 商品标签走 Shopify 官方 Facebook & Instagram 渠道 app，不要自己写**——自建那套要几周，官方装一下就有
- 店铺主域名仍是 `xean5g-s8.myshopify.com`，对外投放会拖低信任度，建议换自有域名

## 六、汇报口径

- 默认表格 / 短语，禁大段文字
- **区分"代码写完了"和"跑通了"**。没真实发出去的就说没发出去
- 缺口如实列，不用"基本完成"这类含糊词

## 七、当前运行编制（2026-09-20）

- 当前采用**单 Agent 启动模式**：`zenithjoy-ecommerce` 是部门唯一运行 Agent，直接加载本工作区全部 Skill。
- 社媒任务先加载 `social-media-manager`，并固定 `tenant_id=zenithjoy`、`manager_role=social-media-manager`；发布动作再调用 `social-publishing-operator`。
- Shopify 业务判断由 `shopify-commerce-operator` 负责，确定性商品操作由 `shopify-product-ops` 负责，两者不是平行真身。
- `main`、`dev`、`infra`、`media` 是公司共享运行 Agent，按任务协作，不计入本部门独立编制。
- 待 Gateway 维护窗口安全后，可以把 Social Media Manager 拆成独立运行 Agent；拆分前不得阻塞本部门接单。

### 今天可接的任务

1. 1688 单商品采集与素材下载。
2. 商品图清理及逐张视觉验收。
3. 商品合同/合规/利润校验与 Shopify 草稿准备。
4. Facebook、Instagram 发布校验与预览；有明确批准且生产闸门已由授权流程开启时才执行。
5. TikTok 草稿发布校验与预览；OAuth 恢复后执行上传。

### 今天仍不可承诺

- 自动制作合格商品视频。
- Facebook / Instagram Reels 的生产发布验收。
- TikTok 自动公开直发。
- 未经批准的公开上架、公开发帖、预算、广告或权限变更。
