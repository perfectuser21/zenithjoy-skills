#!/usr/bin/env python3
"""
learning.md 占位符闸门（九要素 T11）。

背景：harness-report Step 8 旧版用 heredoc 静态模板生成 learning.md，
四类目全是「（无 / 填写…）」占位符 + 三条硬编码「下次预防清单」——假总结混进
docs/learnings/ 与 learnings 数据管道。本闸门在 CI 拦截：

  1. 占位符原文「（无 / 填写」出现在 learning 文件里 → FAIL
  2. 旧硬编码预防清单三条**同时**出现（= 整段照抄模板）→ FAIL
     （只出现单条可能是真实结论，放行）

扫描范围：docs/learnings/**/*.md 与任意路径下的 learning.md。
其他文件（如 SKILL.md 里引用指纹作为禁令说明）不在扫描范围。
"""

from __future__ import annotations

import sys
from pathlib import Path

PLACEHOLDER = "（无 / 填写"

HARDCODED_PREVENTION_TRIO = [
    "检查 contract-draft.md 格式是否符合 evaluator 预期",
    "确认 DoD 所有 [BEHAVIOR] 条目有对应测试",
    "GAN 轮次 > 2 时复盘 evaluator prompt 是否过严",
]

SKIP_DIRS = {".git", "node_modules", "__pycache__"}


def target_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*.md"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        rel = p.relative_to(root)
        if p.name == "learning.md" or (len(rel.parts) >= 3 and rel.parts[0] == "docs" and rel.parts[1] == "learnings"):
            files.append(p)
    return files


def lint(root: Path) -> list[str]:
    errors: list[str] = []
    for f in target_files(root):
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            errors.append(f"{f}: 无法读取（{e}）")
            continue
        rel = f.relative_to(root)
        if PLACEHOLDER in text:
            errors.append(f"{rel}: 含占位符原文「{PLACEHOLDER}…」——learning 必须写真实复盘内容，没有就写「无（本次未遇到）」")
        if all(line in text for line in HARDCODED_PREVENTION_TRIO):
            errors.append(f"{rel}: 「下次预防清单」三条硬编码模板整段照抄——必须从本次真实问题提炼")
    return errors


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    errors = lint(root)
    if errors:
        print(f"❌ lint-learning-placeholders：{len(errors)} 处占位符/模板照抄：")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("✅ lint-learning-placeholders：learning 文件无占位符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
