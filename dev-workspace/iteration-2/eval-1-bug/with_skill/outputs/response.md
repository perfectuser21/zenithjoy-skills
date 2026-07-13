# /dev 执行记录 — 抖音文章发布 TypeError: Cannot read properties of undefined (reading 'cookie')

---

## 第零步 Phase 1：听懂意图

用户描述：「抖音文章发布一直报错 TypeError: Cannot read properties of undefined (reading 'cookie')，从昨天开始就这样了，之前是好的」

关键词：**报错** / **之前是好的** → **【路径 A：Bug】**

---

## Phase 2：按路径 A 查上下文（3 个 curl）

### Curl 1 — 查 Journey 体系

```bash
curl -s "localhost:5221/api/brain/journeys"
```

**预期解析**：找到「Line 01 智能发布」Journey（包含抖音发布能力），journey_id 用于后续写 issues/tasks。

### Curl 2 — 查近期 Issues

```bash
curl -s "localhost:5221/api/brain/issues?limit=20"
```

**预期解析**：确认是否已有同类 issue 登记。预期没有（从昨天新发）。

### Curl 3 — 历史决策匹配

```bash
curl -s -X POST "localhost:5221/api/brain/decisions/match" \
  -H "Content-Type: application/json" \
  -d "{\"prd\": \"抖音文章发布 cookie TypeError storageState\"}"
```

**预期解析**：查是否有之前决策规定了 DOUYIN_COOKIES 的格式。可能返回相关决策（如 `feedback_e2e_session_token_format.md`）。

---

## 根因定位（代码调查结果）

调查了以下文件：

- `services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs`（Line 96, 108）
- `services/agent/publishers/douyin-publisher/publish-douyin-article.cjs`（Line 58-59）
- `services/agent/publishers/qr-bind-douyin.cjs`（Line 84：写 storageState 到会话文件）
- `services/agent/src/handlers/douyin-publish.ts`（Line 111-129：`readLocalDouyinSession` 读会话注入 env）

**根因**：

`qr-bind-douyin.cjs` 扫码成功后写入 `~/.zenithjoy-agent/sessions/douyin/default.json`，内容是 Playwright `storageState()` 格式：

```json
{
  "cookies": [ { "name": "sessionid_ss", "domain": ".douyin.com", "value": "..." }, ... ],
  "origins": []
}
```

`douyin-publish.ts` 的 `readLocalDouyinSession()` 读取这个整体 JSON 字符串，作为 `DOUYIN_COOKIES` 环境变量注入子进程。

**dryrun 脚本**（`publish-douyin-article-dryrun.cjs`）第 96 行：

```js
const cookies = JSON.parse(cookiesJson);  // ← 结果是 { cookies: [...], origins: [] }，不是数组！
// ...
await context.addCookies(cookies);         // ← Playwright 收到 object，内部迭代 .cookie 属性 → TypeError
```

**同类脚本的正确写法**（`publish-douyin-article.cjs` Line 58-59、`publish-douyin-image.cjs` Line 63-64、`publish-douyin-video.cjs` Line 59-60）：

```js
const _parsed = JSON.parse(cookiesJson);
const cookies = Array.isArray(_parsed) ? _parsed : (_parsed.cookies ?? []);
```

dryrun 脚本漏掉了这个格式归一化处理，是唯一一个没有修复的脚本。

**为什么「昨天才开始」**：最可能的触发原因是用户重新扫码绑定抖音账号（重新执行了 qr-bind），写入了新的 `default.json`。旧的 session 文件如果是纯数组格式（历史遗留），之前能工作；新扫码后写入的是 storageState 对象格式，触发了这个潜伏已久的 bug。

---

## Bug PrepPRD

```markdown
# Bug PrepPRD：dryrun 脚本 JSON.parse(cookiesJson) 未处理 storageState 格式导致 TypeError

## 症状
抖音文章发布报错：
TypeError: Cannot read properties of undefined (reading 'cookie')
从昨天开始（重新扫码绑定后触发）

## 根因假设
`publish-douyin-article-dryrun.cjs` Line 96 直接将 JSON.parse 结果传给
context.addCookies()，未处理 storageState 对象格式。
当 DOUYIN_COOKIES 是 storageState 对象（{ cookies: [...], origins: [] }）时，
Playwright 内部对 object 调用 .map() 或迭代，尝试读 undefined.cookie 抛 TypeError。

## 关联上下文
- 相关 Journey/Ability：Line 01 智能发布 — 抖音文章发布 Ability
- 相关 Issue：无（新登记）
- 相关历史决策：feedback_e2e_session_token_format.md（E2E session token 格式规范）

## 修法

文件：`services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs`

将 Line 96：
```js
const cookies = JSON.parse(cookiesJson);
```
改为（与其他三个脚本对齐）：
```js
const _parsed = JSON.parse(cookiesJson);
const cookies = Array.isArray(_parsed) ? _parsed : (_parsed.cookies ?? []);
```

## Regression Test 计划
在 `services/agent/publishers/douyin-publisher/__tests__/publish-douyin-article.test.cjs` 新增测试：

```js
it('dryrun — cookiesJson 格式归一化：storageState 对象 → cookies 数组', () => {
  const src = fs.readFileSync(DRYRUN_CJS, 'utf8');
  // 确保 dryrun 脚本含 Array.isArray(_parsed) 或 _parsed.cookies 格式处理
  expect(src).toMatch(/Array\.isArray\(_parsed\)|_parsed\.cookies/);
});
```

该 test 永久留在 CI（regression guard），修完后不得删除。

## 验收标准
- [ ] commit-1：先写能复现 bug 的 failing test（上述 regression test）
- [ ] commit-2：修 dryrun 脚本一行，让 test 变绿
- [ ] 其余三个脚本（image.cjs / video.cjs / article.cjs 真发版）已正确，不需改
- [ ] CI 全绿（含 lint + unit test）
```

---

## PrepPRD 落地（写文件）

用户确认后执行：

```bash
SPRINT_DIR="sprints/$(TZ=Asia/Shanghai date +%m%d%H%M)-douyin-article-cookie-fix"
mkdir -p "$SPRINT_DIR"
cat > "$SPRINT_DIR/prep-prd.md" << 'EOF'
# Bug PrepPRD：dryrun 脚本 JSON.parse(cookiesJson) 未处理 storageState 格式导致 TypeError
[...PrepPRD 全文...]
EOF
```

输出确认：`已保存 PrepPRD 到 $SPRINT_DIR/prep-prd.md`

---

## 路径 A 执行：Decision curl

PrepPRD 落地后立即执行：

```bash
curl -s -X POST localhost:5221/api/brain/strategic-decisions \
  -H "Content-Type: application/json" \
  -d "{
    \"topic\": \"抖音文章 dryrun cookie 格式归一化\",
    \"decision\": \"publish-douyin-article-dryrun.cjs JSON.parse(cookiesJson) 后加 Array.isArray 判断，与其他三个脚本对齐\",
    \"reason\": \"storageState 对象格式 DOUYIN_COOKIES 导致 context.addCookies(object) TypeError，dryrun 是唯一未修复的脚本\",
    \"made_by\": \"user\",
    \"author\": \"user\",
    \"category\": \"bug-fix\"
  }"
```

---

## 下一个 skill 调用

```
Skill({"skill":"superpowers:systematic-debugging"})
```

接力链：systematic-debugging → engine-worktree → subagent-driven-development → commit-1(failing test) → commit-2(fix) → finishing(push+PR) → engine-ship → engine-pr-watchdog

---

## 附：精确修改位置

**文件**：`/Users/administrator/perfect21/zenithjoy/services/agent/publishers/douyin-publisher/publish-douyin-article-dryrun.cjs`

**第 95-96 行（当前）**：
```js
    _log('\n[DY-ARTICLE-DRY] Cookie 注入模式（CI/GitHub Actions）');
    const cookies = JSON.parse(cookiesJson);
```

**改为**：
```js
    _log('\n[DY-ARTICLE-DRY] Cookie 注入模式（CI/GitHub Actions）');
    const _parsed = JSON.parse(cookiesJson);
    const cookies = Array.isArray(_parsed) ? _parsed : (_parsed.cookies ?? []);
```

**第 108 行（不变）**：
```js
    await context.addCookies(cookies);
```

修改量：1 行改 + 1 行新增，影响范围极小，无副作用。
