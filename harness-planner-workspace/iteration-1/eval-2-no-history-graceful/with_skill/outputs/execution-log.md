# execution-log — 实际执行过的 curl 命令（每行一条）

> 说明：生产 Brain（localhost:5221）在本次执行期间连接拒绝（容器未运行），所有 curl 按 SKILL 自带的 `|| echo '[]' / '{}'` 兜底降级为空数据继续，未报错中断。

curl -sf "localhost:5221/api/brain/context" > /tmp/brain_context.json 2>/dev/null || echo '{}' > /tmp/brain_context.json
curl -sf "localhost:5221/api/brain/tasks/49ec2792-7d81-4690-bbbd-42c534e1fb1c" || echo '{}'   # TASK_JSON（替代 $TASK_PAYLOAD），jq 提取 ability_id/journey_id 均为空
curl -sf "localhost:5221/api/brain/tasks/49ec2792-7d81-4690-bbbd-42c534e1fb1c/golden-path-decisions?category=nfr" > /tmp/nfr_decisions.json 2>/dev/null || echo '[]' > /tmp/nfr_decisions.json
# （journey_feature 级 NFR：ABILITY_ID 为空 → 未发 curl，直接 echo '[]' > /tmp/nfr_feature.json）
curl -sf "localhost:5221/api/brain/tasks/49ec2792-7d81-4690-bbbd-42c534e1fb1c/golden-path-decisions?category=invariant" > /tmp/inv_step.json 2>/dev/null || echo '[]' > /tmp/inv_step.json
# （journey_feature 级 invariant：ABILITY_ID 为空 → 未发 curl，直接 echo '[]' > /tmp/inv_feature.json）
curl -sf "localhost:5221/api/brain/invariants?level=area" > /tmp/inv_area.json 2>/dev/null || echo '[]' > /tmp/inv_area.json
# （累积 FR：JOURNEY_ID 为空 → 未发 curl，直接 echo '[]' > /tmp/line_fr.json —— SKILL Step 0.4 ④ 优雅降级分支）
# （initiative_runs 历史：payload.journey_id 为空 → 按 Step 0.1 条件未调用 /api/brain/harness/runs）

# 诊断性 curl（非 SKILL 步骤，用于确认 5221 状态）：
curl -s -o /dev/null -w "%{http_code}" "http://localhost:5221/api/brain/context"   # → 000 connection refused
curl -s -o /dev/null -w "%{http_code}" "http://localhost:5221/api/brain/ping"      # → 000 connection refused
