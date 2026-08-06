# 小改动 PrepPRD：CI lint 脚本路径对齐 capability skill 改名

## 改什么
`.github/workflows/scripts/lint-gp-contract-layer.py` 的 `RULES` 字典里 4 个文件路径 key：
- `golden-path-proposer/SKILL.md` → `capability-proposer/SKILL.md`
- `golden-path-reviewer/SKILL.md` → `capability-reviewer/SKILL.md`
- `golden-path-mapper/SKILL.md` → `capability-mapper/SKILL.md`
- `golden-path-controller/SKILL.md` → `capability-controller/SKILL.md`

字典里的 marker 字符串本体（如 `golden_paths.journey_id`、`/golden-paths/$GP_ID/contracts`）不动——那些是 Brain DB/API
的既有命名，决策 a340f100 明确把库表层/API 层改名列为「渐进」阶段，本次不动。

## 为什么改
Alex 08-06 拍板（决策 a340f100 追加口径）：golden-path 系 5 个 skill 全面改名为 capability 系
（golden-path→capability / golden-path-mapper→capability-mapper / golden-path-controller→
capability-controller / golden-path-proposer→capability-proposer / golden-path-reviewer→
capability-reviewer）。skill 目录已 `git mv` 完成，本 lint 脚本硬编码了旧目录路径作为读取对象，
不同步会导致 CI 判「文件不存在→marker 全缺失」而误报失败，挡住改名 PR 合并。

## 关联上下文
- 决策 a340f100：词汇终局，ability 一词退役，skill 层改名为本次追加口径
- 同批改动：capability/ capability-mapper/ capability-controller/ capability-proposer/
  capability-reviewer/ 5 个 SKILL.md + capability/references/doctrine.md + capability/evals/evals.json
  + decomp/decomp-check/plan 三个下游 skill 的路由文字，均在同一分支

## 影响范围
仅影响 zenithjoy-skills 仓库 CI 的 `lint-gp-contract-layer.py` 检查本身；不影响 Brain 代码、
DB schema、API 路由（那些字段名保持不变）。

## 验收标准
- [ ] `python3 .github/workflows/scripts/lint-gp-contract-layer.py .` 本地跑通，输出
      `✅ Golden Path contract-layer skill guard passed`
- [ ] CI 全绿
