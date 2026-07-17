# user_facing 交付 staging 预览闸进合同法律：Cecelia=24h通知式/ZJ=阻塞式点头

> **决策来源**: 34a7ad72（2026-07-16，cecelia，level=ability，category=process，status=active）
> **任务 ID**: 8589b916-9b71-4dd8-a986-76670229b06d
> **Sprint 目录**: sprints/07171650-staging-preview-gate
> **版本目标**: harness-contract-proposer v9.16.0 + harness-report v6.9.0

---

## 背景与动机

历史教训（决策34a7ad72 触发背景）：
- **指挥舱空白（Cecelia）**：user_facing 功能直上 prod，主理人首次看到成品就踩雷。
- **16步画像卡（ZJ）**：user_facing 功能直推 production，主理人事后才知道发生了什么。

根因：合同（harness-contract-proposer）未强制要求 user_facing 类交付在 merge 后先落 staging，Final E2E 在 staging 上跑并截图，再由 Bark 推送主理人预览链接，主理人审核后才允许 promote 到 prod。

---

## 本次变更范围

### 改动 ①：harness-contract-proposer/SKILL.md

**新增硬规则「staging 预览步（user_facing 专属）」**：

凡 `journey_type=user_facing` 的 Golden Path 合同，必须在合同末尾新增 `## staging 预览闸` 段，包含以下三步：

**步骤 A — 落 staging 环境**
- merge 后，交付物必须先部署到对应 staging 实例（不直接上 prod）
- Cecelia 仓：staging 端口 = 5212（`http://localhost:5212`）
- ZenithJoy 仓：staging 实例 = ZJ staging（现有 staging-promote 机制，引用不重造）
- 引用衔接：cecelia 仓复用 `auto-staging-deploy` 脚本；ZJ 仓复用 `staging-promote` 相关脚本（只引用，不在本 SKILL 内重造逻辑）

**步骤 B — Final E2E 在 staging 上跑（附截图）**
- Final E2E 脚本的目标地址必须改为 staging 地址（非 localhost:5174 / 非直接 prod）
- 截图路径：`${SPRINT_DIR}/screenshots/staging-<step>.png`
- evaluator 执行 staging E2E 时，截图自动收入 sprint 目录

**步骤 C — Bark 推主理人预览链接**
- 使用 `$BARK_URL`（现有凭据，复用既有 Bark 通知调用方式）
- 推送内容：功能名 + staging 预览地址 + 截图缩略 URL（若有）
- **repo 模式按 `$BASE_REPO` 判断**：
  - `cecelia` 仓（BASE_REPO 含 `cecelia`）→ **通知式**：Bark 消息注明「24h 无异议自动放行，promote_after = <时间戳>」
  - `zenithjoy` 仓（BASE_REPO 含 `zenithjoy`）→ **阻塞式**：Bark 消息注明「需主理人放行后才能 promote 到 prod，请查看 staging 确认后回复或在 Brain 写入 approval」

**阻塞式（ZJ 仓）额外合同条款**：
- prod promote 之前，必须核查 `decisions` 表 或 task 的 `approval` 字段，存在明确放行标记才允许执行 promote
- 合同必须内嵌「未放行禁 promote」的 [BEHAVIOR] 断言（验证 approval 字段存在）
- 若调用链查不到放行标记 → 合同 BEHAVIOR FAIL，promote 步骤不执行

**「autonomous 流程零回归」保护**：
- `journey_type=autonomous` 的合同**不受本规则约束**，不强制加 staging 预览步
- 合同模板新增判断：`if journey_type == user_facing → 加 staging 预览段`

---

### 改动 ②：harness-report/SKILL.md

**收尾步新增「staging 预览通知与放行状态登记」（user_facing 专属）**：

在 Phase A Step 5（飞书通知）之后，新增 **Step 5.5**（仅当 journey_type=user_facing 时执行）：

```
Step 5.5: staging 预览通知 + 放行状态登记（user_facing only）
```

内容：
1. **Bark 推送**：调用 `$BARK_URL` 通知主理人，附 staging 预览链接 + 截图 URL
2. **Brain 登记 promote_after**（Cecelia 通知式）：
   - 写入 task metadata：`{ staging_deployed: true, promote_after: "<UTC timestamp + 24h>", staging_url: "http://localhost:5212/..." }`
   - PATCH `localhost:5221/api/brain/tasks/$TASK_ID` 追加上述字段
3. **Brain 登记 approval_required**（ZJ 阻塞式）：
   - 写入 task metadata：`{ staging_deployed: true, approval_required: true, staging_url: "<ZJ staging URL>" }`
   - approve 后由主理人或自动化写入 `approval` 字段，promote 流程轮询该字段

**完成标志**：Bark 推送 2xx + Brain PATCH 回写成功 → Step 5.5 PASS；任一失败 → CONCERN（非阻断，但必须记入 `.report-concerns`）

---

### 改动 ③：既有 staging 机制衔接（只引用不重造）

**改动本身不实现 staging 部署逻辑**，仅在 SKILL.md 中引用：
- Cecelia 仓：引用 `scripts/auto-staging-deploy.sh`（或现有等价脚本）的调用方式，合同注明调用入口
- ZJ 仓：引用 `scripts/staging-promote.sh`（或现有等价脚本）的调用方式，合同注明调用入口
- **合同撰写者须在 Step 1 读取上述脚本的真实路径与参数**，然后在 `## staging 预览闸` 段引用，不得假设脚本名称

---

## 版本 Bump 计划

| 文件 | 当前版本 | 目标版本 | changelog 条目 |
|------|----------|----------|----------------|
| `harness-contract-proposer/SKILL.md` | 9.15.0 | 9.16.0 | `user_facing staging 预览闸强制规则：merge→staging→E2E截图→Bark推主理人→Cecelia通知式(24h自动放行)/ZJ阻塞式(approval字段放行)` |
| `harness-report/SKILL.md` | 6.8.0 | 6.9.0 | `Step 5.5 新增 user_facing staging 预览通知与放行状态登记（Bark推送+Brain PATCH promote_after/approval_required）` |

---

## Golden Path（本 Sprint 的功能交付路径）

覆盖父路：zenithjoy-skills harness 合同规则体系（独立规则扩展小路，无单一父路）

```
[触发] journey_type=user_facing 的 Sprint GAN 合同起草
  → [Step 1] proposer 读 PRD，识别 journey_type=user_facing
  → [Step 2] proposer 在 contract-draft.md 末尾写入 ## staging 预览闸 段
              （三步：A落staging / B Final-E2E在staging跑截图 / C Bark推通知）
  → [Step 3] proposer 按 BASE_REPO 判定模式（通知式/阻塞式），写入对应条款
  → [Step 4] contract-dod.md 含 [BEHAVIOR] 验证「staging 预览步存在」
  → [Step 5] evaluator PASS 后，harness-report Phase A Step 5.5 执行
              Bark 推主理人 + Brain PATCH promote_after/approval_required
  → [出口 Cecelia] 24h 后无异议 → promote 到 prod
  → [出口 ZJ] 主理人 Brain approval 字段写入 → promote 到 prod
```

---

## 验收标准（Acceptance Criteria）

### AC-1：SKILL 文本 grep 断言

```bash
# 验证 harness-contract-proposer/SKILL.md 含 staging 预览闸规则
grep -c "staging 预览闸" harness-contract-proposer/SKILL.md | grep -qE '^[1-9]' || { echo "FAIL: 无 staging 预览闸段落"; exit 1; }
grep -c "journey_type=user_facing" harness-contract-proposer/SKILL.md | grep -qE '^[2-9]|^[0-9]{2,}' || { echo "FAIL: user_facing 条件判断不足"; exit 1; }
grep -c "通知式" harness-contract-proposer/SKILL.md | grep -qE '^[1-9]' || { echo "FAIL: 无通知式条款"; exit 1; }
grep -c "阻塞式" harness-contract-proposer/SKILL.md | grep -qE '^[1-9]' || { echo "FAIL: 无阻塞式条款"; exit 1; }
grep -c "promote_after" harness-contract-proposer/SKILL.md | grep -qE '^[1-9]' || { echo "FAIL: 无 promote_after 条款"; exit 1; }
grep -c "approval" harness-contract-proposer/SKILL.md | grep -qE '^[2-9]|^[0-9]{2,}' || { echo "FAIL: 无 approval 字段条款"; exit 1; }
grep -c "autonomous.*零回归\|零回归.*autonomous\|autonomous.*不受本规则" harness-contract-proposer/SKILL.md | grep -qE '^[1-9]' || { echo "FAIL: 无 autonomous 豁免保护"; exit 1; }
echo "AC-1 proposer PASS"

# 验证 harness-report/SKILL.md 含 Step 5.5
grep -c "Step 5.5\|5\.5" harness-report/SKILL.md | grep -qE '^[1-9]' || { echo "FAIL: harness-report 无 Step 5.5"; exit 1; }
grep -c "promote_after\|approval_required" harness-report/SKILL.md | grep -qE '^[1-9]' || { echo "FAIL: harness-report 无放行状态登记"; exit 1; }
grep -c "BARK_URL\|Bark" harness-report/SKILL.md | grep -qE '^[2-9]|^[0-9]{2,}' || { echo "FAIL: harness-report 无 Bark 调用"; exit 1; }
echo "AC-1 report PASS"
```

### AC-2：版本号 bump 断言

```bash
grep -qE "^version: 9\.16\.0" harness-contract-proposer/SKILL.md || { echo "FAIL: proposer 版本未 bump 到 9.16.0"; exit 1; }
grep -qE "^version: 6\.9\.0" harness-report/SKILL.md || { echo "FAIL: report 版本未 bump 到 6.9.0"; exit 1; }
echo "AC-2 版本 bump PASS"
```

### AC-3：user_facing 合同样例含预览步全文

本 Sprint 产出的 `contract-draft.md` 示例（由下游 proposer 产出）必须含 `## staging 预览闸` 段，其中包含：
- A. staging 部署引用命令（非空，引用真实脚本路径）
- B. Final E2E staging 目标地址（非 localhost:5174）
- C. Bark 推送命令（含 `$BARK_URL` 变量）
- D. 通知式或阻塞式条款（按 repo 判断）

（此 AC 由下游 proposer 执行，本 sprint 只写 SKILL.md 规则，不产出样例合同）

### AC-4：autonomous 流程零回归

```bash
# journey_type=autonomous 的合同样例不应含 staging 预览步强制要求
grep "autonomous" harness-contract-proposer/SKILL.md | grep -v "staging 预览" | grep -q "autonomous" || true
# 负向验证：SKILL 中不得出现「autonomous.*必须.*staging」字样
grep -qE "autonomous.*必须.*staging|autonomous.*强制.*staging" harness-contract-proposer/SKILL.md && { echo "FAIL: autonomous 流程被错误纳入 staging 规则"; exit 1; } || true
echo "AC-4 autonomous 零回归 PASS"
```

---

## 禁 mock 边清单

（本单纯文档/SKILL 改动，无代码接缝边，N/A）

---

## 八要素需求规范

| 要素 | 本次答案 |
|------|----------|
| **FR（做什么）** | 1. harness-contract-proposer：journey_type=user_facing 合同强制含 staging 预览步（A/B/C 三步），按 repo 分 Cecelia 通知式/ZJ 阻塞式；2. harness-report：Phase A 新增 Step 5.5，user_facing 时 Bark 推通知 + Brain 写 promote_after 或 approval_required |
| **NFR（做得多好）** | SKILL 文本改动，无性能要求；版本 bump 必须单调递增；changelog 必须准确描述本次变更 |
| **Invariant（永不违反）** | autonomous 流程零回归；现有 SKILL 版本机制（version/updated/changelog）格式不破坏；两份 SKILL 修改前后格式一致 |
| **判定点（怎么知道）** | 见下方登记表 |
| **保质期（何时过期）** | 规则永久有效；若 staging 机制重构（如 cecelia auto-staging-deploy 脚本路径变更），需同步更新 SKILL 引用 |
| **死亡告警（停了谁知道）** | 合同合规通过 CI 闸 `lint-skill-grep` 断言（AC-1/AC-2）保障；SKILL 改动后 CI grep 若不过即红 |
| **失败语义（挂了怎么办）** | Step 5.5 Bark/Brain PATCH 失败属非关键步（CONCERN 但不阻断），不阻止 Sprint 报告 DONE |
| **效果确认（已发≠已生效）** | AC-1/AC-2 grep 断言为唯一效果确认手段；文本写入 ≠ CI 通过，必须 grep 验证 |

### 判定点登记表

| 判定点 | 候选方法 | 所选方法 | 依据 | 误判后果 |
|--------|----------|----------|------|----------|
| 判断 repo 类型（cecelia vs ZJ）| A. 读 BASE_REPO 路径含 "cecelia"/"zenithjoy"；B. 读 package.json name 字段 | A. 读 BASE_REPO 路径字符串匹配 | 与 task payload 中 base_repo 字段一致，现有 skill 惯用法 | 选错模式：cecelia 仓走阻塞式（主理人体验差）或 ZJ 仓走通知式（安全漏洞，未经确认 promote） |
| 判断是否 user_facing | 读 sprint-prd.md 末尾 `## journey_type:` 字段 | 读 PRD journey_type 字段（已有 proposer Step 1 读法） | 合同现有协议，無需新增判断逻辑 | autonomous 被误识为 user_facing → 多余 staging 步，浪费但不危险；user_facing 被误识为 autonomous → 漏掉 staging 门槛，主理人踩雷（⚠️ 高危） |

### 失败语义声明

| 场景 | 失败行为 | 重试幂等？ | 降级策略 |
|------|----------|-----------|----------|
| Bark 推送失败 | CONCERN 记录，Sprint 报告 DONE_WITH_CONCERNS | 是（幂等，重发 Bark）| 手动补发 Bark，不阻塞流程 |
| Brain PATCH promote_after 失败 | CONCERN 记录 | 是（幂等 PATCH）| 手动补写，记录在 concerns |
| grep AC-1 断言失败 | CI 红，不允许合并 | N/A（代码改动非幂等）| 修改 SKILL 文本重跑 CI |

### 输入对抗面

N/A（本 sprint 是 SKILL 文档改动，无对外暴露 agent/接口）

---

## 未覆盖真实链路清单

- **cecelia auto-staging-deploy 脚本路径**：本 sprint 只写 SKILL 规则（"引用脚本"），不真实读取脚本，实际路径待 proposer 在写合同时 Step 1 读取。合同阶段真验证计划：proposer 执行 `find /workspace -name "*staging*deploy*" -o -name "auto-staging*"` 定位真实脚本后引用。
- **ZJ staging-promote 脚本路径**：同上，proposer 写合同时读取 ZJ 仓实际脚本路径。

---

## 约束与边界

1. **不改 autonomous 类合同任何现有规则**（零回归硬约束）
2. **staging 部署/promote 逻辑不在本 sprint 实现**，只写"引用方式"进 SKILL 文本
3. **BARK_URL 已在现有环境变量中**，无需新增凭据
4. **版本 bump 必须单调递增**：proposer 9.15.0 → 9.16.0，report 6.8.0 → 6.9.0
5. **不改 harness-report Phase B 逻辑**（db-update 调用不变）

---

## 衔接参考（先读再引用）

Generator 在实施前必须：
```bash
# 读取现有 staging 相关脚本（如有）
find /workspace -maxdepth 3 -name "*staging*" -o -name "*auto-staging*" -o -name "*promote*" 2>/dev/null | grep -v ".git" | head -20
# 读取 harness-report 现有 Bark 调用（复用）
grep -n "BARK_URL\|bark" /workspace/harness-report/SKILL.md | head -20
# 确认版本号
grep "^version:" /workspace/harness-contract-proposer/SKILL.md
grep "^version:" /workspace/harness-report/SKILL.md
```

---

## journey_type

## journey_type: autonomous

> 说明：本 sprint 是修改 SKILL 文档（规则文本），无前端 UI / 用户可见界面，属 autonomous 类（文档/规则级交付）。
> target_environment = local_api（验收用 grep 脚本，本地执行）

## target_environment: local_api
