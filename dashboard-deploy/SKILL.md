---
name: dashboard-deploy
description: 部署 ZenithJoy 或 Cecelia 的 Dashboard 前端。每当用户说"部署 dashboard"、"上线前端"、"dashboard 挂了"、"推一下 ZD"、"把 Cecelia 的 dashboard 更新"、"deploy dashboard"、"前端没更新"、"刷新一下中台"、"网站打不开"、"502"时，必须使用此 skill。ZenithJoy Dashboard 在 https://autopilot.zenjoymedia.media（HK VPS）；Cecelia Dashboard 在 http://perfect21:5211（本地局域网，不在公网）。
---

# Dashboard 部署

## 先确认要部署哪个

| 关键词 | 目标 |
|--------|------|
| ZD / ZenithJoy / autopilot / 中台 | ZenithJoy Dashboard |
| Cecelia / Brain 前端 / 本地 dashboard | Cecelia Dashboard |

---

## ZenithJoy Dashboard

**公网**：https://autopilot.zenjoymedia.media  
**代码**：`~/perfect21/zenithjoy/apps/dashboard/`  
**容器**：HK VPS `autopilot-dashboard`，bind mount `/opt/zenithjoy/autopilot-dashboard/dist/`

### 部署命令

```bash
cd ~/perfect21/zenithjoy && \
  git pull origin main && \
  npm run build --workspace=apps/dashboard && \
  rsync -avz --delete apps/dashboard/dist/ hk-vps:/opt/zenithjoy/autopilot-dashboard/dist/ && \
  ssh hk-vps "docker restart autopilot-dashboard" && \
  sleep 3 && \
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 https://autopilot.zenjoymedia.media/) && \
  [ "$HTTP_CODE" = "200" ] && echo "✅ 部署完成" || echo "❌ 公网验证失败: $HTTP_CODE"
```

两个常见错误：
- `npm run build` 必须在仓库**根目录**执行，不能 cd 进 apps/dashboard
- rsync 目标是 `/opt/zenithjoy/autopilot-dashboard/dist/`，不是 `/opt/zenithjoy/repo/apps/dashboard/dist/`

### 502 排查

```bash
# 1. 容器是否在跑
ssh hk-vps "docker ps | grep autopilot-dashboard"
# 2. 容器本身是否 200
ssh hk-vps "curl -s -o /dev/null -w '%{http_code}' http://localhost/"
# 3. 如果容器 200 但公网 502 → Cloudflare Tunnel ingress 问题
#    tunnel 在容器里，ingress 必须写 http://172.17.0.1:80（宿主机 bridge gateway）
#    不能写 localhost:80（那是 tunnel 容器自己的 localhost）
```

---

## Cecelia Dashboard

**本地**：http://perfect21:5211/pipeline（局域网，不在公网）  
**代码**：`~/perfect21/cecelia/apps/dashboard/`  
**容器**：本机 `cecelia-frontend`（host 网络），bind mount 本地 dist → build 完自动生效

### 方式 A：Brain webhook（推荐）

```bash
curl -s -X POST http://localhost:5221/api/brain/deploy \
  -H "Content-Type: application/json" \
  -d '{"changed_paths": ["apps/dashboard/src/App.tsx"]}' | python3 -m json.tool

# 轮询直到 idle
until [ "$(curl -s http://localhost:5221/api/brain/deploy/status | python3 -c "import sys,json;print(json.load(sys.stdin).get('status','?'))")" = "idle" ]; do sleep 5; done
echo "✅ 完成"
```

### 方式 B：手动 build（Brain 不可用时）

```bash
cd ~/perfect21/cecelia && git pull origin main && npm run build --workspace=apps/dashboard
# build 完 bind mount 自动生效，无需 restart
```

### 验证

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5211/
```
