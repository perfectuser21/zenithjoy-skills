---
name: notion
description: |
  Notion 读写 Skill。操作 AI Hub 9 张核心表（Journey/Steps/Feature/SkillRegistry/API/DB/Test/Issues/Notes）。
  触发词：写进Notion、存到Notion、记录问题/Issue、记录决策/知识/日志、查Notion Issues、更新Journey状态。
  凭据从 1Password CS Vault "Notion" 条目读取，CCAPI2026 集成账号直接可用。
  旧 workspace（OKR/Projects/Initiative/Areas）全部 404，禁止使用。
---

# Notion Skill

## 凭据获取（必须第一步）

```bash
node -e "
const fs = require('fs');
const {execFileSync} = require('child_process');
const env = {};
fs.readFileSync(process.env.HOME + '/.credentials/1password.env', 'utf8')
  .split('\n').forEach(l => { const m = l.match(/^([^=]+)=(.+)/); if (m) env[m[1]]=m[2]; });
// credential 字段存 token，notesPlain 存 DB IDs（ZenithJoy workspace）
const token = execFileSync('op', ['item', 'get', 'Notion', '--vault', 'CS', '--fields', 'credential'],
  {env: {...process.env, ...env}}).toString().trim().replace(/^\"|\"$/g,'');
const note = execFileSync('op', ['item', 'get', 'Notion', '--vault', 'CS', '--fields', 'notesPlain'],
  {env: {...process.env, ...env}}).toString().trim().replace(/^\"|\"$/g,'');
const creds = `NOTION_API_KEY=${token}\n` + note.split('\n').filter(l=>l.startsWith('NOTION_') && !l.startsWith('NOTION_API_KEY')).join('\n') + '\n';
fs.writeFileSync(process.env.HOME + '/.credentials/notion.env', creds, {mode: 0o600});
console.log('✅ Notion 凭据已同步');
"
```

---

## AI Hub 数据库（9 张核心表，CCAPI2026 集成账号）

| 变量 | 用途 | DB ID |
|------|------|-------|
| `NOTION_JOURNEY_DB` | AI Journey — 能力轴 L1 领域（Journey） | `358c40c2-ba63-8148-bde7-e313d789931a` |
| `NOTION_STEPS_DB` | AI Steps — 历史遗留 Step 库（journey_steps，已废弃只读；新 L4 step 落 golden_path 表） | `369c40c2-ba63-812c-9f35-e7e43db25014` |
| `NOTION_JOURNEY_STEP_DB` | Journey-Step 顺序连接表（遗留） | `369c40c2-ba63-81e2-b95a-e5e3d0592676` |
| `NOTION_FEATURE_DB` | AI Feature — journey_features 载体：kind=ability 即 L3 Golden Path/Ability，kind=feature 即 L5 使能件 | `358c40c2-ba63-81e3-96c5-d762b3d34dff` |
| `NOTION_SKILL_REGISTRY_DB` | Skill Registry | `353c40c2-ba63-81bf-ae3e-f0e6fa3753d7` |
| `NOTION_API_REGISTRY_DB` | Sprint State — API Registry | `365c40c2-ba63-81a3-9060-fcef565e5291` |
| `NOTION_DB_SCHEMA_REGISTRY_DB` | Sprint State — DB Schema Registry | `365c40c2-ba63-8181-9a57-ed760fd68ba3` |
| `NOTION_TEST_REGISTRY_DB` | Sprint State — Tests Registry | `365c40c2-ba63-8164-8037-eb72e713809e` |
| `NOTION_ISSUES_DB` | Issues — Bug / 问题追踪 | `a17c40c2-ba63-82fb-9888-8152cefe29ec` |
| `NOTION_NOTES_DB` | AI Notes — 决策/知识/日志 | `185c40c2-ba63-828c-973f-81a9c4582cd6` |

> ⚠️ **旧 workspace 已废弃**：`NOTION_PROJECTS_DB`（b47c40c2）、`NOTION_EXECUTION_DB`（e9ac40c2）、`NOTION_AREAS_DB`（e62c40c2）、`NOTION_OKR_DB`（a29c40c2）、`NOTION_FEATURE_REGISTRY_DB`（352c40c2）均为 404，禁止使用。

---

## 模板 1：Issue

存入 `NOTION_ISSUES_DB`

```javascript
{
  parent: {database_id: env.NOTION_ISSUES_DB},
  properties: {
    Issue: {title: [{text:{content:'【问题标题】'}}]},
    Priority: {select: {name: 'P1'}},
    Horizon: {select: {name: 'Now'}},
    Area: {relation: [{id: '子Area ID'}]},
    Projects: {relation: [{id: 'Project ID'}]},  // 双向关联，必填
  },
  children: [
    h2('问题描述'), p('...'),
    h2('根本原因'), p('...'),
    h2('修复方案'), p('...'),
    h2('验证方式'), p('...'),
  ]
}
```

---

## 模板 2：Decision / Knowledge / Notes

存入 `NOTION_NOTES_DB`

**Type 选项：** `Decision`（架构决策）/ `Research`（知识科普）/ `Log`（日志）/ `Notes`（随手记）

```javascript
{
  parent: {database_id: env.NOTION_NOTES_DB},
  properties: {
    Title: {title: [{text:{content:'【标题】'}}]},
    Type: {select: {name: 'Decision'}},  // 按实际类型填
    Date: {date: {start: new Date().toISOString().split('T')[0]}},
    'Related Areas': {relation: [{id: '子Area ID'}]},
    Projects: {relation: [{id: 'Project ID'}]},  // 可选
  },
  children: [
    // Decision 结构：
    h2('决定了什么'), p('...'),
    h2('为什么这么决定'), p('...'),
    h2('影响范围'), p('...'),
    // Research 结构：
    // h2('是什么'), h2('为什么重要'), h2('正确理解'), h2('当前状态')
  ]
}
```

---

## 通用 Block 构建函数

```javascript
const h2 = text => ({object:'block',type:'heading_2',heading_2:{rich_text:[{type:'text',text:{content:text}}]}});
const h3 = text => ({object:'block',type:'heading_3',heading_3:{rich_text:[{type:'text',text:{content:text}}]}});
const p = text => ({object:'block',type:'paragraph',paragraph:{rich_text:[{type:'text',text:{content:text}}]}});
const todo = text => ({object:'block',type:'to_do',to_do:{rich_text:[{type:'text',text:{content:text}}],checked:false}});
const li = text => ({object:'block',type:'bulleted_list_item',bulleted_list_item:{rich_text:[{type:'text',text:{content:text}}]}});
```

---

## 查询模板

### 查 Issues（按 Priority 排序）

```javascript
fetch('https://api.notion.com/v1/databases/' + env.NOTION_ISSUES_DB + '/query', {
  method: 'POST',
  headers: { 'Authorization': 'Bearer ' + env.NOTION_API_KEY, 'Notion-Version': '2022-06-28', 'Content-Type': 'application/json' },
  body: JSON.stringify({
    filter: {
      and: [
        { property: 'Status', status: { does_not_equal: 'Done' } },
        { property: 'Area', relation: { contains: '子Area ID' } }
      ]
    },
    sorts: [{ property: 'Priority', direction: 'ascending' }]
  })
}).then(r => r.json()).then(d => {
  d.results.forEach(p => {
    const pri = p.properties.Priority?.select?.name;
    const title = p.properties.Issue.title[0]?.plain_text;
    console.log(pri, '|', title);
  });
});
```

---

## 触发条件

- "记录问题 / 新建 Issue" → 模板 1（NOTION_ISSUES_DB）
- "记录决策 / 知识 / 日志" → 模板 2（NOTION_NOTES_DB / AI Notes）
- "更新 Journey / Feature / Step" → 直接用对应 Brain API，再同步 Notion（见 CLAUDE.md 第 11 节）

**写入前必须确认：**
1. 写哪张表？（见 CLAUDE.md 第 11 节 9 张核心表）
2. 标题和一句话摘要是什么？
