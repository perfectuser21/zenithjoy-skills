#!/usr/bin/env python3
"""
lint-skills.py 的 fixture 测试 —— 证明闸门真能拦坏 skill、放好 skill。

不依赖测试框架（CI runner 可能没装 pytest），直接 assert，失败即 exit 1。
每个 case 在临时目录里造一棵最小 skill 树，调 lint(root) 看 errors。
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

# 动态加载被测脚本（带连字符的文件名不能直接 import）
SCRIPT = Path(__file__).resolve().parents[1] / "lint-skills.py"
spec = importlib.util.spec_from_file_location("lint_skills", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def make_skill(root: Path, name: str, frontmatter: str | None, body: str = "# body\n"):
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    if frontmatter is not None:
        (d / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")


def fresh_root(with_changelog: bool = True) -> Path:
    root = Path(tempfile.mkdtemp(prefix="lint-skills-fixture-"))
    if with_changelog:
        (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    return root


PASS = 0
FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}")


def has_err(errors: list[str], needle: str) -> bool:
    return any(needle in e for e in errors)


# ── case 1: 一个完全合格的 skill → 必须绿 ──
print("case 1: 合格 skill 应通过")
r = fresh_root()
make_skill(r, "good-skill", "name: good-skill\nversion: 1.2.3\ndescription: 这是一个干净的测试 skill，触发词 alpha beta gamma")
errors, warnings = mod.lint(r)
check("无 error", len(errors) == 0)

# ── case 2: 缺 description → 必须红 ──
print("case 2: 缺 description 应报红")
r = fresh_root()
make_skill(r, "no-desc", "name: no-desc\nversion: 1.0.0")
errors, _ = mod.lint(r)
check("报缺 description", has_err(errors, "缺少 description"))

# ── case 3: 缺身份字段（name/id）→ 必须红 ──
print("case 3: 缺 name/id 应报红")
r = fresh_root()
make_skill(r, "no-name", "description: 有描述但没名字 zzz yyy xxx")
errors, _ = mod.lint(r)
check("报缺身份字段", has_err(errors, "缺少身份字段"))

# ── case 3b: 仅有 id（无 name）→ 应绿（harness-* 历史写法） ──
print("case 3b: 仅 id 应通过")
r = fresh_root()
make_skill(r, "id-only", "id: id-only-skill\ndescription: 用 id 不用 name rr ss tt")
errors, _ = mod.lint(r)
check("仅 id 不报缺身份", not has_err(errors, "缺少身份字段"))

# ── case 4: name 与目录名不一致 → 必须红 ──
print("case 4: name 与目录名不一致应报红")
r = fresh_root()
make_skill(r, "mydir", "name: otherdir\ndescription: 名字对不上 foo bar baz")
errors, _ = mod.lint(r)
check("报 name 不一致", has_err(errors, "不一致"))

# ── case 5: 非法 version → 必须红 ──
print("case 5: 非法 version 应报红")
r = fresh_root()
make_skill(r, "bad-ver", "name: bad-ver\nversion: v1\ndescription: 版本号乱写 aa bb cc")
errors, _ = mod.lint(r)
check("报 version 非法", has_err(errors, "格式不合法"))

# ── case 6: 合法 version 变体（带 -beta） → 应绿 ──
print("case 6: 合法 prerelease version 应通过")
r = fresh_root()
make_skill(r, "pre-ver", "name: pre-ver\nversion: 2.0.0-beta\ndescription: 预发布版本 qq ww ee")
errors, _ = mod.lint(r)
check("无 version error", not has_err(errors, "格式不合法"))

# ── case 7: 缺 CHANGELOG.md → 必须红 ──
print("case 7: 缺 CHANGELOG.md 应报红")
r = fresh_root(with_changelog=False)
make_skill(r, "ok-skill", "name: ok-skill\ndescription: 有 skill 但仓库没 changelog hh ii jj")
errors, _ = mod.lint(r)
check("报缺 CHANGELOG", has_err(errors, "CHANGELOG"))

# ── case 8: 两个 skill 触发词高度重复 → 必须红 ──
print("case 8: 触发词高度重复应报红")
r = fresh_root()
dup = "douyin 抖音 发布 视频 图文 自动 上传 cookie"
make_skill(r, "dup-a", f"name: dup-a\ndescription: {dup}")
make_skill(r, "dup-b", f"name: dup-b\ndescription: {dup} 几乎一样")
errors, _ = mod.lint(r)
check("报触发词重复", has_err(errors, "高度重复"))

# ── case 9: 两个 skill 触发词不同 → 不应报重复 ──
print("case 9: 触发词不同不应误报重复")
r = fresh_root()
make_skill(r, "uniq-a", "name: uniq-a\ndescription: 抖音 发布 视频 上传")
make_skill(r, "uniq-b", "name: uniq-b\ndescription: 数据库 迁移 备份 回滚")
errors, _ = mod.lint(r)
check("不误报重复", not has_err(errors, "高度重复"))

# ── case 10: 块标量 description（| 形式）应被识别为非空 ──
print("case 10: 块标量 description 应识别为非空")
r = fresh_root()
make_skill(
    r,
    "block-desc",
    "name: block-desc\ndescription: |\n  多行描述第一行 kk\n  第二行 ll mm",
)
errors, _ = mod.lint(r)
check("块标量被识别", not has_err(errors, "缺少 description"))

# ── case 11: *-workspace 目录被忽略（即使缺 SKILL.md 也不炸） ──
print("case 11: -workspace 目录应被忽略")
r = fresh_root()
make_skill(r, "real", "name: real\ndescription: 真 skill nn oo pp")
(r / "real-workspace").mkdir()
(r / "real-workspace" / "junk.txt").write_text("noise", encoding="utf-8")
errors, _ = mod.lint(r)
check("workspace 不报错", len(errors) == 0)

print(f"\n结果：PASS={PASS} FAIL={FAIL}")
sys.exit(0 if FAIL == 0 else 1)
