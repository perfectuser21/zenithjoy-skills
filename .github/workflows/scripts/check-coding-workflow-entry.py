#!/usr/bin/env python3
"""当前 /dev 有头交付入口与已退役自动编排的边界合同。"""
import json
from pathlib import Path
import re
import sys

from archived_skill_source import resolve_skill_source

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]


def section(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]


def requests(text):
    # /dev 的双引号 shell 模板转回 JSON；仅检查点火示例，不匹配历史叙述。
    text = text.replace('\\"', '"')
    return [json.loads(value) for value in re.findall(r"-d [\"'](\{.*?\})[\"']", text, re.S)]


failures = []


def check(name, run):
    try:
        run()
        print(f"✅ {name}")
    except (AssertionError, IndexError, ValueError) as error:
        failures.append(name)
        print(f"❌ {name}: {error}")


def current_dev():
    text = (ROOT / 'dev/SKILL.md').read_text().split('---', 2)[2]
    blocks = re.findall(r'```(?:bash|json)\n(.*?)```', text, re.S)
    assert not any('coding_workflow' in block or 'coding-workflow/new-task.mjs' in block for block in blocks), '当前命令仍调用退役自主编码'
    rows = requests(section(text, '### 路径 C：', '\n## '))
    headed = [row for row in rows if row.get('task_type') == 'dev']
    assert headed and headed[0]['payload']['headed_manual'] == 'true'
    assert '/claim' in text and 'codex_dev' in text
    assert 'engine-ship' in text and 'engine-pr-watchdog' in text


check('dev：有头接力与普通编码Agent入口', current_dev)
# line-strategist 已归档，仅作为历史保留，不再要求新入口复活旧runner。


def retired(name):
    text = resolve_skill_source(ROOT, name + '/SKILL.md').read_text()
    front, body = text[4:].split('\n---\n', 1)
    description = re.search(r'description:\s*[|>]?\s*\n?\s*(.*)', front).group(1)
    assert description.startswith('【已废弃'), 'description 首行缺废弃标注'
    first = body.strip().splitlines()[0]
    assert first.startswith('> **已废弃') and 'coding_workflow' in first


for name in ('harness-controller', 'harness-planner', 'harness-contract-proposer',
             'harness-contract-reviewer', 'harness-generator', 'harness-evaluator', 'harness-report'):
    check(f'{name}：入口停止点火', lambda name=name: retired(name))

sys.exit(bool(failures))
