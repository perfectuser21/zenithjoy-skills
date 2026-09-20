---
name: opc-openclaw-context
description: 识别并操作已部署的 OPC OpenClaw 远程系统，先核对 Gateway、Agent、Skill、cron、任务和历史目标，再进行部署、扩展、修复、验收或回答状态问题。用户提到 OpenClaw、OPC、一人公司、CEO/AI 员工、Skill、远程服务器、Agent、任务流、晨报、FDE、内容增长或“之前的目标”时使用。
---

# OPC OpenClaw 上下文与部署前置

## 核心规则

把行康服务器上的远程 OpenClaw Gateway 视为 OPC 的真实运行时。本地工作区只是蓝图、代码、Skill 参考和报告的工作副本。

绝不因为本机没有 `openclaw` CLI、Docker 容器或 SSH 会话，就推断远程系统未部署。先读取远程 Gateway 证据；只有远程连接本身不可用时，才报告“无法核实”。

默认复用已有系统，不平行创建第二个中枢，不重复创建已有 Agent，不把“写了文档”说成“远程已部署”。

## 触发后的固定顺序

1. **识别范围**：判断用户是在问现状、找目标、修改已有 Skill、增加岗位、部署能力，还是做业务任务。
2. **盘点远程运行时**：使用已连接的 OpenClaw 工具读取会话和运行证据：
   - `mcp__openclaw__conversations_list`：列出 Agent/渠道/任务会话；按 `OPC`、Skill 名、业务关键词过滤。
   - `mcp__openclaw__conversation_get`：确认具体会话、渠道和最近状态。
   - `mcp__openclaw__messages_read`：需要历史依据时读取消息；从工具输出中提取真实用户指令、部署结果、失败、目标和证据。
   - `mcp__openclaw__messages_send`：只有用户明确要求远程执行或当前任务确实需要修改远程系统时使用；发送前写清精确目标、范围、验收标准和不可扩大的边界。
3. **盘点本地基线**：优先读取以下文件，再决定是否需要更多文件：
   - `opc-openclaw-blueprint/README.md`
   - `opc-openclaw-blueprint/AI-NATIVE-COMPANY-OS-V1.md`
   - `opc-openclaw-blueprint/COMPANY-COMMUNICATION-LOOPS-V1.md`
   - `opc-openclaw-blueprint/OPENCLAW-AMBIENT-RUNTIME-V1.md`
   - `opc-openclaw-blueprint/reports/` 中最新报告
   - 对应 Agent 的 `AGENTS.md`、`IDENTITY.md`、`USER.md`
4. **恢复已有目标**：先从目标、OKR、任务、Skill、晨报和远程会话中找已有目标；合并同义目标，不新造目标。
5. **建立映射**：输出“目标 → 现有 Agent → 现有 Skill → 队列/业务对象 → 当前证据 → 缺口”。
6. **增量行动**：只补缺口；修改远程系统前先保留原状态、执行最小变更，并验证目标系统真实回写。
7. **交付报告**：明确区分“已核实远程运行”“本地已写入”“仅提出方案”“仍未验证”。

## 已知 OPC 运行基线

当前默认检查以下已存在对象，不要重新创建：

- `main`：OPC 中枢/CEO，负责理解目标、拆解、委派、验收和汇总。
- `people`：组织与任务运营。
- `media`：内容、抖音、增长与线索。
- `fde`：需求发现、方案、评测、交付和验收。
- `dev`：研发、测试、Skill/连接器和技术文档。
- `infra`：Gateway、节点、容器、网络、备份、监控和安全。
- `main` 已有 `taskflow-router` 与 `task-progress-card`；`taskflow-router` 的远程参考路径是 `/Users/administrator/openclaw-root/workspaces-root/clawd/skills/taskflow-router/SKILL.md`。
- `main` 已有 `opc-morning-brief`，会调用五个专业 Agent 采集证据。
- 媒体侧已有 `douyin-leadgen-phone` 与 `douyin-reference-capture-phone` 等 Skill；涉及手机、账号、飞书写入时必须遵守其设备绑定和审批边界。

不要将 20 个逻辑岗位误写成 20 个远程基础设施进程。岗位可以先由已有六个 Runtime Agent 承载，只有出现并发、隔离或记忆需求时才拆分。

## 目标恢复口径

当前 OPC 的公司级目标是：让 AI 从“被老板消息驱动”升级为“业务对象进入队列后持续推进，遇到审批点才找老板”。

增长闭环必须保持为：

`自媒体内容 → 公域/私域线索 → 线下沙龙/需求访谈 → FDE 方案与交付 → 产品化资产/客户案例 → 新内容`

运行闭环必须保持为：

`目标/项目 → Work Item → Agent Run → 产物/动作 → 目标系统回写 → 验证 → Done/Blocked/Approval → next_check_at`

每个开放对象至少应有：`object_id`、`status`、`human_owner`、`ai_owner`、`next_action`、`next_check_at`、`acceptance_criteria`、`evidence_url`、`last_updated_at`。

如果用户说“之前的目标”，先返回以上目标及其当前证据；再指出具体目标（例如沙龙 V1、内容到线索、FDE 交付或 AI 常驻运行）当前处于哪一层。找不到唯一目标时，先报告已找到的候选和差异，只问一个必要问题。

## Skill/部署操作规则

### 找已有 Skill

先查远程会话和本地工作区中对应的 `skills/<name>/SKILL.md`。Skill 的“已存在”必须有路径或远程运行记录；只有聊天里提到过不算。

### 写新 Skill

新 Skill 必须说明：

- 唯一名称和 canonical 路径；
- 触发场景；
- 输入、输出、依赖 Agent 和目标系统；
- 只读/草稿/内部写入/外部动作/生产动作边界；
- 验收命令或可观察证据；
- 与已有 Skill 的复用关系，避免重复造轮子。

本 Skill 的 canonical 本地路径是 `/Users/XX/.codex/skills/opc-openclaw-context/SKILL.md`。如果要让行康服务器上的 OpenClaw 使用它，必须另行把同一版本写入远程 Gateway 的 `/Users/administrator/openclaw-root/workspaces-root/clawd/skills/opc-openclaw-context/SKILL.md`，并回读验证；本地存在不等于远程已安装。

### 远程变更

远程部署、启用 Skill、改 Agent 配置、改 cron、改权限或修改生产运行参数时：

1. 先读取当前文件/配置/Skill/会话状态。
2. 明确变更的单一目标和回滚点。
3. 高风险操作（权限扩大、对外发布、生产变更、删除、重启、密钥、付费、人事）先取得老板批准。
4. 写入后必须重新读取目标系统，检查版本、路径、加载状态和一次最小 smoke test。
5. 只有目标系统真实回写才报告完成；只生成文本不算交付。

### Gateway 维护防撞

任何修改 Gateway 配置、替换容器或执行重启前，必须先运行：

```bash
docker exec openclaw-gateway node /Users/administrator/openclaw-root/workspaces-root/clawd/skills/opc-openclaw-context/scripts/check-gateway-maintenance.mjs
```

- 命令发现任一 `Work Commander` ledger 尚未写入不可变 `terminal` 时，退出码为 `2`；此时禁止重启、替换或停止 Gateway，等待流程结束或进入明确的协调维护窗口。
- 不得为了逐项配置反复重启。先在备份后批量完成配置，离线校验一次，再通过检查并执行一次协调重启。
- 重启后必须核对容器启动时间、Gateway 健康、关键 Agent 配置和被保护工作流的 terminal/恢复状态。
- `--allow-run <run_id>` 只用于明确批准维护期间允许忽略的单一测试 run；不得使用通配符，也不得把它作为日常绕过方式。

## 回答格式

对 OPC/OpenClaw 任务，优先按下面顺序回答：

1. **已核实现状**：远程 Gateway、已有 Agent/Skill/cron/任务。
2. **之前目标**：从本地目标文档和远程记录恢复的目标，不凭空新增。
3. **当前缺口**：已部署但不完善的地方。
4. **本次动作**：实际修改了什么，在哪里修改。
5. **验证证据**：读取、运行、回写或 smoke test 的结果。
6. **下一步**：只给一个最重要的下一动作，除非用户要求完整路线图。

避免说“从零搭建”“本地没有所以没部署”“已经部署完成”这类未经远程证据支持的结论。
