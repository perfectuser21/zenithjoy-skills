---
name: notion-issue
description: 把当前对话里发现的系统性问题记录到 Notion Issues 数据库。当用户说"记到 issue"、"写进 notion"、"log this"、"这个问题记一下"、"把这个放到 issue 里"，或者输入 /notion-issue 时触发。不要等用户明确给出所有字段——从对话上下文推断 title、sub-area、priority，直接创建，给用户确认链接即可。
---

## 这个 skill 做什么

从当前对话中提取问题上下文，自动填好所有字段，在 Notion Issues DB 创建一条 issue。

**触发场景**（满足其一）：
- 用户说"记到 issue"/"写进 notion"/"log this"/"这个问题记一下"
- 用户输入 `/notion-issue`
- 对话中发现某个组件被反复修（同一根因多次出现）

**不触发**：用户只是在讨论问题，没有明确说要记录。

---

## 执行步骤

### 1. 从对话提取上下文

读当前对话，提取：

| 字段 | 来源 | 推断方法 |
|---|---|---|
| `title` | 问题一句话概括 | 动词开头，< 30 字 |
| `body` | 根因 + 实证 | 从对话中已讨论的细节提取 |
| `priority` | 影响范围 | P0=生产崩 / P1=严重影响功能 / P2=一般缺陷 / P3=优化 |
| `sub-area` | 涉及的代码模块 | 见下方映射表 |

**Sub Area 映射**：
- 改动 `packages/brain/` 或讨论 Brain 逻辑 → `brain`
- 改动 `packages/engine/` 或讨论 hooks/skills → `engine`
- 改动 `apps/dashboard/`（Cecelia）→ `dashboard`
- 改动 `apps/api/`（ZenithJoy）→ `zenithjoy`
- 改动 `packages/workflows/` 或讨论 multi-agent → `multi-agent`
- 不确定 → `brain`（默认）

### 2. 运行脚本创建 issue

```bash
node /Users/administrator/perfect21/cecelia/scripts/notion-create-issue.js \
  --title "<title>" \
  --priority <P0|P1|P2|P3> \
  --sub-area <sub-area> \
  --body "<body>"
```

脚本输出 Notion URL，直接给用户。

### 3. 修复完成后关闭 issue（可选，修复时再做）

```bash
node -e "
const fs=require('fs'),env={};
fs.readFileSync(process.env.HOME+'/.credentials/notion.env','utf8')
  .split('\n').forEach(l=>{const m=l.match(/^([^=]+)=(.+)/);if(m)env[m[1]]=m[2];});
fetch('https://api.notion.com/v1/pages/<PAGE_ID>',{
  method:'PATCH',
  headers:{'Authorization':'Bearer '+env.NOTION_API_KEY,'Notion-Version':'2022-06-28','Content-Type':'application/json'},
  body:JSON.stringify({properties:{'Status':{status:{name:'Closed'}}}})
}).then(()=>console.log('closed'));
"
```

---

## 输出格式

创建成功后，输出：

```
✅ Issue 已创建：<Notion URL>
   标题：<title>
   优先级：<priority> | Sub Area：<sub-area>
```

如果推断的字段不确定，先创建，再告诉用户"title/priority 我是这样推断的，有问题可以在 Notion 里改"。
