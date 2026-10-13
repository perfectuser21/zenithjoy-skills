---
name: codex-login
description: |
  Codex / ChatGPT 账号登录修复 runbook。当某个 codex 账号（team1~5）跑不动、报 401/403、
  token 过期刷不出来、报 refresh_token_reused、或国内机器（西安 Mac/5060）登不上 OpenAI 时触发。
  覆盖："codex 登不上 / codex 登录失败 / 账号挂了 / account 401 / 重新登录 codex / token 过期刷不动 /
  refresh_token_reused / unsupported_country / codex 跑不了 / 西安 codex 不能用 / 某个 team 账号坏了"。
  只要是 codex 账号「认证/登录」层面的故障就用本 skill；纯查额度/用量走 [[llm-quota]]。
  账号清单与机器映射见 llm-quota，本 skill 不重复抄。
---

# Codex 账号登录修复 Runbook

修一个登不上的 codex 账号，本质是回答两个问题：**坏在哪一层？** 然后 **从干净出口重新拿一张 token。**

账号清单、邮箱、机器映射在 `llm-quota` skill 里，这里不重复。下面只讲「怎么修」。

---

## 0. 心智模型（先懂这 4 条，少走 90% 弯路）

1. **codex 账号 = ChatGPT OAuth 登录**（`auth_mode: chatgpt`）。token 存在 `~/.codex-teamN/auth.json`，
   里面有 `access_token`（约 10 天有效）+ `refresh_token`（用来续期）。

2. **地域封锁只封「登录/刷新」端点，不封「API」端点**。这是最反直觉、最容易误判的一点：
   - 国内机器连 `auth.openai.com`（登录 + 刷新 token）→ **403 `unsupported_country`**
   - 但连实际跑任务的 API 端点 → **通的**
   - 推论：**一张有效 token 在国内照样能跑 codex**；国内跑不动的账号，几乎都是「token 过期 + 国内刷不了」，而不是「网络全断」。用一个没过期的账号实测一下就能证明（见 §2）。

3. **refresh_token 是一次性轮换的**。每刷新一次，旧的立即作废、发一张新的。
   - 如果某次刷新的新 token **没存回**该机器，这台手里的就变成「已用过的旧票」→ 再刷报
     **`refresh_token_reused`** → **这张彻底废了，只能重新登录**。
   - 这就是为什么 [[llm-quota]] 里写「禁止两台机器 sync 同一账号」——会互相把对方的票轮换死。

4. **哪些出口 OpenAI 认**：
   - ✅ **美国本机家用 IP `38.23.47.81`**（mac-mini-m4-us）——OpenAI 认
   - ❌ **机房 IP**：vps-us `134.199.234.147`（DigitalOcean）、vps-hk `124.156.138.116`（腾讯云）
     —— 即使地理在美国，也被 OpenAI 当 VPN/机房 IP **稳定 403**，不是「一阵一阵」，是封死。
   - 国内机器要登录，要么经一个 OpenAI 没拉黑的干净出口（如美国本机 / WARP 出口），
     要么干脆在美国本机上登好再同步过去（见 §3）。

---

## 1. 看 token 现状（第一步永远先做这个）

```bash
# 在持有该账号的机器上跑（teamN 替换成实际账号；西安账号加 ssh xian-m4 前缀）
python3 - "$HOME/.codex-team3/auth.json" << 'PY'
import json,base64,datetime,sys
a=json.load(open(sys.argv[1])); t=a.get("tokens",{})
def claim(tok,k):
    try:
        p=tok.split(".")[1]; p+="="*(-len(p)%4)
        return json.loads(base64.urlsafe_b64decode(p)).get(k)
    except: return None
print("邮箱      :", claim(t.get("id_token",""),"email"))
print("auth_mode :", a.get("auth_mode"))
exp=claim(t.get("access_token",""),"exp")
print("access_exp:", datetime.datetime.utcfromtimestamp(exp) if exp else "?", "UTC")
print("last_refr :", a.get("last_refresh"))
print("有 refresh_token:", bool(t.get("refresh_token")))
PY
```

- `access_exp` 还没过 → token 没坏，问题在别处（网络 / 额度 / 配置）。
- 已过期 → 进 §2 判断「能不能刷」。

---

## 2. 判断坏在哪一层（关键分诊）

### 2a. 先证明「网络/API 端点是好的」——用一个没过期的账号实测

```bash
# 在执行机（如西安）上跑一个 token 没过期的账号（如 team4）
ssh xian-m4 'export PATH=$HOME/.nvm/versions/node/v22.20.0/bin:$PATH
  env CODEX_HOME=$HOME/.codex-team4 codex exec --skip-git-repo-check "只回复:你好" 2>&1 | tail -6'
```

- 输出「你好」或提示 **额度满（usage limit）** → **API 端点是通的**，坏账号纯粹是 token 问题。
- 报 401/连接错误 → 才需要怀疑网络/出口。

### 2b. 再判断「坏账号的 refresh_token 还能不能刷」——必须从干净出口测

```bash
# 在美国本机（干净出口 38.23.47.81）上跑；refresh_token 从坏账号 auth.json 里取
python3 << 'PY'
import json,urllib.request,urllib.error,subprocess
raw=subprocess.check_output(["ssh","xian-m4","cat ~/.codex-team3/auth.json"]).decode()
rt=json.loads(raw)["tokens"]["refresh_token"]
body=json.dumps({"grant_type":"refresh_token","client_id":"app_EMoamEEZ73f0CkXaXp7hrann","refresh_token":rt}).encode()
for url in ["https://auth0.openai.com/oauth/token","https://auth.openai.com/oauth/token"]:
    try:
        r=urllib.request.urlopen(urllib.request.Request(url,data=body,headers={"Content-Type":"application/json"}),timeout=30)
        print("✅ 刷新成功，token 没死，直接刷新+同步即可"); break
    except urllib.error.HTTPError as e:
        print(url, e.code, e.read().decode()[:200])
PY
```

判读结果：
| 返回 | 含义 | 走哪条 |
|------|------|--------|
| 200 / 刷新成功 | token 还活，只是过期 | 刷新拿新 token → §3 的同步部分 |
| `refresh_token_reused` | 票被轮换作废 | **必须完整重登** → §3 |
| `unsupported_country` 403 | 你不在干净出口测的 | 换到美国本机再测 |

> 经验：这次 T3 就是 `refresh_token_reused` —— 老票早被某次刷新轮换了、新票没回写。**这种没有捷径，只能重登。**

---

## 3. 重新登录（核心修复，这次验证过能成）

`codex login` 是浏览器 OAuth，**必须在「OpenAI 认的干净出口」机器上跑**。
推荐在**美国本机**跑（出口 `38.23.47.81` 干净），登好再同步到执行机。

### 3a. 启动登录（美国本机）

```bash
export PATH=$HOME/.nvm/versions/node/v22.14.0/bin:$PATH
CODEX_HOME=~/.codex-team3 codex login    # 必须带 CODEX_HOME，否则写进默认 ~/.codex
```

它会打印一个授权 URL，并在 **本机 `localhost:1455`** 起一个回调监听。

### 3b. 完成授权 + 投递回调（这次最值钱的一招）

远程/无头机器的坑：你在自己电脑的浏览器里授权完，OpenAI 重定向到
`http://localhost:1455/auth/callback?code=...`，但这个 `localhost:1455` 在**跑 codex login 的那台机器**上，
你本地浏览器打不开。解决：

1. 用**对应账号**（如 T3 = subodou@gmail.com）在浏览器里授权完，**复制那个打不开的回调 URL**。
2. 找到监听进程在哪台机器：
   ```bash
   lsof -nP -iTCP:1455 -sTCP:LISTEN     # 哪台有这个 = codex login 在哪台
   ```
3. 在**那台机器**上把回调 curl 投递给它（PKCE 校验绑在该进程，必须投对机器）：
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" --max-time 30 \
     'http://localhost:1455/auth/callback?code=<粘贴完整回调query>'
   ```
   返回 **302** = 成功。该进程用干净出口完成 code→token 交换、写好 auth.json。

### 3c. 验证 + 同步到执行机

```bash
# 1. 验证登对账号 + 新 token（美国本机）—— 复用 §1 的脚本，确认邮箱对、exp 是 ~10 天后
# 2. 同步到执行机（西安）
ssh xian-m4 'chmod 644 ~/.codex-team3/auth.json 2>/dev/null'
scp ~/.codex-team3/auth.json xian-m4:'~/.codex-team3/auth.json'
# 3. 在执行机实测（应像 team4 一样能跑）
ssh xian-m4 'export PATH=$HOME/.nvm/versions/node/v22.20.0/bin:$PATH
  env CODEX_HOME=$HOME/.codex-team3 codex exec --skip-git-repo-check "只回复:你好" 2>&1 | tail -6'
```

输出「你好」/ tokens used → **修好了**。

---

## 4. 防复发（不做的话过 ~10 天又死一遍）

根因是「token 到期要刷新，但国内刷不了 / 两地轮换打架」。固化原则：

- **一个账号只让一台干净出口机器（美国本机）持有 + 刷新**，只读同步给执行机（西安）。执行机只用、不刷。
- 本机刷新脚本 `~/bin/refresh-codex-tokens.sh` 历史上只覆盖 `for i in 1 2`，**team3/4/5 是孤儿** → 这就是它们到期没人续的原因。要根治就把它扩到 `1 2 3 4 5`，并确保 `sync-codex-tokens.sh` 把刷好的 token 推回西安（推送后 chmod 444 只读，防西安回写 rotate）。
- 同步用 §3c 的单文件 scp 即可应急；批量长期维护用现成的 `sync-codex-tokens.sh`。

> ⚠️ 提醒：team4/team5 的票只在西安、美国本机没有，到期（看 [[llm-quota]] 查 exp）会重蹈 T3 覆辙。
> 趁手时一并在美国本机把 4/5 也 `codex login` 一遍，让本机持有，纳入统一刷新。

---

## 5. 速查：常见报错 → 病因

| 现象 | 病因 | 动作 |
|------|------|------|
| `401 Missing bearer` | access_token 过期且没刷成 | §2b 测刷新 |
| `refresh_token_reused` | 票被轮换作废 | §3 重登 |
| `403 unsupported_country_region_territory` | 从被封 IP（国内/机房）连了登录端点 | 换干净出口（§0.4） |
| `usage limit / try again at...` | 账号额度满（**不是故障**） | 等窗口重置，或换别的账号 |
| login status 显示已登录但跑不了 | login status 只读文件、不验网络；token 可能已过期 | 别信它，按 §1 看真实 exp |

> 大原则：**`codex login status` 没有判别力**（只读 auth.json，不验证 token 是否过期/可用），别拿它当「能不能用」的依据。一切以 §1 的真实 exp + §2 的实测为准。
