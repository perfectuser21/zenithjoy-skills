---
name: cecelia-harness-debug
description: |
  Cecelia harness pipeline 7 层 bug 优先级 filter。遇到任何"不符合预期"的行为先触发本 skill 排查"应该先怀疑哪一层"，定位后**必须接力** superpowers:systematic-debugging 深挖。
  专门解决 LLM-agent 系统 debug 难定位的痛点：每次都是"我以为 X 修 X，发现不对再修 Y"浪费几小时。

  Use when ANY of these:
  - harness pipeline 行为不符预期（task=completed 但 verdict=FAIL，generator 漂移，evaluator 漏判）
  - skill 改了但 LLM 没生效
  - brain restart 后行为没变
  - agent 间数据流断点
  - PR 合并后 W 任务结果不符预期
  - 任何"我以为 X，但 Y 发生了"

  Triggers: 触发词包括 debug、排查、不对、没生效、为什么、怎么回事、卡了、跑挂了。
---

# Cecelia Harness Debug — 7 层优先级 Filter

> **语言规则**: 所有输出简体中文。
> **执行规则**: 严格按 7 层顺序排查，禁跳层。每层 5 min 内出结论。

## 角色

LLM-agent 系统 debug 优先级排查官。**不修 bug**，只定位到根因层，然后接力 `superpowers:systematic-debugging` 深挖修复。

## Iron Law（铁律）

```
不按 7 层顺序排查就直接修 = 大概率修错层 → 浪费几小时
```

历史教训（每次都是跳层导致）：
- W21: 跳过 Layer 1（host main 没 pull）→ brain 跑旧代码 38 min 浪费
- W22: 跳过 Layer 4（agent 间协议矛盾）→ PR A 没对齐 proposer
- W23: 跳过 Layer 2（SKILL discovery）→ reviewer 没读 v6.2 SKILL，PR C 部分失效

每层有具体诊断命令——5 分钟跑完 7 层定位根因，比 "直接修" 模式省几小时。

---

## 7 层 Checklist

按"应该先怀疑"顺序。每层跑诊断命令，PASS → 进下一层；FAIL → 锁定根因层，跳到 Handoff 段。

### Layer 1: 配置/部署（最先怀疑）

**症状**：改了代码/SKILL，部署后行为没变。

**为什么先看**：最常见、最便宜定位（grep 命令秒级出结果）、跳过它会浪费整个 W 任务（W21 实证 38 min）。

**诊断命令**（按需替换 `<changed-file>` 与 `<key>` 标识）：

```bash
# 1. host main 是不是最新？
cd /Users/administrator/perfect21/cecelia
git fetch origin main 2>&1 | tail -1
LOCAL=$(git rev-parse main)
REMOTE=$(git rev-parse origin/main)
[ "$LOCAL" = "$REMOTE" ] && echo "✅ main is latest" || echo "❌ main 落后 origin/main: local=$LOCAL remote=$REMOTE"

# 2. 改的代码/SKILL 在 host 是否到位
grep -c "<key>" packages/<changed-file>
# 期望 ≥ 1；为 0 → 改动没合到 main 或 host 没 pull

# 3. brain container 是否用最新代码（mount path 一致）
NEWID=$(docker ps -q -f name=cecelia-node-brain)
docker exec $NEWID grep -c "<key>" /Users/administrator/perfect21/cecelia/packages/<changed-file>

# 4. brain restart 时间在改后？
docker inspect $NEWID --format 'StartedAt: {{.State.StartedAt}}'
git log -1 --format='%ai' origin/main
# StartedAt 必须 > git commit time
```

**FAIL signal**: 任一显示旧版/落后/StartedAt 在改前 → **Layer 1 是根因**。

**Fix path**:
```bash
git stash
git pull --ff-only origin main
bash scripts/brain-reload.sh
sleep 3
curl -s localhost:5221/api/brain/health | jq -c '.status,.uptime_seconds'
```

**Memory 引用**: `feedback_brain_pull_before_reload`

---

### Layer 2: SKILL Discovery（LLM 实际读到的 SKILL）

**症状**：Layer 1 PASS（代码到位），但 LLM 行为还是旧 pattern（看输出像 SKILL 没改）。

**为什么先看（在 Layer 3 缓存前）**：discovery 是确定性 bug，缓存是概率性。先排查确定性。

**诊断命令**（按需替换 TID）：

```bash
TID=<your task UUID>

# 1. 找 LLM 实际收到的 prompt
LATEST=$(ls -t /Users/administrator/claude-output/cecelia-prompts/$TID*.prompt 2>/dev/null | head -1)
echo "Prompt file: $LATEST"
[ -z "$LATEST" ] && echo "❌ 找不到 prompt 文件" && exit

# 2. LLM 看到的 SKILL version 是不是最新？
grep -E "^version:" "$LATEST" | head -3
# 跟 packages/workflows/skills/<skill>/SKILL.md 的 version 对比

# 3. LLM 看到的 prompt 含你改的关键标识吗？
grep -c "<key>" "$LATEST"
# 期望 ≥ 1；为 0 → LLM prompt 不含你改的 SKILL → discovery bug

# 4. brain 是用 slash command 还是 inline SKILL 内容？
head -3 "$LATEST"
# 第一行是 "/skill-name" → slash command（container 自己解析，可能读旧 SKILL）
# 第一行是 "你是 X agent" + SKILL 内容 → inline（最新内容直传）
```

**FAIL signal**: prompt 里没你改的 key / SKILL version 是旧版 → **Layer 2 是根因**。

**Fix path 选项**:
- A. brain prompt 改成 inline SKILL.md 内容（不用 slash command）—— 最彻底
- B. 排查 container 内 skill resolver 路径，让它读 mount 的 SKILL

**已知**: W23 实证 reviewer/proposer 有此 bug — slash command 解析到旧 SKILL。

---

### Layer 3: 缓存（LLM 复用旧响应）

**症状**：Layer 1+2 PASS，prompt 看起来对，但 LLM 输出还是旧 pattern。

**诊断命令**:

```bash
TID=<your task UUID>
LATEST_STDOUT=$(ls -t /Users/administrator/claude-output/cecelia-prompts/$TID*.stdout 2>/dev/null | head -1)

# 看缓存命中比例
cat "$LATEST_STDOUT" | jq -c '.usage | {input: .input_tokens, cache_read: .cache_read_input_tokens, cache_creation: .cache_creation_input_tokens}'

# cache_read / (cache_read + cache_creation + input) > 0.5 → 高复用，可能命中旧响应
```

**FAIL signal**: cache_read 高（> 50% input） + 输出 pattern 跟之前任务相似 → 可能命中旧响应。

**Fix path**:
- 改 prompt 前缀打破缓存（加 task id / timestamp 进 system prompt）
- 或等 1h cache 过期重试

**注意**: 缓存层很难 100% 确认是它的问题。如果 Layer 1+2 都 PASS 但还失败，先怀疑这层但同时也看 Layer 4。

---

### Layer 4: 协议/接口（agent 间 SKILL 协议矛盾）

**症状**：Layer 1+2+3 PASS，单独审每个 SKILL 都对，但 agent A 输出不满足 agent B 期望。

**诊断命令**:

```bash
# 列出涉及 agent 间通信的关键概念（数据字段、文件路径、命令格式等）
CONCEPT="<共享概念，如 BEHAVIOR / contract-dod-ws / verdict>"

# 比对所有 SKILL 对该概念的定义
for skill in packages/workflows/skills/harness-*/SKILL.md; do
  echo "=== $skill ==="
  grep -A 2 "$CONCEPT" "$skill" | head -10
done

# 看是否有协议矛盾（A 说 X 在位置 P，B 找位置 Q）
```

**FAIL signal**: 不同 SKILL 对同一概念定义不一致 → **Layer 4 是根因**。

**Fix path**: 统一协议，改其中一方 SKILL 让两边对齐。改完必须**两个 SKILL 都重新审一遍**。

**已知**: W22 实证 BEHAVIOR 位置矛盾（PR C 修了），但还有 query name 协议、verdict 字段等可能存在类似问题。

---

### Layer 5: SKILL 内容（单一 SKILL prompt 写不严）

**症状**：Layer 1-4 PASS，协议一致，但 LLM 自由发挥导致输出漂移。

**诊断**:

```bash
# 读 SKILL 找"自由度太高"的指令
SKILL_FILE=packages/workflows/skills/<skill>/SKILL.md
cat $SKILL_FILE

# 标记 high-freedom 词:
# - "尽量..." / "建议..." / "应该..." → 改 "必须" / "禁止"
# - "覆盖 X" 没说数量 → 改 "至少 N 条"
# - 模板用 "示例" 单数 → 改 4 条不同场景示例
# - 反例缺失 → 加 "禁止" 反例
```

**FAIL signal**: SKILL 用太多软词 / 缺硬阈值 / 缺反例 → **Layer 5 是根因**。

**Fix path**: 加硬约束 + 数量阈值 + 正反例。

---

### Layer 6: 架构（节点流/数据流根本设计错）

**症状**：Layer 1-5 都修了仍失败 / 同一个 bug 反复出现。

**诊断**: 看 graph 定义、数据流图、识别反模式（如 W8 自指环路）。

**Fix path**: 重新设计架构而不是继续修 SKILL。

**触发条件**: superpowers:systematic-debugging 也说"3 次 fix 失败 = 质疑架构"。

---

### Layer 7: 代码（最后怀疑）

**症状**：Layer 1-6 都对，但 implementation 真有 bug。

**诊断**: unit test / git log / 单步调试。

**Fix path**: 修代码 + 加 test。

**为什么放最后**: 代码有 TS/lint/test/CI 多层强约束，最不易出错。

---

## Handoff 段（定位根因层 N 之后）

**强制接力**：定位到 Layer N 后，**下一个 tool call 必须是**：

```
Skill({"skill":"superpowers:systematic-debugging"})
```

然后按 systematic-debugging 4 phases 深挖：
- Phase 1 Root Cause（focus 在 Layer N，做 multi-component evidence gathering）
- Phase 2 Pattern Analysis（找 working example）
- Phase 3 Hypothesis & Testing（单一假设 + 最小测试）
- Phase 4 Implementation（写失败测试 + 单一 fix + 验证）

**禁止**：在 cecelia-harness-debug 里直接写代码修。本 skill 只定位，不修复。

## 反模式 Red Flags（出现立即停）

- "我直接知道是 Layer 5 SKILL 问题，跳过 1-4" → 错，每次必按顺序跑 1
- "Layer 1 上次 OK 这次也 OK，跳过" → 错，每次必跑（W21 实证）
- "看起来 Layer 3 缓存不太可能" → 错，数据说话不靠直觉
- "改完赶时间，先修再说" → 错，5 min 排查比几小时 thrashing 快
- "我先做几个修复试试" → 错，违反 systematic-debugging Iron Law

## 输出格式

完成 7 层排查后，输出：

```
## 根因层定位
**Layer N**: <层名>

## 诊断证据
<具体哪个命令 FAIL，输出是什么>

## Fix path
<对应 fix 方案概述>

## 接力
下一步 invoke superpowers:systematic-debugging 深挖修复。
```

## 实证教训表（提醒未来）

| W 任务 | 跳层 | 浪费时间 | 真根因层 |
|---|---|---|---|
| W21 | 跳 Layer 1 | 38 min（整个 pipeline 跑旧代码）| Layer 1 配置 |
| W22 | 跳 Layer 4 | PR A 没修彻底 | Layer 4 协议 |
| W23 | 跳 Layer 2 | PR C reviewer 部分失效 | Layer 2 discovery |

每次"先排查再修"5 min vs "直接修"几小时——选哪个？
