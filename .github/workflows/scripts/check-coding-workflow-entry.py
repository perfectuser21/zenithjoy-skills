#!/usr/bin/env python3
"""Cecelia #6356 的入口合同；可传只读基线目录做修复前后对照。"""
import json
from pathlib import Path
import re
import sys

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


def entry(name, start, end):
    text = section((ROOT / name / 'SKILL.md').read_text(), start, end)
    rows = requests(text)
    coding = [row for row in rows if row.get('task_type') == 'coding_workflow']
    assert coding, '缺少 coding_workflow 建单示例'
    assert not any(row.get('task_type') == 'harness_initiative' for row in rows), '仍建旧无头单'
    for row in coding:
        payload = row['payload']
        assert payload.get('coding_workflow') is True
        assert payload.get('repo') and payload.get('acceptance')
        assert 'orchestrator' not in payload
    assert 'repos.json' in text, '必须先查当前支持的仓库'
    if name == 'dev':
        assert 'packages/brain/scripts/coding-workflow/new-task.mjs' in text
        headed = [row for row in rows if row.get('task_type') == 'dev']
        assert headed and headed[0]['payload']['headed_manual'] == 'true'
        assert '/claim' in text


check('dev 路径 C：runner 点火与有头兜底', lambda: entry('dev', '### 路径 C：', '\n## '))
check('line-strategist 路径 C：runner 点火', lambda: entry('line-strategist', '**路径C', '\n**补货'))


def retired(name):
    text = (ROOT / name / 'SKILL.md').read_text()
    front, body = text[4:].split('\n---\n', 1)
    description = re.search(r'description:\s*[|>]?\s*\n?\s*(.*)', front).group(1)
    assert description.startswith('【已废弃'), 'description 首行缺废弃标注'
    first = body.strip().splitlines()[0]
    assert first.startswith('> **已废弃') and 'coding_workflow' in first


for name in ('harness-controller', 'harness-planner', 'harness-contract-proposer',
             'harness-contract-reviewer', 'harness-generator', 'harness-evaluator', 'harness-report'):
    check(f'{name}：入口停止点火', lambda name=name: retired(name))

sys.exit(bool(failures))
