# Skill Benchmark: harness-evaluator

**Version**: 1.17.0 vs 1.16.0 baseline
**Date**: 2026-06-19
**Evals**: eval-0-machine-probe

## Summary

| Metric | With Skill (v1.17.0) | Old Skill (v1.16.0) | Delta |
|--------|---------------------|---------------------|-------|
| Pass Rate | **100%** (3/3) | **67%** (2/3) | **+33pp** |

## Per-Eval Breakdown

### eval-0-machine-probe

| Assertion | With Skill | Old Skill |
|-----------|-----------|----------|
| e0: Machine Probe 步骤执行 | ✅ Step B-1.9 明确运行 | ❌ 旧版无此步骤 |
| e1: 检测到硬编码路径 /Users/ | ✅ 精确定位两处路径 | ✅ 作为附带发现 |
| e2: 最终裁定 FAIL | ✅ failed_step=absolute_path_in_e2e | ✅ failed_step=golden_path_gap（不同原因） |
| **小计** | **3/3** | **2/3** |

## Analyst Notes

- 新版 Machine Probe 步骤精确定位硬编码路径并以此作为首要 FAIL 原因
- 旧版虽也 FAIL，但首要原因是 golden_path 未覆盖，硬编码路径是附带发现
- e1/e2 两版本均通过，说明这两条区分度较低；e0 是关键区分断言
