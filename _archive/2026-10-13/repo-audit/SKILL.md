---
name: repo-audit
description: 主理人 3 层 Repo 审核。扫描任意 repository 的真实健康状态，输出评分卡 + 反模式命中 + 优先修复计划。核心原则是"先怀疑再证明"——CI 全绿不代表健康，必须读配置文件验证。当用户说"审一下 repo"、"跑 audit"、"看看仓库健康"、"repo 主理人检查"、"帮我查查这个仓库有没有问题"、"/repo-audit" 时触发。也适合在设置新主理人、建立 baseline 分数、每周定期检查时使用。
---

# /repo-audit — 主理人审核框架

**核心原则：表面红很容易发现，表面绿才是真正的危险。**

所有"绿"信号都不可信，直到配置文件证明它可信为止。禁止用表面信号直接打分——CI 通过不等于 CI 健康，文件存在不等于功能有效。

---

## 3 层 24 项评分模板

```
L1 管业务（6项）  —— 在做对的事吗？
L2 管仓库（13项） —— 系统能撑住吗？（代码层 7 + 运行层 6）
L3 管沟通（5项）  —— 信息流通吗？
```

评分：✅ 5（配置证明健康）/ ⚠️ 3（命中 1 个反模式）/ ❌ 1（缺失或命中 2+）/ 🔴虚假绿（表面绿但配置腐烂，最危险）

### L1 管业务
| # | 项目 | 检查方式 |
|---|------|---------|
| 1 | OKR 清晰度 | Brain API 查 active goals，有没有脏数据/测试条目污染？ |
| 2 | 任务可执行性 | 任务拆解到 PR 级了吗？近期有实际交付吗？ |
| 3 | 进度可见性 | Dashboard/报告能看到真实进度吗？还是空壳？ |
| 4 | 定期复盘 | 有 retrospective 记录吗？上次是什么时候？ |
| 5 | 资源成本控制 | API/算力成本有没有被追踪？ |
| 6 | 战略方向验证 | 这个 repo 解决的问题现在还成立吗？ |

### L2 管仓库 — 代码层
| # | 项目 | 检查方式 |
|---|------|---------|
| 7 | CI 有效性 | 运行 `scripts/check-ci.sh`，对照反模式清单。全绿但命中反模式 → 🔴虚假绿 |
| 8 | 代码质量 | `--max-warnings` 是多少？TypeScript strict？警告趋势上涨还是下降？ |
| 9 | 测试有效性 | 运行 `scripts/check-tests.sh`：test/source 比例、覆盖率门禁、是否全 mock |
| 10 | 依赖安全 | 运行 `scripts/check-deps.sh`：**根目录** npm audit，不在子目录，不 --omit=dev |
| 11 | 技术债 | 单文件 >500 行清单 + TODO/FIXME 积累数量 + **文档腐烂**（见 Step 2c） |
| 12 | 可观测性 | 结构化日志（winston/pino）？/health 端点？外部错误上报（Sentry）？ |
| 13 | 安全态势 | 运行 Step 2b 的 grep；.gitignore 覆盖 .env；branch protection `enforce_admins`。**发现硬编码密钥 → 直接 ❌ 1，无例外** |

### L2 管仓库 — 运行层
| # | 项目 | 检查方式 |
|---|------|---------|
| 14 | 可执行性 | 主链路端到端能跑通吗？入口→处理→输出全通？ |
| 15 | 注册表鲜活 | 注册在册的资源（Skills/Agents/服务）还活着吗？ |
| 16 | 数据完整性+灾备 | 孤岛/僵尸数据？DB 有备份策略吗？ |
| 17 | 自动化覆盖 | 还有多少步骤需要人工触发？ |
| 18 | 闭环率 | 发布→采集→分析→选题的反馈环在转吗？ |
| 19 | SLO 基线 | 有没有定义"正常"是什么？有异常阈值吗？ |

### L3 管沟通
| # | 项目 | 检查方式 |
|---|------|---------|
| 20 | 向上汇报 | 有自动日报/飞书推送给 Alex 吗？（有 webhook 代码，不是有登录组件） |
| 21 | 卡点上报 | P0 出现时有主动告警机制吗？ |
| 22 | 决策提请 | 需要 Alex 判断时有提出来的机制吗？ |
| 23 | 横向协调 | Agent 任务分配清晰？反馈能回收吗？ |
| 24 | 事故响应 | 有 P0 playbook 吗？ |

---

## 执行流程

### Step 1 — 存在性侦测
```bash
# 判断 repo 类型，决定后续检查路径
ls .github/workflows/ 2>/dev/null && echo "有 CI"
curl -s http://localhost:5221/api/brain/goals 2>/dev/null | jq 'length' && echo "有 Brain"
ls package.json 2>/dev/null && echo "Node 项目"
ls requirements.txt setup.py pyproject.toml 2>/dev/null && echo "Python 项目"
```

### Step 1.5 — 配置文件精读（不能跳过，这是发现虚假绿的关键）

运行 `scripts/check-ci.sh` 并记录反模式命中：

```
CI 反模式清单：
□ admin_bypass      — enforcement_level: non_admins
□ audit_scope_wrong — npm audit 只在子目录 / 用 --omit=dev
□ no_coverage_gate  — 有 --coverage 但无 --coverage.thresholds
□ lint_too_lenient  — --max-warnings > 20
□ l1_not_on_push    — PR title 检查不覆盖 push to main
□ missing_modules   — 某 app 无 lint/typecheck/test job
□ no_audit_in_ci    — 完全没有 npm/pip audit
□ no_branch_protect — 无 required status checks
```

命中 0 → CI 可信；命中 1 → ⚠️ 3分；命中 2+ → 🔴 虚假绿 ❌ 1分

### Step 2 — 安全扫描（两步都要做）

```bash
# Step 2a: 依赖漏洞（必须在根目录，不能在子目录，不能加 --omit=dev）
bash scripts/check-deps.sh

# Step 2b: 硬编码密钥（必须跑，这是 eval 发现的主要漏洞）
grep -r --include="*.js" --include="*.ts" --include="*.py" --include="*.env" \
  -E "(pat_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9]{20,}|api[_-]?key\s*[:=]\s*['\"][^'\"]{10,}['\"]|['\"][A-Za-z0-9_-]{40,}['\"])" \
  . 2>/dev/null | grep -v node_modules | grep -v ".git" | head -20
```

**关于 Step 2b 的重要规则**：发现任何硬编码凭据（不管是 token、key、secret），`#13 安全态势` 直接 ❌ 1 分，无论其他安全项多好。硬编码凭据已在 git 历史里意味着密钥必须立即吊销。

```bash
# Step 2c: 文档腐烂检测（代码 vs 文档更新时间差）
# 代码最后变更（排除文档目录）
git log --oneline -1 --format="%ar | %ai" -- "*.ts" "*.tsx" "*.js" "*.py" "*.sh" \
  apps/ src/ services/ packages/ 2>/dev/null

# 文档最后更新
git log --oneline -1 --format="%ar | %ai" -- \
  DEFINITION.md README.md ARCHITECTURE.md SYSTEM_MAP.md docs/ 2>/dev/null
```

**Step 2c 评分规则（映射到 #11 技术债）**：
```
代码 vs 文档差距 < 2 周  → 文档健康，不影响评分
代码 vs 文档差距 2–4 周  → 文档可能过期，#11 最高 ⚠️3
代码 vs 文档差距 > 4 周  → 文档已腐烂，#11 直接 ❌1
无文档目录（无 docs/、无 DEFINITION.md） → 文档缺失，#11 直接 ❌1
```
报告中如文档腐烂需单独标注「文档腐烂：代码 X 天前更新，文档 Y 天前更新」。

### Step 3 — 逐项填写
每项必须有：分数 + 存在性证据 + 有效性判断（命中哪些反模式）

打 ✅ 5 分必须说明为什么可以信任，不能只说"有"或"通过了"。

**常见边界情况评分指南**（减少歧义）：

| 场景 | 评分 | 理由 |
|------|------|------|
| 有 playbook 但格式不规范 | ⚠️ 3 | 存在即有价值 |
| 完全没有 playbook | ❌ 1 | 缺失 |
| 有备份文档但无自动化 cron | ⚠️ 3 | 部分覆盖 |
| DB 无任何备份策略 | ❌ 1 | 缺失 |
| 有飞书 webhook UI 但无自动发送代码 | ⚠️ 3 | 有基础设施，无实现 |
| 完全没有汇报机制 | ❌ 1 | 缺失 |
| 有决策记录但机制依赖人工触发 | ⚠️ 3 | 弱机制 |
| 发现任何硬编码密钥 | ❌ 1 | 安全项必须最严，见 Step 2b 规则 |

### Step 4 — 输出报告

使用以下模板：

```
# Repo Audit — [repo名] [日期]

## 反模式命中（CI 精读）
[列出所有命中项]

## L1 管业务：X/30
| # | 项目 | 分 | 证据 |

## L2 管代码：X/35
| # | 项目 | 分 | 证据（含反模式命中） |

## L2 管运行：X/30
| # | 项目 | 分 | 证据 |

## L3 管沟通：X/25
| # | 项目 | 分 | 证据 |

## 总分：X/120 (X%)

## 关键发现
（重点写虚假绿、结构性盲点——不写显而易见的）

## 修复计划
P0（今天）：
P1（本周）：
P2（两周内）：
```

### Step 5 — 写入分数历史
```bash
bash scripts/save-score.sh <repo_name> <total_score> "<关键发现摘要>"
```

---

## 评分规则

| 分 | 标准 |
|----|------|
| ✅ 5 | 配置文件证明健康 + 无反模式命中 + 有真实数据支撑，且能说明为何可信 |
| ⚠️ 3 | 存在 + 命中 1 个反模式，或配置不完整 |
| ❌ 1 | 不存在，或命中 2+ 个反模式 |
| 🔴虚假绿 ❌ | 表面绿但配置腐烂——在报告里单独标注，这是最危险的状态 |

---

## 定期运行
每周一次由 Brain scheduler 触发，结果推送飞书 + 写入分数历史。
修完 P0 后立即重跑，确认分数回升。
