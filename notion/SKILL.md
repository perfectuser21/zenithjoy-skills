---
name: notion
version: 1.1.0
updated: 2026-10-14
description: |
  Notion 知识/内容真身读写与投影只读；任务、决定、Issues及研发登记写Brain。
  触发词：写进Notion、存到Notion、记录问题/Issue、记录决策/知识/日志、查Notion Issues、更新Journey状态。
  凭据从 1Password CS Vault "Notion" 条目读取，CCAPI2026 集成账号直接可用。
  禁止使用正文列出的旧库ID；现行库以现场总台账和读回为准。
---

# Notion Skill

规矩锚点：六去向（b28e7a9f / 52f1d55d / e10d74cb）。先判真身；知识与内容可直接写Notion，Tasks/Projects等有Brain直连时写Brain真身。AI Hub、Events、Ops、决定、Rules和总台账属于投影，只读。

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

## AI Hub 投影查询（只读，禁止直接写入）

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
| `NOTION_NOTES_DB` | AI Notes — 研发材料投影 | `185c40c2-ba63-828c-973f-81a9c4582cd6` |

> ⚠️ **旧 workspace 已废弃**：`NOTION_PROJECTS_DB`（b47c40c2）、`NOTION_EXECUTION_DB`（e9ac40c2）、`NOTION_AREAS_DB`（e62c40c2）、`NOTION_OKR_DB`（a29c40c2）、`NOTION_FEATURE_REGISTRY_DB`（352c40c2）均为 404，禁止使用。

---

## 写入路由

| 需求 | 入口 |
|---|---|
| 记录问题 | `POST /api/brain/issues`，按db-update正式字段写；GET读回确认，Notion Issues自动投影 |
| 记录用户决定 | `POST /api/brain/strategic-decisions`，理由与actor当场留痕；不写AI Notes或决定投影 |
| 任务/完成/session交接 | Brain tasks及result.handoff，先登记后开工，完成留事实/证据/actor |
| Journey/Feature/Steps/Skill登记 | Brain对应正式接口；不直写AI Hub |
| 知识 | 下方知识三库，优先更新已有知识页 |
| 内容 | Ideas → Seed → Core → 发布编排台真身；发布成功回写Brain事件 |

## 知识真身写入

| 分类 | Notion database ID |
|---|---|
| Knowledge_Reference | `770c40c2ba6383ea86d001eba832c218` |
| Knowledge_Operational | `7b7c40c2ba6383649f7681203bb3d1de` |
| Insights | `351c40c2ba6380c0ada0e527f051a9ec` |

先查既有页查重，读目标库schema确定标题等字段名；凭据按credentials技能从1Password取并双写600缓存。只对选定知识真身创建或更新页，写后GET读回标题、正文与链接。操作知识页不改变任务/设备/版本状态；来源事实指回Brain任务证据。

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

- 记录问题、决定、任务、研发登记：按上方Brain路由执行并读回；禁止写投影。
- 知识/内容：定位Notion真身后直接更新并读回；不创建AI Notes副本。
- 无Brain直连工具按现场AGENTS规定的Notion工作面进入，默认lane=待分拣；此例外不开放只读投影写入。
