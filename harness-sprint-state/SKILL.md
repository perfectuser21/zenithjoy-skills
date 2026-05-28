---
id: harness-sprint-state-skill
description: |
  Harness Sprint State Sync — Harness pipeline 完成后先写本地 Brain DB，再同步系统现状到 8 个 Notion DB + 本地 state 文件。
  由 harness-evaluator Mode B PASS 后调用，也可独立手动触发。
  8 个 DB：AI Journey / AI Feature / Skill Registry / API Registry / DB Schema Registry / Tests Registry / AI Notes（Decisions）/ AI Steps / Journey-Step 连接表。
  本地写入：sprint-states/<journey_id>/state.md（累积更新）+ sprints/<id>/sprint-state-delta.md（本次归档）。
  Brain 8 张独立表：journeys / journey_steps / journey_step_links / journey_features / skill_registry / api_registry / db_schema_registry / test_registry。
version: 1.2.0
created: 2026-05-20
updated: 2026-05-26
changelog:
  - 1.0.0: 初版 — 从 harness-evaluator Step B-4 拆出，成为独立 skill；支持 6 个 Notion DB 同步 + 本地 state 文件写入 + git commit
  - 1.1.0: 新增 Step 0 写本地 Brain DB（sprint_states / journey_steps）；新增 Step 5b/5c 同步 AI Steps + Journey-Step 连接表；共 8 个 Notion DB
  - 1.2.0: 8 张表统一架构 — skill_registry 独立表（从 system_registry type=skill 迁出）+ journey_step_links 连接表；修正端点路径（journey_steps 下划线）；新增 GET /api/brain/skills、GET /api/brain/journey_step_links 端点说明
---

> **语言规则: 所有输出必须使用简体中文。严禁日语、韩语或其他语言。**
> **执行规则: 严格按照下面列出的步骤执行。**

# /harness-sprint-state — Sprint State Sync

**角色**：Sprint 状态同步器  
**调用时机**：harness-evaluator Mode B PASS 后；或手动触发补同步

---

## 前置变量（由调用方注入，或手动指定）

| 变量 | 含义 | 来源 |
|------|------|------|
| `SPRINT_DIR` | Sprint 目录，如 `sprints/run-20260519-1400` | harness-evaluator 注入 |
| `SPRINT_ID` | Sprint ID，如 `sprint-0519` | harness-evaluator 注入 |
| `TASK_ID` | Brain task UUID | harness-evaluator 注入 |

`JOURNEY_ID` 和 `JOURNEY_NOTION_ID` 从 `$SPRINT_DIR/sprint-prd.md` 读取，不需额外注入。

---

## Brain 本地 DB — 8 张独立表（2026-05-26 架构）

| 表名 | 用途 | 主要 API 端点 |
|------|------|--------------|
| `journeys` | Journey 列表 | `GET /api/brain/journeys`, `GET /api/brain/journeys/:id` |
| `journey_steps` | Step 节点 | `GET/POST /api/brain/journey_steps` |
| `journey_step_links` | Journey-Step 连接（多对多） | `GET/POST /api/brain/journey_step_links` |
| `journey_features` | Feature 脚本 | `GET /api/brain/journeys/:id/features` |
| `skill_registry` | Skill 清单（独立表，不走 system_registry） | `GET/POST/PATCH /api/brain/skills` |
| `api_registry` | API 端点注册 | `GET /api/brain/registry?type=api` |
| `db_schema_registry` | DB 表结构 | `GET /api/brain/registry?type=db_schema` |
| `test_registry` | 测试清单 | `GET /api/brain/registry?type=test` |

**注意**：`/api/brain/registry?type=skill` 已改为路由到 `skill_registry` 表（返回 `notion_id` 字段）；直接写 skill 用 `POST /api/brain/skills`，不要再往 `system_registry` 写 type=skill 数据。

---

## Notion DB ID（固定，不需每次查）

```
NOTION_JOURNEY_DB       = 358c40c2-ba63-8148-bde7-e313d789931a   # 章节1 Walking Skeleton
NOTION_FEATURE_DB       = 358c40c2-ba63-81e3-96c5-d762b3d34dff   # 章节2 Features
NOTION_SKILL_DB         = 353c40c2-ba63-81bf-ae3e-f0e6fa3753d7   # Skill Registry
NOTION_API_DB           = 365c40c2-ba63-81a3-9060-fcef565e5291   # 章节3 APIs
NOTION_SCHEMA_DB        = 365c40c2-ba63-8181-9a57-ed760fd68ba3   # 章节4 DB Schema
NOTION_TESTS_DB         = 365c40c2-ba63-8164-8037-eb72e713809e   # 章节5 Tests
NOTION_NOTES_DB         = 185c40c2-ba63-828c-973f-81a9c4582cd6   # 章节6 Decisions
NOTION_STEPS_DB         = 369c40c2-ba63-812c-9f35-e7e43db25014   # AI Steps
NOTION_JOURNEY_STEP_DB  = 369c40c2-ba63-81e2-b95a-e5e3d0592676   # Journey-Step 连接表
```

---

## 执行流程

### Step 0: 写本地 Brain DB（先于 Notion，本地是 source of truth）

从 sprint-contract.md 提取 steps/features/apis/db/tests 数据，写入本地 postgres：

```javascript
// 连接本地 DB（通过 Brain API）
async function writeToBrainDB(journeyId, sprintId, steps, features, apis, tables, tests) {
  const BASE = process.env.BRAIN_API || 'http://localhost:5221';
  
  // 1. 写 sprint_states 快照
  await fetch(`${BASE}/api/brain/sprint-state`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      journey_id: journeyId,
      sprint_id: sprintId,
      snapshot: { steps, features, apis, db_schema: tables, tests }
    })
  });

  // 2. upsert journey_steps（每个 step 的状态）
  for (const step of steps) {
    await fetch(`${BASE}/api/brain/journey_steps`, {    // 注意：下划线，不是连字符
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        journey_id: journeyId,
        step_id: step.id,
        step_order: step.order,
        status: step.status,
        shared: step.shared || false
      })
    });
  }

  // 3. upsert skills（如果 sprint 产出新 Skill）
  for (const skill of skills || []) {
    await fetch(`${BASE}/api/brain/skills`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: skill.name,
        description: skill.description,
        location: skill.location,
        status: skill.status || 'active'
      })
    });
  }

  console.log('✅ Brain DB 写入完成:', journeyId, sprintId);
}
```

**注意**：
- `/api/brain/journey_steps`（下划线）— 实现于 migration 283 + journeys.js 路由（2026-05-26 上线）
- `/api/brain/skills` — skill_registry 独立表端点（GET/POST/PATCH），不要用 `/api/brain/registry?type=skill` 写入
- `/api/brain/sprint-state` — 需要 migration `20260523_000000_walking_skeleton_state.sql`，当前 sprint 可先 WARN 继续
- `system_registry WHERE type='skill'` 已废弃，171 条数据已迁移到 `skill_registry`

---

### Step 1: 准备凭据 + 读取输入文件

```bash
# 凭据
source ~/.credentials/notion.env 2>/dev/null || \
  node -e "
  const fs=require('fs'),{execFileSync}=require('child_process');
  const env={};
  fs.readFileSync(process.env.HOME+'/.credentials/1password.env','utf8')
    .split('\n').forEach(l=>{const m=l.match(/^([^=]+)=(.+)/);if(m)env[m[1]]=m[2];});
  const tok=execFileSync('op',['item','get','Notion','--vault','CS','--fields','credential','--reveal'],
    {env:{...process.env,...env}}).toString().trim().replace(/^\"|\"$/g,'');
  fs.writeFileSync(process.env.HOME+'/.credentials/notion.env','NOTION_API_KEY='+tok+'\n',{mode:0o600});
  console.log('凭据已同步');
  "
source ~/.credentials/notion.env

# 从 sprint-prd.md 读 journey_id + journey_notion_id
JOURNEY_ID=$(grep -m1 "^## journey_id:" "$SPRINT_DIR/sprint-prd.md" \
  | sed 's/## journey_id: //' | tr -d ' \r')
JOURNEY_NOTION_ID=$(grep -m1 "^## journey_notion_id:" "$SPRINT_DIR/sprint-prd.md" \
  | sed 's/## journey_notion_id: //' | tr -d ' \r')

if [ -z "$JOURNEY_ID" ]; then
  echo "❌ FATAL: sprint-prd.md 缺少 journey_id 字段，无法同步"
  exit 1
fi

echo "Journey ID: $JOURNEY_ID"
echo "Journey Notion ID: ${JOURNEY_NOTION_ID:-（未填，跳过 Journey/Feature Notion 回写）}"
echo "Sprint ID: $SPRINT_ID"
```

---

### Step 2: 解析数据源

```bash
SPRINT_PRD="$SPRINT_DIR/sprint-prd.md"
CONTRACT="$SPRINT_DIR/contract-draft.md"
STATE_DIR="$(pwd)/sprint-states/${JOURNEY_ID}"
STATE_FILE="${STATE_DIR}/state.md"
PREV_STATE=""
[ -f "$STATE_FILE" ] && PREV_STATE=$(cat "$STATE_FILE")

mkdir -p "$STATE_DIR"
```

**从文件中提取各章节数据**（Node.js 执行）：

```javascript
// 解析函数（后续步骤复用）
const fs = require('fs');
const prd      = fs.existsSync(process.env.SPRINT_PRD) ? fs.readFileSync(process.env.SPRINT_PRD, 'utf8') : '';
const contract = fs.existsSync(process.env.CONTRACT)   ? fs.readFileSync(process.env.CONTRACT, 'utf8')   : '';
const prev     = fs.existsSync(process.env.STATE_FILE) ? fs.readFileSync(process.env.STATE_FILE, 'utf8') : '';
const sprintId = process.env.SPRINT_ID || process.env.TASK_ID || 'sprint-unknown';
const today    = new Date().toISOString().split('T')[0];

// 提取 API 列表（从 contract [BEHAVIOR] 块）
const apis = [...contract.matchAll(/\[BEHAVIOR\][\s\S]*?Method:\s*(GET|POST|PUT|DELETE|PATCH)\s*\n\s*Endpoint:\s*(\S+)([\s\S]*?)(?=\[BEHAVIOR\]|\[ARTIFACT\]|$)/gi)]
  .map(m => ({
    method:   m[1].toUpperCase(),
    endpoint: m[2],
    request:  (m[3].match(/Request Body:\s*(.+)/)   || [])[1] || '{}',
    response: (m[3].match(/Expected Response:\s*(.+)/) || [])[1] || '200 {}',
  }));

// 提取 DB 表（从 contract/prd Table: 行）
const tables = [...(contract + '\n' + prd).matchAll(/Table:\s*(\w+)[\s\S]*?Columns?:\s*([^\n]+)/gi)]
  .map(m => ({ table: m[1].trim(), columns: m[2].trim() }));

// 提取 Tests（smoke 行 + Test: .test.ts 路径）
const tests = [];
const smokeMatch = prd.match(/Smoke:\s*(.+)/);
if (smokeMatch) tests.push({ type: 'smoke', path: smokeMatch[1].trim(), status: 'passing' });
[...contract.matchAll(/Test:\s*(?:manual:bash\s+)?(.+\.test\.[tj]sx?)/gi)]
  .forEach(m => tests.push({ type: 'unit', path: m[1].trim(), status: 'passing' }));
[...contract.matchAll(/Test:\s*(?:manual:bash\s+)?curl\s.+?(\/api\/\S+)/gi)]
  .forEach(m => tests.push({ type: 'integration', path: m[1].trim() + ' curl', status: 'passing' }));

// 提取 Features（从 prd ## Features 区块）
const features = [...prd.matchAll(/\|\s*([^|]{3,})\|\s*(\d[^|]*)\|\s*(thin|medium|thick|mature)\s*\|\s*(DONE|WIP|done|building|planned)\s*\|/gi)]
  .map(m => ({ name: m[1].trim(), step: m[2].trim(), thickness: m[3].trim(), status: m[4].toLowerCase() }));

console.log(JSON.stringify({ apis, tables, tests, features, sprintId, today }, null, 2));
```

---

### Step 3: 同步 Notion — 章节 3 API Registry

每个 API endpoint 查找 Notion API DB 是否已存在（按 Endpoint + Method 去重），存在则更新，不存在则新建：

```javascript
async function syncAPIs(apis, journeyId, sprintId) {
  const NOTION_KEY = process.env.NOTION_API_KEY;
  const API_DB = '365c40c2-ba63-81a3-9060-fcef565e5291';

  for (const api of apis) {
    const name = `${api.method} ${api.endpoint}`;

    // 查是否已存在
    const q = await notionQuery(API_DB, {
      filter: { property: 'Name', title: { equals: name } }
    });
    const existing = q.results?.[0];

    const props = {
      Name:        { title: [{ text: { content: name } }] },
      Method:      { select: { name: api.method } },
      Endpoint:    { rich_text: [{ text: { content: api.endpoint } }] },
      Request:     { rich_text: [{ text: { content: api.request } }] },
      Response:    { rich_text: [{ text: { content: api.response } }] },
      'Journey ID':{ rich_text: [{ text: { content: journeyId } }] },
      Status:      { select: { name: 'active' } },
      'Updated In':{ rich_text: [{ text: { content: sprintId } }] },
    };

    if (existing) {
      await notionPatch(existing.id, props);
      console.log('✅ API 更新:', name);
    } else {
      await notionCreate(API_DB, props);
      console.log('✅ API 新建:', name);
    }
  }
}
```

---

### Step 4: 同步 Notion — 章节 4 DB Schema Registry

```javascript
async function syncDBSchema(tables, journeyId, sprintId) {
  const SCHEMA_DB = '365c40c2-ba63-8181-9a57-ed760fd68ba3';

  for (const t of tables) {
    const q = await notionQuery(SCHEMA_DB, {
      filter: { property: 'Name', title: { equals: t.table } }
    });
    const existing = q.results?.[0];

    const props = {
      Name:        { title: [{ text: { content: t.table } }] },
      Columns:     { rich_text: [{ text: { content: t.columns } }] },
      'Journey ID':{ rich_text: [{ text: { content: journeyId } }] },
      Status:      { select: { name: 'active' } },
      'Updated In':{ rich_text: [{ text: { content: sprintId } }] },
    };

    if (existing) {
      await notionPatch(existing.id, props);
      console.log('✅ DB Schema 更新:', t.table);
    } else {
      await notionCreate(SCHEMA_DB, props);
      console.log('✅ DB Schema 新建:', t.table);
    }
  }
}
```

---

### Step 5: 同步 Notion — 章节 5 Tests Registry

```javascript
async function syncTests(tests, journeyId, sprintId) {
  const TESTS_DB = '365c40c2-ba63-8164-8037-eb72e713809e';

  for (const t of tests) {
    const q = await notionQuery(TESTS_DB, {
      filter: { property: 'Name', title: { equals: t.path } }
    });
    const existing = q.results?.[0];

    const props = {
      Name:        { title: [{ text: { content: t.path } }] },
      Type:        { select: { name: t.type } },
      Path:        { rich_text: [{ text: { content: t.path } }] },
      Status:      { select: { name: t.status } },
      'Journey ID':{ rich_text: [{ text: { content: journeyId } }] },
      'Updated In':{ rich_text: [{ text: { content: sprintId } }] },
    };

    if (existing) {
      await notionPatch(existing.id, props);
      console.log('✅ Test 更新:', t.path);
    } else {
      await notionCreate(TESTS_DB, props);
      console.log('✅ Test 新建:', t.path);
    }
  }
}
```

---

### Step 5b: 同步 Notion — AI Steps（更新状态）

```javascript
async function syncSteps(journeyId, steps) {
  // 查 Steps DB 里属于这个 Journey 的 step 记录
  const existing = await notionQuery(NOTION_STEPS_DB, {
    filter: { property: 'Journey', relation: { contains: journeyNotionId } }
  });
  
  for (const step of steps) {
    const match = existing.results?.find(p => 
      p.properties['Step ID']?.rich_text?.[0]?.plain_text === step.id
    );
    if (!match) continue;
    await notionPatch(match.id, {
      Maturity: { select: { name: step.status } }
    });
    console.log('✅ Step 状态更新:', step.id, '→', step.status);
  }
}
```

### Step 5c: 同步 Journey-Step 连接表（更新 Status）

```javascript
async function syncJourneyStepTable(journeyId, steps) {
  // 查 Journey-Step 连接表里属于这个 Journey 的记录
  const existing = await notionQuery(NOTION_JOURNEY_STEP_DB, {
    filter: { property: 'Journey', relation: { contains: journeyNotionId } }
  });
  
  for (const step of steps) {
    const match = existing.results?.find(p => {
      const name = p.properties['Name']?.title?.[0]?.plain_text || '';
      return name.includes(step.id);
    });
    if (!match) continue;
    await notionPatch(match.id, {
      Status: { select: { name: step.status } }
    });
    console.log('✅ Journey-Step 状态更新:', step.id, '→', step.status);
  }
}
```

---

### Step 6: 同步 Notion — 章节 2 Feature DB（需 CCAPI2026 权限）

```javascript
async function syncFeatures(features, journeyNotionId, sprintId) {
  if (!journeyNotionId) {
    console.log('⏭️  journey_notion_id 未填，跳过 Feature Notion 回写');
    return;
  }

  // 从 Journey 页面拿所有 Feature ID
  const journey = await notionGet('/pages/' + journeyNotionId);
  const featureIds = journey.properties?.Features?.relation?.map(f => f.id) || [];

  for (const fid of featureIds) {
    const f = await notionGet('/pages/' + fid);
    const name = f.properties?.Name?.title?.[0]?.plain_text || '';

    // 在本次 PRD features 里找对应条目
    const match = features.find(ft => ft.name === name || name.includes(ft.name.slice(0,10)));
    if (!match) continue;

    await notionPatch(fid, {
      Status:    { select: { name: match.status === 'done' ? 'done' : 'building' } },
      Thickness: { select: { name: match.thickness } },
    });
    console.log('✅ Feature 回写 Notion:', name, '→', match.thickness, match.status);
  }
}
```

---

### Step 7: 同步 Notion — 章节 1 Journey Maturity（需 CCAPI2026 权限）

```javascript
async function syncJourneyMaturity(journeyNotionId, features) {
  if (!journeyNotionId) return;

  const allDone = features.length > 0 && features.every(f => f.status === 'done');
  const journey = await notionGet('/pages/' + journeyNotionId);
  const currentMaturity = journey.properties?.Maturity?.select?.name || 'not_started';

  // 规则：所有 Feature thin+done → 至少 skeleton
  let newMaturity = currentMaturity;
  if (allDone && currentMaturity === 'not_started') newMaturity = 'skeleton';

  if (newMaturity !== currentMaturity) {
    await notionPatch(journeyNotionId, {
      Maturity: { select: { name: newMaturity } }
    });
    console.log('✅ Journey Maturity 更新:', currentMaturity, '→', newMaturity);
  } else {
    console.log('ℹ️  Journey Maturity 无变化:', currentMaturity);
  }
}
```

---

### Step 8: 写本地 sprint-states/<journey_id>/state.md

生成标准 6 章节 Markdown 并写入：

```javascript
function buildStateDoc(prd, contract, prev, sprintId, today, apis, tables, tests, features) {
  const journeyMeta = (prd.match(/Journey:\s*(.+)/) || [])[1] || '（见 sprint-prd.md）';

  // 合并 prev 中旧 step 行（不覆盖已有历史）
  const mergeRows = (prevContent, newRows, sprintId, headerCount) => {
    const thisKeys = new Set(newRows.map(r => r.split('|')[1]?.trim()));
    const prevRows = prevContent
      ? [...prevContent.matchAll(/\|([^|\n-][^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|/g)]
          .filter(m => !thisKeys.has(m[1].trim()) && !m[0].includes('---'))
          .map(m => `|${m[1]}|${m[2]}|${m[3]}|${m[4]}|`)
      : [];
    return [...prevRows, ...newRows].join('\n') || '| — | — | — | — |';
  };

  const sec1 = `## 1. Walking Skeleton
Journey: ${journeyMeta}

| Step | 描述 | 状态 | 更新于 |
|------|------|------|--------|
${mergeRows(prev, [], sprintId, 4)}

Smoke: ${(prd.match(/Smoke:\s*(.+)/) || prev?.match?.(/Smoke:\s*(.+)/) || [])[1] || '待更新'}`;

  const featureRows = features.map(f =>
    `| ${f.name} | ${f.step} | ${f.thickness} | ${f.status} | ${sprintId} |`);
  const sec2 = `## 2. Features

| Feature | Journey Step | Thickness | 状态 | 更新于 |
|---------|-------------|-----------|------|--------|
${mergeRows(prev, featureRows, sprintId, 5)}`;

  const apiRows = apis.map(a =>
    `| ${a.method} | ${a.endpoint} | ${a.request} | ${a.response} | ${sprintId} |`);
  const sec3 = `## 3. APIs

| Method | Endpoint | Request | Response | 更新于 |
|--------|----------|---------|----------|--------|
${mergeRows(prev, apiRows, sprintId, 5)}`;

  const schemaRows = tables.map(t =>
    `| ${t.table} | ${t.columns} | ${sprintId} |`);
  const sec4 = `## 4. Database

| Table | Columns | 更新于 |
|-------|---------|--------|
${mergeRows(prev, schemaRows, sprintId, 3)}`;

  const testRows = tests.map(t =>
    `| ${t.type} | ${t.path} | ✅ | ${sprintId} |`);
  const sec5 = `## 5. Tests

| Type | 路径 / 描述 | 状态 | 更新于 |
|------|------------|------|--------|
${mergeRows(prev, testRows, sprintId, 4)}`;

  const sec6 = `## 6. Decisions

| 决策 | 原因 | 更新于 |
|------|------|--------|
${prev ? (prev.match(/## 6\. Decisions[\s\S]*/) || [''])[0].split('\n').slice(3).join('\n') : '| — | — | — |'}`;

  return [
    `# Sprint State\n> Last updated: ${sprintId} | ${today}`,
    sec1, sec2, sec3, sec4, sec5, sec6
  ].join('\n\n');
}
```

---

### Step 9: git commit + push main

```bash
git add "sprint-states/${JOURNEY_ID}/state.md" \
        "${SPRINT_DIR}/sprint-state-delta.md" 2>/dev/null || true

git diff --cached --quiet && echo "无变更，跳过 commit" && exit 0

git commit -m "chore(sprint-state): ${SPRINT_ID} 更新 ${JOURNEY_ID} 系统现状快照"
git push origin main || (git pull --rebase origin main && git push origin main)
echo "✅ sprint-state.md 已 commit 推送 main"
```

---

### Step 10: 更新 Sprint State Dashboard 页面（Notion）

在 Harness 开发流水线 / Sprint State Dashboard 页面追加本次 Sprint 摘要：

```javascript
const DASHBOARD_ID = '365c40c2-ba63-813a-aaa0-f86db3fa6854';
await notionAppendBlock(DASHBOARD_ID, [
  { object:'block', type:'divider', divider:{} },
  { object:'block', type:'heading_3', heading_3:{ rich_text:[{type:'text',text:{content:`Sprint: ${sprintId} — ${journeyId}`}}] } },
  { object:'block', type:'paragraph', paragraph:{ rich_text:[{type:'text',text:{content:
    `APIs: ${apis.length} 个 | Tables: ${tables.length} 个 | Tests: ${tests.length} 个 | Features: ${features.length} 个`
  }}] } },
]);
console.log('✅ Dashboard 已更新');
```

---

## 通用 Notion 工具函数

```javascript
const NOTION_KEY = process.env.NOTION_API_KEY;

async function notionReq(method, path, body) {
  const r = await fetch('https://api.notion.com/v1' + path, {
    method,
    headers: { 'Authorization':'Bearer '+NOTION_KEY, 'Notion-Version':'2022-06-28', 'Content-Type':'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const d = await r.json();
  if (!r.ok) console.warn('Notion WARN', r.status, path, JSON.stringify(d).slice(0,120));
  return d;
}
const notionGet         = path  => notionReq('GET',   path);
const notionPatch       = (id, props) => notionReq('PATCH', '/pages/'+id, { properties: props });
const notionCreate      = (dbId, props) => notionReq('POST',  '/pages', { parent:{database_id:dbId}, properties:props });
const notionQuery       = (dbId, body)  => notionReq('POST',  '/databases/'+dbId+'/query', body);
const notionAppendBlock = (id, children)=> notionReq('PATCH', '/blocks/'+id+'/children', { children });
```

---

## 错误处理原则

- **任何单个 DB 写入失败** → WARN 继续，不中断整体同步
- **journey_notion_id 未填** → 跳过 Journey/Feature Notion 回写，仅写本地 state 文件
- **DB 权限不足（404）** → WARN 输出 DB 名称，提示在 Notion 手动 share CCAPI2026
- **git push 失败** → rebase 重试一次，仍失败则 WARN 输出文件路径供手动 commit

---

## 调用方：harness-evaluator 修改（Mode B PASS 后）

在 harness-evaluator Step B-3 PASS 判断后，**删除** Step B-4 的内嵌逻辑，改为：

```bash
# Step B-4: 同步 Sprint State（调用独立 skill）
SPRINT_DIR="$SPRINT_DIR" SPRINT_ID="$SPRINT_ID" TASK_ID="$TASK_ID" \
  /harness-sprint-state
```

evaluator 本身不再包含任何 Notion 逻辑。
