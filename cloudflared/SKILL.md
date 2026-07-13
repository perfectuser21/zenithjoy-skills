---
name: cloudflared
description: >
  配置和使用 mac-mini-m4-us（美国 Mac mini M4，公网 38.23.47.81）的 SSH 快速连接（走 Cloudflare Tunnel，绕开中国电信 202.97 拥塞）。
  无论用户是否明说 "cloudflared"，只要涉及以下任一场景都要用本 skill：
  设置一台新电脑（Mac 或 Windows）连这台美国 Mac、SSH 连那台美国机很卡/连不上/timeout、
  配置或排查 slot / tslot / us-mac 这些 ssh host、cloudflared 装不上或报错、
  Cloudflare Tunnel 与 Tailscale 怎么选/有什么区别、SSH tunnel 报 503 或 websocket bad handshake、
  连接器（connector）down、轮换服务令牌（service token）、
  或用户问 "怎么连美国机器 / 为什么 SSH 卡 / 新机器怎么配"。
  涵盖：客户端配置（Mac/Windows）、服务端搭建与重建、Tailscale 兜底、国内下载绕行（COS）、故障排查。
---

# Cloudflared SSH 快路（mac-mini-m4-us）

## 这是什么

从国内（西安等）SSH 连美国机房的 `mac-mini-m4-us` 时，走 **Cloudflare Tunnel** 而不是 Tailscale 直连。

**为什么**：Tailscale 直连的数据面贴着中国电信 **202.97 国际骨干**跑，晚高峰拥塞，单程往返 ~253ms，SSH 逐字符回显非常卡。Cloudflare 走它自己的全球骨干，绕开 202.97，明显更跟手。

**核心原理（记住这一条就懂全部）**：隧道是**两边都"出站"到 Cloudflare 汇合**的——客户端出站连 Cloudflare，Mac 上的连接器也主动出站连 Cloudflare，Cloudflare 在中间对接。所以 **Mac 公网一个入站端口都不用开**（公网 22 一直被 pf 防火墙封死），照样能连。安全性也更高：要同时过 **Access 服务令牌 + SSH 公钥**两层。

## 关键标识（速查）

| 项 | 值 |
|---|---|
| 目标机 | mac-mini-m4-us，公网 38.23.47.81，Tailscale 100.71.151.105 |
| SSH 域名 | `ssh.zenjoymedia.media` |
| Tunnel | `vps-ssh-tunnel`，id `9cb079fa-7c9f-4896-898f-cd808d10c913` |
| CF 账号 | `1e06934c7e8134910ffcc5b7761fbc68` |
| Zone | `9a727922d105edee31731da20276e009`（zenjoymedia.media）|
| 连接器 | launchd `com.cloudflare.cloudflared-ssh`（Mac 上，开机自启）|
| 连接器日志 | `/Library/Logs/com.cloudflare.cloudflared-ssh.{err,out}.log` |
| Access 应用 | "VPS SSH (mac-mini-m4-us)"，id `eb5ef6e9-26ec-4241-9166-72faf5fdde66` |
| 服务令牌 | name `rog-xian-ssh`，token_id `e146d448-5b2f-4402-82d1-3096d96d356d` |
| Mac sshd | 仅公钥（关密码登录）|

**凭据位置**：CF 全权限 API token 在 1Password CS 金库 **"Cloudflare"** 条目 notesPlain 的 `Token:` 行（账号级 token，`/user/tokens/verify` 报错是正常的，账号级接口正常可用）。Notion/COS 等见 `credentials` / `device-transfer` skill。

## 三个 SSH 入口（客户端 ~/.ssh/config）

| 命令 | 走哪 | 速度 | 说明 |
|---|---|---|---|
| `ssh slot1` … `slot7` | **Cloudflare** | 🚀 | 日常入口，自动进对应 tmux 会话 |
| `ssh tslot1` … `tslot7` | Tailscale | 🐢 | 兜底（同一批 tmux 会话；需 Tailscale 开着）|
| `ssh us-mac` | Cloudflare | 🚀 | 不带 tmux 的普通登录 |

`slot*` 和 `us-mac` 用 `ProxyCommand cloudflared access ssh --hostname %h --service-token-id <ID> --service-token-secret <SECRET>`，靠服务令牌**免登录、免浏览器验证码**。
`slot*` 额外带 `RequestTTY yes` + `RemoteCommand env LANG=en_US.UTF-8 LC_CTYPE=en_US.UTF-8 tmux -u new -A -s slotN`。

> **WARP ≠ cloudflared**（最常见混淆）：WARP 是常驻 VPN App，slot 这条 SSH **不需要 WARP**。需要的是 `cloudflared` 命令行工具 + ssh config。

## mosh vs SSH（slot 用的是 SSH，不是 mosh）

slot / tslot / us-mac **全是纯 SSH**。tmux 是 SSH 连上后靠 `RemoteCommand ... tmux -u new -A -s slotN` 自动挂的，mosh 不参与。

**为什么走 Cloudflare 这条只能 SSH、不能 mosh**：mosh 的数据面走 **UDP**（60000-61000，SSH 只负责引导），而 Cloudflare 隧道只代理 **TCP**（到 `ssh://localhost:22`），UDP 穿不过去——所以 mosh 和 cloudflared 隧道天生不兼容。

**两种降低卡顿的思路（区别要讲清）**：

| 方案 | 路由 | 打字手感 | 输出/滚屏 |
|---|---|---|---|
| slot（Cloudflare + SSH，现状） | 真·改快（绕开 202.97） | 取决于真实延迟 | 快 |
| mosh over Tailscale | 没变（仍走 202.97 ~253ms） | 零延迟（本地预测回显藏住） | 仍有延迟 |

- **Cloudflare = 把路由真正改快**（连接/输出/滚屏全快），但没有本地预测回显。
- **mosh = 路由没变、靠预测回显把打字延迟藏起来**，需要 UDP 所以只能走 Tailscale。

实践：先用 slot（Cloudflare SSH）实测，若延迟够低则不需要 mosh。若仍嫌打字肉，可另配一套 **mosh 版 tslot**（mosh over Tailscale）做对比——服务端已装 mosh 1.4.0，客户端需 mosh-client（Windows 走 WSL）。

## 配置一台新机器

新机器需要三样：① 1Password（提供 SSH 公钥）② `cloudflared` 命令行 ③ ssh config（含服务令牌）。**不需要 WARP。**

### 新 Mac（更简单）

1. **cloudflared**：`brew install cloudflared`。国内慢就用清华/中科大 brew 镜像，或从 COS 下 macOS 版二进制（见下"国内下载绕行"）。
2. **SSH key**：1Password App → 设置 → 开发者 → 开启 **SSH agent**。key 在金库里自动同步、Mac 已授权（authorized_keys 里那把 1Password key），无感。Mac 上不用像 Windows 那样禁用系统 ssh-agent。
3. **ssh config**：把 slot/tslot/us-mac 那套写进 `~/.ssh/config`（可从 1Password 安全笔记取，或从已配好的机器复制）。

### 新 Windows PC

1. **cloudflared**：`winget install --id Cloudflare.cloudflared`。**国内大概率失败**（GitHub 被墙，报 `0x80072efd`）→ 走"国内下载绕行"。装完确认在 PATH（可把 `cloudflared.exe` 放某目录并把该目录加入用户 PATH）。
2. **SSH key**：装 1Password + 开 SSH agent。⚠️ Windows 须先**禁用系统自带 ssh-agent 服务**腾出命名管道（见 memory `reference_1password_ssh_agent_gui_key`）。若新机用的不是同一把已授权 key，要把新公钥加到 Mac 的 `~/.ssh/authorized_keys`。
3. **ssh config**：写到 `C:\Users\<你>\.ssh\config`。

### 让 Claude 远程代配（推荐）

如果新机已在 tailnet 里且能 `ssh <alias>` 进去，直接让 Claude：把 cloudflared 传过去（COS/scp）+ 写 ssh config + 验证。`xian-rog`（用户 asus）就是这么配好的。

## 国内下载绕行（cloudflared 拉不下来时）

国内机直接下 GitHub 必失败 → 触发 `device-transfer` skill。本质：**us-mac 访问 GitHub 正常**，所以：

1. **现成 COS 直链（已传，国内秒下）**：
   - Windows: `https://zenithjoy-static-1333590468.cos.ap-guangzhou.myqcloud.com/tools/cloudflared-windows-amd64.exe`
   - macOS (Apple Silicon): `https://zenithjoy-static-1333590468.cos.ap-guangzhou.myqcloud.com/tools/cloudflared-darwin-arm64`（已解压的二进制，下完 `chmod +x` 直接用）
   - macOS 也可直接 `brew install cloudflared`（多数情况能成）。
   - 失效/要别的平台版就重新下 + 传：GitHub `https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-<platform>`（windows-amd64.exe / darwin-arm64.tgz），us-mac 下好后 `coscmd upload <file> /tools/<name>`。
2. 或直传：**us-mac → 西安**经 Tailscale `scp`（~0.5MB/s，52MB 约几分钟）。
3. 放到位（重命名 `cloudflared.exe`）+ 把所在目录加进 PATH（或在 ssh config 的 ProxyCommand 写完整路径）。

## 服务端搭建 / 重建

详细 CF API 命令见 `references/server-rebuild.md`。要点（最易踩的坑放最前）：

1. **ingress 必须显式 PUT**：token 模式连接器不会自动带 ingress，否则报 "No ingress rules → 503 / websocket: bad handshake"。`PUT /accounts/<acc>/cfd_tunnel/<id>/configurations` 写 `ssh.zenjoymedia.media → ssh://localhost:22`（+ catch-all 404），再 `sudo launchctl kickstart -k system/com.cloudflare.cloudflared-ssh` 重启连接器。
2. **DNS**：CNAME `ssh` → `<tunnel-id>.cfargotunnel.com`（proxied）。
3. **连接器**：launchd plist 跑 `cloudflared tunnel --no-autoupdate run --token <tunnel-token>`（token 从 `GET /cfd_tunnel/<id>/token`）。
4. **Access**：self_hosted 应用绑域名 + 策略（身份 `xuxiao21xx@icloud.com` / IdP onetimepin + 服务令牌 non_identity）。

## 故障排查

| 症状 | 原因 | 处理 |
|---|---|---|
| `websocket: bad handshake` / GET 返回 503 | 连接器没加载 ingress | API PUT ingress + `launchctl kickstart -k`（见上）|
| 302 跳 `cloudflareaccess.com/login` | 服务令牌没被接受 / 刚改没传播 | 等 ~1 分钟传播；确认令牌没过期；JWT meta 看 `service_token_status` |
| `Permission denied (publickey)` | 到了 sshd 但没钥匙 | **路径是通的！** 用有 1Password key 的 GUI 会话连即可；非交互会话拿不到 1Password key |
| `Cannot execute command-line and remote command` | slot 已设 RemoteCommand，又额外传了命令 | 正常，别再附加命令 |
| Claude 从 us-mac `ssh xian-rog` 超时 | 那台把 **Tailscale 关了** | 让用户开回 Tailscale（也恢复 tslot 兜底）|
| cloudflared 装不上（国内） | GitHub 被墙 0x80072efd | 见"国内下载绕行" |
| **国内连接器连不上 / `QUIC: timeout` / `Failed to dial quic`** | GFW 挡 QUIC(UDP) | **连接器加 `--protocol http2`(走 TCP)**。美国机不用，国内机(如 xian-m4)必须。改 launchd plist 的 ProgramArguments 加 `--protocol http2` 再 bootout+bootstrap。precheck 可能报 hard_fail，但只要日志出现 `Registered tunnel connection ... protocol=http2` 就是连上了 |

## 已有的隧道（多机）

| 机器 | 隧道 | SSH 域名 | 连接器协议 |
|---|---|---|---|
| mac-mini-m4-us（美国） | vps-ssh-tunnel `9cb079fa…` | `ssh.zenjoymedia.media` | QUIC（默认） |
| mac-mini-m4-xian（西安，给同事用） | xian-ssh-tunnel `535e3e3e…` | `ssh-xian.zenjoymedia.media` | **http2**（国内必须） |

每台客户端/每个同事建独立服务令牌（可单独吊销），配置可存 1Password 安全笔记。同事走本地 key（不用 1Password），公钥加到目标机 authorized_keys 即可。

## 给同事/新用户开通访问（不用 Tailscale、不用 1Password）

适用场景：同事和目标机不在同一网络，原来只能靠 Tailscale。改用 Cloudflare 隧道后，同事从任何地方都能连，且不用装 Tailscale/WARP，也不用 1Password。

**服务端（你/Claude 做，用 CF API）：**
1. 确认目标机已有隧道（us=`ssh.zenjoymedia.media`，xian=`ssh-xian.zenjoymedia.media`）；没有就按"服务端搭建"建。
2. 建**该同事专属**服务令牌：`POST /accounts/<acc>/access/service_tokens {"name":"<谁>-ssh"}`。
3. 把令牌加进该机 Access 应用的策略：`non_identity` + `service_token`。
4. 把同事 ssh config（`Host <alias>` → HostName=该机域名 + User + `ProxyCommand cloudflared access ssh --hostname %h --service-token-id <CID> --service-token-secret <CSEC>`）存进 1Password 安全笔记，发给同事。
5. 同事发来公钥后，加到目标机的 `~/.ssh/authorized_keys`（共用现有账号，或 `sysadminctl`/系统设置建独立用户更干净、好审计）。

**客户端（同事做）：**
1. 装 cloudflared（Windows: COS 直链；Mac: brew）。**不用 WARP。**
2. `ssh-keygen -t ed25519`，把 `~/.ssh/id_ed25519.pub` 发给你。
3. 把 1Password 笔记里的 config 贴到 `~/.ssh/config`。
4. `ssh <alias>` 连上。

**吊销**：删该同事的服务令牌（`DELETE .../service_tokens/<id>`）+ 从目标机 authorized_keys 删他的公钥。

**已建的 1Password 配置笔记**（CS 金库）：`SSH-CloudflareTunnel-newpc 配置`（Windows 新机）、`SSH-Xian-同事配置(xianmac)`（同事连西安机，User=jinnuoshengyuan）。

## 工具怎么选：连机器 vs 翻墙（别同时开多个 VPN 互相抢）

"折腾/卡"的根源 = 同时开了多个"接管全部流量"的工具（Tailscale exit node / WARP / Clash），它们互相抢路由。**拆成两件独立的事就清爽：**

| 需求 | 用什么 | 影响正常上网吗 |
|---|---|---|
| 连西安自己的机器（M4 等） | **Tailscale（关 exit node）** | ❌ 不影响 |
| 连美国 Mac / 给同事 | **slot（Cloudflare cloudflared）** | ❌ 不影响 |
| 翻墙（Google/YouTube 等） | **Clash（rule 模式）** | 只代理被墙站点，国内直连 |

- **不要用 Tailscale exit node**：把全部流量绕去美国，是"上网卡"的元凶；翻墙交给 Clash。
- **不要再用 WARP**：当初只为连美国 Mac 公网，已被 slot 取代。
- 日常常开：**Tailscale（关 exit node）+ Clash（rule）**，两者共存不打架（Tailscale 关 exit node 只管 `100.x`，不碰普通上网）。
- 坑：Clash TUN 模式若把 `100.x` 也抓走导致 Tailscale 连不上 → Clash 直连/绕过规则加 `100.64.0.0/10`。

## 速度真相（同城别用 Cloudflare）

- **西安↔西安 走 Tailscale**：直连本地局域网（`192.168.3.x`），实测 **16~64ms**。点对点不经 exit node，所以 M4 的美国 exit node 不影响同城互联。
- **西安↔西安 走 `xian-m4c`(Cloudflare)**：连接器锚在 San Jose（国内 QUIC 被墙、http2 只连得上美国边缘），流量绕美国一圈，**~600ms（慢 10~40 倍）**。
- **客户端位置对 `xian-m4c` 的影响**（连接器锚 San Jose，所以 San Jose→西安 这段跨太平洋雷打不动都有）：美国客户端最快（单次跨太平洋 ~380ms）、国内/香港最慢（双次跨 ~600ms）——反直觉，**美国连反而最快**。
- **结论**：同城 / 能上 Tailscale → 一律用 Tailscale（`xian-m4`，快几十倍）；`xian-m4c`(Cloudflare) 只留给**不能上 Tailscale 的人**（同事、远程）兜底。

## 轮换服务令牌（密钥泄露/定期）

`POST /accounts/<acc>/access/service_tokens/e146d448.../rotate` → 返回新 client_id + client_secret。更新所有客户端 ssh config 里的 `--service-token-id/--service-token-secret`（策略引用的是 token_id，不变，不受轮换影响）。新密钥**别打印**到日志/终端（用 base64 / `powershell -EncodedCommand` 之类传给远端写入）。

## 相关

- memory：`project_mac_mini_m4_us_ssh_fastpath`、`project_mac_mini_m4_us_security`、`reference_1password_ssh_agent_gui_key`
- skill：`device-transfer`（国内传文件）、`credentials`（取凭据）
- 详细服务端命令：`references/server-rebuild.md`
