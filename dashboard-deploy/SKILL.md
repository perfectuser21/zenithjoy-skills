---
name: dashboard-deploy
description: 部署 ZenithJoy 或 Cecelia 的 Dashboard 前端，以及把单个页面/报表/HTML 视图放上 dashboard。每当用户说"部署 dashboard"、"上线前端"、"dashboard 挂了"、"推一下 ZD"、"把 Cecelia 的 dashboard 更新"、"deploy dashboard"、"前端没更新"、"刷新一下中台"、"网站打不开"、"502"，或者说"把这个页面放到 dashboard 上"、"放到 perfect21:5211 / autopilot 上"、"做个页面让我能打开"、"页面打开自动回主页 / 回首页 / 被打回主页"时，必须使用此 skill。ZenithJoy Dashboard 在 https://autopilot.zenjoymedia.media（HK VPS，客户端公网）；Cecelia Dashboard 在 http://perfect21:5211（本机局域网，不在公网）。两个都是 PWA 单页应用——直接丢静态 .html 会被 service worker 打回主页，必须看本 skill 的"放单个页面"章节。
---

# Dashboard 部署

## 先确认要部署哪个

| 关键词 | 目标 |
|--------|------|
| ZD / ZenithJoy / autopilot / 中台 | ZenithJoy Dashboard |
| Cecelia / Brain 前端 / 本地 dashboard | Cecelia Dashboard |

也先分清是哪种任务：**整体部署**（改了前端代码、要上线一版）走下面的 ZenithJoy / Cecelia 章节；**放单个页面**（把一个报表 / HTML 视图 / 看板挂到 dashboard 上给人看）走下面这节。

---

## 放单个页面到 Dashboard（不是整体部署）

用户想"把这个页面放到 dashboard 上 / 给我个能打开的链接"时走这里。**两个 dashboard 都是 PWA 单页应用（service worker + 前端路由），这会咬人**——先理解坑，再选路子。

### ⚠️ 核心坑：直接丢静态 .html 会被打回主页

很自然的做法是把 `xxx.html` 丢进 dashboard 的 `dist/`，服务器确实会服务它——`curl http://perfect21:5211/xxx.html` 能拿到正确内容、200。**但用户浏览器打开却自动跳回主页**。原因：

- dashboard 注册了 **service worker**，它控制整个源（scope `/`）下的所有页面导航。
- 用户浏览器里那个 SW 往往是**上一版部署留下的旧 SW**，会把导航请求拦截、返回 app 壳（= 主页），轮不到你的静态文件。
- **`Cmd+Shift+R` 硬刷绕不过 SW**（硬刷只跳过 HTTP 缓存，请求仍走 SW 的 fetch 拦截）。必须**注销 SW**（DevTools → Application → Service Workers → Unregister）或关掉所有该站点标签页让新 SW 接管，才轮到静态文件。
- 另外 Cecelia 的 `frontend-proxy.js` 逻辑是"文件存在就服务、不存在就 SPA 兜底返回 index.html"，所以**路径名打错 / 文件没真落到 dist** 也会表现为"回主页"——先 `curl` 确认服务端真能 200 拿到你的内容，再排查浏览器 SW。

诊断口诀：**`curl` 拿得到内容但浏览器回主页 = SW 在作怪；`curl` 也回主页 = 文件没到位 / 路径错。**

### 选哪条路

| 目的 | 做法 | 为什么 |
|------|------|--------|
| **就想现在看一眼**（内容还在迭代、没定稿） | 用**无 SW 的独立端口**起静态服务，给独立 URL | 换个源就没有 SW 来抢，绝不回主页，零浏览器折腾。最适合"先看看对不对" |
| **要做成 dashboard 里的永久页** | 在前端 app 里加**真 SPA 路由**（React Router），再 `vite build` + 部署 | rebuild 会**重新生成 SW**，回主页问题自动消失；页面是一等公民，能带导航入口、读 Brain 实时数据 |
| 一定要用静态 .html 放进现有 build | 把文件放 `public/`，并在 `vite.config` 的 workbox `globPatterns` 加上 `html` 让 SW 预缓存，再 rebuild + 让用户更新 SW | 不加预缓存的 .html 是二等公民，仍会被 SW/路由挤掉。一般不如直接做成路由 |

**无 SW 预览（看一眼，最省事）：**

```bash
# 把要看的 html 所在目录起一个纯静态服务，换个端口 = 换个源 = 没有 SW
nohup python3 -m http.server 5300 --bind 0.0.0.0 --directory <html所在目录> > /tmp/preview.log 2>&1 &
sleep 1 && curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5300/<file>.html
# 给用户：http://perfect21:5300/<file>.html
```

**永久页（做成路由）**：在对应 dashboard 加路由组件后，走下面的整体部署流程（Cecelia rebuild / ZenithJoy CI 部署）。这才是"真正放进 dashboard"。

### SW 还在打回主页？两个治本手段

如果用户已经在用 dashboard 同源访问、绕不开旧 SW，给他这段**浏览器 console 一键注销 SW** 的脚本（比口头教他点 DevTools 快）：

```js
// 贴进浏览器 console 执行，然后硬刷新
navigator.serviceWorker.getRegistrations().then(rs => rs.forEach(r => r.unregister()))
```

要从**服务端根上**防"回主页"，给 nginx 的 `index.html` 和 `sw.js` 关缓存（新版 SW/壳能立刻接管，不会被旧副本顶着）：

```nginx
location = /index.html { add_header Cache-Control "no-cache, no-store, must-revalidate"; }
location = /sw.js      { add_header Cache-Control "no-cache, no-store, must-revalidate"; }
```

> Vite 给 JS/CSS 资源自带 hash 文件名（`app.abc123.js`），所以只要 `index.html` 不被缓存，浏览器就会自动拉新资源——根因永远是 `index.html`/`sw.js` 被旧副本顶住。

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
