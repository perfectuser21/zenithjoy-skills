#!/bin/bash
# Create the source in the current central worktree, then install a reference.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "Usage: $0 <skill-name> <description> [simple|complex]" >&2
    exit 1
fi
name="$1"
description="$2"
kind="${3:-simple}"
[[ "$name" =~ ^[a-z][a-z0-9-]*$ ]] || { echo 'Skill name must be kebab-case.' >&2; exit 1; }
[[ "$kind" == simple || "$kind" == complex ]] || { echo 'Type must be simple or complex.' >&2; exit 1; }
root="$(bash "$SCRIPT_DIR/register-skill.sh" --check-root)"
# Preflight both locations before creating the source. Never overwrite an install.
python3 - "$root" "$name" "$description" "$kind" <<'PY'
import json
from pathlib import Path
import sys

root, name, description, kind = sys.argv[1:]
source = Path(root) / name
installation = Path.home() / '.claude' / 'skills' / name
for target in (source, installation):
    if target.exists() or target.is_symlink():
        sys.exit('Existing path preserved: ' + str(target))
source.mkdir()
if kind == 'complex':
    (source / 'scripts').mkdir()
body = ('---\nname: ' + name + '\ndescription: ' + json.dumps(description, ensure_ascii=False) +
        '\n---\n\n# ' + name + '\n\n## Purpose\n\n' + description +
        '\n\n## Procedure\n\n1. Describe the verified steps.\n\n## Resources\n\n'
        'Resolve supporting resources relative to this central skill directory.\n'
        'Reference business runtime implementations in their business repository.\n')
(source / 'SKILL.md').write_text(body, encoding='utf-8')
print('Created central skill: ' + str(source))
PY
bash "$SCRIPT_DIR/register-skill.sh" personal "$name" "$description" "$root/$name"
