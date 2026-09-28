// 本地 SSOT → Notion 同步:按 notion_page_id upsert 属性 + 重写 page content 三段
// 用法: node sync-to-notion.mjs steps/line02-jinnuo-leadgen.json
import fs from 'fs';
const env = {};
fs.readFileSync(process.env.HOME + '/.credentials/notion.env','utf8').split('\n')
  .forEach(l => { const m = l.match(/^([^=]+)=(.+)/); if (m) env[m[1]]=m[2]; });
const H = { 'Authorization': 'Bearer '+env.NOTION_API_KEY, 'Notion-Version':'2022-06-28', 'Content-Type':'application/json' };
const api = async (path, method='GET', body) => (await fetch('https://api.notion.com/v1/'+path,{method,headers:H,body:body?JSON.stringify(body):undefined})).json();
const h2=t=>({object:'block',type:'heading_2',heading_2:{rich_text:[{type:'text',text:{content:t}}]}});
const p =t=>({object:'block',type:'paragraph',paragraph:{rich_text:[{type:'text',text:{content:t}}]}});
const li=t=>({object:'block',type:'bulleted_list_item',bulleted_list_item:{rich_text:[{type:'text',text:{content:t}}]}});

const file = process.argv[2] || 'steps/line02-jinnuo-leadgen.json';
const doc = JSON.parse(fs.readFileSync(new URL('../'+file, import.meta.url),'utf8'));
for (const s of doc.steps) {
  const props = {
    '步骤':{title:[{text:{content:s.name}}]},
    '阶段':{select:{name:s.stage}},
    '顺序':{number:s.order},
    '现在走的是':{select:{name:s.impl_now}},
    '目标标签':{select:{name:s.target}},
    '有确定性判定?':{select:{name:s.deterministic}},
    '状态':{select:{name:s.status}},
    '所属Workflow':{relation:[{id:doc.notion_workflow_row}]},
  };
  let pageId = s.notion_page_id;
  if (pageId) {
    await api('pages/'+pageId,'PATCH',{properties:props});
    // 清旧正文再写(简单粗暴但幂等)
    const old = await api('blocks/'+pageId+'/children?page_size=100');
    for (const b of (old.results||[])) await api('blocks/'+b.id,'DELETE');
  } else {
    const created = await api('pages','POST',{parent:{database_id:doc.notion_step_db},properties:props});
    pageId = created.id; s.notion_page_id = pageId;
  }
  const blocks=[h2('✅ 验证信号(确定性判定)'),p(s.signal||'—'),h2('📜 迭代历史')];
  for (const x of (s.history&&s.history.length?s.history:['(暂无)'])) blocks.push(li(x));
  blocks.push(h2('🕳 证据/坑'),p(s.evidence||'—'));
  await api('blocks/'+pageId+'/children','PATCH',{children:blocks});
  console.log('✓', s.order, s.name);
}
fs.writeFileSync(new URL('../'+file, import.meta.url), JSON.stringify(doc,null,2));
console.log('✅ 同步完成', doc.steps.length, '步');
