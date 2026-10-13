#!/usr/bin/env python3
"""
lint-skills.py — zenithjoy-skills 仓库的 lint 闸门。

校验项（针对每个真实 skill 目录，即「顶层、非 *-workspace、含 SKILL.md」的目录）：
  1. SKILL.md frontmatter 必须有身份字段 name（或历史等价的 id）且非空；
     若提供 name 则必须与目录名一致（id 是 harness-* 历史写法，仅作身份兜底）；
  2. SKILL.md frontmatter 必须有 description（非空）；
  3. 若有 version 字段，格式必须合法（语义化版本 X.Y.Z）；
  4. 仓库根目录必须存在 CHANGELOG.md；
  5. trigger/description 跨 skill 不应有明显重复冲突（尽力而为的重复检测，
     基于触发词 token 的 Jaccard 相似度，超阈值即报错；剔除 pipeline/stage 等
     模板样板词，避免 Stage-N 系列被误判）。

用法：
  python3 lint-skills.py [ROOT]
    ROOT 默认 = 仓库根（脚本所在目录上溯三层）。
  环境变量 LINT_SKILLS_ROOT 可覆盖根目录（fixture 测试用）。

退出码：0 = 全部通过；1 = 有 ERROR。
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from archived_skill_source import resolve_skill_source

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+([.-][0-9A-Za-z.-]+)?$")

# 顶层目录里这些不是真实 skill，跳过
SKIP_DIRS_EXACT = {"hooks", ".git", ".github", "node_modules"}
SKIP_DIRS_SUFFIX = ("-workspace",)
SKIP_DIRS_CONTAINS = ("workspace",)  # 例如 dev-workspace

COMMON_STOPWORDS = {
    "触发词", "触发", "skill", "the", "and", "use", "when", "to", "a", "of",
    "用户", "一下", "帮我", "or", "for", "is", "this", "触发场景", "时触发",
    # pipeline / stage 系列的模板样板词：是脚手架，不是区分性触发词
    "content", "pipeline", "stage", "单命令执行", "单命令", "运维",
}

DUP_SIMILARITY_THRESHOLD = 0.72  # Jaccard，超过即视为明显冲突（剔除样板词后）


def is_skill_dir(p: Path) -> bool:
    if not p.is_dir():
        return False
    name = p.name
    if name.startswith("."):
        return False
    if name in SKIP_DIRS_EXACT:
        return False
    if name.endswith(SKIP_DIRS_SUFFIX):
        return False
    if any(c in name for c in SKIP_DIRS_CONTAINS):
        return False
    return True


def split_frontmatter(text: str) -> str | None:
    """提取 SKILL.md 顶部 --- ... --- 之间的 frontmatter 原文，没有则 None。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    return None


def parse_top_level_keys(fm: str) -> dict[str, str]:
    """
    解析 frontmatter 的顶层 key -> value（字符串）。
    支持单行值与 |/> 块标量。只取顶层（行首无缩进）的 key。
    值仅用于「非空」与格式判断，拼接即可。
    """
    result: dict[str, str] = {}
    lines = fm.splitlines()
    i = 0
    top_key_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s?(.*)$")
    while i < len(lines):
        line = lines[i]
        if line and not line[0].isspace():
            m = top_key_re.match(line)
            if m:
                key = m.group(1)
                rest = m.group(2).strip()
                if rest in ("|", ">", "|-", ">-", "|+", ">+"):
                    block: list[str] = []
                    i += 1
                    while i < len(lines):
                        nxt = lines[i]
                        if nxt.strip() == "":
                            block.append("")
                            i += 1
                            continue
                        if nxt[0].isspace():
                            block.append(nxt.strip())
                            i += 1
                        else:
                            break
                    result[key] = " ".join(b for b in block if b).strip()
                    continue
                result[key] = rest
        i += 1
    return result


def tokenize_triggers(skill: dict) -> set[str]:
    """从 trigger + description 抽取触发词 token，用于重复检测。"""
    raw = " ".join(
        v for k, v in skill["keys"].items() if k in ("trigger", "description")
    )
    raw = re.sub(r"[\\/、，,|·;；\n\t]+", " ", raw)
    raw = re.sub(r"[\"'“”‘’()（）\[\]【】>—\-]+", " ", raw)
    parts = [p.strip() for p in raw.split() if p.strip()]
    tokens: set[str] = set()
    for p in parts:
        if len(p) <= 1:
            continue
        if p.lower() in COMMON_STOPWORDS:
            continue
        tokens.add(p.lower())
    return tokens


def collect_skills(root: Path) -> list[dict]:
    skills: list[dict] = []
    for child in sorted(root.iterdir()):
        if not is_skill_dir(child):
            continue
        if not (child / "SKILL.md").is_file():
            archived = resolve_skill_source(root, child.name + "/SKILL.md")
            if archived.is_relative_to(root.resolve() / "_archive"):
                continue  # 经退役清单与摘要验证的共用资源目录，不是缺失入口。
        skill_md = child / "SKILL.md"
        entry = {
            "dir": child.name,
            "path": child,
            "has_skill_md": skill_md.is_file(),
            "looks_like_skill": (child / "scripts").is_dir() or skill_md.is_file(),
            "keys": {},
            "frontmatter_found": False,
        }
        if skill_md.is_file():
            text = skill_md.read_text(encoding="utf-8", errors="replace")
            fm = split_frontmatter(text)
            if fm is not None:
                entry["frontmatter_found"] = True
                entry["keys"] = parse_top_level_keys(fm)
        skills.append(entry)
    return skills


def lint(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    # 4. CHANGELOG.md 存在
    if not (root / "CHANGELOG.md").is_file():
        errors.append("根目录缺少 CHANGELOG.md")

    skills = collect_skills(root)
    validated = [s for s in skills if s["has_skill_md"]]

    if not validated:
        errors.append("未发现任何含 SKILL.md 的 skill 目录（root 是否正确？）")

    for s in validated:
        d = s["dir"]
        if not s["frontmatter_found"]:
            errors.append(f"[{d}] SKILL.md 缺少 frontmatter（--- ... --- 块）")
            continue
        keys = s["keys"]
        # 1. 身份字段 name（或历史等价 id）
        name = keys.get("name", "").strip()
        sid = keys.get("id", "").strip()
        if not name and not sid:
            errors.append(f"[{d}] frontmatter 缺少身份字段（name 或 id）或为空")
        elif name and name != d:
            errors.append(f"[{d}] frontmatter name='{name}' 与目录名 '{d}' 不一致")
        # 2. description
        desc = keys.get("description", "").strip()
        if not desc:
            errors.append(f"[{d}] frontmatter 缺少 description 或为空")
        # 3. version（可选，有则校验格式）
        if "version" in keys:
            ver = keys["version"].strip().strip("'\"")
            if ver and not SEMVER_RE.match(ver):
                errors.append(f"[{d}] version='{ver}' 格式不合法（需 X.Y.Z）")

    # 看起来像 skill 但没有 SKILL.md → 警告（不阻塞，避免历史遗留目录炸闸门）
    for s in skills:
        if s["looks_like_skill"] and not s["has_skill_md"]:
            warnings.append(f"[{s['dir']}] 目录像 skill 但缺少 SKILL.md（建议补全）")

    # 5. 跨 skill 触发词重复冲突检测（尽力而为）
    token_map = {s["dir"]: tokenize_triggers(s) for s in validated if s["keys"]}
    items = [(d, t) for d, t in token_map.items() if len(t) >= 3]
    for i in range(len(items)):
        d1, t1 = items[i]
        for j in range(i + 1, len(items)):
            d2, t2 = items[j]
            inter = t1 & t2
            union = t1 | t2
            if not union:
                continue
            jac = len(inter) / len(union)
            if jac >= DUP_SIMILARITY_THRESHOLD:
                shared = "、".join(sorted(inter)[:6])
                errors.append(
                    f"[{d1}] 与 [{d2}] 触发词/描述高度重复"
                    f"（相似度 {jac:.2f}，共享: {shared}）"
                )

    return errors, warnings


def main() -> int:
    if len(sys.argv) > 1:
        root = Path(sys.argv[1]).resolve()
    elif os.environ.get("LINT_SKILLS_ROOT"):
        root = Path(os.environ["LINT_SKILLS_ROOT"]).resolve()
    else:
        # 脚本在 .github/workflows/scripts/ → 上溯三层到仓库根
        root = Path(__file__).resolve().parents[3]

    print(f"🔍 lint-skills: 校验根目录 {root}")
    errors, warnings = lint(root)

    for w in warnings:
        print(f"⚠️  WARN  {w}")
    for e in errors:
        print(f"❌ ERROR {e}")

    if errors:
        print(f"\n💥 lint 失败：{len(errors)} 个错误，{len(warnings)} 个警告")
        return 1
    print(f"\n✅ lint 通过：0 错误，{len(warnings)} 个警告")
    return 0


if __name__ == "__main__":
    sys.exit(main())
