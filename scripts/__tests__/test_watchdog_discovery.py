"""执行真实 Skill Step1/3a；仅隔离 gh 与副作用边界，不复制判断逻辑。"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class WatchdogDiscoveryTest(unittest.TestCase):
    def run_block(self, step, response='[]', exit_code=0, fail_repo=''):
        text = (ROOT / 'engine-pr-watchdog/SKILL.md').read_text()
        section = text.split('## Step 1:')[1].split('## Step 2:')[0] if step == 1 else text.split('### 3a.')[1].split('### 3b.')[0]
        block = section.split('```bash\n')[1].split('```')[0]
        with tempfile.TemporaryDirectory(prefix='watchdog-discovery-') as tmp:
            base = Path(tmp)
            gh = base / 'gh'
            gh.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
p=pathlib.Path(os.environ['FIXTURE_DIR']); args=sys.argv[1:]
with (p/'calls').open('a') as f: f.write(json.dumps(args)+'\\n')
if args[:2]==['pr','list']:
    repo=args[args.index('--repo')+1]
    if not os.environ['FAIL_REPO'] or repo==os.environ['FAIL_REPO']:
        if int(os.environ['API_EXIT']): sys.exit(int(os.environ['API_EXIT']))
        raw=os.environ['RESPONSE']
    else: raw='[{"number":1,"headRefName":"cp-owned","title":"owned"}]'
    if '--jq' in args:
        try:
            for item in json.loads(raw): print(str(item['number'])+' '+item['headRefName'])
        except Exception: print(raw)
    else: print(raw)
    sys.exit(0)
if args[:2]==['pr','checks']:
    fields=args[args.index('--json')+1].split(',')
    if any(x not in ['bucket','link','name','state'] for x in fields):
        print('Unknown JSON field',file=sys.stderr); sys.exit(1)
    print(os.environ['RESPONSE']); sys.exit(int(os.environ['API_EXIT']))
if args[:2]==['run','view']:
    if args[2:3]!=['42']: sys.exit(1)
    print('owned failure log'); sys.exit(0)
sys.exit(99)
''')
            gh.chmod(0o755)
            for name in ('git', 'curl'):
                p = base / name
                p.write_text('#!/bin/sh\necho forbidden >> "$FIXTURE_DIR/forbidden"\nexit 99\n')
                p.chmod(0o755)
            env = {**os.environ, 'PATH': str(base)+':'+os.environ['PATH'],
                   'FIXTURE_DIR': str(base), 'RESPONSE': response, 'API_EXIT': str(exit_code),
                   'FAIL_REPO': fail_repo, 'PR_NUMBER': '1', 'REPO': 'owned/fixture'}
            result = subprocess.run(['bash', '-c', block], env=env, cwd=base,
                                    capture_output=True, text=True, timeout=5)
            calls = [json.loads(x) for x in (base/'calls').read_text().splitlines()]
            self.assertFalse((base/'forbidden').exists())
            self.assertFalse(any(c[:2] in (['pr','merge'], ['api','PATCH']) for c in calls))
            return result, calls

    def test_discovery_failure_or_invalid_response_is_unknown_without_targets(self):
        for response, code in [('[]',1), ('',0), ('  \n',0), ('not json',0),
                               ('{}',0), ('null',0), ('[{}]',0),
                               ('[{"number":true,"headRefName":"cp-x","title":"x"}]',0)]:
            with self.subTest(response=response, code=code):
                r, _ = self.run_block(1, response, code, 'perfectuser21/zenithjoy-workspace')
                self.assertEqual(r.returncode, 12, r.stderr)
                self.assertNotIn('REPO=', r.stdout)
                self.assertNotIn('已合并', r.stdout)

    def test_empty_array_means_no_open_targets_not_merged(self):
        r, calls = self.run_block(1)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('无待监控', r.stdout)
        self.assertNotIn('已合并', r.stdout)
        self.assertEqual(len(calls), 3)

    def test_valid_targets_are_emitted_only_after_all_repositories_are_read(self):
        r, calls = self.run_block(1, '[{"number":7,"headRefName":"cp-owned","title":"owned"}]')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count('PR=7 BRANCH=cp-owned'), 3)
        self.assertEqual(len(calls), 3)

    def test_real_failure_diagnostic_uses_supported_fields_and_action_run(self):
        r, calls = self.run_block(3, '[{"bucket":"fail","link":"https://github.com/owned/fixture/actions/runs/42/job/99"}]', 1)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('owned failure log', r.stdout)
        self.assertTrue(any(c[:3]==['run','view','42'] for c in calls))

    def test_failure_diagnostic_rejects_unknown_or_foreign_run(self):
        for response in ['', 'not json', '[]', '[{"bucket":"pass","link":"https://github.com/owned/fixture/actions/runs/42"}]',
                         '[{"bucket":"fail","link":"https://github.com/other/repo/actions/runs/42"}]']:
            r, calls = self.run_block(3, response)
            self.assertEqual(r.returncode, 12, r.stderr)
            self.assertFalse(any(c[:2]==['run','view'] for c in calls))


if __name__ == '__main__':
    unittest.main()
