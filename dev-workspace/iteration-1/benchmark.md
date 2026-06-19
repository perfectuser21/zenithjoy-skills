# Skill Benchmark: dev

**Version**: 21.2.0 vs 21.0.x baseline
**Date**: 2026-06-19
**Evals**: eval-0-large-feature-adversarial, eval-2-bug-path-a

## Summary

| Metric | With Skill (v21.x) | Old Skill (v20.1.0) | Delta |
|--------|-------------------|---------------------|-------|
| Pass Rate | **100%** (7/7) | 71% (5/7) | **+29pp** |

## Per-Eval Breakdown

### eval-0-large-feature-adversarial

| Assertion | With Skill | Old Skill |
|-----------|-----------|----------|
| a1: GAN Phase1 Proposer/Challenger | ✅ | ❌ 无对抗结构 |
| a2: Phase2 三路并行 Agent B/C/D | ✅ | ❌ 无三路结构 |
| a3: 决策点为业务决策非工程标准 | ✅ | ✅ |
| a4: PrepPRD 含错误路径 | ✅ | ✅ |
| **小计** | **4/4** | **2/4** |

### eval-2-bug-path-a

| Assertion | With Skill | Old Skill |
|-----------|-----------|----------|
| c1: 路径A识别为Bug | ✅ | ✅ |
| c2: 根因假设质量 | ✅ | ✅ |
| c3: regression-test计划 | ✅ | ✅ |
| **小计** | **3/3** | **3/3** |

## Analyst Notes

- 关键差异在大功能路径（路径C）：新版 GAN 对抗步骤带来结构性改进，旧版完全无此环节
- Bug 路径（路径A）两版本均正确，质量相当
- 旧 eval 目录（eval-1-bug/eval-2-small-change/eval-3-big-feature）因使用不同断言格式已清理，不计入本 benchmark
