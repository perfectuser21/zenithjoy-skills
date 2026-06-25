# 贡献指南 — zenithjoy-skills

本仓库是 Claude skills 的集合：每个顶层目录一个 skill，包含一份 `SKILL.md`（frontmatter
+ 正文）和少量脚本。靠软链分发到 `~/.claude/skills/`，无后端、无服务。

CI 闸门只做机器能客观判断的事（见 `.github/workflows/lint-skills.yml`）。提交前请按本指南
自检，能省一轮 CI 往返。

---

## 1. PR 变更清单（提交前自检）

- [ ] **分支命名** `cp-<时间戳>-<简述>`（例 `cp-06251442-skills-cigate`）。只有 `cp-*`
      分支的 PR 才会被 auto-merge。
- [ ] **改了 `.github/**`** → PR 标题加 `[CONFIG]` 前缀。
- [ ] 新建或修改的 skill，其 `SKILL.md` frontmatter 满足下面「frontmatter 规范」。
- [ ] 改了任何 skill → 在根 `CHANGELOG.md` 顶部追加一条记录（格式见下）。
- [ ] 本地跑过 lint 与 self-test，全绿：
      ```bash
      python3 .github/workflows/scripts/test/test_lint_skills.py   # fixture 自测
      python3 .github/workflows/scripts/lint-skills.py             # 全量 lint
      ```
- [ ] 不提交临时文件（`.dev-mode.*`、`*-workspace/` 下的运行产物、`__pycache__/` 等）。

---

## 2. SKILL.md frontmatter 规范

frontmatter 是 `SKILL.md` 顶部 `---` 包起来的 YAML 块。lint 强制：

| 字段 | 要求 |
|---|---|
| `name` | **必填**（或历史等价的 `id`，仅 harness-* 沿用）。若用 `name`，**必须与目录名完全一致**。 |
| `description` | **必填、非空**。一句话讲清这个 skill 做什么 + 触发词。支持 `|` 块标量多行。 |
| `version` | 选填。一旦出现，**必须是合法语义化版本** `X.Y.Z`（可带 `-beta` 等后缀）。 |
| `trigger` | 选填。补充触发词；会与 description 一起参与「跨 skill 重复检测」。 |

新 skill 一律用 `name`（不要新增 `id`，`id` 只是历史遗留）。

**跨 skill 触发词不要撞车**：lint 会对所有 skill 的 trigger + description 做 token
相似度检测，相似度过高（共享触发词太多）会报红。新 skill 的触发词要和已有 skill 有
区分度；同一系列（如 `pipeline-*` 各 Stage）靠各自的 Stage 名/动作词区分。

---

## 3. 版本号（version bump）规范

仅对带 `version` 字段的 skill 适用。遵循语义化版本：

- **PATCH**（`x.y.Z`）：措辞润色、修错别字、补一两条排查、不改触发行为。
- **MINOR**（`x.Y.0`）：新增能力/小节/触发词，向后兼容。
- **MAJOR**（`X.0.0`）：步骤重排、删除能力、触发语义改变等破坏性变更。

bump version 时，同步在 SKILL.md 的内联 `changelog:` 列表顶部加一行（与现有 skill 写法
一致），简述本次改动。

---

## 4. CHANGELOG.md 写法

每次改 skill，在根 `CHANGELOG.md` **顶部**追加一条，沿用现有格式：

```markdown
## [YYYY-MM-DD] <skill-name> — created|updated（一句话摘要）
**症状**: 触发这次改动的现象 / 用户痛点。
**根因**: 为什么会这样。
**修改**: 具体改了什么。
```

---

## 5. eval 要求（可选，推荐）

触发率（recall/specificity）是 skill 质量的核心。**本轮 CI 暂不强制 eval gate**，但强烈建议：

- 改动 description/trigger 后，用 `skill-creator` 的 run_eval 对触发词跑一轮 eval，
  在 CHANGELOG 里附上 recall/specificity 实测数（多数现有条目已这么做）。
- 目标：recall ≥ 90%、specificity ≥ 90%。本环境 eval 偶有失真（裸 `claude` CLI 需
  `stdin=/dev/null`、需匹配真实已安装 skill 名），失真时以人工判定为准并在 CHANGELOG 说明。
- 完整 eval harness 作为后续工作，未来可能升级为强制 gate。

---

## 6. 合并方式

- `cp-*` 分支 PR，`lint-skills` 闸门（self-test + 全量 lint）全绿后 → 由 auto-merge
  workflow **自动 squash 合并并删分支**。
- auto-merge 自指安全：它 `needs` lint 闸门，坏 gate 自己也过不了，不会乱合。
- 非 `cp-*` 分支不自动合并，走人工 review。
