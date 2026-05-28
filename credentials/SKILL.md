---
name: credentials
description: |
  1Password 凭据查找与管理。当需要任何 API Key、Token、Secret、密钥时必须触发此 skill。
  触发场景：调用第三方 API（OpenAI/Anthropic/OpenRouter/Notion/飞书等）、设置 GitHub Actions Secret、
  部署到服务器、连接数据库、用户说"找一下 XXX 的 token"、"需要 API key"、遇到 401/403 认证错误。
  禁止在不走此 skill 的情况下猜测凭据或从旧缓存直接使用。
---

# 凭据管理

**核心原则：1Password CS Vault 是唯一真实源。每次查找都走下面的标准协议，不猜条目名，不猜字段名。**

---

## 标准查找协议（必须按顺序执行）

### Step 1：先搜索，找到条目

不知道确切条目名时，先 list 搜索：

```javascript
// 标准搜索模板 — 复制修改 keyword
node -e "
const fs = require('fs');
const {execFileSync} = require('child_process');
const env = {};
fs.readFileSync(process.env.HOME + '/.credentials/1password.env', 'utf8')
  .split('\n').forEach(l => { const m = l.match(/^([^=]+)=(.+)/); if (m) env[m[1]]=m[2]; });
const items = JSON.parse(execFileSync('op', ['item', 'list', '--vault', 'CS', '--format', 'json'],
  {env: {...process.env, ...env}}).toString());
const keyword = 'openrouter';  // ← 改这里，小写关键词
const found = items.filter(i => i.title.toLowerCase().includes(keyword));
console.log(JSON.stringify(found.map(i=>({id:i.id, title:i.title})), null, 2));
"
```

### Step 2：获取所有字段，找到有值的那个

拿到条目 ID 或 title 后，dump 全部字段，不要猜字段名：

```javascript
// 标准字段 dump 模板
node -e "
const fs = require('fs');
const {execFileSync} = require('child_process');
const env = {};
fs.readFileSync(process.env.HOME + '/.credentials/1password.env', 'utf8')
  .split('\n').forEach(l => { const m = l.match(/^([^=]+)=(.+)/); if (m) env[m[1]]=m[2]; });
const item = JSON.parse(execFileSync('op',
  ['item', 'get', 'ITEM_ID_OR_TITLE', '--vault', 'CS', '--format', 'json', '--reveal'],
  {env: {...process.env, ...env}}).toString());
// 打印所有字段及其值前20字符，找有值的
item.fields.forEach(f => {
  if (f.value && f.value.length > 0 && f.label !== 'notesPlain') {
    console.log(f.label + ': ' + f.value.substring(0, 30) + (f.value.length > 30 ? '...' : ''));
  }
});
"
```

### Step 3：写本地缓存，source 后使用

```bash
echo "SERVICE_KEY=actual_value" > ~/.credentials/service.env
chmod 600 ~/.credentials/service.env
source ~/.credentials/service.env
```

---

## 已知条目字典（跳过搜索，直接取）

| 服务 | 1Password 条目名 | 字段名 | 本地文件 |
|------|----------------|--------|---------|
| OpenRouter | `OpenRouter API Key` | `api_key` | `openrouter.env` → `OPENROUTER_API_KEY` |
| GitHub (classic, secrets权限) | `GitHub Tokens` | `notesPlain` 解析 `GITHUB_CLASSIC_TOKEN=ghp_...` | `github-classic.env` |
| GitHub (标准 PAT) | `GitHub Tokens` | `notesPlain` 解析 `GITHUB_PAT_NEW=...` | `github.env` |
| GitHub (ZenithJoycloud org) | `GitHub Tokens` | `notesPlain` 解析 `GITHUB_PAT_ZENITHJOYCLOUD=...` | — |
| Notion | `Notion` | `notesPlain` 解析 `NOTION_*` | `notion.env` |
| Anthropic | `Anthropic Claude API` | `credential` | `anthropic.json` |
| OpenAI | `OpenAI-claudecode2026` | `credential` | `openai.env` |
| Cecelia PostgreSQL | `Cecelia PostgreSQL` | `password` 或 `credential` | `database.env` |
| Feishu 飞书 | `Feishu 飞书` | `credential` | `feishu.env` |

**GitHub Tokens 特殊说明**：这个条目的 `notesPlain` 字段包含多行 KEY=VALUE 格式，需要解析：

```javascript
const notes = item.fields.find(f => f.label === 'notesPlain').value;
const match = notes.match(/GITHUB_CLASSIC_TOKEN=(ghp_\S+)/);
const classicToken = match[1];
```

三个 token 的权限：
- `GITHUB_CLASSIC_TOKEN` (`ghp_...`) → **有 secrets:write**，用于 `gh secret set`
- `GITHUB_PAT_NEW` (`github_pat_11...`) → 标准 PAT，日常 git/API 操作
- `GITHUB_PAT_ZENITHJOYCLOUD` → ZenithJoycloud 组织专用

---

## 常见操作快查

### 设置 GitHub Actions Secret

```bash
# 先 source classic token
source ~/.credentials/github-classic.env

# 设置 secret（只有 classic token 有权限）
GH_TOKEN=$GITHUB_CLASSIC_TOKEN gh secret set SECRET_NAME \
  --body "$SECRET_VALUE" \
  --repo owner/repo-name

# 验证
GH_TOKEN=$GITHUB_CLASSIC_TOKEN gh secret list --repo owner/repo-name
```

### 读取 OpenRouter Key

```bash
# 如果本地已有缓存
source ~/.credentials/openrouter.env
echo $OPENROUTER_API_KEY

# 如果需要从 1P 重新获取
node -e "
const fs = require('fs'), {execFileSync} = require('child_process');
const env = {};
fs.readFileSync(process.env.HOME + '/.credentials/1password.env', 'utf8')
  .split('\n').forEach(l => { const m = l.match(/^([^=]+)=(.+)/); if (m) env[m[1]]=m[2]; });
const key = execFileSync('op', ['item', 'get', 'OpenRouter API Key', '--vault', 'CS',
  '--fields', 'api_key', '--reveal'], {env: {...process.env, ...env}}).toString().trim().replace(/^\"|\"$/g,'');
fs.writeFileSync(process.env.HOME + '/.credentials/openrouter.env', 'OPENROUTER_API_KEY=' + key + '\n', {mode: 0o600});
console.log('✅ OPENROUTER_API_KEY 已缓存，length=' + key.length);
"
```

### 读取 GitHub Tokens

```bash
node -e "
const fs = require('fs'), {execFileSync} = require('child_process');
const env = {};
fs.readFileSync(process.env.HOME + '/.credentials/1password.env', 'utf8')
  .split('\n').forEach(l => { const m = l.match(/^([^=]+)=(.+)/); if (m) env[m[1]]=m[2]; });
const item = JSON.parse(execFileSync('op', ['item', 'get', 'GitHub Tokens', '--vault', 'CS',
  '--format', 'json', '--reveal'], {env: {...process.env, ...env}}).toString());
const notes = item.fields.find(f => f.label === 'notesPlain').value;
// 解析所有 KEY=VALUE 行
const creds = {};
notes.split('\n').forEach(l => { const m = l.match(/^(GITHUB_\w+)=([\S]+)/); if (m) creds[m[1]]=m[2]; });
// 写 classic token 文件
if (creds.GITHUB_CLASSIC_TOKEN) {
  fs.writeFileSync(process.env.HOME + '/.credentials/github-classic.env',
    'GITHUB_CLASSIC_TOKEN=' + creds.GITHUB_CLASSIC_TOKEN + '\n', {mode: 0o600});
  console.log('✅ github-classic.env 已写入');
}
// 写标准 token 文件
if (creds.GITHUB_PAT_NEW) {
  fs.writeFileSync(process.env.HOME + '/.credentials/github.env',
    'GITHUB_TOKEN=' + creds.GITHUB_PAT_NEW + '\n', {mode: 0o600});
  console.log('✅ github.env 已写入');
}
"
```

---

## 存储新凭据

```javascript
// 先写 1Password，再 sync 到本地
node -e "
const fs = require('fs'), {execFileSync} = require('child_process');
const env = {};
fs.readFileSync(process.env.HOME + '/.credentials/1password.env', 'utf8')
  .split('\n').forEach(l => { const m = l.match(/^([^=]+)=(.+)/); if (m) env[m[1]]=m[2]; });
execFileSync('op', [
  'item', 'create', '--vault', 'CS', '--category', 'API Credential',
  '--title', 'SERVICE_NAME', '--tags', 'TAG', 'api_key=VALUE'
], {env: {...process.env, ...env}, stdio: 'inherit'});
"
```

常用 tags：`ai` / `infra` / `trading` / `social` / `dev` / `tool`

---

## 安全规则

1. 凭据不入 git，不在命令行参数中硬编码（bash-guard 会拦截）
2. 写 credentials 文件后 chmod 600
3. 新凭据流程：**1P 先写 → 本地缓存** ，绝不反向
4. 发现本地有但 1P 没有 → 立即补到 1P

**最后更新**: 2026-04-02
