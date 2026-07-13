# 2GB 模型文件从 us-mac 传到 xian-m4 最快方案

## 核心判断

跨国传输（美国 → 中国西安），瓶颈是国际带宽，不是本地网络。最快方案取决于两台机器是否能直接 SSH 互通。

---

## 方案一：rsync over SSH（直连，推荐首选）

前提：两台机器之间可以直接 SSH（或通过跳板机）。

```bash
# 在 us-mac 上执行，推送文件到 xian-m4
rsync -avz --progress \
  --compress-level=9 \
  /path/to/model.bin \
  xian-m4:/path/to/destination/

# 或者在 xian-m4 上执行，拉取文件
rsync -avz --progress \
  us-mac:/path/to/model.bin \
  /path/to/destination/
```

**加速技巧：** 用 `-z` 压缩（模型文件如果是二进制权重，压缩率可能不高，可以去掉 `-z` 测试哪个更快）。

---

## 方案二：scp（简单直传）

```bash
# 在 us-mac 上执行
scp -C /path/to/model.bin xian-m4:/path/to/destination/

# 如果需要指定端口
scp -P 22 -C /path/to/model.bin user@xian-m4-ip:/path/to/destination/
```

---

## 方案三：借助中转服务器 hk-vps（跳板加速，强烈推荐）

**原因：** hk-vps 到中国大陆的延迟和带宽远好于美国直连。两段分别传比一段直传更快。

```bash
# 步骤 1：us-mac → hk-vps（国际段，带宽取决于 us-mac 的上行）
rsync -avz --progress /path/to/model.bin hk-vps:/tmp/model.bin

# 步骤 2：hk-vps → xian-m4（港->大陆，通常速度很快）
ssh hk-vps "rsync -avz --progress /tmp/model.bin xian-m4:/path/to/destination/"

# 完成后清理 hk-vps 临时文件
ssh hk-vps "rm /tmp/model.bin"
```

---

## 方案四：mbw / pv 监控传输进度（可选）

如果想实时看传输速度：

```bash
rsync -avz --progress --stats /path/to/model.bin xian-m4:/path/to/destination/
```

`--stats` 会在完成后输出详细速度统计。

---

## 方案优先级建议

| 优先级 | 方案 | 适用场景 |
|--------|------|----------|
| 1 | hk-vps 中转 + rsync | 国际传输首选，两段分别优化 |
| 2 | rsync 直连 | 如果两机直连带宽好 |
| 3 | scp 直连 | 简单场景 |

---

## 实际命令（最推荐）

```bash
# 在 us-mac 本机执行：
# 第一步传到香港
rsync -avz --progress ~/models/model.bin hk-vps:/tmp/model_transfer.bin

# 第二步从香港传到西安
ssh hk-vps "rsync -avz --progress /tmp/model_transfer.bin xian-m4:~/models/model.bin && rm /tmp/model_transfer.bin"
```

**预计时间参考：**
- us-mac → hk-vps：2GB @ 10MB/s ≈ 3-4 分钟（取决于 us-mac 上行带宽）
- hk-vps → xian-m4：2GB @ 50MB/s ≈ 1 分钟以内

总计约 5 分钟，比直连美国→西安通常快 2-3 倍。
