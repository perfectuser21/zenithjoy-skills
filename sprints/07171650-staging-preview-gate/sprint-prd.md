# user_facing 交付 staging 预览闸进合同法律：Cecelia=24h通知式/ZJ=阻塞式点头

> **决策来源**: 34a7ad72（2026-07-16，cecelia，level=ability，category=process，status=active）
> **任务 ID**: 8589b916-9b71-4dd8-a986-76670229b06d
> **Sprint 目录**: sprints/07171650-staging-preview-gate
> **版本目标**: harness-contract-proposer v9.16.0 + harness-report v6.9.0

## 背景与动机

历史教训：指挥舱空白（Cecelia）和 16步画像卡（ZJ）均为 user_facing 功能直上 prod，主理人首踩雷。根因：合同未强制 user_facing 类交付在 merge 后先落 staging 再由主理人确认。

## 本次变更范围

### 改动 ①：harness-contract-proposer/SKILL.md（v9.15.0 → v9.16.0）

凡 `journey_type=user_facing` 的合同，必须在末尾含 `## staging 预览闸` 段，包含三步：

**步骤 A — 落 staging**：merge 后先部署到对应 staging 实例（Cecelia=localhost:5212，ZJ=ZJ staging），复用现有 staging 脚本，只引用不重造。

**步骤 B — Final E2E 在 staging 跑**：E2E 目标地址改为 staging 地址，截图存 `${SPRINT_DIR}/screenshots/staging-<step>.png`。

**步骤 C — Bark 推主理人预览链接**（复用 `$BARK_URL`），按 `$BASE_REPO` 判模式：
- `cecelia` 仓 → **通知式**：Bark 注明「24h 无异议自动放行」，Brain PATCH task metadata 写 `promote_after` 时间戳
- `zenithjoy` 仓 → **阻塞式**：Bark 注明「需主理人放行」，prod promote 前必须核查 `decisions` 表或 task `approval` 字段，未放行禁 promote

`journey_type=autonomous` 流程零回归：本规则仅限 user_facing，autonomous 合同不受约束。

### 改动 ②：harness-report/SKILL.md（v6.8.0 → v6.9.0）

Phase A Step 5（飞书通知）之后，新增 **Step 5.5**（仅 journey_type=user_facing 时执行）：
1. Bark 推送 staging 预览链接 + 截图 URL
2. Brain PATCH：Cecelia 仓写 `promote_after`（UTC+24h）；ZJ 仓写 `approval_required: true`
3. 失败属非关键步（CONCERN，不阻断）

## Invariant 约束

- INV-1：autonomous 流程零回归，journey_type=autonomous 的合同不得含 staging 预览步强制要求
- INV-2：版本号必须单调递增（proposer 9.15.0→9.16.0，report 6.8.0→6.9.0）
- INV-3：staging 部署/promote 逻辑本 sprint 不实现，只写引用方式进 SKILL 文本
- INV-4：不改 harness-report Phase B 逻辑（db-update 调用不变）

## 累积 FR

context-manifest 端点不可达，累积 FR 加载：N/A（/api/brain/line/context-manifest 返回 Cannot GET）

## NFR

- 无性能要求（纯 SKILL 文本改动）
- 版本 bump 必须准确写入 changelog
- Bark/Brain PATCH 失败为 CONCERN 非阻断

## 验收标准（含可执行 bash 断言）

```bash
# AC-1: proposer SKILL 含关键词
grep -q "staging 预览闸" harness-contract-proposer/SKILL.md || { echo "FAIL: 无 staging 预览闸"; exit 1; }
grep -q "通知式" harness-contract-proposer/SKILL.md || { echo "FAIL: 无通知式条款"; exit 1; }
grep -q "阻塞式" harness-contract-proposer/SKILL.md || { echo "FAIL: 无阻塞式条款"; exit 1; }
grep -q "promote_after" harness-contract-proposer/SKILL.md || { echo "FAIL: 无 promote_after"; exit 1; }
grep -qE "autonomous.*不受本规则|autonomous.*零回归|autonomous.*不强制" harness-contract-proposer/SKILL.md || { echo "FAIL: 无 autonomous 豁免"; exit 1; }
# AC-2: report SKILL 含 Step 5.5
grep -q "5\.5" harness-report/SKILL.md || { echo "FAIL: harness-report 无 Step 5.5"; exit 1; }
grep -q "promote_after" harness-report/SKILL.md || { echo "FAIL: 无 promote_after"; exit 1; }
# AC-3: 版本 bump
grep -qE "^version: 9\.16\.0" harness-contract-proposer/SKILL.md || { echo "FAIL: proposer 版本未 bump"; exit 1; }
grep -qE "^version: 6\.9\.0" harness-report/SKILL.md || { echo "FAIL: report 版本未 bump"; exit 1; }
# AC-4: autonomous 零回归
grep -qE "autonomous.*必须.*staging|autonomous.*强制.*staging" harness-contract-proposer/SKILL.md && { echo "FAIL: autonomous 被错误纳入"; exit 1; } || true
echo "ALL AC PASS"
```

## 禁 mock 边清单

N/A（纯文档/SKILL 改动，无代码接缝边）

## 未覆盖真实链路清单

- cecelia auto-staging-deploy / ZJ staging-promote 脚本真实路径：proposer 写合同时须 `find` 定位后引用，本 sprint SKILL 只写规则引用占位

## journey_type: autonomous

> 本 sprint 是修改 SKILL 文档（规则文本），无前端 UI，属 autonomous 类。

## target_environment: local_api
