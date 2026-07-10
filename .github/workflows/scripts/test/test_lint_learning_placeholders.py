#!/usr/bin/env python3
"""
lint-learning-placeholders.py 的 fixture 测试 —— 证明闸门真能拦占位符 learning.md、放真实 learning.md。

背景（九要素 T11）：harness-report Step 8 旧版用 heredoc 静态模板生成 learning.md，
四类目全是「（无 / 填写…）」占位符 + 三条硬编码「下次预防清单」。本闸门拦截：
  1. 占位符原文「（无 / 填写」出现在任何 learning 文件里 → FAIL
  2. 旧硬编码预防清单三条**同时**出现（= 整段照抄模板）→ FAIL
扫描范围：docs/learnings/**/*.md 与 **/learning.md。

不依赖测试框架，直接 assert，失败即 exit 1。
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "lint-learning-placeholders.py"
spec = importlib.util.spec_from_file_location("lint_learning_placeholders", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PASS = 0
FAIL = 0


def fresh_root() -> Path:
    return Path(tempfile.mkdtemp(prefix="lint-learning-fixture-"))


def write(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def check(name: str, cond: bool) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}")


HARDCODED_TRIO = """## 下次预防清单

- [ ] 检查 contract-draft.md 格式是否符合 evaluator 预期
- [ ] 确认 DoD 所有 [BEHAVIOR] 条目有对应测试
- [ ] GAN 轮次 > 2 时复盘 evaluator prompt 是否过严
"""

REAL_LEARNING = """# Learning — 示例功能

## 运行指标

- GAN 轮次：2
- PR：https://github.com/x/y/pull/1

## 发现的问题

### [PROMPT] Prompt 类问题

- 无（本次未遇到）

### [BUG] 代码缺陷

- evaluator 断言路径拼错导致误判：现象是 verdict=FAIL，根因是双斜杠路径，修法是统一 %/ 去尾。

### [INFRA] 基础设施问题

- 无（本次未遇到）

### [DESIGN] 设计缺陷

- 无（本次未遇到）

## 下次预防清单

- [ ] sprint 路径拼装前统一去尾斜杠
"""


# case 1: 含占位符原文的 learning.md → 报错
root = fresh_root()
write(root, "sprints/07101200-demo/learning.md", "## 发现的问题\n\n- （无 / 填写本次遇到的 prompt 设计问题）\n")
errors = mod.lint(root)
check("占位符原文被拦截", len(errors) >= 1)

# case 2: docs/learnings/ 下含占位符 → 报错
root = fresh_root()
write(root, "docs/learnings/cp-07101200-demo.md", "- （无 / 填写本次修复的 bug）\n")
errors = mod.lint(root)
check("docs/learnings 占位符被拦截", len(errors) >= 1)

# case 3: 硬编码预防清单三条整段照抄 → 报错
root = fresh_root()
write(root, "docs/learnings/cp-07101201-demo.md", "# Learning\n\n真实内容。\n\n" + HARDCODED_TRIO)
errors = mod.lint(root)
check("硬编码预防清单整段照抄被拦截", len(errors) >= 1)

# case 4: 只出现其中一条（可能是真实结论）→ 放行
root = fresh_root()
write(root, "docs/learnings/cp-07101202-demo.md",
      "# Learning\n\n## 下次预防清单\n\n- [ ] 确认 DoD 所有 [BEHAVIOR] 条目有对应测试\n- [ ] 本次新增：合同测试文件 commit 1 后不可改\n")
errors = mod.lint(root)
check("单条同款预防项（真实结论）放行", len(errors) == 0)

# case 5: 真实 learning → 放行
root = fresh_root()
write(root, "sprints/07101203-demo/learning.md", REAL_LEARNING)
errors = mod.lint(root)
check("真实 learning 放行", len(errors) == 0)

# case 6: 非 learning 文件（如 SKILL.md）含指纹 → 不扫描、放行
root = fresh_root()
write(root, "harness-report/SKILL.md", "禁止出现占位符原文「（无 / 填写」。\n")
errors = mod.lint(root)
check("非 learning 文件不在扫描范围", len(errors) == 0)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
