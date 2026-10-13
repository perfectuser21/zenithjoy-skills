---
name: device-transfer
description: "选择设备间传文件、跨国传输、GitHub 拉取、插件分发、COS 或 NAS 的通道，排查传输慢和网络超时。涉及跨设备传输或依赖下载故障时使用。"
---

# 数据传输决策 Skill

## 第一步：确认传输类型

```
A. 代码 / GitHub clone / pull
B. 插件 / 配置文件 / 内部工具分发（自己用）
C. 客户交付（视频 / 图片 / 成品）
D. 设备之间传自用文件（日志、模型、二进制等）
```

---

## A 类：代码 / GitHub

### 从西安设备拉 GitHub（最常见痛点）

**问题**：不开 exit node → GitHub 超慢/超时；开 exit node → COS 废了

**方案一（日常推荐）：临时开 exit node，拉完关**
```bash
sudo tailscale set --exit-node=100.86.118.99   # 开 HK exit node
git clone https://github.com/...
git pull
sudo tailscale set --exit-node=                 # 拉完立即关（否则 COS 废）
```

**方案二（一劳永逸，不用切 exit node）：git 走美国代理**

在 us-mac 上开 SOCKS5（只需配一次，开机自启）：
```bash
# us-mac 执行
ssh -D 100.71.151.105:1080 -N -f administrator@localhost
```

在每台西安机器上配 git（只需配一次）：
```bash
git config --global http.proxy socks5h://100.71.151.105:1080
git config --global https.proxy socks5h://100.71.151.105:1080
```
配完后 exit node 随便开关，git 永远走美国出口。

### 从 us-mac 拉 GitHub
直接拉，无需任何配置。

### 西安机器之间同步代码
直接 SCP 或 git remote，Tailscale 直连即可：
```bash
scp -r /path/to/project jinnuoshengyuan@100.86.57.69:/path/
```

---

## B 类：插件 / 内部工具分发

插件通常是自己的机器下载自己的工具，走 COS 分发（统一入口，和客户交付用同一套）：

```bash
# 上传（西安机器，先关 exit node）
sudo tailscale set --exit-node=
source ~/.credentials/tencent-cloud.env
coscmd config -a $TENCENT_SECRET_ID -s $TENCENT_SECRET_KEY -b zenithjoy-static-1333590468 -r ap-guangzhou
coscmd upload /path/plugin /plugins/$(basename /path/plugin)

# 任意设备下载（国内关 exit node，美国无需管）
curl -L "https://zenithjoy-static-1333590468.cos.ap-guangzhou.myqcloud.com/plugins/filename" -o /local/path
```

---

## C 类：客户交付（视频 / 图片）

永远走 COS，上传后给客户公网 URL：

```bash
sudo tailscale set --exit-node=          # 国内机器先关 exit node
source ~/.credentials/tencent-cloud.env
coscmd config -a $TENCENT_SECRET_ID -s $TENCENT_SECRET_KEY -b zenithjoy-static-1333590468 -r ap-guangzhou
coscmd upload "$1" "/publish/$(basename $1)"
echo "客户链接：https://zenithjoy-static-1333590468.cos.ap-guangzhou.myqcloud.com/publish/$(basename $1)"
```

---

## D 类：设备之间传自用文件

### 决策矩阵

| 方向 | 大小 | 时间 | 最优路径 | 速度 |
|------|------|------|---------|------|
| 西安内部任意设备 | < 100MB | 随时 | Tailscale SCP 直连 | 4~11 MB/s |
| 西安内部任意设备 | ≥ 100MB | 随时 | NAS 中转 | 40~46 MB/s |
| 西安 → us-mac | < 10MB | 随时 | Tailscale 直连 SCP | 0.5 MB/s |
| 西安 → us-mac | 10MB~500MB | 白天（要快） | 接力中转 | ~4 MB/s |
| 西安 → us-mac | 10MB~500MB | 晚上（不急） | Tailscale 直连 SCP | 0.5 MB/s，睡觉前开着跑 |
| 西安 → us-mac | > 500MB | 随时 | COS | 看 COS 速度 |
| us-mac → 西安 | 任意 | 随时 | COS（接力反向 0.27 MB/s 更慢）| 看 COS 速度 |
| 任意 ↔ HK/US VPS | 任意 | 随时 | Tailscale SCP 直连 | 9~31 MB/s |
| hk-vps → xian-pc/rog（Windows）| 任意 | 随时 | hk-vps 上传 COS → xian curl 下载 | hk-vps→COS ~300KB/s，COS→xian 快 |

### 西安内部传输命令

```bash
# m4 ↔ m1（直连 10.8 MB/s）
scp /path/file xx-macmini@100.88.166.55:/path/
scp /path/file jinnuoshengyuan@100.86.57.69:/path/

# m1/m4 ↔ xian-pc（别名已配）
scp /path/file xian-pc:C:/path/       # 用户名 xuxia，已配 ~/.ssh/config

# m1/m4 ↔ xian-rog（别名已配）
scp /path/file xian-rog:C:/path/      # 用户名 asus，已配 ~/.ssh/config

# m1/m4 → NAS（大文件，40~46 MB/s）
mkdir -p /tmp/nas-mount
mount_smbfs "//%E5%BE%90%E5%95%B8:895211XxXx@192.168.3.50/ZenithJoy-%E7%9F%AD%E8%A7%86%E9%A2%91" /tmp/nas-mount
cat /path/file > /tmp/nas-mount/transfer/filename    # 用 cat 不用 cp（SMB xattr 问题）
diskutil unmount /tmp/nas-mount
```

### 西安 → us-mac 接力中转（白天，~4 MB/s）

```bash
# 三步接力：西安→HK（4MB/s）→USVPS（9MB/s）→us-mac（31MB/s）
FILE=/path/to/file
scp $FILE root@100.86.118.99:/tmp/
ssh root@100.86.118.99 "scp /tmp/$(basename $FILE) root@100.79.41.61:/tmp/"
ssh root@100.79.41.61 "scp /tmp/$(basename $FILE) administrator@100.71.151.105:/local/"
```

### us-mac → 西安（COS 路径）

```bash
# us-mac 上传（美国机器不用管 exit node）
source ~/.credentials/tencent-cloud.env
coscmd config -a $TENCENT_SECRET_ID -s $TENCENT_SECRET_KEY -b zenithjoy-static-1333590468 -r ap-guangzhou
coscmd upload /local/file /temp/$(basename /local/file)

# 西安任意机器下载（先关 exit node）
sudo tailscale set --exit-node=
curl -L "https://zenithjoy-static-1333590468.cos.ap-guangzhou.myqcloud.com/temp/filename" -o /local/path
```

---

## 设备全景

### 西安办公室（192.168.3.x）

| 设备 | SSH | Tailscale IP | 角色 |
|------|-----|-------------|------|
| Mac mini M4 | `jinnuoshengyuan@100.86.57.69` | 100.86.57.69 | 主力，Codex |
| Mac mini M1 | `xx-macmini@100.88.166.55` | 100.88.166.55 | content-service |
| NAS (Synology) | — | 100.110.241.76 | 存储，有线千兆 |
| xian-pc (Win) | `xuxia@100.97.242.124`（不是 worker/Administrator！）| 100.97.242.124 | Playwright |
| xian-rog (Win) | `asus@100.98.253.95` | 100.98.253.95 | Agent 部署 |
| MacBook Air | Tailscale（不常开）| — | 偶尔使用 |

> ⚠️ xian-pc / xian-rog 在 **192.168.1.x**（不同子网），m1/m4 只能通过 Tailscale 访问，不能用局域网 IP。
> m1/m4 的 `~/.ssh/config` 已配 `xian-pc` 和 `xian-rog` 别名，直接 `scp xian-pc:...` 即可。

**NAS 凭据**：用户名 `%E5%BE%90%E5%95%B8`（徐啸），密码 `895211XxXx`，Share `ZenithJoy-%E7%9F%AD%E8%A7%86%E9%A2%91`

**西安 WiFi**：`华为306-5G`（5GHz），密码 `lj123456`。切换命令：
```bash
networksetup -setairportnetwork en1 "华为306-5G" lj123456
```

### 海外节点

| 设备 | SSH | Tailscale IP | 公网 IP |
|------|-----|-------------|--------|
| us-mac（主力研发）| 本机 / `administrator@100.71.151.105` | 100.71.151.105 | 38.23.47.81 |
| hk-vps | `root@100.86.118.99` | 100.86.118.99 | 124.156.138.116 |
| us-vps（exit node）| `root@100.79.41.61` | 100.79.41.61 | 134.199.234.147 |

### COS（腾讯对象存储）

- Bucket：`zenithjoy-static-1333590468`，Region：`ap-guangzhou`，public-read
- URL：`https://zenithjoy-static-1333590468.cos.ap-guangzhou.myqcloud.com/<path>`
- 凭据：`source ~/.credentials/tencent-cloud.env`

**凭据文件可能为空或不存在，用前先验证：**
```bash
source ~/.credentials/tencent-cloud.env && echo $TENCENT_SECRET_ID
# 如果输出为空，从 1Password 重新拉：
source ~/.credentials/1password.env && export OP_SERVICE_ACCOUNT_TOKEN
eval "$(op item get "Tencent Cloud (腾讯云)" --vault CS --format json | \
  python3 -c "
import json,sys,re
d=json.load(sys.stdin)
notes=next(f['value'] for f in d['fields'] if f['id']=='notesPlain')
for m in re.finditer(r'(TENCENT_VPS_SECRET_(?:ID|KEY))=(\S+)', notes):
    print(f'export TENCENT_SECRET_{m.group(1).split(\"_\")[-1]}={m.group(2)}')
")"
# 写入文件备用
echo "export TENCENT_SECRET_ID=$TENCENT_SECRET_ID" > ~/.credentials/tencent-cloud.env
echo "export TENCENT_SECRET_KEY=$TENCENT_SECRET_KEY" >> ~/.credentials/tencent-cloud.env
```

---

## Exit Node 规则

| 操作 | Exit Node 状态 | 原因 |
|------|-------------|------|
| GitHub clone/pull（方案一）| **开 HK**（100.86.118.99）| GitHub 需要翻墙 |
| COS 上传/下载 | **关闭**（`sudo tailscale set --exit-node=`）| exit node 开着 COS 变 27KB/s |
| Tailscale SCP（设备间）| **无所谓**，Tailscale peer traffic 不走 exit node | |
| 接力中转 | **无所谓** | 都是 Tailscale 直连 |

---

## 速度参考（全部实测，2026-05-20）

| 路径 | 速度 | 备注 |
|------|------|------|
| m4 → NAS（SMB，5GHz WiFi） | **40 MB/s** | |
| m1 → NAS（SMB，5GHz WiFi） | **46 MB/s** | |
| m4 → m1（Tailscale SCP） | **10.8 MB/s** | |
| m1/m4 → xian-pc/rog（Tailscale SCP）| **4~5 MB/s** | |
| xian-m4 → hk-vps | **4 MB/s** | 出境畅通 |
| hk-vps → xian-m4 | **0.27 MB/s** | GFW 入境限速 |
| hk-vps → us-vps | **30.6 MB/s** | 机房对机房 |
| us-vps → hk-vps | **9.2 MB/s** | |
| us-vps → us-mac | **31 MB/s** | 同国直连 |
| us-mac → us-vps | **21.6 MB/s** | |
| hk-vps → us-mac（直连）| **0.25 MB/s** | 跨太平洋打普通 ISP 慢 |
| xian → us-mac（直连）| **0.5 MB/s** | 同上 |
| **xian → HK → USVPS → us-mac（接力）** | **~4 MB/s** | 快 8 倍，瓶颈在第一段 |
| m4 → COS（exit node 关）| **2~33 MB/s** | 国内直连 |
| m4 → COS（exit node 开）| **27 KB/s** | 完全不可用 |

**跨太平洋规律**：出中国快（4 MB/s），进中国慢（0.27 MB/s，GFW 限速）。VPS 机房对机房快（9~30 MB/s），任何→us-mac 直连慢（0.25~0.5 MB/s，ISP 入向限制）。

---

## 常见坑

| 症状 | 原因 | 解法 |
|------|------|------|
| GitHub 超时/极慢 | exit node 关闭，GFW 拦截 | 临时开 HK exit node，或配 git proxy |
| COS 上传只有 27KB/s | exit node 开着 | `sudo tailscale set --exit-node=` |
| NAS mount Authentication error | 用了错误用户名 | 必须用 `%E5%BE%90%E5%95%B8`（徐啸）+ `895211XxXx` |
| NAS mount 卡死（UN 进程）| SMB 断联 | `diskutil unmount force /tmp/nas-mount`（等 5 分钟或强制）|
| `cp` 从 NAS 报 xattr 错误 | SMB 不支持 macOS 扩展属性 | 用 `cat src > dst` 替代 `cp` |
| SSH 到 xian-pc 连接重置 | 用了 worker/Administrator | 必须用 `ssh xuxia@100.97.242.124` |
| m1/m4 网络超慢 | 连的 2.4GHz 华为306 | `networksetup -setairportnetwork en1 "华为306-5G" lj123456` |
| Chrome 在 SSH 下被 SIGKILL | macOS 无 GUI session | `nohup bash -c 'exec "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new ... 2>&1' > log &` |
| HK VPS → 西安接力比直连慢 | GFW 入境限速（0.27 MB/s）| 接力只对出中国有效，进中国走 COS |
| hk-vps 上传 COS 慢（~300KB/s）| 用了 `cos.accelerate.myqcloud.com`，反而绕远 | hk-vps 物理近 Guangzhou，不加 `-e` 用默认直连节点 `cos.ap-guangzhou.myqcloud.com` |

---

## 快速决策卡

```
GitHub 拉代码（西安）  → 开 exit node(HK) 拉，拉完关；或配 git proxy 一劳永逸
插件/工具分发          → COS 上传，curl 下载
客户交付视频图片       → COS + 公网 URL
西安内部 < 100MB       → Tailscale SCP 直连
西安内部 ≥ 100MB       → NAS（40~46 MB/s）
西安 → us-mac（白天）  → 接力中转（~4 MB/s）
西安 → us-mac（晚上）  → 直连 SCP（0.5 MB/s，睡觉前跑）
us-mac → 西安          → COS（唯一可用快速路径）
涉及 COS               → 先确认 exit node 已关
hk-vps → Windows 机器  → hk-vps 上传 COS（不加 -e），xian-pc/rog 用 curl 下载
COS 凭据为空/不存在    → 从 1Password "Tencent Cloud (腾讯云)" notesPlain 拿 VPS key
```

## 触发范围与原运行约束

设备之间的数据传输决策。涉及以下任何场景时必须先读这个 skill：
触发词：传文件、下载、上传、SCP、GitHub 拉代码、插件分发、COS、怎么把X传到Y、
设备之间传、速度慢、exit node、NAS 挂载、跨国传输、
下载失败、拉不下来、下载超慢、下载不了、timeout、Connection refused、timed out、
apt 慢、pip 慢、npm 慢、curl 失败、wget 失败、安装超时、网络超时、连不上、
GitHub releases 下载、从外网拿、国内访问不了。
