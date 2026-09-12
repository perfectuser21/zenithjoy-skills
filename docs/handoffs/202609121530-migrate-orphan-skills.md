# Handoff：迁移13个孤岛skill进 zenithjoy-skills 仓库（含 android 真机发布家族）

- task_id: unknown（本次是对话内发现+用户拍板的小改动，未走 `POST /api/brain/tasks` 注册）
- journey_id: none（infra，skill 仓库治理，不挂业务 journey）
- verdict: PASS

## 背景

用户对 android-\*-publish 系列做了一次 rpa-audit 审计并当场补了一条 P0 修复（发布类动作单次铁律），
过程中发现这些 skill 在 `~/.claude/skills` 里是**真实目录，不是 setup.sh 建的符号链接**——从没进过
`zenithjoy-skills` 仓库，没有 git 历史、没有远程备份。用户追问后确认：应该把所有孤岛 skill 都迁进仓库。

## 完成
- 扫描 `~/.claude/skills` 全部 125 个 skill 目录，识别出 13 个真实目录（非符号链接）孤岛：
  - android-publish 底座 + 7 个平台发布 skill（抖音/小红书/快手/头条/微博/B站/视频号）
  - avatar / ci-patrol / deploy / docs-center / html-deck
- 逐目录扫描硬编码凭据模式（sk-/api_key/password/私钥头/AKIA/ghp_ 等），无真实命中
  （html-deck 一处命中是 base64 图片数据里的随机子串误报）
- `deploy/SKILL.md` 原本完全没有 frontmatter，补上 `name: deploy` + description，否则过不了
  `lint-skills.py` 的 frontmatter 硬校验
- android-publish 底座里已包含 2026-09-12 早前补的「发布类动作单次铁律」（防止静默平台发布后
  被误判成没点中而重复点击导致重复发帖）
- PR #192（perfectuser21/zenithjoy-skills）已合并：https://github.com/perfectuser21/zenithjoy-skills/pull/192

## 没做（显式范围外）
- **`~/.claude/skills` 里对应的 13 个真实目录还没换成指向本仓库的符号链接**——本次只完成"进库"，
  "把本地目录换成 symlink 让 setup.sh 语义闭环"这一步还没做，留给下一步
- 没有逐条重新审查这 13 个 skill 本身的内容质量/触发词是否需要优化（迁移只搬内容，不改内容，
  除了 deploy 那处 frontmatter 硬伤）
- 没有检查是不是还有其他 repo（非 `~/.claude/skills`）也存在类似孤岛 skill 的情况

## 下一步
1. 把 `~/.claude/skills` 里这 13 个真实目录删掉，改建符号链接指向
   `/Users/administrator/perfect21/zenithjoy-skills/<name>`（即重跑一次
   `setup.sh` 的符号链接建立逻辑，或手动 `rm -rf` + `ln -s`）
2. 确认符号链接建好后这些 skill 在新会话里仍能正常触发（尤其 android-publish 系列，
   之前是"文本手册"型 skill，不涉及代码执行，风险低）
3. 今天新建的 `rpa-audit` skill 本身也在仓库里但还没建符号链接到 `~/.claude/skills`，
   顺带一起建掉，否则它在新会话里也不会出现在可用 skill 列表里

## 数据源
- 本次对话（用户拍板"是的"，同意迁移全部 13 个孤岛 skill）
- `~/.claude/skills/*/SKILL.md` frontmatter 逐一核对（name 与目录名一致、description 非空）
- `zenithjoy-skills/.github/workflows/scripts/lint-skills.py` 本地跑通（0 错误）

## 产物
- PR: https://github.com/perfectuser21/zenithjoy-skills/pull/192
- branch: cp-09121526-migrate-orphan-skills（已合并，worktree 已清理）
