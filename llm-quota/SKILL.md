---
name: llm-quota
description: "查询 Claude Code、Codex、Grok 账号的额度、用量、余额、到期和登录可用性。用于账号用量检查、5小时或7天额度，以及 token 状态查询。"
---

# LLM 账号用量总览

## 账号清单

### Claude Code（2个有效，account1/2）

| 账号 | 邮箱 | 缩写 | 状态 |
|------|------|------|------|
| account1 | alexperfectapi01@gmail.com | AP01 | ✅ 活跃 |
| account2 | chalexlch@gmail.com | LCH | ✅ 活跃 |
| account3 | zenithjoy21xx@gmail.com | ZJ | ⚠️ 未充值，不派任务 |

配额窗口（独立计算）：
- `5h Session` — 5小时会话窗口
- `7d All-Model` — 7天全模型总用量
- `7d Sonnet` — 7天 Sonnet 单独上限

### Codex（5个，分两台机器）

| 账号 | 邮箱 | Plan | 机器 |
|------|------|------|------|
| team1 | xuxiao21xx@icloud.com | Team | 美国 Mac M4（本机） |
| team2 | xuxiao21xx@icloud.com | Plus | 美国 Mac M4（本机） |
| team3 | subodou@gmail.com | Team | 西安 Mac M4（ssh xian-m4） |
| team4 | zenithjoycloud@gmail.com | Team | 西安 Mac M4（ssh xian-m4） |
| team5 | perfect21xxxx@gmail.com | Team | 西安 Mac M4（ssh xian-m4） |

配额窗口（2个独立）：
- `5h Primary` — 5小时主窗口
- `7d Secondary` — 7天次窗口

**架构说明（2026-05-27）**：team1/2 和 team3/4/5 各自独立刷新，互不同步。
rotating refresh token 机制下两台机器共享账号会互相消耗，已永久禁止 sync。

---

## 查询脚本

Claude 侧直接调 Anthropic `oauth/usage`（不走 Brain，避免 3min 缓存滞后 / Brain 宕机时无法查询）。
Codex 侧直接调 ChatGPT `wham/usage`。两边均并行请求。

脚本直接输出格式化的 markdown 表格，**直接展示给用户，不需要再加工**。

```bash
node -e "
const { readFileSync } = require('fs');
const { homedir } = require('os');
const now = Date.now();
const TZ = 'Asia/Shanghai';

function fmtTime(ms) {
  if (!ms) return '-';
  const d = new Date(ms);
  const diffH = (ms - now) / 3600000;
  let remain = '';
  if (diffH > 0) {
    if (diffH < 1) remain = Math.round(diffH*60) + '分钟后';
    else if (diffH < 24) remain = diffH.toFixed(1) + 'h后';
    else remain = (diffH/24).toFixed(1) + '天后';
  } else { remain = '已过'; }
  const timeStr = d.toLocaleString('zh-CN', {timeZone:TZ, month:'numeric', day:'numeric', hour:'2-digit', minute:'2-digit'});
  return timeStr + ' (' + remain + ')';
}

function bar(pct) {
  pct = Math.round(pct || 0);
  if (pct === 0) return '░░░░░ 0%';
  if (pct <= 25) return '█░░░░ ' + pct + '%';
  if (pct <= 50) return '██░░░ ' + pct + '%';
  if (pct <= 75) return '███░░ ' + pct + '%';
  if (pct < 100) return '████░ ' + pct + '%';
  return '█████ 100%';
}

async function queryClaude(id) {
  try {
    const creds = JSON.parse(readFileSync(homedir()+'/.claude-'+id+'/.credentials.json','utf8'));
    const token = creds.claudeAiOauth?.accessToken;
    if (!token) return {error:'no token'};
    const r = await fetch('https://api.anthropic.com/api/oauth/usage', {
      headers: {'Authorization':'Bearer '+token, 'anthropic-beta':'oauth-2025-04-20', 'Accept':'application/json'},
      signal: AbortSignal.timeout(8000)
    });
    if (!r.ok) return {error:'HTTP '+r.status};
    return await r.json();
  } catch(e) { return {error:e.message}; }
}

async function queryCodex(id) {
  try {
    const a = JSON.parse(readFileSync(homedir()+'/.codex-'+id+'/auth.json','utf8'));
    const t=a.tokens?.access_token; const aid=a.tokens?.account_id;
    if(!t) return {error:'no token'};
    const r = await fetch('https://chatgpt.com/backend-api/wham/usage',{
      headers:{'Authorization':'Bearer '+t,'ChatGPT-Account-Id':aid},
      signal:AbortSignal.timeout(8000)
    });
    if(!r.ok) return {error:'HTTP '+r.status};
    return await r.json();
  } catch(e) { return {error:e.message}; }
}

(async () => {
  const shNow = new Date().toLocaleString('zh-CN', {timeZone:TZ, year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit'});

  console.log('## LLM 账号用量');
  console.log('> ' + shNow + '（北京时间 UTC+8）| 括号 = 距当前剩余时间 | 数据源：Anthropic / ChatGPT 官方 API（无缓存）');
  console.log('');

  // Claude Code — 3 账号并行
  const CI = [{id:'account1',name:'AP01'},{id:'account2',name:'LCH'},{id:'account3',name:'ZJ'}];
  const claudeResults = await Promise.all(CI.map(c => queryClaude(c.id)));

  console.log('### Claude Code');
  console.log('');
  console.log('| 账号 | 5h Session | 5h 到期 | 7d All-Model | 7d 到期 | 7d Sonnet | Sonnet 到期 |');
  console.log('|------|-----------|---------|-------------|---------|----------|------------|');

  for (let i = 0; i < CI.length; i++) {
    const {name} = CI[i]; const d = claudeResults[i];
    if (d?.error) { console.log('| ' + name + ' | ❌ ' + d.error + ' | | | | | |'); continue; }
    const fh = d.five_hour, sd = d.seven_day, ss = d.seven_day_sonnet;
    const fhMs = fh?.resets_at ? new Date(fh.resets_at).getTime() : null;
    const sdMs = sd?.resets_at ? new Date(sd.resets_at).getTime() : null;
    const ssMs = ss?.resets_at ? new Date(ss.resets_at).getTime() : null;
    console.log('| ' + name + ' | ' + bar(fh?.utilization) + ' | ' + fmtTime(fhMs) + ' | ' + bar(sd?.utilization) + ' | ' + fmtTime(sdMs) + ' | ' + bar(ss?.utilization) + ' | ' + fmtTime(ssMs) + ' |');
  }

  // Codex 本机 team1/2
  const XI_LOCAL = [{id:'team1',name:'xuxiao(T1)'},{id:'team2',name:'xuxiao(T2)'}];
  const codexLocalResults = await Promise.all(XI_LOCAL.map(x => queryCodex(x.id)));

  console.log('');
  console.log('### Codex（本机 team1/2）');
  console.log('');
  console.log('| 账号 | 5h Primary | 5h 到期 | 7d Secondary | 7d 到期 |');
  console.log('|------|-----------|---------|-------------|---------|');

  for (let i = 0; i < XI_LOCAL.length; i++) {
    const {name} = XI_LOCAL[i]; const d = codexLocalResults[i];
    if (d?.error) { console.log('| ' + name + ' | ❌ ' + d.error + ' | | | |'); continue; }
    const pw=d.rate_limit?.primary_window, sw=d.rate_limit?.secondary_window;
    const phMs=pw?.reset_after_seconds?now+pw.reset_after_seconds*1000:null;
    const shMs=sw?.reset_after_seconds?now+sw.reset_after_seconds*1000:null;
    console.log('| ' + name + ' | ' + bar(pw?.used_percent) + ' | ' + fmtTime(phMs) + ' | ' + bar(sw?.used_percent) + ' | ' + fmtTime(shMs) + ' |');
  }
})();
"
```

脚本输出就是最终展示内容，直接贴给用户。

**西安 team3/4/5**（SSH 查询）：

```bash
ssh xian-m4 'node -e "
const { readFileSync } = require(\"fs\");
const { homedir } = require(\"os\");
const now = Date.now();
const TZ = \"Asia/Shanghai\";
function fmtTime(ms) {
  if (!ms) return \"-\";
  const diffH = (ms - now) / 3600000;
  let remain = diffH > 0 ? (diffH < 1 ? Math.round(diffH*60)+\"分钟后\" : diffH < 24 ? diffH.toFixed(1)+\"h后\" : (diffH/24).toFixed(1)+\"天后\") : \"已过\";
  const timeStr = new Date(ms).toLocaleString(\"zh-CN\", {timeZone:TZ, month:\"numeric\", day:\"numeric\", hour:\"2-digit\", minute:\"2-digit\"});
  return timeStr + \" (\" + remain + \")\";
}
function bar(pct) {
  pct = Math.round(pct || 0);
  if (pct===0) return \"░░░░░ 0%\";
  if (pct<=25) return \"█░░░░ \"+pct+\"%\";
  if (pct<=50) return \"██░░░ \"+pct+\"%\";
  if (pct<=75) return \"███░░ \"+pct+\"%\";
  if (pct<100) return \"████░ \"+pct+\"%\";
  return \"█████ 100%\";
}
async function queryCodex(id) {
  try {
    const a = JSON.parse(readFileSync(homedir()+\"/.codex-\"+id+\"/auth.json\",\"utf8\"));
    const t=a.tokens?.access_token; const aid=a.tokens?.account_id;
    if(!t) return {error:\"no token\"};
    const r = await fetch(\"https://chatgpt.com/backend-api/wham/usage\",{
      headers:{\"Authorization\":\"Bearer \"+t,\"ChatGPT-Account-Id\":aid},
      signal:AbortSignal.timeout(8000)
    });
    if(!r.ok) return {error:\"HTTP \"+r.status};
    return await r.json();
  } catch(e) { return {error:e.message}; }
}
(async () => {
  const XI = [{id:\"team3\",name:\"subodou(T3)\"},{id:\"team4\",name:\"zenithjoy(T4)\"},{id:\"team5\",name:\"perfect21(T5)\"}];
  const results = await Promise.all(XI.map(x => queryCodex(x.id)));
  console.log(\"### Codex（西安 team3/4/5）\");
  console.log(\"\");
  console.log(\"| 账号 | 5h Primary | 5h 到期 | 7d Secondary | 7d 到期 |\");
  console.log(\"|------|-----------|---------|-------------|---------|\" );
  for (let i=0;i<XI.length;i++) {
    const {name}=XI[i]; const d=results[i];
    if(d?.error){console.log(\"| \"+name+\" | ❌ \"+d.error+\" | | | |\");continue;}
    const pw=d.rate_limit?.primary_window,sw=d.rate_limit?.secondary_window;
    const phMs=pw?.reset_after_seconds?now+pw.reset_after_seconds*1000:null;
    const shMs=sw?.reset_after_seconds?now+sw.reset_after_seconds*1000:null;
    console.log(\"| \"+name+\" | \"+bar(pw?.used_percent)+\" | \"+fmtTime(phMs)+\" | \"+bar(sw?.used_percent)+\" | \"+fmtTime(shMs)+\" |\");
  }
})();
"'
```

---

## Token 自动续期

Claude Code token 由 `~/bin/refresh-claude-tokens.sh` 每 2 小时自动刷新（cron），使用 refresh_token API，不需要交互式登录。

## 手动登录（仅 token 失效时）

| 情况 | 处理 |
|------|------|
| Claude Code token 失效 | `claude-login 1\|2`（自动校验邮箱，存错拒绝） |
| 本机 team1/2 失效 | `CODEX_HOME=~/.codex-teamX codex` 登录，授权后将回调 URL 发给 Claude Code，Claude 立即 curl localhost:1455 |
| 西安 team3/4/5 失效 | 同上，但 Claude Code 用 `ssh xian-m4 'curl ...'` 发送回调 |

**⚠️ 禁止同步**：team1/2 和 team3/4/5 的 auth.json 绝不互相 scp/rsync。
OpenAI 使用 rotating refresh token，同步会导致两台机器互相消耗 token，造成两边都失效的死循环。

## 触发范围与原运行约束

LLM 账号用量查询 Skill。当用户问 "额度"、"用量"、"账号还有多少"、"查一下账号"、"5小时"、"7天"、"codex 额度"、"claude 额度"、"llm 额度"、"账号余额"、"召唤codex"、"token 状态"、"到期时间" 时自动触发。
- 2 个 Claude Code 有效账号：account1/2（account3 未充值，不派任务），credentials 在 ~/.claude-accountX/.credentials.json
- 5 个 Codex 账号：team1/2 在美国 Mac M4（本机），team3/4/5 在西安 Mac M4（ssh xian-m4）
- Claude Code API：api.anthropic.com/api/oauth/usage（5h / 7d all-models / 7d sonnet）
- Codex API：chatgpt.com/backend-api/wham/usage（5h primary / 7d secondary）
全局适用，所有项目共享。
