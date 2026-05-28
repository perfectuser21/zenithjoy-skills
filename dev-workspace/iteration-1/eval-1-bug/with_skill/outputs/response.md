# /dev Eval 执行记录 — Bug 路径

## 第零步：查 Brain DB

Brain API（localhost:5221）**可用**。查询结果摘要：

- 当前活跃 tasks：以 sprint/harness 类型为主，无直接关联本 bug 的活跃任务
- 最近相关 commit（来自 git log）：
  - `d731073` fix(agent): article dryrun v2 — 修复抖音文章编辑器真实导航流与封面上传 (#451)
  - `57bc9fb` fix(agent): article dryrun — 登录检测 + 编辑器导航 + profile 模式 (#448)
  - `e75c6b1` feat(e2e): 抖音文章 dryrun — cookie 注入模式 + GHA windows runner 截图验证 (#447)
- GitHub Actions 最近 3 次 douyin-article-e2e 运行：全部 **failure**（2026-05-24 起）

---

## 类型判断

**类型：Bug（P0）**

判断依据：
- 功能之前正常（用户明确说"之前是好的，昨天开始出问题"）
- 有具体报错信息：`TypeError: Cannot read properties of undefined (reading 'cookie')`
- GitHub Actions 日志确认：2026-05-24 起所有 dryrun 运行失败
- 报错点在 Playwright `context.addCookies()` 调用链内

---

## Bug PrepPRD

### 标题
fix(agent): 抖音文章 dryrun — DOUYIN_COOKIES 格式不匹配导致 addCookies TypeError

### 背景 & 现象

2026-05-25 起，抖音文章发布（dryrun 模式）在 GitHub Actions 上持续失败，报错：

```
TypeError: Cannot read properties of undefined (reading 'cookie')
```

GitHub Actions 日志（run #26381014751，2026-05-25）：
```
[DY-ARTICLE-DRY] Cookie 注入模式（CI/GitHub Actions）
[DY-ARTICLE-DRY] 已注入 46 个 cookies    ← 注入本身未抛错
{"ok":false,"error":"检测到登录页面内容"}  ← 实际失败点
```

注：用户描述的 TypeError 可能在本地调用栈中出现，GHA 上被 `emitFailure()` 捕获并转为 JSON 输出。

### 根本原因分析

**根因：DOUYIN_COOKIES GitHub Secret 的 JSON 格式与 `addCookies()` 期望格式不匹配。**

**证据链：**

1. `qr-bind-douyin.ts`（绑定扫码时保存 cookies）：
   ```js
   const storageState = await ctx.storageState();
   fs.writeFileSync(sessionPath, JSON.stringify(storageState, null, 2));
   ```
   `storageState()` 返回格式：`{ cookies: [...], origins: [...] }`

2. `publish-douyin-article-dryrun.cjs`（使用 cookies）：
   ```js
   const cookies = JSON.parse(cookiesJson);   // 直接 parse，不做格式检查
   await context.addCookies(cookies);          // 期望 CookieEntry[]，收到 storageState 对象
   ```

3. Playwright `addCookies()` 内部对每个元素访问 `.cookie` 字段。当传入的是 storageState 对象（非数组）或数组元素格式不对时，抛出：
   ```
   TypeError: Cannot read properties of undefined (reading 'cookie')
   ```

**次要原因（已注入但仍显示未登录）：**

即使格式正确，`DOUYIN_COOKIES` 中的 cookie 已过期（session cookie 生命周期通常 7~30 天），导致注入后抖音仍跳登录页。最后一次成功时间推测在 2026-05-24 之前，与用户描述吻合。

### 影响范围

| 组件 | 影响 |
|------|------|
| `services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs` | 直接受影响，cookie 注入逻辑 |
| GitHub Actions `douyin-article-e2e.yml` | E2E 自检每日定时跑，全部失败 |
| 生产发布链路（ZENITHJOY_AGENT_REAL_PUBLISH=1）| 同样受影响，真发脚本 `publish-douyin-article.cjs` 未使用 cookie 注入模式，但底层 CDP 连接依赖本地已登录 Chrome，与 CI 无关 |

### 修复方案

**Fix 1（主修复）：格式兼容 — 支持 storageState 和平铺数组两种格式**

在 `publish-douyin-article-dryrun.cjs` 的 `cookiesJson` parse 后添加格式检测：

```js
let parsedCookies = JSON.parse(cookiesJson);
// 兼容 Playwright storageState 格式 {cookies: [...], origins: [...]}
if (parsedCookies && !Array.isArray(parsedCookies) && Array.isArray(parsedCookies.cookies)) {
  parsedCookies = parsedCookies.cookies;
}
await context.addCookies(parsedCookies);
```

**Fix 2（配套）：Cookie 过期检测 & 刷新流程**

在注入前检测 cookie 的 `expires` 字段，过期则打告警日志并触发 Bark 通知提示重新扫码绑定。

**Fix 3（长期）：DOUYIN_COOKIES Secret 刷新 SOP**

补充运维文档：扫码绑定成功后，CI Secret 须同步更新（当前无自动化）。

### 复现步骤

```bash
# 1. 构造一个 storageState 格式的 cookies 文件
export DOUYIN_COOKIES='{"cookies":[{"name":"s_v_web_id","value":"xxx","domain":".douyin.com","path":"/"}],"origins":[]}'

# 2. 构造 queue.json（title/content/cover 随意）
echo '{"title":"test","content":"test","cover":"/tmp/test.png"}' > /tmp/queue.json
touch /tmp/test.png

# 3. 运行 dryrun 脚本
cd services/agent && node publishers/douyin-publisher/publish-douyin-article-dryrun.cjs /tmp/queue.json
# 预期：抛 TypeError: Cannot read properties of undefined (reading 'cookie')
```

### 验收标准

1. `DOUYIN_COOKIES` 为 storageState 格式时，`addCookies()` 不再抛 TypeError
2. `DOUYIN_COOKIES` 为平铺数组格式时，行为不变
3. Cookie 过期时，输出清晰的错误信息而非 TypeError
4. 需要新增 unit test：`__tests__/publish-douyin-article.test.cjs` 覆盖两种格式

### 关联文件

- `services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs` — 主修复点（第 96-110 行）
- `services/agent/publishers/douyin-publisher/__tests__/publish-douyin-article.test.cjs` — 新增格式兼容测试
- `services/agent/src/handlers/qr-bind-douyin.ts` — 保存 storageState 的上游代码（无需修改，但需理解格式）
- `.github/workflows/douyin-article-e2e.yml` — CI 定时任务，修复后应恢复通过

---

## 后续动作

### Decision 内容

```json
{
  "type": "bug_fix",
  "title": "fix(agent): DOUYIN_COOKIES storageState 格式兼容",
  "context": "抖音文章 dryrun 脚本 addCookies() 期望 CookieEntry[] 但收到 storageState 对象，2026-05-25 起所有 E2E 失败",
  "resolution": "parse DOUYIN_COOKIES 后检测格式，自动提取 .cookies 数组；同时修复 cookie 过期检测",
  "branch": "cp-YYYYMMDD-fix-douyin-article-cookie-format"
}
```

### 路由

→ **`systematic-debugging` skill**

执行步骤：
1. 先写 failing regression test（`__tests__/publish-douyin-article.test.cjs` 新增用例：传 storageState 格式 → 不应抛 TypeError）
2. 修复 `publish-douyin-article-dryrun.cjs` 第 94-110 行的 cookie parse 逻辑
3. 同步修复 `publish-douyin-article.cjs`（真发版，同样逻辑）
4. 本地 `node services/agent/publishers/douyin-publisher/__tests__/publish-douyin-article.test.cjs` 验证
5. 处理 cookie 过期问题（另一个独立子问题：需刷新 GHA Secret DOUYIN_COOKIES）
6. PR → main，等 CI douyin-article-e2e 绿灯
