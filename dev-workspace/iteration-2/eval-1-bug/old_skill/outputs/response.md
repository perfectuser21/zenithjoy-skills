# /dev 技能执行记录

## Phase 1：意图识别

用户描述：「抖音文章发布一直报错 TypeError: Cannot read properties of undefined (reading 'cookie')，从昨天开始就这样了，之前是好的」

关键词：报错、TypeError、昨天开始。

**判定：【路径 A：Bug】**

---

## Phase 2：上下文查询（路径 A — 3 个 curl）

### 执行的 curl 命令

```bash
# 1. 查所有 Journey，定位抖音文章发布属于哪条线
curl -s "localhost:5221/api/brain/journeys"

# 2. 查最近 20 个 Issue，看有没有已登记的同类 bug
curl -s "localhost:5221/api/brain/issues?limit=20"

# 3. 历史决策匹配，看有没有 cookie / storageState 相关决策
curl -s -X POST "localhost:5221/api/brain/decisions/match" \
  -H "Content-Type: application/json" \
  -d "{\"prd\": \"抖音 cookie storageState publish article TypeError\"}"
```

### 上下文分析（基于实际代码库探查）

**通过代码库直接分析，找到了确定性根因：**

1. **出错脚本**：`services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs`（line 96）

2. **根因**：2026-05-30 的 PR #581（commit `9e6b22a`）修复了 `storageState` 格式兼容问题，但**只改了 `publish-douyin-article.cjs`（真发版），漏改了 `publish-douyin-article-dryrun.cjs`（dryrun 版）**。

   - 修复后的真发版（正确）：
     ```js
     const _parsed = JSON.parse(cookiesJson);
     const cookies = Array.isArray(_parsed) ? _parsed : (_parsed.cookies ?? []);
     ```
   - 未修复的 dryrun 版（错误）：
     ```js
     const cookies = JSON.parse(cookiesJson);   // line 96，直接用对象
     ...
     await context.addCookies(cookies);          // line 108，期望数组，收到 storageState 对象
     ```

3. **为什么「昨天开始」**：session 格式发生了变化（或 CI 切换到了用 storageState 格式存储的 session），触发了这个已存在的兼容 bug。`qr-bind-douyin.ts` 的 `requireLogin` 调用 `ctx.storageState()` 存入 `~/.zenithjoy-agent/sessions/douyin/default.json`，格式是 `{cookies:[...], origins:[...]}` 对象，不是纯数组。当 `DOUYIN_COOKIES` 设置为这个值后，dryrun 脚本解析后直接传给 `addCookies`，Playwright 内部遍历时读 `undefined.cookie` 崩溃。

4. **影响范围**：只影响 dryrun 模式（默认模式）。真发模式（`ZENITHJOY_AGENT_REAL_PUBLISH=1`）的同名脚本已在 PR #581 中修复。

---

## PrepPRD

```markdown
# Bug PrepPRD：抖音文章 dryrun 脚本不支持 storageState 格式 DOUYIN_COOKIES

## 症状
调用抖音文章发布（dryrun 模式）时报错：
`TypeError: Cannot read properties of undefined (reading 'cookie')`
昨天之前正常，昨天开始持续失败。

## 根因假设
`publish-douyin-article-dryrun.cjs` line 96 用 `JSON.parse(cookiesJson)` 直接解析 DOUYIN_COOKIES，
未判断结果是纯数组还是 Playwright `storageState` 对象（`{cookies:[...], origins:[...]}`）。
Playwright `context.addCookies()` 期望数组，收到对象后内部遍历时读 `undefined.cookie` 崩溃。

PR #581（2026-05-30，commit 9e6b22a）已在真发版 `publish-douyin-article.cjs` 加了兼容判断，
但漏掉了 dryrun 版，导致一半路径仍有问题。

## 关联上下文
- 相关 Journey/Step：Line 01 智能发布 — Path 1 Step 6（dryrun 发布）
- 相关 Issue：需新建（commit 9e6b22a 的遗漏）
- 相关历史决策：PR #581 决策"三个 publisher 同时支持纯数组和 storageState 两种格式"——
  这条决策的执行结果不完整，dryrun 版漏掉了

## 修法
**只改一行**，在 `publish-douyin-article-dryrun.cjs` line 96 套用与真发版相同的兼容逻辑：

```diff
- const cookies = JSON.parse(cookiesJson);
+ const _parsed = JSON.parse(cookiesJson);
+ const cookies = Array.isArray(_parsed) ? _parsed : (_parsed.cookies ?? []);
```

文件：`services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs`

## Regression Test 计划
在 `services/agent/publishers/douyin-publisher/__tests__/publish-douyin-article.test.cjs` 中新增：
- 用例 1：`DOUYIN_COOKIES` 为纯数组格式 `[{name,value,...}]` → `addCookies` 收到数组（正确）
- 用例 2：`DOUYIN_COOKIES` 为 storageState 格式 `{cookies:[...],origins:[...]}` → `addCookies` 收到 `.cookies` 数组（修复后正确，修复前崩溃）

两个用例都 mock Playwright context，不需要真实浏览器。

## 验收标准
- [ ] failing test 先 commit（commit-1）：新增两个用例，第二个用例在修复前 FAIL
- [ ] 修复代码让 test 变绿（commit-2）：改 dryrun.cjs line 96-97
- [ ] CI 全绿（douyin-article-e2e.yml 通过）
```

---

## Decision curl（PrepPRD 确认后执行）

```bash
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d "{
    \"topic\": \"抖音文章 dryrun cookie 格式兼容 bug\",
    \"decision\": \"修复 publish-douyin-article-dryrun.cjs：addCookies 入参改为同真发版的 storageState 兼容逻辑（Array.isArray 判断，取 _parsed.cookies ?? []）\",
    \"reason\": \"PR #581 修真发版漏掉 dryrun 版，导致 storageState 格式 DOUYIN_COOKIES 注入时 Playwright addCookies 收到对象而非数组，内部读 undefined.cookie 崩溃\",
    \"made_by\": \"user\",
    \"author\": \"user\",
    \"category\": \"bug-fix\"
  }"
```

---

## 下一步调用

PrepPRD 落地后，下一 tool call：

```
Skill({"skill":"superpowers:systematic-debugging"})
```

接力链：systematic-debugging → engine-worktree → subagent-driven-development → finishing（push + PR）→ engine-ship → engine-pr-watchdog

---

## 附：PrepPRD 落地命令

```bash
SPRINT_DIR="sprints/$(TZ=Asia/Shanghai date +%m%d%H%M)-douyin-article-dryrun-cookie-fix"
mkdir -p "$SPRINT_DIR"
cat > "$SPRINT_DIR/prep-prd.md" << 'EOF'
# Bug PrepPRD：抖音文章 dryrun 脚本不支持 storageState 格式 DOUYIN_COOKIES
...（PrepPRD 全文）...
EOF
echo "已保存 PrepPRD 到 $SPRINT_DIR/prep-prd.md"
```

---

## 技能执行摘要

| 项 | 值 |
|---|---|
| 识别路径 | 路径 A（Bug） |
| 出错文件 | `services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs` |
| 出错位置 | line 96 `const cookies = JSON.parse(cookiesJson)` |
| 根因 | PR #581 storageState 兼容修复漏掉 dryrun 版 |
| 修复范围 | 1 行（与真发版对齐） |
| Regression Test | dryrun 脚本 cookie 格式解析单测 × 2 |
| 下一 skill | `superpowers:systematic-debugging` |
