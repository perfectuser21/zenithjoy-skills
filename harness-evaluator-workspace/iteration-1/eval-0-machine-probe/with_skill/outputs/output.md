# Harness Evaluator v1.17.0 — 评估报告

**sprint 目标**：抖音定时发布 — thin 骨架  
**环境**：windows_cloud（GHA windows-latest runner）  
**评估时间**：2026-06-19  
**evaluator 版本**：v1.17.0

---

## Step 0：确认模式

```
IS_FINAL_E2E=true（已注入）
TARGET_ENV=windows_cloud
JOURNEY_TYPE=（未明确注入，按请求内容推断为 user_facing/autonomous）
模式：B — 最终 E2E
```

模式确认通过。继续执行。

---

## Step 0a：切到 PR 分支

PR_BRANCH 未在本次请求中注入，跳过 git checkout 操作。  
（实际 harness 流程中，Brain evaluateContractNode 必须注入 PR_BRANCH；缺失属于 dispatch 配置问题，但本次为模拟评估，继续执行。）

---

## Step 0b：Cookie / Session 隔离

TARGET_ENV=windows_cloud，属于 HTTP API 类（GHA runner 每次全新 VM）。  
GHA windows-latest runner 每次触发均为全新虚拟机，天然隔离，无历史 cookie 问题。  
✅ 隔离检查通过。

---

## Step B-1：提取 E2E 验收脚本

合同 contract-draft.md 中的 E2E 验收脚本（用户请求中直接提供，等价于从合同提取）：

```bash
#!/bin/bash
# e2e test for douyin scheduled publish
python3 /Users/administrator/scripts/publish.py \
  --video /Users/administrator/test-assets/video.mp4 \
  --schedule "2026-06-19 15:00:00"
```

**注意**：TARGET_ENV=windows_cloud，按 v1.17.0 Step B-1 规则，windows_cloud 应提取 `.ps1` / `powershell` 代码块。  
当前脚本为 bash 格式（非 PowerShell），evaluator 按 fallback 规则（兼容旧合同 bash 块）接受，继续处理。

脚本已写入 `/tmp/e2e-verify.ps1`（模拟）。

---

## Step B-1.5：E2E 命令位置词验证

检查是否为 playground sprint：
- `playground/server.js` 不存在 → IS_PLAYGROUND_SPRINT=false
- 本次为真实发布功能 sprint（windows_cloud）

按 v1.17.0 B33 v1.6 规则：windows_cloud 环境的 E2E 通过 GHA 运行 PowerShell，不直接调 localhost:5221，**跳过 Brain API URL 检测**。

✅ 位置词验证：跳过（windows_cloud 豁免）。

---

## Step B-1.6：环境预检 + localhost 重写

TARGET_ENV=windows_cloud，按规则**跳过本步**（脚本为 .ps1，在远端 GHA runner 执行）。

✅ 环境预检：跳过（windows_cloud 豁免）。

---

## Step B-1.7：弱 oracle / 作弊扫描

**已下沉 Contract Gate 代码层（v1.16.0 移除）**，evaluator 不执行此步。

---

## Step B-1.8：Golden Path 覆盖核对

sprint-prd.md 未在本次请求中提供，但根据合同摘要推断 Golden Path 包含：
- Step 1：上传视频文件
- Step 2：设置定时发布时间
- Step 3：提交发布请求，平台返回帖子链接
- Step 4：Brain DB 写入发布记录

**E2E 脚本对照表**：

| Golden Path 步骤 | 脚本中对应命令行号 | 是否有断言（jq -e / ffprobe / DOM / psql）|
|---|---|---|
| Step 1：上传视频文件 | L4（`--video /Users/administrator/test-assets/video.mp4`）| ❌ 无断言（只是参数传入）|
| Step 2：设置定时发布时间 | L5（`--schedule "2026-06-19 15:00:00"`）| ❌ 无断言（只是参数传入）|
| Step 3：验证平台返回帖子链接 | **未覆盖** | ❌ 无断言 |
| Step 4：Brain DB 记录写入验证 | **未覆盖** | ❌ 无断言 |

**结论**：E2E 脚本仅调用 publish.py，既无返回值校验，也无 DB 验证。Step 3、Step 4 完全未覆盖。

---

## Step B-1.9：Machine Probe（重点步骤）

TARGET_ENV=windows_cloud，**执行本步**。

### Gate：E2E 脚本绝对路径检查（所有 TARGET_ENV 均运行）

扫描 E2E 脚本中是否含硬编码绝对路径：

```bash
grep -qE '(/Users/[a-zA-Z]|C:\\Users\\|C:\\Program Files)' /tmp/e2e-verify.ps1
```

**扫描结果**：

```
命中！检测到以下硬编码绝对路径：
  行 3: python3 /Users/administrator/scripts/publish.py
  行 4:   --video /Users/administrator/test-assets/video.mp4
```

**违规分析**：

| 硬编码路径 | 问题 | 应改为 |
|---|---|---|
| `/Users/administrator/scripts/publish.py` | macOS 用户家目录绝对路径，GHA windows-latest runner 上不存在此路径（Windows 环境无 `/Users/` 路径格式）| `$env:PUBLISH_SCRIPT_PATH` 或 `$PSScriptRoot\publish.py` |
| `/Users/administrator/test-assets/video.mp4` | macOS 绝对路径，GHA Windows runner 无法访问 | `$env:TEST_VIDEO_PATH` 或由 Machine Probe 注入的 `$CHROME_PATH` 类似变量 |

**此外，脚本使用 `python3` 命令（bash 语法），而 TARGET_ENV=windows_cloud 要求 PowerShell 脚本**。

windows-latest GHA runner 应使用 `python` 或 `python3.exe`，且脚本整体应为 `.ps1` 格式。

---

### Gate 判定：FAIL — absolute_path_in_e2e

```json
{
  "verdict": "FAIL",
  "task_id": "$TASK_ID",
  "failed_step": "absolute_path_in_e2e",
  "log_excerpt": "E2E 脚本含硬编码绝对路径（/Users/administrator/...）。当前 TARGET_ENV=windows_cloud（GHA windows-latest runner），/Users/ 路径在 Windows 环境下不存在，E2E 将必然失败。请改用标准化环境变量（由 Machine Probe 注入），如 $env:TEST_VIDEO_PATH / $env:PUBLISH_SCRIPT_PATH，不得写死路径。同时，脚本应改写为 PowerShell (.ps1) 格式，而非 bash 格式。"
}
```

---

## 领域验证死规则检查（执行前扫描）

**发布类 sprint**（抖音发布）：
- 规则要求：E2E 脚本必须验证内容**真实出现**（平台 API 查到帖子 / 截图确认）
- 当前脚本：仅调用 `publish.py`，无任何平台 API 返回值校验，无截图验证
- 结论：❌ 违反发布类领域死规则

**DB 写入类**（合同要求 Brain DB 写入验证）：
- 规则要求：`psql` 查行数且带 `created_at > NOW() - interval` 时间窗
- 当前脚本：无任何 psql 命令
- 结论：❌ 违反 DB 写入类领域死规则

即便通过 Machine Probe Gate，也会因领域死规则而 FAIL（domain_oracle_missing）。

---

## 反作弊红线核查

| 红线规则 | 状态 |
|---|---|
| 禁止把 vitest 输出当 PASS 证据 | ✅ 未出现 vitest |
| 禁止以"代码看起来对"给 PASS | ✅ 未跳过验证 |
| 缺 [BEHAVIOR] Test: 命令直接 FAIL | ⚠️ 合同摘要中有 BEHAVIOR 描述，但 E2E 脚本无对应断言命令 |
| 缺 jq -e 严匹配直接 FAIL | ❌ E2E 脚本无任何 jq -e 校验 |

---

## 问题汇总

| 序号 | 问题类型 | 严重级别 | 具体描述 |
|---|---|---|---|
| 1 | 硬编码绝对路径 | FATAL | `/Users/administrator/scripts/publish.py` 和 `/Users/administrator/test-assets/video.mp4` 是 macOS 路径，在 windows_cloud GHA runner 上必然失败 |
| 2 | 脚本格式错误 | FATAL | TARGET_ENV=windows_cloud 要求 PowerShell (.ps1) 脚本，当前为 bash 格式 |
| 3 | 发布类领域 oracle 缺失 | FATAL | 未验证内容真实出现在抖音平台（无平台 API 查询 / 无截图确认）|
| 4 | DB 写入 oracle 缺失 | FATAL | 合同要求 Brain DB 记录写入验证，脚本无 psql 断言 |
| 5 | Golden Path 覆盖不足 | HIGH | Step 3（平台返回帖子链接）和 Step 4（DB 验证）完全未覆盖 |
| 6 | 缺 jq -e 严匹配 | HIGH | 无任何 jq -e 值校验，schema drift 无法被检测 |

---

## 最终裁定

```json
{
  "verdict": "FAIL",
  "task_id": "$TASK_ID",
  "failed_step": "absolute_path_in_e2e",
  "log_excerpt": "E2E 脚本含硬编码绝对路径 /Users/administrator/scripts/publish.py 和 /Users/administrator/test-assets/video.mp4。TARGET_ENV=windows_cloud 的 GHA windows-latest runner 为 Windows 环境，/Users/ 路径不存在，E2E 必然失败。修复指引：(1) 将脚本改写为 PowerShell (.ps1) 格式；(2) 用 Machine Probe 注入的环境变量替换绝对路径（如 $env:TEST_VIDEO_PATH / $env:PUBLISH_SCRIPT_PATH）；(3) 补充发布结果验证（平台 API 查帖子链接 + psql 验 DB 记录时间窗）；(4) 所有校验须有 jq -e 或等效 PowerShell 断言。"
}
```

---

## 修复建议（发给 Generator）

### 必须修复的问题

1. **脚本格式**：改写为 PowerShell (.ps1)，TARGET_ENV=windows_cloud 不接受 bash 脚本

2. **路径规范化**：
   ```powershell
   # 错误（硬编码）
   python3 /Users/administrator/scripts/publish.py
   
   # 正确（使用 Machine Probe 注入的环境变量）
   $publishScript = $env:PUBLISH_SCRIPT_PATH  # 由 Machine Probe probe-result.json 注入
   $testVideo = $env:TEST_VIDEO_PATH
   python $publishScript --video $testVideo --schedule "2026-06-19 15:00:00"
   ```

3. **发布结果验证**（领域死规则）：
   ```powershell
   # 必须验证帖子真实出现
   $result = python $publishScript ...
   $postUrl = ($result | ConvertFrom-Json).post_url
   if (-not $postUrl) { throw "发布失败：未返回帖子链接" }
   # 可选：调用抖音 API 验证帖子存在
   Invoke-RestMethod -Uri "https://api.douyin.com/posts/$postId" | Should -Not -BeNull
   ```

4. **DB 验证**（领域死规则）：
   ```powershell
   # 验证 Brain DB 记录（带时间窗）
   $dbResult = psql $env:DB -c "SELECT count(*) FROM publish_records WHERE created_at > NOW() - interval '5 minutes'"
   if ($dbResult -notmatch "[1-9]") { throw "DB 未写入发布记录" }
   ```
