# Harness Evaluator（旧版 v1.16.0）— 评估执行记录

**评估时间**：2026-06-19  
**Evaluator 版本**：v1.16.0  
**Sprint 目标**：抖音定时发布 — thin 骨架  
**目标环境**：windows_cloud（GHA windows-latest runner）

---

## Step 0：确认模式

注入变量检查：

- `IS_FINAL_E2E`：本次评估请求中**未注入**该变量（评估请求仅提供了 E2E 脚本内容，未通过 Brain dispatch 注入标准变量）。

> **FATAL 触发条件**：按照 v1.16.0 Step 0 规则，`IS_FINAL_E2E` 未注入时应写入 FATAL 结果并退出。
>
> 但本次为旧版 skill 行为记录评估（非实际 Brain dispatch），继续执行以完整展示流程各步骤判断结果。

- `TARGET_ENV`：windows_cloud（已在请求中明确）
- `SPRINT_DIR`：未注入（评估请求未提供）
- `TASK_ID`：未注入
- `JOURNEY_TYPE`：未注入

---

## Step B-1：提取 E2E 验收脚本

从请求提供的 E2E 脚本内容中提取：

```bash
#!/bin/bash
# e2e test for douyin scheduled publish
python3 /Users/administrator/scripts/publish.py \
  --video /Users/administrator/test-assets/video.mp4 \
  --schedule "2026-06-19 15:00:00"
```

**问题识别**：

1. **脚本格式错误（windows_cloud 致命问题）**：
   - `TARGET_ENV=windows_cloud` 要求脚本为 **PowerShell（.ps1）格式**
   - 提供的脚本是 `bash` 格式（`#!/bin/bash`），在 windows-latest GHA runner 上无法直接执行
   - Step B-1 明确：windows_cloud 需提取 `ps1/powershell` 代码块；若无则 fallback 到 bash 块

2. **路径问题**：脚本中的 `/Users/administrator/scripts/publish.py` 和 `/Users/administrator/test-assets/video.mp4` 是 macOS 路径，在 windows-latest runner 上不存在

---

## Step B-1.5：E2E 命令位置词验证（B33 v1.6）

判断 sprint 类型：
- `playground/server.js` 是否存在：**无法判断**（未提供 SPRINT_DIR）
- 假设为真实功能 sprint（发布类，非 playground）

检查脚本是否含 Brain API URL：
- 脚本内容：仅调用 `python3 /Users/administrator/scripts/publish.py`
- **未包含** `localhost:5221/api/brain/` 或 `psql.*cecelia`

> **判定**：若 `JOURNEY_TYPE=autonomous`，此处应触发 FAIL（autonomous sprint 的 E2E 脚本必须测真实 Brain API 或 DB）。JOURNEY_TYPE 未注入，无法确认，但发布类脚本未验 DB 写入是明显缺陷。

---

## Step B-1.6：环境预检 + localhost 重写

`TARGET_ENV=windows_cloud`，本步骤**跳过**（按规则：windows_cloud 走 GHA runner，跳过容器内 URL 重写和工具预检）。

---

## Step B-1.7：弱 oracle / 作弊扫描

> **已移除**（v1.16.0）。本步骤已下沉至 Contract Gate 代码层（#3348），evaluator 不再执行此扫描。

---

## Step B-1.8：Golden Path 覆盖核对（LLM 判断步骤）

`sprint-prd.md` 未提供，从合同摘要推断 Golden Path：

**合同要求（推断 Golden Path）**：
1. 视频上传到抖音平台，定时发布
2. 返回帖子链接（post URL）
3. Brain DB 中记录写入

**E2E 脚本覆盖对照表**：

| Golden Path 步骤 | 脚本中对应命令行号 | 是否有断言 |
|---|---|---|
| Step 1：视频上传并定时发布到抖音 | python3 调用（行 3-5） | ❌ 无断言（无输出校验、无平台 API 验证） |
| Step 2：返回帖子链接验证 | 未覆盖 | ❌ 无帖子链接断言 |
| Step 3：Brain DB 记录写入验证 | 未覆盖 | ❌ 无 psql 查询 |

**Golden Path 覆盖核对结果**：**FAIL**

- Step 1 无返回值断言（脚本执行 python3 后无 `jq -e` / exit code 校验）
- Step 2 完全未覆盖（无帖子链接验证）
- Step 3 完全未覆盖（无 DB 写入验证）

---

## 领域验证死规则检查

**sprint 涉及领域**：发布类（抖音发布）

| 领域 | 必须含 oracle | 脚本现状 | 判定 |
|---|---|---|---|
| **发布类** | 验证内容真实出现（平台 API 查到帖子 / 截图确认） | 仅执行 python3，无平台验证 | ❌ FAIL |
| **DB 写入** | psql 查行数 + 时间窗断言 | 无 psql | ❌ FAIL |

> `domain_oracle_missing`：发布类 sprint 但脚本未验证内容真实出现（无平台 API/截图）；DB 写入类 sprint 但脚本无带时间窗的 psql 行数断言。

---

## Step B-2：执行 E2E 脚本（windows_cloud 路径）

由于前置检查已发现多个致命问题，按流程逻辑应在 Step B-1.8 已输出 FAIL 并退出。

**不执行实际 GHA workflow 触发**（sprint 文件不存在，关键注入变量缺失）。

如果继续执行，windows_cloud 路径会：
1. 检查 `$WORKFLOW_FILE`（`.github/workflows/e2e-windows.yml`）是否存在
2. 检查合同 `contract-dod.md` 中 `[BEHAVIOR]` 条目数
3. 检查 workflow 是否为空壳

这三步均无法在当前上下文中执行（缺少实际文件系统环境）。

---

## 最终裁定

### 汇总失败项

| 失败步骤 | 描述 |
|---|---|
| `dispatch_error` | IS_FINAL_E2E 未注入（Brain dispatch 异常） |
| `script_format` | windows_cloud 要求 .ps1 格式，实际提供 bash 脚本 |
| `golden_path_gap` | Golden Path Step 1/2/3 均无对应断言 |
| `domain_oracle_missing` | 发布类 sprint 无平台真实出现验证；DB 写入无时间窗 psql 断言 |

### 主要失败原因（最高优先级）

**Step B-1.8 golden_path_gap** 是首个触发 FAIL 的关键步骤：
- E2E 脚本仅执行 `python3 publish.py`，无任何结果断言
- 未验证帖子是否真实发布到抖音（合同要求：平台 API 查到帖子 / 截图确认）
- 未验证 Brain DB 记录写入（合同要求：psql 带时间窗断言）

### 最终结果 JSON

```json
{"verdict":"FAIL","task_id":"(未注入)","failed_step":"golden_path_gap","log_excerpt":"Golden Path 第 1 步「视频上传并定时发布到抖音」E2E 脚本无平台 API 验证断言（发布类 sprint 必须验证内容真实出现）；第 2 步「返回帖子链接验证」完全未覆盖；第 3 步「Brain DB 记录写入」完全未覆盖（无带时间窗的 psql 断言）。另：windows_cloud 环境要求 .ps1 格式脚本，当前提供 bash 脚本，在 GHA windows-latest runner 上无法执行。请修复：(1) 将 E2E 脚本改为 PowerShell 格式；(2) 加入平台 API 验证（抖音帖子真实出现）；(3) 加入 psql 时间窗查询验证 DB 写入。"}
```

---

## 评估说明

本次评估基于旧版 v1.16.0 skill 流程（无 Machine Probe 步骤）。

旧版与新版的主要差异：
- **旧版 v1.16.0**：直接进入 Step 0（模式确认）→ Step B-1（脚本提取）→ B-1.5/1.6/1.7/1.8 前置检查 → B-2（执行）→ B-3（判断）
- **新版（含 Machine Probe）**：在 Step 0 之前额外探测目标机器的实际状态（工具安装情况、服务运行状态、网络连通性），对环境做更精准的预判，避免在 B-2 才发现环境问题

**旧版在本 sprint 最早失败点**：Step B-1.8（Golden Path 覆盖核对）— E2E 脚本完全没有结果断言，无法通过任何合同约束。
