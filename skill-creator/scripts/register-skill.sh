#!/bin/bash
# Legacy classification CLI retained; installation is now a reference only.
set -euo pipefail
python3 - "$@" <<'PY'
import os
from pathlib import Path
import re
import subprocess
import sys


def root():
    try:
        workspace = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=subprocess.DEVNULL).strip()).resolve()
        remote = subprocess.check_output(['git', '-C', str(workspace), 'remote', 'get-url', 'origin'], text=True, stderr=subprocess.DEVNULL).strip()
        branch = subprocess.check_output(['git', '-C', str(workspace), 'symbolic-ref', '--short', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        raise ValueError('Run from an independent zenithjoy-skills worktree on a feature branch.')
    if remote not in ('git@github.com:perfectuser21/zenithjoy-skills.git', 'https://github.com/perfectuser21/zenithjoy-skills.git', 'https://github.com/perfectuser21/zenithjoy-skills'):
        raise ValueError('Skill bodies belong in zenithjoy-skills; switch to its independent worktree.')
    if not (workspace / '.git').is_file() or branch in ('main', 'master', 'develop'):
        raise ValueError('Use an independent zenithjoy-skills worktree on a feature branch.')
    return workspace


try:
    workspace = root()
    if sys.argv[1:] == ['--check-root']:
        print(workspace)
        sys.exit(0)
    if len(sys.argv) != 5:
        raise ValueError('Usage: register-skill.sh <core|personal> <skill-name> <description> <central-skill-path>')
    classification, name, description, path = sys.argv[1:]
    if classification not in ('core', 'personal') or not re.fullmatch(r'[a-z][a-z0-9-]*', name):
        raise ValueError('Expected core|personal and a kebab-case skill name.')
    source = Path(path).resolve()
    if source != workspace / name or (workspace / name).is_symlink() or not (source / 'SKILL.md').is_file():
        raise ValueError('Register only a real skill directory at the current central worktree root.')
    destination = Path.home() / '.claude' / 'skills' / name
    if destination.is_symlink() and destination.resolve() == source:
        pass
    elif destination.exists() or destination.is_symlink():
        raise ValueError('Existing installation preserved: ' + str(destination))
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source, target_is_directory=True)
    print(f'Installed reference: {destination} -> {source}')
    print('Review and submit the skill in zenithjoy-skills; business repositories update their pinned source lock.')
    print('Business runtime implementations stay in their business repository.')
except (ValueError, OSError) as error:
    sys.exit(str(error))
PY
