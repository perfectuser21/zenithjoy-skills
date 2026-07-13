# 西安 m4 git clone GitHub 仓库 timeout 解决方案

## 根本原因

国内（西安）访问 GitHub 直连经常被墙或限速，导致 TCP 连接 timeout。

---

## 方案一：走代理（推荐，最稳）

如果 m4 上已有代理（Clash/Surge/V2Ray 等），先确认代理端口，然后：

```bash
# 查代理监听端口（常见 7890 或 1080）
# Clash 默认 HTTP 代理 7890，SOCKS5 代理 7891

# 方式 A：临时为当前 shell 设置代理
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7891

git clone https://github.com/xxx/yyy.git

# 方式 B：只为这一条 git 命令设置代理
git -c http.proxy=http://127.0.0.1:7890 clone https://github.com/xxx/yyy.git
```

完成后清除临时代理：
```bash
unset https_proxy http_proxy all_proxy
```

或者永久写入 git 配置（只影响 git，不影响系统）：
```bash
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
# 以后不需要时取消：
# git config --global --unset http.proxy
# git config --global --unset https.proxy
```

---

## 方案二：SSH 替代 HTTPS

HTTPS 走 443 端口容易被 QoS 限速，SSH 走 22 端口有时更稳。

```bash
# 前提：已在 GitHub 账号添加 m4 的 SSH 公钥
# 查看公钥（没有则先生成）
cat ~/.ssh/id_rsa.pub || cat ~/.ssh/id_ed25519.pub

# 生成（如果没有）
ssh-keygen -t ed25519 -C "xian-m4" -f ~/.ssh/id_ed25519

# 测试 SSH 连通性
ssh -T git@github.com

# 用 SSH 协议 clone
git clone git@github.com:xxx/yyy.git
```

如果 22 端口也被封，GitHub 支持 SSH over HTTPS（443 端口走 SSH）：

```bash
# ~/.ssh/config 添加：
cat >> ~/.ssh/config << 'EOF'
Host github.com
  Hostname ssh.github.com
  Port 443
  User git
EOF

# 再测试
ssh -T git@github.com
```

---

## 方案三：加大超时 + 关闭压缩（弱网下有效）

```bash
git clone \
  --config http.lowSpeedLimit=1000 \
  --config http.lowSpeedTime=60 \
  --depth=1 \
  https://github.com/xxx/yyy.git
```

- `--depth=1`：只拉最新一次提交，大幅减少数据量
- `lowSpeedTime=60`：60 秒内速度低于 1000 字节/秒才算 timeout（默认 10 秒）

---

## 方案四：从 HK VPS 中转 clone 再传回来

如果以上都不行，借助 hk-vps（香港，网络好）中转：

```bash
# 在 hk-vps 上 clone 并打包
ssh hk-vps "git clone --depth=1 https://github.com/xxx/yyy.git /tmp/yyy && cd /tmp && tar czf yyy.tar.gz yyy"

# 把压缩包拉回 m4
scp hk-vps:/tmp/yyy.tar.gz ~/Desktop/

# 本地解压
tar xzf ~/Desktop/yyy.tar.gz
```

---

## 快速排查命令

```bash
# 测试 443 端口是否通
nc -zv github.com 443

# 测试 DNS 是否正常解析
nslookup github.com 8.8.8.8

# 抓包看卡在哪（需要 sudo）
curl -v --max-time 10 https://github.com 2>&1 | head -30
```

---

## 推荐顺序

1. **先检查 m4 上是否已有代理软件（Clash/Surge）在跑** → 方案一
2. 代理没有 → 用 **SSH over HTTPS（方案二 + 443 端口）**
3. 还不行 → **hk-vps 中转（方案四）** 最保险
