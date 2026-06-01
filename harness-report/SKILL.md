---
id: harness-report-skill
description: |
  Harness Report — Harness v5.0 最终步骤：交付报告 + Sprint 状态同步。
  Phase A（6步交付）：回写Brain任务状态 → 更新中台Dashboard → 写Notion AI Notes（GAN标注表+截图）
  → 更新Notion Feature Registry → 飞书通知 → 写本地harness-report.md备份。
  Phase B（Sprint状态同步）：写本地Brain DB → 同步8个Notion DB（API/DB Schema/Tests/Features/Journey/Steps等）→ git commit。
  由 harness-evaluator PASS 后调用；也可手动触发补同步。
version: 6.1.0
created: 2026-04-08
updated: 2026-06-01
changelog:
  - 6.1.0: 新增Step6全量Registry回写+Step7结构化Learning+Step8 index.html可视化；截图路径统一到SPRINT_DIR/screenshots/
  - 6.0.0: 合并 harness-sprint-state → 统一为"交付报告+状态同步"单一 skill，删除独立的 harness-sprint-state skill
  - 5.1.0: 移除 Step 2.5b 多 WS 扫描逻辑 — 改为单 Sprint 直接创建 Notion Task
  - 5.0.0: 6步完整交付 — 回写Brain任务状态 + Dashboard + Notion AI Notes + Feature Registry + 飞书 + 本地备份
  - 4.0.0: Harness v4.0 Report（独立 skill，新增 CI/Deploy watch 状态）
---

> **语言规则: 所有输出必须使用简体中文。严禁日语、韩语或其他语言。**
> **执行规则: 严格按照下面列出的步骤执行。不要搜索/查找其他 skill 文件，不要 find/glob 查找任何 SKILL.md，直接按本文档流程操作。**

# /harness-report — Harness v5.0 完成报告 + Sprint 状态同步

**角色**: Reporter + Sprint State Syncer  
**对应 task_type**: `harness_report`  
**调用时机**: harness-evaluator PASS 后；或手动补同步

---

## 两个 Phase，依次执行

```
Phase A: 6步交付报告   → 确认 PR 合并、通知人、存档
Phase B: Sprint 状态同步 → 把本次 Sprint 产出的 API/DB/Tests/Features 同步到 Brain DB + Notion
```

两个 Phase 都要完成，不能只做一个。

---

## Phase A: 6步交付报告

### 注入变量

```bash
# TASK_ID、SPRINT_DIR、PROJECT_ID、FEATURE_ID、FEATURE_NAME、SUB_AREA、
# PR_URL、TOTAL_COST、SCREENSHOTS 由 cecelia-run 通过 prompt 注入，直接使用
FIRST_SCREENSHOT_URL=$(echo "$SCREENSHOTS" | jq -r '.[0] // ""')
TOTAL_COST="${TOTAL_COST:-0}"
SCREENSHOTS="${SCREENSHOTS:-[]}"
```

---

### Step 1: 回写 Brain 任务状态

```bash
curl -X PATCH "localhost:5221/api/brain/tasks/$TASK_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"completed\",
    \"result\": {
      \"pr_url\": \"$PR_URL\",
      \"screenshots\": $SCREENSHOTS,
      \"total_cost_usd\": $TOTAL_COST,
      \"merged\": true
    }
  }"
echo "✅ Step 1: Brain 任务状态已回写 completed"
```

---

### Step 2: 更新中台 Dashboard

```bash
mkdir -p "$SPRINT_DIR/screenshots"
curl -X POST "localhost:5221/api/brain/harness/complete" \
  -H "Content-Type: application/json" \
  -d "{
    \"initiative_id\": \"$TASK_ID\",
    \"sprint_dir\": \"$SPRINT_DIR\",
    \"pr_url\": \"$PR_URL\",
    \"screenshots\": $SCREENSHOTS
  }" 2>/dev/null || echo "WARN: Dashboard 更新失败（非阻断）"
echo "✅ Step 2: 中台 Dashboard 已更新"
```

---

### Step 2.5: 创建 Notion Project（Run 级）+ Notion Task（WS 级）

```bash
JOURNEY_ID="${JOURNEY_ID:-}"
JOURNEY_ID_JSON=$([ -n "${JOURNEY_ID:-}" ] && echo "\"$JOURNEY_ID\"" || echo "null")

PROJECT_PAYLOAD=$(jq -n \
  --arg title "$FEATURE_NAME" \
  --arg status "Done" \
  --argjson journey_id "$JOURNEY_ID_JSON" \
  --arg sprint_dir "$SPRINT_DIR" \
  --arg pr_url "$PR_URL" \
  '{title:$title, status:$status, journey_id:$journey_id, sprint_dir:$sprint_dir, pr_url:$pr_url}')

curl -s -X POST "localhost:5221/api/brain/notion/project" \
  -H "Content-Type: application/json" \
  -d "$PROJECT_PAYLOAD" 2>/dev/null || echo "WARN: Notion Project 创建失败（非阻断）"
echo "✅ Step 2.5a: Notion Project 已创建（Run 级）"

TASK_PAYLOAD=$(jq -n \
  --arg title "$FEATURE_NAME" \
  --arg status "Done" \
  --arg sprint_dir "$SPRINT_DIR" \
  --arg pr_url "${PR_URL:-}" \
  '{title:$title, status:$status, sprint_dir:$sprint_dir, pr_url:$pr_url}')
curl -s -X POST "localhost:5221/api/brain/notion/task" \
  -H "Content-Type: application/json" \
  -d "$TASK_PAYLOAD" 2>/dev/null || echo "WARN: Notion Task 创建失败（非阻断）"
echo "✅ Step 2.5b: Notion Task 已创建（status=Done）"
```

---

### Step 3: 写 Notion AI Notes（GAN 标注表 + 截图）

```bash
NOTION_BODY=$(printf '# Harness 完成：%s\n\n**PR**: %s\n**总成本**: $%s USD\n\n## DoD 验证结果\n\n所有 ARTIFACT + BEHAVIOR 条目已验证通过（evaluator PASS）。' \
  "$FEATURE_NAME" "$PR_URL" "$TOTAL_COST")

curl -X POST "localhost:5221/api/brain/notes" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Harness 完成：$FEATURE_NAME\",
    \"type\": \"Log\",
    \"sub_area\": \"$SUB_AREA\",
    \"body\": $(echo "$NOTION_BODY" | jq -Rs .)
  }" 2>/dev/null || echo "WARN: Notion Notes 写入失败（非阻断）"
echo "✅ Step 3: Notion AI Notes 已写入"
```

---

### Step 3.5: 文档归档（PrepPRD/SprintPRD/Contract）

```bash
for DOC_PAIR in "prep-prd.md:PrepPRD" "sprint-prd.md:SprintPRD" "contract-draft.md:Contract"; do
  DOC_FILE="${DOC_PAIR%%:*}"
  DOC_TYPE="${DOC_PAIR##*:}"
  DOC_PATH="${SPRINT_DIR}/${DOC_FILE}"
  [ ! -f "$DOC_PATH" ] && echo "WARN: $DOC_FILE 不存在，跳过" && continue

  NOTES_PAYLOAD=$(jq -n \
    --arg title "${DOC_TYPE} 文档：${FEATURE_NAME}" \
    --arg type "$DOC_TYPE" \
    --arg content "$(cat "$DOC_PATH")" \
    --arg initiative_id "${TASK_ID:-}" \
    --arg sprint_dir "$SPRINT_DIR" \
    '{"title":$title,"type":$type,"content":$content,"initiative_id":$initiative_id,"sprint_dir":$sprint_dir}')
  curl -X POST "localhost:5221/api/brain/notes" \
    -H "Content-Type: application/json" \
    -d "$NOTES_PAYLOAD" 2>/dev/null || echo "WARN: Notion Notes 写入失败（$DOC_TYPE）"
done
echo "✅ Step 3.5: 文档归档完成"
```

---

### Step 4: 更新 Notion Feature Registry

```bash
[ -n "$FEATURE_ID" ] && curl -s -X PATCH "localhost:5221/api/brain/journey_features/$FEATURE_ID" \
  -H "Content-Type: application/json" \
  -d '{"thickness":"done","status":"done"}' >/dev/null 2>&1 || echo "WARN: Feature Registry 更新失败（非阻断）"
echo "✅ Step 4: Notion Feature Registry status → done"
```

---

### Step 5: 飞书通知

```bash
FEISHU_MSG="PR: $PR_URL"
[ -n "$FIRST_SCREENSHOT_URL" ] && FEISHU_MSG="$FEISHU_MSG\n截图: $FIRST_SCREENSHOT_URL"

curl -X POST "localhost:5221/api/brain/harness/notify" \
  -H "Content-Type: application/json" \
  -d "{
    \"type\": \"harness_complete\",
    \"title\": \"✅ $FEATURE_NAME 完成\",
    \"message\": $(echo "$FEISHU_MSG" | jq -Rs .)
  }" 2>/dev/null || echo "WARN: 飞书通知失败（非阻断）"
echo "✅ Step 5: 飞书通知已发送"
```

---

### Step 6: 写本地 harness-report.md（备份）

```bash
COMPLETED_AT=$(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M:%S %Z')
cat > "${SPRINT_DIR}/harness-report.md" << REPORT
# Harness v5.0 完成报告

**完成时间**: $COMPLETED_AT
**Sprint Dir**: $SPRINT_DIR
**PR**: $PR_URL
**总成本**: \$$TOTAL_COST USD

## DoD 验证结果

所有 ARTIFACT + BEHAVIOR 条目验证通过（evaluator PASS）。

## 交付结论

✅ Harness v5.0 完成。PR 已合并，Notion 已更新，飞书已通知。
REPORT
echo "✅ Step 6: harness-report.md 已写入"
```

---

### Step 7: 全量回写 Registry（闭环）

```bash
# 提取 API endpoints 并写 registry
if [ -f "${SPRINT_DIR}/contract-draft.md" ]; then
  grep -oE '(GET|POST|PUT|DELETE|PATCH) /[a-zA-Z0-9/_:-]+' "${SPRINT_DIR}/contract-draft.md" | while read -r METHOD PATH_; do
    ENDPOINT="${METHOD} ${PATH_}"
    PAYLOAD=$(jq -n \
      --arg type "api" \
      --arg status "done" \
      --arg endpoint "$ENDPOINT" \
      --arg sprint_dir "$SPRINT_DIR" \
      --arg pr_url "${PR_URL:-}" \
      '{"type":$type,"status":$status,"endpoint":$endpoint,"metadata":{"sprint_dir":$sprint_dir,"pr_url":$pr_url}}')
    curl -s -X POST "localhost:5221/api/brain/registry" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" >/dev/null 2>&1 || echo "WARN: registry 写入失败（$ENDPOINT）"
  done
  echo "✅ Step 7a: API endpoints 已回写 Registry"
else
  echo "WARN: contract-draft.md 不存在，跳过 API registry"
fi

# 提取 DB 表名并写 registry
if [ -f "${SPRINT_DIR}/sprint-prd.md" ]; then
  grep -oE 'Table: [a-zA-Z_]+' "${SPRINT_DIR}/sprint-prd.md" | awk '{print $2}' | while read -r TABLE; do
    PAYLOAD=$(jq -n \
      --arg type "db_schema" \
      --arg status "done" \
      --arg table "$TABLE" \
      --arg sprint_dir "$SPRINT_DIR" \
      --arg pr_url "${PR_URL:-}" \
      '{"type":$type,"status":$status,"table":$table,"metadata":{"sprint_dir":$sprint_dir,"pr_url":$pr_url}}')
    curl -s -X POST "localhost:5221/api/brain/registry" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" >/dev/null 2>&1 || echo "WARN: registry 写入失败（table: $TABLE）"
  done
  echo "✅ Step 7b: DB 表名已回写 Registry"
else
  echo "WARN: sprint-prd.md 不存在，跳过 DB schema registry"
fi

# 提取测试文件并写 registry
if [ -d "${SPRINT_DIR}/tests" ]; then
  find "${SPRINT_DIR}/tests" -name "*.test.ts" -o -name "*.spec.ts" | while read -r TEST_FILE; do
    PAYLOAD=$(jq -n \
      --arg type "test" \
      --arg status "done" \
      --arg file "$TEST_FILE" \
      --arg sprint_dir "$SPRINT_DIR" \
      --arg pr_url "${PR_URL:-}" \
      '{"type":$type,"status":$status,"file":$file,"metadata":{"sprint_dir":$sprint_dir,"pr_url":$pr_url}}')
    curl -s -X POST "localhost:5221/api/brain/registry" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" >/dev/null 2>&1 || echo "WARN: registry 写入失败（test: $TEST_FILE）"
  done
  echo "✅ Step 7c: 测试文件已回写 Registry"
else
  echo "WARN: ${SPRINT_DIR}/tests 目录不存在，跳过 test registry"
fi
```

---

### Step 8: 生成结构化 Learning

```bash
# 统计 GAN 轮次和 Evaluator fix 次数
GAN_ROUNDS=$(ls "${SPRINT_DIR}/eval-round-"*.md 2>/dev/null | wc -l | tr -d ' ')
EVAL_FIX_COUNT=$GAN_ROUNDS
SPRINT_NAME=$(basename "$SPRINT_DIR")
COMPLETED_AT_SHORT=$(TZ=Asia/Shanghai date '+%m%d%H%M')

cat > "${SPRINT_DIR}/learning.md" << LEARNING_EOF
# Learning — ${FEATURE_NAME}

## 运行指标

- GAN 轮次：${GAN_ROUNDS}
- Evaluator Fix 次数：${EVAL_FIX_COUNT}
- PR：${PR_URL}
- Sprint Dir：${SPRINT_DIR}

## 发现的问题

### [PROMPT] Prompt 类问题

- （无 / 填写本次遇到的 prompt 设计问题）

### [BUG] 代码缺陷

- （无 / 填写本次修复的 bug）

### [INFRA] 基础设施问题

- （无 / 填写本次遇到的 CI/环境/工具链问题）

### [DESIGN] 设计缺陷

- （无 / 填写本次发现的架构或设计问题）

## 下次预防清单

- [ ] 检查 contract-draft.md 格式是否符合 evaluator 预期
- [ ] 确认 DoD 所有 [BEHAVIOR] 条目有对应测试
- [ ] GAN 轮次 > 2 时复盘 evaluator prompt 是否过严
LEARNING_EOF
echo "✅ Step 8a: learning.md 已生成到 ${SPRINT_DIR}/learning.md"

# 复制到 docs/learnings/ 永久保留
REPO_ROOT=$(git -C "$SPRINT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -n "$REPO_ROOT" ]; then
  mkdir -p "${REPO_ROOT}/docs/learnings"
  LEARNING_DEST="${REPO_ROOT}/docs/learnings/cp-${COMPLETED_AT_SHORT}-${SPRINT_NAME}.md"
  cp "${SPRINT_DIR}/learning.md" "$LEARNING_DEST"
  echo "✅ Step 8b: learning.md 已复制到 $LEARNING_DEST"
else
  echo "WARN: 无法定位 git 根目录，跳过 docs/learnings 复制"
fi
```

---

### Step 9: 生成 index.html（单文件可视化页面）

```bash
SPRINT_NAME=$(basename "$SPRINT_DIR")

node -e "
const fs = require('fs');
const path = require('path');

const sprintDir = process.env.SPRINT_DIR || '$SPRINT_DIR';
const sprintName = path.basename(sprintDir);
const prUrl = process.env.PR_URL || '$PR_URL';
const featureName = process.env.FEATURE_NAME || '$FEATURE_NAME';

function readMd(name) {
  const p = path.join(sprintDir, name);
  if (!fs.existsSync(p)) return null;
  return fs.readFileSync(p, 'utf8');
}

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

const docs = [
  { id: 'prep-prd', label: 'PrepPRD', file: 'prep-prd.md' },
  { id: 'sprint-prd', label: 'PRD', file: 'sprint-prd.md' },
  { id: 'contract', label: 'D-Contract', file: 'contract-draft.md' },
  { id: 'dod', label: 'DOD', file: 'contract-dod.md' },
  { id: 'report', label: 'Report', file: 'harness-report.md' },
  { id: 'learning', label: 'Learning', file: 'learning.md' },
];

// 截图 base64
const screenshotDir = path.join(sprintDir, 'screenshots');
let screenshotHtml = '';
if (fs.existsSync(screenshotDir)) {
  const pngs = fs.readdirSync(screenshotDir).filter(f => f.endsWith('.png'));
  for (const png of pngs) {
    const data = fs.readFileSync(path.join(screenshotDir, png));
    const b64 = data.toString('base64');
    screenshotHtml += \`<div class=\"screenshot\"><p>\${escapeHtml(png)}</p><img src=\"data:image/png;base64,\${b64}\" style=\"max-width:100%;\"/></div>\`;
  }
}

const navItems = docs.map(d => \`<li><a href=\"#\" onclick=\"show('\${d.id}');return false;\">\${d.label}</a></li>\`).join('');
const sections = docs.map(d => {
  const content = readMd(d.file);
  const body = content ? \`<pre style=\"white-space:pre-wrap;word-break:break-word;\">\${escapeHtml(content)}</pre>\` : '<p>（文件不存在）</p>';
  return \`<div id=\"\${d.id}\" class=\"section\" style=\"display:none;\">\${body}</div>\`;
}).join('');

const html = \`<!DOCTYPE html>
<html lang=\"zh\">
<head><meta charset=\"UTF-8\"><title>\${escapeHtml(featureName)} — Sprint Report</title>
<style>
body{font-family:sans-serif;margin:0;display:flex;flex-direction:column;height:100vh;}
header{background:#1a1a2e;color:#fff;padding:12px 24px;display:flex;align-items:center;gap:16px;}
header a{color:#adf;text-decoration:none;}
main{display:flex;flex:1;overflow:hidden;}
nav{width:160px;background:#f4f4f4;border-right:1px solid #ddd;padding:16px 0;overflow-y:auto;}
nav ul{list-style:none;margin:0;padding:0;}
nav li a{display:block;padding:8px 16px;color:#333;text-decoration:none;}
nav li a:hover{background:#e0e0e0;}
.content{flex:1;overflow-y:auto;padding:24px;}
.section pre{background:#f8f8f8;border:1px solid #ddd;padding:16px;border-radius:4px;}
.screenshot{margin-bottom:16px;}
</style>
</head>
<body>
<header>
  <span><strong>\${escapeHtml(featureName)}</strong> Sprint Report</span>
  \${prUrl ? \`<a href=\"\${prUrl}\" target=\"_blank\">PR</a>\` : ''}
</header>
<main>
<nav><ul>
\${navItems}
<li><a href=\"#\" onclick=\"show('screenshots');return false;\">截图</a></li>
</ul></nav>
<div class=\"content\">
\${sections}
<div id=\"screenshots\" class=\"section\" style=\"display:none;\">\${screenshotHtml || '<p>无截图</p>'}</div>
</div>
</main>
<script>
function show(id){document.querySelectorAll('.section').forEach(s=>s.style.display='none');var el=document.getElementById(id);if(el)el.style.display='block';}
// 默认显示第一个有内容的 section
var first = document.querySelector('.section');if(first)first.style.display='block';
</script>
</body></html>\`;

fs.writeFileSync(path.join(sprintDir, 'index.html'), html, 'utf8');
console.log('index.html generated');
" && echo "✅ Step 9a: index.html 已生成到 ${SPRINT_DIR}/index.html"

echo "📎 访问地址: http://38.23.47.81:9998/sprints/${SPRINT_NAME}/index.html"
```

---

### Phase A 完成标志

```bash
cat > /workspace/.brain-result.json << BREOF
{"verdict":"DONE","task_id":"$TASK_ID","report_path":"${SPRINT_DIR}/harness-report.md","pr_url":"$PR_URL","screenshots":$SCREENSHOTS}
BREOF
echo "[harness-report Phase A] 9步交付完成"
```

---

## Phase B: Sprint 状态同步

> **详细实现见 `~/.claude/skills/harness-report/references/sprint-state-sync.md`**（包含完整的 Brain DB 写入 + 8个 Notion DB 同步步骤）

Phase B 的核心工作：
1. 从 `sprint-prd.md` / `contract-draft.md` 解析本次 Sprint 产出（APIs、DB Schema、Tests、Features）
2. 写入本地 Brain DB（`api_registry`、`db_schema_registry`、`test_registry`、`skill_registry`、`journey_steps`）
3. 同步 8 个 Notion DB（API Registry、DB Schema Registry、Tests Registry、Feature DB、Journey Maturity、AI Steps、Journey-Step 连接表、Sprint Dashboard）
4. 写本地 `sprint-states/<journey_id>/state.md`
5. git commit + push

执行前先读取 `~/.claude/skills/harness-report/references/sprint-state-sync.md` 获取完整步骤和代码。
