# 将 80MB 插件从 m4 分发到 xian-pc 的方案

## 推荐方案：scp 直传（最简单）

```bash
# 在 m4 上执行
scp /path/to/plugin.zip xian-pc:/path/to/destination/
```

如果 xian-pc 的 SSH 端口或用户名有特殊配置：
```bash
scp -P 22 /path/to/plugin.zip user@xian-pc:/C/path/to/destination/
```

---

## 备选方案

### 方案 2：rsync（支持断点续传，适合不稳定网络）

```bash
# 在 m4 上执行
rsync -avz --progress /path/to/plugin.zip xian-pc:/path/to/destination/
```

### 方案 3：Python 临时 HTTP 服务器（不需要 SSH）

```bash
# 在 m4 上，进入插件所在目录，启动临时 HTTP 服务
cd /path/to/plugin/directory
python3 -m http.server 8080

# 在 xian-pc 上，用浏览器或 curl/wget 下载
# 浏览器访问：http://<m4的局域网IP>:8080/plugin.zip
# 或命令行：
curl -O http://<m4的局域网IP>:8080/plugin.zip
```

### 方案 4：SSH 反向代理（如果 m4 无法直连 xian-pc）

```bash
# 在 xian-pc 上主动拉取（xian-pc 连 m4）
scp m4:/path/to/plugin.zip C:\path\to\destination\
```

---

## 选择建议

| 场景 | 推荐方案 |
|------|---------|
| 两台机器在同一局域网，SSH 通 | scp（最快最简单） |
| 网络不稳定，怕中断 | rsync |
| xian-pc 没有 SSH 服务，只有浏览器 | Python HTTP 服务器 |
| m4 无法主动连 xian-pc | 在 xian-pc 上反向拉取 |

80MB 文件用 scp 局域网传输通常 10 秒内完成，直接用方案 1 即可。
