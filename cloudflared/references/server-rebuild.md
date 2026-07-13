# 服务端搭建 / 重建详细命令

从零（或修复）把 `ssh.zenjoymedia.media` 的 Cloudflare SSH Tunnel 跑起来。所有命令在 **mac-mini-m4-us** 上执行。

## 0. 取 CF API token + 公共变量

```bash
source ~/.credentials/1password.env && export OP_SERVICE_ACCOUNT_TOKEN
TOKEN=$(op item get "Cloudflare" --vault CS --format json | python3 -c "import sys,json,re
for f in json.load(sys.stdin).get('fields',[]):
 if f.get('label')=='notesPlain':
  m=re.search(r'Token:\s*([A-Za-z0-9_-]{40})',f.get('value') or ''); print(m.group(1) if m else '')")
H="Authorization: Bearer $TOKEN"
ACC=1e06934c7e8134910ffcc5b7761fbc68
TID=9cb079fa-7c9f-4896-898f-cd808d10c913   # vps-ssh-tunnel
ZONE=9a727922d105edee31731da20276e009       # zenjoymedia.media
APP=eb5ef6e9-26ec-4241-9166-72faf5fdde66    # Access 应用 "VPS SSH"
```

> 该 token 是**账号级**：`/user/tokens/verify` 会报 `Invalid API Token`，但 `/accounts/...` 接口正常——这是预期，不要被 verify 误导。

## 1. 列出 tunnel（确认 vps-ssh-tunnel 在）

```bash
curl -s "https://api.cloudflare.com/client/v4/accounts/$ACC/cfd_tunnel?is_deleted=false" -H "$H" \
 | python3 -c "import sys,json;[print(t['name'],t['id'],t['status']) for t in json.load(sys.stdin)['result']]"
```

## 2. DNS：ssh → tunnel（proxied）

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records" -H "$H" \
 -H "Content-Type: application/json" \
 --data "{\"type\":\"CNAME\",\"name\":\"ssh\",\"content\":\"${TID}.cfargotunnel.com\",\"proxied\":true}"
```

## 3. ingress（最关键，token 连接器必须显式 PUT）

```bash
curl -s -X PUT "https://api.cloudflare.com/client/v4/accounts/$ACC/cfd_tunnel/$TID/configurations" -H "$H" \
 -H "Content-Type: application/json" \
 --data '{"config":{"ingress":[{"hostname":"ssh.zenjoymedia.media","service":"ssh://localhost:22"},{"service":"http_status:404"}]}}'
```

## 4. 启动 / 持久化连接器（launchd）

取 tunnel 运行 token：
```bash
SSHTOKEN=$(curl -s "https://api.cloudflare.com/client/v4/accounts/$ACC/cfd_tunnel/$TID/token" -H "$H" \
 | python3 -c "import sys,json;print(json.load(sys.stdin)['result'])")
```

写 `/Library/LaunchDaemons/com.cloudflare.cloudflared-ssh.plist`（ProgramArguments：
`/opt/homebrew/bin/cloudflared tunnel --no-autoupdate run --token <SSHTOKEN>`，
`RunAtLoad`/`KeepAlive` true，日志 `/Library/Logs/com.cloudflare.cloudflared-ssh.{err,out}.log`），然后：

```bash
sudo launchctl bootstrap system /Library/LaunchDaemons/com.cloudflare.cloudflared-ssh.plist
# 改了 ingress / plist 后让它重新拉配置：
sudo launchctl kickstart -k system/com.cloudflare.cloudflared-ssh
```

验证连接器加载了 ingress：
```bash
grep -a "Updated to new configuration" /Library/Logs/com.cloudflare.cloudflared-ssh.err.log | tail -1
# 应看到 ingress: ssh.zenjoymedia.media -> ssh://localhost:22
```

## 5. Access 应用 + 策略

```bash
# 自托管应用
APPID=$(curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$ACC/access/apps" -H "$H" \
 -H "Content-Type: application/json" \
 --data '{"name":"VPS SSH (mac-mini-m4-us)","domain":"ssh.zenjoymedia.media","type":"self_hosted","session_duration":"730h","app_launcher_visible":false,"auto_redirect_to_identity":true}' \
 | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['id'])")

# 策略 1：允许身份（人，邮箱验证码登录）
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$ACC/access/apps/$APPID/policies" -H "$H" \
 -H "Content-Type: application/json" \
 --data '{"name":"Allow owner","decision":"allow","include":[{"email":{"email":"xuxiao21xx@icloud.com"}}]}'

# 策略 2：允许服务令牌（机器免登录）
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$ACC/access/apps/$APPID/policies" -H "$H" \
 -H "Content-Type: application/json" \
 --data '{"name":"svc-rog","decision":"non_identity","include":[{"service_token":{"token_id":"e146d448-5b2f-4402-82d1-3096d96d356d"}}]}'
```

## 6. 验证

```bash
# Access 是否接受服务令牌（503=穿过 Access 打到 SSH 后端=对；302=被拒）
curl -s -o /dev/null -w "%{http_code}\n" \
 -H "CF-Access-Client-Id: <CID>" -H "CF-Access-Client-Secret: <CSEC>" https://ssh.zenjoymedia.media

# 端到端（客户端）：到 sshd 报 publickey 即全链路通
ssh -o PreferredAuthentications=publickey us-mac
```

## 7. 客户端 ssh config 模板

```
Host slot1
    RemoteCommand env LANG=en_US.UTF-8 LC_CTYPE=en_US.UTF-8 tmux -u new -A -s slot1
# … slot2-7 同理 …
Host slot*
    HostName ssh.zenjoymedia.media
    User administrator
    RequestTTY yes
    ProxyCommand cloudflared access ssh --hostname %h --service-token-id <CID> --service-token-secret <CSEC>

Host tslot1
    RemoteCommand env LANG=en_US.UTF-8 LC_CTYPE=en_US.UTF-8 tmux -u new -A -s slot1
# … tslot2-7 同理（会话名复用 slotN）…
Host tslot*
    HostName 100.71.151.105
    User administrator
    RequestTTY yes

Host us-mac
    HostName ssh.zenjoymedia.media
    User administrator
    ProxyCommand cloudflared access ssh --hostname %h --service-token-id <CID> --service-token-secret <CSEC>
```

Windows 上 cloudflared 不在 PATH 时，把 ProxyCommand 里的 `cloudflared` 换成完整路径（如 `C:\Users\asus\cloudflared.exe`）。
