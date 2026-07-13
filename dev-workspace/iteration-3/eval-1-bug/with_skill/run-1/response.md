# /dev 执行报告 — 抖音文章发布 TypeError cookie bug

## 路径

**路径 A：Bug**

判断依据：用户描述"报错 TypeError: Cannot read properties of undefined (reading 'cookie')，从昨天开始就这样了，之前是好的" → 明确 Bug 路径。

---

## 执行的 curl 命令（Phase 2）

### curl 1：查询 Journeys

```bash
curl -s "localhost:5221/api/brain/journeys"
```

**返回摘要**：共 19 条 Journey，其中与本 bug 相关的是：
- `c019cdeb` 智能发布 Journey（maturity: skeleton, status: active）

### curl 2：查询 Issues

```bash
curl -s "localhost:5221/api/brain/issues?limit=20"
```

**返回摘要**：接口返回 `Cannot GET /api/brain/issues`（404，该端点不存在）。

### curl 3：历史决策匹配

```bash
curl -s -X POST "localhost:5221/api/brain/decisions/match" \
  -H "Content-Type: application/json" \
  -d "{\"prd\": \"抖音文章发布 cookie undefined TypeError\"}"
```

**返回摘要**：`{"matched":[],"missing":[]}` — 无历史相关决策。

### curl 4（路径 A 写 decision）

```bash
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d "{\"topic\":\"抖音文章 dryrun 脚本 cookie 格式不兼容\",\"decision\":\"在 publish-douyin-article-dryrun.cjs 补充 storageState 格式兼容解析（Array.isArray 判断），与真发版保持一致；同步检查 image/video dryrun 脚本\",\"reason\":\"v1.1.66 修了三个真发版脚本的 storageState cookie 格式支持，但遗漏了 dryrun 版，导致 DOUYIN_COOKIES 为 {cookies:[...]} 格式时 context.addCookies 收到对象而非数组，Playwright 内部访问 undefined.cookie 抛出 TypeError\",\"made_by\":\"user\",\"author\":\"user\",\"category\":\"bug-fix\"}"
```

**返回摘要**：
```json
{
  "success": true,
  "data": {
    "id": "bc358a35-1c9b-43e6-be12-cb2a5bc41780",
    "category": "bug-fix",
    "topic": "抖音文章 dryrun 脚本 cookie 格式不兼容",
    "status": "active"
  }
}
```

---

## PrepPRD 路径

```
/Users/administrator/perfect21/zenithjoy/sprints/06090938-douyin-article-dryrun-cookie-fix/prep-prd.md
```

---

## Decision 写入 Brain DB 的返回 ID

```
bc358a35-1c9b-43e6-be12-cb2a5bc41780
```

---

## 根因简述（代码层）

- **出错文件**：`services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs` 第 96 行
- **问题代码**：`const cookies = JSON.parse(cookiesJson);` — 直接当数组用，未处理 storageState 包装格式
- **触发原因**：commit `9e6b22a`（v1.1.66，2026-05-30）为三个真发版脚本加了 storageState 格式兼容（`Array.isArray` 判断），但 **dryrun 版遗漏**
- **错误链路**：`DOUYIN_COOKIES = {"cookies":[...]}` → JSON.parse → 对象 → `context.addCookies(对象)` → Playwright 内部遍历时 `undefined.cookie` → TypeError

---

## 下一步

下一步应调用 `superpowers:systematic-debugging`，按以下顺序执行：
1. commit-1：在 `__tests__/publish-douyin-article.test.cjs` 写 storageState 格式兼容性 failing test
2. commit-2：修复 `publish-douyin-article-dryrun.cjs` 第 96 行（+ 同步检查 image/video dryrun 脚本）
3. CI 全绿后走 engine-worktree → engine-ship → engine-pr-watchdog
