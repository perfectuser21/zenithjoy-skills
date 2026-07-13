# /dev 执行记录 — 快手内容发布功能

## 走的路径

**路径 C（大功能/Harness）**

用户说"我想做快手内容发布功能"，属于新功能立项，判断为路径 C。

---

## 执行的 curl 命令及 API 返回摘要

### curl 1：GET /api/brain/journeys
返回 20 条 Journey。与本次相关的：
- `c019cdeb`「智能发布」— journey_type: autonomous, maturity: **skeleton**, status: active
  - 描述：8 平台自动发布能力（抖音/快手/小红书/微博/知乎/头条/视频号/公众号）

### curl 2：GET /api/brain/abilities?limit=50
返回 25 条 Ability/Feature。关键发现——快手相关已有 2 条 **status=working** 的记录：
- `6a64605a`「快手图文发布」— kind: ability, status: **working**, workflow_ref: `publishers/kuaishou-publisher/publish-kuaishou-image.cjs`
- `01321fec`「快手视频发布」— kind: ability, status: **working**, workflow_ref: `publishers/kuaishou-publisher/publish-kuaishou-video.cjs`

### curl 3：GET /api/brain/tasks?status=in_progress&limit=20
返回：`[]`（无进行中任务）

### curl 4：GET /api/brain/harness/runs?limit=20
返回 20 条历史 Run，最近一条（`1aec967a`）phase=done，于 2026-06-09 01:05 完成。

### curl 5：POST /api/brain/decisions/match（prd="快手内容发布 图文 视频 publisher"）
返回：`{"matched":[],"missing":[]}`（无历史相关决策）

---

## Golden Path 草稿（步骤 0 输出）

### 对应 Journey
**智能发布**（`c019cdeb`，maturity: skeleton，Notion: `374c40c2-ba63-81ca-8e1d-d1b2270130fe`）

### 已有（✅ 不动）
- ✅ 快手图文发布 — status: working（`publish-kuaishou-image.cjs` 已存在，21KB 真实实现）
- ✅ 快手视频发布 — status: working（`publish-kuaishou-video.cjs` 已存在）
- ✅ 快手图文 dryrun — `publish-kuaishou-image-dryrun.cjs` 存在
- ✅ 快手视频 dryrun — `publish-kuaishou-video-dryrun.cjs` 存在
- ✅ kuaishou-e2e.yml — GHA E2E workflow 已存在，跑 windows-latest + KUAISHOU_COOKIES
- ✅ 快手 UI smoke — `.github/workflows/scripts/smoke/kuaishou-publish-ui-smoke.sh` 已存在

### 本次需澄清（➕）
> abilities 表已显示 status=working，代码文件也存在于 `services/agent/publishers/kuaishou-publisher/`。用户说"快手完全没有"可能指：
> a) Dashboard UI 没有快手选项，或
> b) 真发功能（非 dryrun）跑不通，或
> c) 不知道已有这些文件

需要先确认用户意图再确定 sprint 范围。

### 建议 Golden Path（用户视角）

**[首次使用]**
1. 用户在 Dashboard 选择"快手"平台 → 上传图文/视频素材 → 填写标题/描述
2. 用户点"发布" → 系统调用快手 cookie 鉴权 → 提交内容到快手
3. 系统返回发布结果（成功/失败）→ 用户看到发布状态

**[日常使用]**
1. 用户在内容队列里给内容指定"快手"目标平台
2. 系统自动按时发布 → 回写发布结果到队列

**[出错/掉线后]**
1. 快手 cookie 过期 → 系统在 Dashboard 显示"快手 session 失效" → 用户重新扫码登录
2. 发布失败 → 系统标记队列任务为 failed，用户在 Dashboard 看到错误原因 → 重试

---

## 前置工作核查结果

| 前置项 | 检查命令 | 结果 |
|---|---|---|
| `~/.credentials/kuaishou.env` | `ls ~/.credentials/kuaishou.env` | ❌ NOT FOUND |
| 1Password CS Vault 快手凭据 | `op item list --vault CS` 过滤快手/kuaishou | ❌ 无匹配条目 |
| `~/.credentials/` 中任何快手相关文件 | `ls ~/.credentials/ \| grep -i kuaishou` | ❌ 无结果 |
| GHA Secret `KUAISHOU_COOKIES` | `gh secret list -R perfectuser21/zenithjoy-workspace` | ✅ 已存在（2026-05-27 创建） |
| 快手 publisher 代码 | `ls services/agent/publishers/kuaishou-publisher/` | ✅ 文件存在（image.cjs / video.cjs / dryrun 等） |
| kuaishou-e2e.yml | `.github/workflows/kuaishou-e2e.yml` | ✅ 存在 |
| kuaishou smoke.sh | `.github/workflows/scripts/smoke/kuaishou-publish-ui-smoke.sh` | ✅ 存在 |

### 核查结论

**GHA Secret `KUAISHOU_COOKIES` 已存在**，但：
1. `~/.credentials/kuaishou.env` **不存在** — 本地无法直接跑真实发布
2. 1Password CS Vault 里**没有快手凭据条目** — 凭据未入库，不符合凭据管理规范
3. 用户说"快手完全没有"但 abilities 表显示 status=working、代码文件存在 — **需要先澄清用户实际遇到的问题**

---

## 是否写了 PrepPRD

**否。**

原因：按 SKILL.md 步骤 0 规定，Golden Path 草稿需要用户确认（说"对"/"走"/"可以"）后才能进入步骤 1（前置工作核对），再进入 PrepPRD 写作。

另外，在展示 Golden Path 草稿之前，发现一个关键问题需先向用户澄清：abilities 表里"快手图文发布"和"快手视频发布"都已是 status=working，代码文件也真实存在——用户说"快手完全没有"的意思需要确认，否则 sprint 范围无法确定。

---

## 是否调用了 Harness

**否。**

前置工作核查发现凭据状态不完整（本地 kuaishou.env 不存在，1Password 无快手条目），且用户意图尚未确认——不满足"全部 ✅ 才继续写 PrepPRD"的硬门槛，更不符合点火 Harness 的条件。

---

## 向用户索要的清单

在继续之前，需要用户回答以下问题：

### 问题 1（意图澄清，必答）

查 DB 发现"快手图文发布"和"快手视频发布"在 abilities 表里已是 `status=working`，代码文件 `publish-kuaishou-image.cjs` 和 `publish-kuaishou-video.cjs` 也真实存在于 `services/agent/publishers/kuaishou-publisher/`。

你说"快手完全没有"，请确认是哪种情况：
- A：Dashboard UI 里没有快手选项（前端没接入）
- B：代码存在但真发跑不通（有报错或 E2E 挂了）
- C：其他——请描述具体看到的问题

### 凭据问题（确认意图后，如需真实发布必须解决）

GHA Secret `KUAISHOU_COOKIES` 已存在，但：

1. **本地凭据文件缺失**：`~/.credentials/kuaishou.env` 不存在，1Password CS Vault 也无快手凭据条目
   - 需要：把快手 cookie（完整 JSON 字符串）存入 1Password CS Vault，条目名建议"Kuaishou"，同时双写到 `~/.credentials/kuaishou.env`

2. **测试账号确认**：E2E 需要哪个快手账号？该账号 cookie 是否仍有效（快手 cookie 有效期一般 7-30 天）？

> 如果你只要做 thin dryrun 骨架（不验真实发布行为），凭据可以暂时不提供，但 PrepPRD 验收标准里不能写真实发布验证。
