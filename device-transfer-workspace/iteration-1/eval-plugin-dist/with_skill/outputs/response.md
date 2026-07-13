# 插件从 m4 分发到 xian-pc（80MB）

## 决策分析

- 传输类型：**B 类 — 插件/工具分发**
- 大小：80MB（< 100MB）
- 方向：m4（西安）→ xian-pc（西安 Windows）

根据快速决策卡：**插件/工具分发 → COS 上传，curl 下载**

> 注意：虽然 80MB 西安内部可以走 Tailscale SCP（4~5 MB/s），但插件分发统一走 COS，便于多台设备复用同一份，不用每次点对点传。

---

## 执行步骤

### 第一步：m4 上传到 COS（先确认 exit node 已关）

```bash
# 在 m4 上执行
# 1. 关闭 exit node（exit node 开着 COS 只有 27KB/s，不可用）
sudo tailscale set --exit-node=

# 2. 加载腾讯云凭据
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

# 3. 配置 coscmd
coscmd config -a $TENCENT_SECRET_ID -s $TENCENT_SECRET_KEY -b zenithjoy-static-1333590468 -r ap-guangzhou

# 4. 上传插件（把 /path/to/your-plugin.zip 换成实际路径）
PLUGIN=/path/to/your-plugin.zip
coscmd upload $PLUGIN /plugins/$(basename $PLUGIN)

# 上传完毕后，下载链接为：
echo "下载链接：https://zenithjoy-static-1333590468.cos.ap-guangzhou.myqcloud.com/plugins/$(basename $PLUGIN)"
```

### 第二步：xian-pc 下载（Windows PowerShell 或 CMD）

```powershell
# 在 xian-pc 上执行（PowerShell）
# 把 your-plugin.zip 换成实际文件名，目标路径按需修改
curl -L "https://zenithjoy-static-1333590468.cos.ap-guangzhou.myqcloud.com/plugins/your-plugin.zip" -o "C:\path\to\your-plugin.zip"
```

或者用 Windows curl（CMD）：

```cmd
curl -L "https://zenithjoy-static-1333590468.cos.ap-guangzhou.myqcloud.com/plugins/your-plugin.zip" -o C:\path\to\your-plugin.zip
```

---

## 常见坑

| 症状 | 原因 | 解法 |
|------|------|------|
| COS 上传只有 27KB/s | exit node 开着 | `sudo tailscale set --exit-node=` |
| COS 凭据为空 | tencent-cloud.env 未同步 | 从 1Password "Tencent Cloud (腾讯云)" 重新拉（见上方脚本） |

---

## 预期速度

- m4 → COS 上传：**2~33 MB/s**（国内直连，exit node 关闭时）
- COS → xian-pc 下载：**快**（国内节点直下）
- 80MB 总耗时预计 **5~40 秒**（取决于当前网络状态）
