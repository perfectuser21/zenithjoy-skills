// 把 Notion 步骤库全量拉回本地 JSON(含 page content),使本地成为完整 SSOT
import fs from 'fs';
const env = {};
fs.readFileSync(process.env.HOME + '/.credentials/notion.env','utf8').split('\n')
  .forEach(l => { const m = l.match(/^([^=]+)=(.+)/); if (m) env[m[1]]=m[2]; });
const H = { 'Authorization': 'Bearer '+env.NOTION_API_KEY, 'Notion-Version':'2022-06-28', 'Content-Type':'application/json' };
const api = async (path, method='GET', body) => (await fetch('https://api.notion.com/v1/'+path,{method,headers:H,body:body?JSON.stringify(body):undefined})).json();
const STEP_DB='3d9c40c2ba638195a41bf529056a4aa8';
let cursor, pages=[];
do { const q=await api('databases/'+STEP_DB+'/query','POST',cursor?{start_cursor:cursor}:{}); pages.push(...q.results); cursor=q.has_more?q.next_cursor:undefined; } while(cursor);
const steps=[];
for (const pg of pages) {
  const P=pg.properties;
  const blocks=await api('blocks/'+pg.id+'/children?page_size=100');
  let section=null, signal='', history=[], evidence='';
  for (const b of (blocks.results||[])) {
    const txt=(b[b.type]?.rich_text||[]).map(r=>r.plain_text).join('');
    if(b.type==='heading_2'){ section = txt.includes('验证信号')?'sig':txt.includes('迭代')?'hist':txt.includes('证据')?'ev':null; continue; }
    if(section==='sig'&&txt) signal+=txt;
    if(section==='hist'&&txt) history.push(txt);
    if(section==='ev'&&txt) evidence+=txt;
  }
  steps.push({
    order: P['顺序']?.number,
    stage: P['阶段']?.select?.name,
    name: P['步骤']?.title?.[0]?.plain_text,
    impl_now: P['现在走的是']?.select?.name,
    target: P['目标标签']?.select?.name,
    deterministic: P['有确定性判定?']?.select?.name,
    status: P['状态']?.select?.name,
    signal, history, evidence,
    notion_page_id: pg.id,
  });
}
steps.sort((a,b)=>a.order-b.order);
const p=process.env.HOME+'/perfect21/zenithjoy-skills/workflow-lifecycle/steps/line02-jinnuo-leadgen.json';
const doc=JSON.parse(fs.readFileSync(p,'utf8'));
doc.steps=steps; doc.steps_note='本地SSOT:改本文件→跑 scripts/sync-to-notion.mjs 推送';
fs.writeFileSync(p, JSON.stringify(doc,null,2));
console.log('✅ 拉回', steps.length, '步 →', p);
