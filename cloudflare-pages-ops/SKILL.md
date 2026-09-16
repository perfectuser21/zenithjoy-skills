---
name: cloudflare-pages-ops
description: Cloudflare Pages 站点运维（✅ 2026-09-12 实测：wrangler 直传部署 / 绑自定义域+签证书 / Functions 上线）。
  以 zenithjoyai.com（Astro GEO 站）为实例，含构建假卡死、curl -I 假象、权限误判三个真实踩坑。
  触发场景：部署 zenithjoyai / 更新 GEO 站 / Pages 部署 / 绑子域名 / wrangler / Pages Functions / 加验证文件。
---

# Cloudflare Pages 运维

**与 `cloudflared` skill 无关**（那个是 SSH 隧道）。本 skill 管 Pages 站点。

## 实例档案

| 项 | 值 |
|---|---|
| account | `1e06934c7e8134910ffcc5b7761fbc68`（Alex Xu，唯一账号） |
| Pages 项目 | `zenithjoyai`（另有 `zenithjoyai-preview`） |
| 自定义域 | `zenithjoyai.com`、`www.zenithjoyai.com` 均 active |
| 源码 | `zenithjoy-workspace/apps/geoai`（Astro + i18n zh/en） |
| **部署方式** | **直传（未连 Git）——合并 main 不会自动部署，必须手动跑** |

## 部署

```bash
cd ~/perfect21/zenithjoy-workspace/apps/geoai
npm install && npm run build
source ~/.credentials/cloudflare.env
export CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID=1e06934c7e8134910ffcc5b7761fbc68
npx wrangler@latest pages deploy dist --project-name=zenithjoyai --branch=main --commit-dirty=true
```

`functions/` 目录会随 `dist/` 一并上传，不需要单独操作。

## 🔴 坑 1：构建"卡死"其实是正常的

`src/data/posts.ts` 构建时会拉 `https://dashboard.zenjoymedia.media:3000/api/contents`。
**3000 不在 Cloudflare 可代理端口列表**，该连接必然 SYN_SENT 挂起到超时（每页 ~10.5s），
然后走静态 fallback（commit f526515b 就是为此加的）。

- 页面多时整个构建要 **5-10 分钟**，日志刷 `UND_ERR_CONNECT_TIMEOUT` 是**预期行为不是故障**
- 判断进度看 `dist/` 文件数在涨、日志在出新页面路径
- **不要用 `pgrep -f "astro build"` 写等待循环**——watcher 自己的命令行含这串字会自匹配，永远不退出（实测僵住 7 小时）。用 `pgrep -f 'node.*\.bin/astro'`

## 🔴 坑 2：`curl -I` 测 Functions 会得到假结果

Pages Function 若只导出 `onRequestGet`，**HEAD 请求不走它**，落到 Pages 静态默认处理，
于是你看到的是默认响应头，会误判"我设的安全头被平台覆盖了"。

**测 Function 必须用 GET**：`curl -s -D - -o /dev/null <url>`

## 🔴 坑 3：Pages 权限 ≠ Zone 权限

`~/.credentials/cloudflare.env` 那个 token 备注写"全权限"，实际**按域名授权、只含 zenjoymedia.media**：

| 操作 | 该 token 能否 |
|---|---|
| 列 Pages 项目 / 部署 / 绑自定义域 | ✅ 能（账号级 Pages 权限） |
| 查 `zenithjoyai.com` 的 zone / 改 DNS | ❌ 不能（`/zones?name=` 返回 success 但 0 条） |
| 创建新 API token | ❌ 不能（`9109 Valid user-level authentication not found`） |
| `/user/tokens/verify` | ❌ 报 Invalid（缺 User→API Tokens→Read，**不代表 token 失效**） |

**教训**：某资源查不到时先分清是哪类权限，别一刀切说"没权限"就把活推给用户。
查不到 zone 时，DNS 现状可用 `dig @1.1.1.1` 公共查询替代。

## 绑自定义域

```bash
# 1 查现有
curl -s ".../accounts/$ACCT/pages/projects/zenithjoyai/domains" -H "Authorization: Bearer $TOKEN"
# 2 关联（DNS CNAME 若已指向 <project>.pages.dev 则保持不动，不要删了重建）
curl -s -X POST ".../domains" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"name":"www.zenithjoyai.com"}'
# 3 轮询到 active（实测 Google CA 约 90 秒）
curl -s ".../domains/www.zenithjoyai.com" -H "Authorization: Bearer $TOKEN"
```

status 流转：`initializing → pending → active`。未 active 前 TLS 握手必失败，此时做 HTTP 验收没意义。

## 静态文件 / 验证文件

放 `public/`，构建后自动进 `dist/`。**只改 `dist/` 不改 `public/` 的话，下次构建就丢**。

急用时可两边都写（`public/` 保命 + `dist/` 免去重新构建直接部署）。

`.txt` 会自动以 `text/plain; charset=utf-8` 提供。

## Astro 尾斜杠

`/zh/privacy-policy` 会 301 补成 `/zh/privacy-policy/`。
**对外提交 URL（如平台审核表单）一律带尾斜杠**，否则多一跳重定向。
