---
name: deploy
description: 部署指南——ZenithJoy + Cecelia 统一部署模型（push main→CI 自动 staging→smoke test→人工手点 promote 生产）。AI 只部署到 staging，生产必须人工手点放行。触发场景：部署代码、发布到生产、promote 上线、staging 验证。
---

# 部署指南（ZenithJoy + Cecelia 统一模型）

## 核心模型（两个 repo 完全一致）

```
push main → CI 自动 staging → smoke test ✅
                ↓
        人工打开 staging 验证
                ↓
        GitHub Actions 手点 promote → 生产
```

**死规矩：AI 只部署到 staging，生产必须人工手点放行。**

---

## ZenithJoy Dashboard

**Staging（自动）**
- 触发：push main 命中 `apps/dashboard/**`
- Workflow：`deploy-dashboard-staging.yml`
- URL：https://staging-autopilot.zenjoymedia.media
- Smoke：`.github/workflows/scripts/smoke/staging-smoke.sh`（HTML 内容校验）

**生产（人工放行）**
- 入口：GitHub Actions → `promote-dashboard-prod.yml` → workflow_dispatch
- 确认：confirm 输入框填 `PROMOTE`
- URL：https://autopilot.zenjoymedia.media

**应急手动部署（绕过 CI，慎用）**
```bash
cd ~/perfect21/zenithjoy && git pull origin main && bash deploy.sh hk
```
含：git 安全三检（未提交/未跟踪/未 push）+ build + rsync + 备份 + 公网 smoke

---

## Cecelia Dashboard

**Staging（自动）**
- 触发：push main
- Workflow：`auto-staging-deploy.yml`
- URL：http://perfect21:5222
- Smoke：`scripts/auto-staging-smoke.sh`

**生产（人工放行）**
- 入口：GitHub Actions → `promote-dashboard-prod.yml` → workflow_dispatch
- 确认：confirm 输入框填 `PROMOTE`
- URL：http://perfect21:5211

**应急手动部署（绕过 CI，慎用）**
```bash
bash scripts/promote-dashboard.sh
```

---

## Cecelia Brain / API

**自动部署**
- 触发：push main 命中 `packages/brain/**`
- Workflow：`brain-ci-deploy.yml`
- 无手动 promote（Brain 改动直接上生产）

---

## Cecelia Workflows（AI Gateway + N8N）

```bash
bash packages/workflows/deploy/deploy.sh hk
```

---

## 502 / 页面空白排查

**ZenithJoy 502：**
```bash
ssh hk-vps "docker ps | grep autopilot"
ssh hk-vps "curl -s -o /dev/null -w '%{http_code}' http://localhost/"
# 502 但容器 200 → Cloudflare Tunnel ingress 问题
# tunnel 必须写 http://172.17.0.1:80，不能写 localhost:80
```

**Cecelia PWA 显示旧版（SW 缓存）：**
```js
// 浏览器 console 执行
navigator.serviceWorker.getRegistrations().then(rs => rs.forEach(r => r.unregister()))
```

---

## 何时用应急手动 vs 正常 CI

| 场景 | 用法 |
|------|------|
| 日常改代码 | PR merge → CI 自动 staging → 手点 promote |
| CI 挂了但必须立刻上线 | 应急手动（`bash deploy.sh hk`） |
| 只改配置/nginx | 应急手动更快 |
| 新功能/重要改动 | 必须走 CI，不走应急 |
