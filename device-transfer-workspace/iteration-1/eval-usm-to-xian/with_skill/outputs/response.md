# us-mac → xian-m4 传输 2GB 模型文件：最快方案

## 结论

**走 COS 中转**，这是 us-mac → 西安唯一可用的快速路径。

直连（Tailscale SCP）只有 **0.5 MB/s**，2GB 文件需要约 **68 分钟**。
COS 路径：us-mac 上传 COS → xian-m4 从 COS 下载，速度取决于 COS，但国内下载 COS 可达 **2~33 MB/s**，远快于直连。

---

## 具体步骤

### 第一步：在 us-mac 上上传到 COS

```bash
# us-mac 执行（美国机器不需要关 exit node）
source ~/.credentials/tencent-cloud.env && echo $TENCENT_SECRET_ID

# 如果凭据为空，从 1Password 重新拉：
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

# 配置 coscmd 并上传（替换 /path/to/model.bin 为实际路径）
coscmd config -a $TENCENT_SECRET_ID -s $TENCENT_SECRET_KEY -b zenithjoy-static-1333590468 -r ap-guangzhou
coscmd upload /path/to/model.bin /temp/model.bin
```

### 第二步：在 xian-m4 上从 COS 下载

```bash
# xian-m4 执行

# 重要：先确认 exit node 已关闭，否则 COS 速度会从 2~33 MB/s 跌到 27 KB/s
sudo tailscale set --exit-node=

# 下载（替换 model.bin 为实际文件名，/local/path/ 为目标目录）
curl -L "https://zenithjoy-static-1333590468.cos.ap-guangzhou.myqcloud.com/temp/model.bin" \
  -o /local/path/model.bin
```

---

## 速度对比

| 方案 | 速度 | 2GB 预计耗时 |
|------|------|------------|
| Tailscale SCP 直连 | 0.5 MB/s | ~68 分钟 |
| **COS 中转（推荐）** | **2~33 MB/s**（国内下载） | **~1~17 分钟** |

---

## 常见坑

- **exit node 一定要关**：xian-m4 下载 COS 时如果 exit node 开着，速度会跌到 27 KB/s，完全不可用。
- **凭据为空**：`source ~/.credentials/tencent-cloud.env` 后 `echo $TENCENT_SECRET_ID` 为空时，按上方步骤从 1Password 重新拉取。
