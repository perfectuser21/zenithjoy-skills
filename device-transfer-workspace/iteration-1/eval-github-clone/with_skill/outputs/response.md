# 西安 m4 上 GitHub clone timeout 解决方案

这是典型的 A 类问题：**西安设备拉 GitHub 被 GFW 拦截**。有两个方案，推荐先用方案一快速解决，再用方案二一劳永逸。

---

## 方案一（日常推荐）：临时开 HK exit node，拉完立即关

```bash
# 第一步：开 HK exit node
sudo tailscale set --exit-node=100.86.118.99

# 第二步：正常 clone
git clone https://github.com/你的仓库地址

# 第三步：拉完立即关！！（不关的话 COS 上传会变成 27KB/s，完全废掉）
sudo tailscale set --exit-node=
```

**注意**：exit node 开着时 COS 上传/下载会从 2~33 MB/s 直接跌到 27KB/s，所以 clone 完务必立即关掉。

---

## 方案二（一劳永逸）：让 git 永远走美国代理，不再需要切 exit node

**第一步：在 us-mac 上开 SOCKS5 隧道（只需配一次，开机自启）**

```bash
# 在 us-mac 上执行
ssh -D 100.71.151.105:1080 -N -f administrator@localhost
```

**第二步：在 xian-m4 上配 git 代理（只需配一次）**

```bash
# 在 xian-m4 上执行
git config --global http.proxy socks5h://100.71.151.105:1080
git config --global https.proxy socks5h://100.71.151.105:1080
```

配完之后，exit node 随便开关，git clone/pull 永远走美国出口，不再 timeout，也不影响 COS。

---

## 根本原因

西安不开 exit node → GitHub 直连走 GFW → 超时/极慢。
开了 exit node → GitHub 正常 → 但 COS 变 27KB/s。
方案二的 git proxy 绕开了这个矛盾，两者互不干扰。
