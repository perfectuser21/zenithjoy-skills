#!/usr/bin/env bash
# setup.sh — 新机器初始化 Claude Code skills + hooks
#
# 用途：在任何跑 Claude Code 的机器上一键同步 zenithjoy-skills
# 注意：仅适用于 Claude Code，Codex 不使用此脚本
#
# 用法：
#   git clone https://github.com/perfectuser21/zenithjoy-skills.git ~/perfect21/zenithjoy-skills
#   bash ~/perfect21/zenithjoy-skills/setup.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DST="$HOME/.claude/skills"
HOOKS_DST="$HOME/.claude/hooks"

echo "=== ZenithJoy Skills + Hooks 初始化 ==="
echo "源目录: $REPO_DIR"
echo ""

mkdir -p "$SKILLS_DST" "$HOOKS_DST"

# Skills: 每个含 SKILL.md 的子目录建 symlink
echo "[1/2] 同步 skills..."
for src in "$REPO_DIR"/*/; do
  name=$(basename "$src")
  [[ "$name" == "hooks" ]] && continue
  [[ ! -f "$src/SKILL.md" ]] && continue
  dst="$SKILLS_DST/$name"
  if [ -L "$dst" ]; then
    echo "  ✓ $name (已存在)"
  elif [ -e "$dst" ]; then
    echo "  ⚠️  $name (已有非 symlink，跳过)"
  else
    ln -s "$src" "$dst"
    echo "  → $name"
  fi
done

# Hooks: 每个 .sh 建 symlink
echo ""
echo "[2/2] 同步 hooks..."
for src in "$REPO_DIR/hooks/"*.sh; do
  [ -f "$src" ] || continue
  name=$(basename "$src")
  dst="$HOOKS_DST/$name"
  if [ -L "$dst" ]; then
    echo "  ✓ $name (已存在)"
  elif [ -e "$dst" ]; then
    echo "  ⚠️  $name (已有非 symlink，跳过)"
  else
    ln -s "$src" "$dst"
    chmod +x "$src"
    echo "  → $name"
  fi
done

echo ""
echo "=== 完成 ==="
echo "Skills: $SKILLS_DST"
echo "Hooks:  $HOOKS_DST"
echo "下一步：确认 ~/.claude/settings.json 里的 hooks 路径指向 $HOOKS_DST"
