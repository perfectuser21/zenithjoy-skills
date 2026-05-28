# 调查报告：抖音文章发布 TypeError: Cannot read properties of undefined (reading 'cookie')

## TL;DR

这个错误有**两个根本原因**，都需要处理：

1. **Windows 机器上的 agent 版本是 v1.0.0，而 repo 已经是 v1.1.28**，agent 根本没有部署最新代码，文章发布功能压根没有运行到新代码路径。

2. **GitHub Actions CI 里的 `DOUYIN_COOKIES` secret 已经过期**，导致注入 cookie 后页面仍然显示登录状态，脚本在检测到"扫码登录"内容时提前 `emitFailure`。

---

## 调查过程

### 错误来源定位

搜索了整个 repo 和 Windows 机器上安装的 agent，没有找到用户代码里直接访问 `undefined.cookie` 的地方。这个错误是 JavaScript 运行时在执行类似 `something.cookie` 时、`something` 是 `undefined` 时自动生成的，说明来自某个间接路径。

### 实际 CI 失败记录

查看了三次最近的 GitHub Actions `douyin-article-e2e` workflow 失败记录：

- **2026-05-26（最新）**：`{"ok":false,"error":"检测到登录页面内容"}` — cookie 注入后，抖音仍然认为未登录。
- **2026-05-25**：`{"ok":false,"error":"抖音未登录（检测到登录页面内容）"}` — 同一原因。
- **2026-05-24（最早）**：`locator.setInputFiles: Timeout 30000ms exceeded` — 旧版 dryrun 脚本没找到 file input。

**没有一次 CI 失败是 `TypeError: Cannot read properties of undefined (reading 'cookie')`**。

### Windows Agent 版本不匹配

```
Windows 机器（xian-rog）安装版本: v1.0.0
Repo 当前版本: v1.1.28
```

Windows 机器上 `dist/handlers/douyin-publish.js` 的 `SUPPORTED_DOUYIN_TYPES` 只包含 `video` 和 `image`，**明确写了 "article 暂未实现"**。当中台下发 `type=article` 的任务时，会直接抛出：

```
[type-route] no script for type article on platform douyin (supported: video/image; article 暂未实现)
```

这个错误被 `fail()` 捕获并返回失败结果，不是 TypeError。

### 用户报告错误的可能来源

基于调查，`TypeError: Cannot read properties of undefined (reading 'cookie')` 最可能来自以下场景之一：

**场景 A（最可能）**：用户在本地手动运行了旧版的 `publish-douyin-article.js`（位于 `services/content-pipeline/scripts/publishers/douyin-publisher/`），该脚本连接 CDP 后：

```js
const browser = await chromium.connectOverCDP('http://localhost:19222');
const context = browser.contexts()[0];  // 如果 Chrome 没开，这里返回 undefined
const page = context.pages()[0];        // <- 在 undefined 上调用 .pages() 触发
```

如果 Chrome debug 模式没有运行，或者 CDP 连接虽然成功但 contexts 列表为空，`context` 就是 `undefined`，之后调用 `context.pages()` 就会报 `Cannot read properties of undefined`。

但这里读的是 `.pages` 不是 `.cookie`。

**场景 B**：Playwright 在处理网络请求时，内部调用 `_updateRequestCookieHeader`，如果 storageState 或 cookies 数组里某个 cookie 对象格式异常（比如 `domain` 字段缺失），在 `new Cookie(c).matches(url)` 调用时，`_raw.domain` 是 undefined，调用 `domainMatches` 时 `domain.startsWith` 就会报错。但这个错误信息应该是 `Cannot read properties of undefined (reading 'startsWith')` 不是 `'cookie'`。

**场景 C（实际最可能触发这个精确错误的路径）**：在 content-pipeline 的某个旧 Python 或 JS 脚本里，获取了 HTTP response 对象然后访问 `response.cookie`，而 `response` 在某些错误路径下返回了 `undefined`。

---

## 当前状态确认

通过 CI 日志确认，文章发布功能**昨天开始一直在失败**的真正原因是：

**DOUYIN_COOKIES GitHub Secret 已经过期**

具体证据：
- CI 运行日志显示 "已注入 46 个 cookies"（说明 secret 存在且格式正确）
- 但随后检测到 "扫码登录" 页面内容，说明这些 cookies 已经失效（抖音 session 过期）

---

## 需要做的事

### 立即修复（恢复功能）

**重新刷新 DOUYIN_COOKIES Secret**：

1. 在 xian-rog 的 Chrome 里重新登录抖音创作者后台
2. 导出新的 cookies（用 EditThisCookie 或 Cookie-Editor 插件，Playwright 格式 JSON）
3. 更新 GitHub Secret：
   ```bash
   gh secret set DOUYIN_COOKIES < douyin-cookies.json
   ```

### 同步部署 Agent（解决 v1.0.0 vs v1.1.28 的版本落差）

1. 重新构建 agent bundle
2. 部署到 xian-rog

### 关于 TypeError 本身

需要用户提供更多信息：
- 错误出现在哪里？是 CI 还是本地运行？是 agent 日志还是手动执行脚本？
- 完整的 stack trace（`at ...` 那几行）

当前 CI 失败不是 TypeError，是 cookie 过期。如果 TypeError 是本地重现的，大概率是 Chrome 没有开 debug 模式（`--remote-debugging-port=19222`）。

---

## 相关文件

- `/services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs` — 主要的 dryrun 脚本（repo 最新版本，324 行）
- `/services/agent/publishers/douyin-publisher/publish-douyin-article.cjs` — 真发版
- `/.github/workflows/douyin-article-e2e.yml` — CI workflow
- Windows: `C:\Users\asus\zenithjoy-agent\publishers\douyin-publisher\publish-douyin-article-dryrun.cjs` — 旧版（281 行），已过时

---

## 结论

"从昨天开始就这样了，之前是好的" 对应了 DOUYIN_COOKIES 过期这个根因。抖音的 session cookie 有效期通常是 30 天，昨天过期了。用户报告的 TypeError 可能是在本地调试时遇到的，需要 stack trace 才能精确定位，但当前 CI 的修复路径很清晰：**刷新 DOUYIN_COOKIES Secret**。
