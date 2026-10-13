---
name: docs-center
description: "将内部总结、报告、方法手册或培训 HTML 发布到 ZenithJoy 香港文档中心，提供公网分享链接。用户要求放公网、发布文档或给可打开网页链接时使用。"
---

# ZenithJoy 文档中心发布

团队内部总结 / 方法手册 / 培训材料 / 报告的**统一公网存放处**。全部收敛到 HK 一个地方,别再散落各处。

## 关键事实(先记住,别踩坑)

- **公网入口(首选,HTTPS)**:`https://docs.zenjoymedia.media/`
- **兜底入口**:`http://124.156.138.116:8088/`(裸端口,无 HTTPS;域名故障时用)
- **为什么用独立子域名 / 独立端口、不用 dashboard 域名**:dashboard(`cn.zenjoymedia.media`)是 PWA,**同源**下放静态页会被 service worker 打回主页。`docs.zenjoymedia.media` 是**独立子域名 = 独立 origin**,PWA 的 SW 够不着 → 绝不回主页。**永远不要把文档塞进 cn / dashboard 域名下。**
- **访问口令**:Basic Auth,凭据在 1Password CS Vault "ZenithJoy 文档中心 (HK docs)"(user=xuxiao21xx@icloud.com)。口令给**看的人**用;**发布动作走 SSH,不需要口令**。
- **架构**:HK 上 Caddy(容器 `cn-https`,Caddyfile 在 `/opt/cn-caddy/Caddyfile`)以站点块 `docs.zenjoymedia.media { reverse_proxy zj-docs:80 }` 反代到文档容器,Caddy 自动签 Let's Encrypt(TLS-ALPN over 443)。文档容器 `zj-docs`(nginx:alpine,`--restart unless-stopped`,`-p 8088:80`,已接入 `zenithjoy-net`),docroot 只读挂载 HK `/data/docs/`。Basic Auth + `X-Robots-Tag: noindex` 在容器 nginx 里(`/opt/zj-docs/default.conf` + `/opt/zj-docs/.htpasswd`)。加文件即时生效,不用重启。
- DNS:`docs` A 记录在 Cloudflare 区 `zenjoymedia.media`(proxied=false/grey,直指 124.156.138.116)。Cloudflare API 凭据在 1Password CS "Cloudflare"。

## 发布一份新文档(标准流程)

### 1. 写好 HTML(自带骨架)
本地写完整 HTML,**必须自带** doctype/html/head/body 骨架(裸静态直出,不像 Artifact 会外包)。head 放 charset、viewport、title,建议加 `<meta name="robots" content="noindex,nofollow">`。设计语言复用文档中心那套(蓝 accent `#2b6cb0` / PingFang / 深浅主题 token),可先拉现有页 `/eval-training/` 抄 `:root` token 块。视觉要求高时配合 `artifact-design` skill。给文档起 kebab-case slug。

### 2. 传到 HK 并落位
用 SSH 把 HTML 送到 `hk-vps:/tmp/<slug>.html`,再 `sudo` 落位:`sudo mkdir -p /data/docs/<slug>` → `sudo cp` 到 `/data/docs/<slug>/index.html` → `sudo chmod 644`。HK 写 `/data/docs`、`/opt/zj-docs` 需 `sudo`(免密可用)。

### 3. 首页索引加卡
编辑 HK `/data/docs/index.html`,在 `<div class="grid">` 加一张卡(照抄现有卡):
```html
<a class="card" href="/<slug>/">
  <h2>文档标题</h2>
  <p>一句话描述。</p>
  <div class="meta"><span class="tag">分类</span><span>YYYY-MM-DD</span><span>打开 →</span></div>
</a>
```
拉到本地改→送回 HK `/tmp`→`sudo cp` 覆盖。日期用真实当天。

### 4. 验证公网可达(必做)
从**异地**(如美国机)`curl` `https://docs.zenjoymedia.media/<slug>/`:无口令应 401;带口令(`-u <邮箱>:<pass>`)应 200 且抓到 `<title>`。pass 从 1Password 取:`source ~/.credentials/1password.env && export OP_SERVICE_ACCOUNT_TOKEN && op item get "ZenithJoy 文档中心 (HK docs)" --vault CS --fields password`。
注意:刚建的新 slug 若某机 `curl` 报 `Could not resolve`,是该机 DNS 负缓存,用 `dig @8.8.8.8` 或 `--resolve ...:443:124.156.138.116` 验证真身,别误判故障。

### 5. 交付
给用户 `https://docs.zenjoymedia.media/<slug>/`,提醒账号密码在 1Password CS("ZenithJoy 文档中心 (HK docs)")。

## 常见坑
- **不要**放进 cn / dashboard 域名(PWA 打回主页)。docs 子域名/8088 端口就是为躲这个。
- **不要**在美国机 wx 域名或别处另开一份 → 那是"散"的来源,已清理,别复活。
- 裸静态页**必须自带 doctype/html/head/body 骨架**。
- 新域名/新页 `curl 000` 多半是本机 DNS 负缓存,不是真挂;`dig @8.8.8.8` 一验便知。

相关记忆:见 memory `zenithjoy_docs_center_hk`。

## 触发范围与原运行约束

把生成的总结 / 方法手册 / 培训 / 报告等 HTML 发布到 ZenithJoy 内部文档中心(HK 香港节点,公网可访问)。只要用户说"放公网 / 放到公网 / 放文档中心 / 发布这份总结 / 把这个放上去 / 给我个能打开的网页 / publish this doc",哪怕没说"文档中心"原词,都要触发本 skill。这是团队所有内部 HTML 文档的唯一统一入口——不要再往美国机、artifact、dashboard 域名下散着放。凡是"要把一份 HTML 内容变成一个能分享的公网链接",默认走这里。
