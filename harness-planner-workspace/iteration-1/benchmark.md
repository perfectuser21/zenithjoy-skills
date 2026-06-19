# Skill Benchmark: harness-planner

**Version**: 8.11.0 vs 8.10.0 baseline
**Date**: 2026-06-19
**Evals**: eval-0-nfr-injection (NFR 双源读取)

## Summary

| Metric | With Skill (v8.11.0) | Old Skill (v8.10.0) | Delta |
|--------|---------------------|---------------------|-------|
| Pass Rate | **100%** (3/3) | **0%** (0/3) | **+100pp** |

## Per-Eval Breakdown

### eval-0-nfr-injection

| Assertion | With Skill | Old Skill |
|-----------|-----------|----------|
| p0: ## NFR 约束章节存在 | ✅ | ❌ 无该章节 |
| p1: 包含 decisions API 内容 | ✅ nfr-001/nfr-002 均注入 | ❌ |
| p2: 双源合并（decisions + PrepPRD）| ✅ 明确标注两来源 | ❌ |
| **小计** | **3/3** | **0/3** |

## Analyst Notes

- 差异极为显著：新版完整注入 NFR 约束章节，旧版完全无此结构
- 断言具有高区分度（非平凡）
- 历史 benchmark（v8.10.0 vs baseline 90%/32%）保留在 git 历史中