---
name: zenithjoy-deploy
description: ZenithJoy Dashboard 构建和部署到香港服务器的完整流程。每次需要构建、部署、更新 dashboard 到 autopilot.zenjoymedia.media 时必须使用此 skill。涵盖正确的构建命令、rsync 路径、服务器架构、nginx 变更，以及历次踩坑的防坑指南。
---

# ZenithJoy Dashboard 部署

**项目路径**：`/Users/administrator/perfect21/zenithjoy`
**目标服务器**：香港 VPS，SSH 别名 `hk-vps`
**公网地址**：https://autopilot.zenjoymedia.media

---

## 服务器架构（重要，先看这里）

```
用户请求
  → Cloudflare CDN (autopilot.zenjoymedia.media)
  → Cloudflare Tunnel (cecelia-tunnel, host 网络)
  → autopilot-dashboard 容器 (port 80, host 网络) ← 真正的入口
```

**三个 nginx 容器，但入口只有一个：**

| 容器 | 端口 | 网络 | 说明 |
|------|------|------|------|
| `autopilot-dashboard` | 80 (host) | host | **Cloudflare 隧道的真实入口** |
| `autopilot-prod` | 521:80 | bridge | 备用/测试 |
| `autopilot-dev` | 520:80 | bridge | 备用/测试 |

三个容器**共用同一份** nginx.conf：`/opt/zenithjoy/autopilot-dashboard/nginx.conf`

**关键陷阱**：`sed -i` 或 `cp` 修改 nginx.conf 会产生新 inode，三个容器都需要重启才能读到新文件。vim/nano 就地编辑不换 inode，只需 `nginx -s reload`。

---

## nginx.conf 当前路由规则

```nginx
# Brain API
location /api/brain/        →  http://100.71.151.105:5221/api/brain/

# ZenithJoy Mac API（Tailscale）
location /api/              →  http://100.71.151.105:5200/api/

# OAuth 回调（抖音等）
location /auth/             →  http://100.71.151.105:5200/auth/

# SPA fallback
location /                  →  try_files → index.html
```

**新增 API 路由**：Mac API 已通过 `/api/` 代理，只需在 Express 里加路由即可，无需改 nginx。

---

## 标准部署流程（前端 Dashboard）

### 前提：代码已合并到 main

```bash
cd /Users/administrator/perfect21/zenithjoy
git checkout main && git pull origin main
```

### 步骤 1：构建

**必须在仓库根目录执行：**

```bash
npm run build --workspace=apps/dashboard
```

**构建后验证关键改动在 bundle 中**（防止 Vite 用旧缓存）：

```bash
# 如果怀疑构建结果不对，强制全量重建
rm -rf apps/dashboard/dist && npm run build --workspace=apps/dashboard
```

**踩坑（2026-03-31）**：`git reset --hard` 后立即构建，源文件时间戳异常导致 Vite 用旧缓存。

### 步骤 2：rsync 到服务器

```bash
rsync -avz --delete \
  apps/dashboard/dist/ \
  hk-vps:/opt/zenithjoy/autopilot-dashboard/dist/
```

### 步骤 3：重启所有三个容器（必须）

```bash
ssh hk-vps "docker restart autopilot-dashboard autopilot-prod autopilot-dev"
```

**为什么三个都要重启**：共用同一份 bind mount dist/，rsync 产生新 inode，三个容器都需要重新解析路径。

### 步骤 4：验证

```bash
ssh hk-vps "docker ps | grep autopilot"
```

用**无痕窗口**访问 https://autopilot.zenjoymedia.media 验证。

---

## 一键脚本

```bash
cd /Users/administrator/perfect21/zenithjoy && \
  git pull origin main && \
  npm run build --workspace=apps/dashboard && \
  rsync -avz --delete apps/dashboard/dist/ hk-vps:/opt/zenithjoy/autopilot-dashboard/dist/ && \
  ssh hk-vps "docker restart autopilot-dashboard autopilot-prod autopilot-dev" && \
  echo "✅ 部署完成"
```

---

## 修改 nginx 配置

```bash
# 就地编辑（推荐，inode 不变，reload 即可）
ssh hk-vps "vim /opt/zenithjoy/autopilot-dashboard/nginx.conf"
ssh hk-vps "docker exec autopilot-dashboard nginx -t && docker exec autopilot-dashboard nginx -s reload"

# 如果用 sed -i / cp 替换了文件（inode 变了），必须重启三个容器
ssh hk-vps "docker restart autopilot-dashboard autopilot-prod autopilot-dev"
```

---

## Mac API 后端（5200 端口）

Mac 上跑 Node.js API，通过 Tailscale 暴露给 HK 服务器。

```bash
# 查看进程
lsof -i:5200 -n -P

# 重建并重启（注意 kill 旧进程）
lsof -ti:5200 | xargs kill -9 && sleep 1
npm run build --workspace=apps/api
nohup node /Users/administrator/perfect21/zenithjoy/apps/api/dist/index.js > /tmp/api.log 2>&1 &

# 验证
curl http://localhost:5200/health
```

---

## Service Worker 注意事项

Dashboard 有 PWA Service Worker（vite-plugin-pwa）。

- SW 的 `NavigationRoute` 拦截所有浏览器导航请求，`/api/` 路径已加 denylist 排除（2026-04-07 修复）
- 部署新版本后，用户浏览器的旧 SW 需要更新。如果功能异常：
  - Chrome DevTools → Application → Service Workers → Unregister
  - 或无痕窗口验证

---

## 常见问题速查

| 症状 | 原因 | 解决 |
|------|------|------|
| `npm run build` 报 `@vitejs/plugin-react not found` | 在子目录执行 | 切到仓库根目录 |
| rsync 成功但浏览器还是旧版本 | Docker bind mount inode 问题 | 重启三个容器 |
| `/auth/` 或 `/api/` 路径跳回 SPA 首页 | SW NavigationRoute 拦截 | DevTools → SW → Unregister |
| autopilot-dashboard 启动失败：`host not found in upstream "n8n"` | host 网络容器无法解析 Docker hostname | nginx.conf 里用 `172.22.0.2:5678` 而非 `n8n:5678` |
| 修改 nginx.conf 后不生效 | sed/cp 换了 inode | 重启三个容器 |
| 页面白屏（axios 拿到 HTML） | nginx `/api/` 未匹配返回了 index.html | 检查 nginx.conf 有无 /api/ 代理规则 |
| sidebar 菜单不显示 | feature flag 未开启 | 检查 `autopilotConfig.features` |

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `hk-vps:/opt/zenithjoy/autopilot-dashboard/nginx.conf` | 三容器共用的 nginx 配置 |
| `apps/api/src/` | Mac 本地 API 源码（Express） |
| `apps/dashboard/vite.config.ts` | PWA/SW 配置（含 denylist） |
