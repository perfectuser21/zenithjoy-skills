# Sprint PRD — staging 预览闸补丁（harness-contract-proposer + harness-report）

## OKR 对齐

- **对应 KR**：harness 质量门完整性（user_facing 禁直上 prod）
- **当前进度**：N/A（skill 元改动）
- **本次推进预期**：user_facing 合同强制含 staging 预览步，report 收尾登记放行状态

## 背景

决策34a7ad72：user_facing 禁直上 prod。案例：指挥舱空白(Cecelia)/16步画像卡(ZJ)均主理人 prod 首踩雷。改 zenithjoy-skills：①harness-contract-proposer 合同加 staging 预览步规则；②harness-report 收尾加 Bark 通知+放行状态登记。既有 staging_e2e 派生（harness-controller Step 6，`POST /api/brain/harness/staging-e2e`）只引用不重造。autonomous 类流程零回归。

## Golden Path（核心场景）

用户/系统从 [proposer 识别 journey_type=user_facing] → 经过 [合同加 staging 预览步 → merge → Final E2E in staging → Bark 通知 → 放行判定] → 到达 [prod promote 获主理人授权]

具体：
1. proposer 读 sprint-prd.md，journey_type=user_facing 时，contract-draft.md 末尾写入 `## staging 预览闸` 段（三步：A落staging / B Final-E2E在staging跑截图 / C Bark推主理人预览链接，复用 BARK_URL）
2. 按 BASE_REPO 判定模式：cecelia 仓=通知式（Bark 注明「24h 无异议自动放行」），ZJ 仓=阻塞式（主理人须写入 approval 字段，未放行禁 promote）
3. evaluator PASS 后 harness-report Phase A 新增 Step 5.5（user_facing 专属）：Bark 推主理人 + Brain PATCH 写 promote_after 时间戳（cecelia）或 approval_required 标记（ZJ）

## 边界情况

- autonomous/dev_pipeline/agent_remote：不加 staging 预览步（零回归）
- Bark/Brain PATCH 失败：CONCERN 记录，不阻断 report（best-effort）
- BASE_REPO 未知：默认 ZJ 阻塞式（更保守）

## 范围限定

**在范围内**：harness-contract-proposer/SKILL.md 文本修改（版本 9.15.0→9.16.0）；harness-report/SKILL.md 文本修改（版本 6.8.0→6.9.0）
**不在范围内**：cecelia auto-staging-deploy 脚本实现；harness-controller Step 6 staging_e2e 派生逻辑；autonomous 类合同任何现有规则

## 假设

- [ASSUMPTION: BARK_URL 已作为环境变量在 harness-report 执行上下文可用]
- [ASSUMPTION: staging_e2e 派生由 harness-controller 负责，本 sprint 只在 report 层引用结果]
- [ASSUMPTION: promote_after 时间戳写入 task custom_props 字段（Brain PATCH tasks/:id）]

## 预期受影响文件

- `harness-contract-proposer/SKILL.md`：新增 user_facing staging 预览步硬规则 + 版本 bump + changelog
- `harness-report/SKILL.md`：新增 Phase A Step 5.5（Bark 推送 + Brain PATCH）+ 版本 bump + changelog

## E2E 验收

```bash
# proposer GAN 阶段补全完整脚本；以下为验收点框定：
# 1. harness-contract-proposer/SKILL.md grep 到「staging 预览闸」与 user_facing 联动规则
grep -q "staging 预览闸" /workspace/harness-contract-proposer/SKILL.md || { echo "FAIL: proposer 缺 staging 预览闸"; exit 1; }
grep -qE "autonomous.*零回归|autonomous.*不受本规则|journey_type=user_facing.*staging|staging.*user_facing" /workspace/harness-contract-proposer/SKILL.md || { echo "FAIL: 缺 user_facing/autonomous 分支规则"; exit 1; }
# 2. harness-report/SKILL.md grep 到 promote_after 与 Bark 条款
grep -q "promote_after" /workspace/harness-report/SKILL.md || { echo "FAIL: report 缺 promote_after 登记"; exit 1; }
grep -qE "BARK_URL|Bark.*user_facing|user_facing.*Bark" /workspace/harness-report/SKILL.md || { echo "FAIL: report 缺 Bark 通知"; exit 1; }
# 3. 版本号 bump
grep -q "version: 9.16.0" /workspace/harness-contract-proposer/SKILL.md || { echo "FAIL: proposer 版本未 bump"; exit 1; }
grep -q "version: 6.9.0" /workspace/harness-report/SKILL.md || { echo "FAIL: report 版本未 bump"; exit 1; }
# 4. autonomous 零回归负向验证
grep -qE "autonomous.*必须.*staging|autonomous.*强制.*staging" /workspace/harness-contract-proposer/SKILL.md && { echo "FAIL: autonomous 被错误纳入 staging 规则"; exit 1; } || true
echo "ALL AC PASS"
```

## NFR 约束

<!-- 来源: decisions 表 category=nfr，PrepPRD 显式值优先 -->
- 超时/延迟: Bark/Brain PATCH best-effort，失败不阻塞
- 频控: 每次 user_facing 合同一条 Bark 推送
- 版本要求: proposer 9.16.0（单调递增）；report 6.9.0（单调递增）
- 可观测: Step 5.5 失败必须写 `.report-concerns`

## Invariant 约束（铁律，proposer/evaluator 不得违反）

<!-- 来源: decisions category=invariant，step + journey_feature + area 三源合并去重 -->
- [零回归] autonomous/dev_pipeline/agent_remote 类合同禁止加 staging 预览步（来源: thin_prd 决策34a7ad72）
- [await] 测试文件读源码必须包装 async function，不能直接 readFileSync（来源: area）
- [Red-commit] git add 精确路径，禁止 git add .（来源: area）
- [generator-no-merge] generator 禁自行 merge PR，merge 权归 controller（来源: area）

## 累积 FR（本 line 已验收行为，本 sprint 不得回退/重复）

（本 line 暂无历史——journey_id=null，无可查 journey golden-paths）

## journey_type: dev_pipeline
## journey_type_reason: 改的是 skill 元文件（harness 工具链规则文本），属 packages/engine 类 dev_pipeline，无 Dashboard UI/agent 协议/Brain API 行为变更
## target_environment: local_api
## target_environment_reason: 验收为 SKILL.md 文本 grep 断言，本机 local_api 执行即可
## journey_id: none
## step_id: none（PrepPRD 未锚定）
