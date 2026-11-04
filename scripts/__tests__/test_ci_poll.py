"""真实 ci-poll 与 watchdog 命令块回归；仅替换外部 gh/sleep。"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def check(status='COMPLETED', conclusion='SUCCESS', name='build'):
    return {'__typename': 'CheckRun', 'name': name, 'status': status, 'conclusion': conclusion}


def snapshot(checks=None, merge='CLEAN'):
    return {'mergeStateStatus': merge, 'statusCheckRollup': [check()] if checks is None else checks}


class CiPollTest(unittest.TestCase):
    def run_entry(self, snapshots, *, api_exit=0, watchdog=False, state_exit=0, cleanup=False, initial_state="OPEN", final_state="MERGED", final_state_exit=0):
        with tempfile.TemporaryDirectory(prefix='ci-poll-regression-') as tmp:
            base = Path(tmp)
            bin_dir = base / 'bin'
            bin_dir.mkdir()
            (base / 'fixtures.json').write_text(json.dumps(snapshots))
            # gh fixture只交付外部响应；不包含CI成功/失败判断。
            gh = bin_dir / 'gh'
            gh.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
p = pathlib.Path(os.environ['FIXTURE_DIR'])
args = sys.argv[1:]
with (p/'calls').open('a') as f: f.write(json.dumps(args)+'\\n')
if args[:2] == ['pr', 'merge']: sys.exit(0)
if '--json' in args and args[args.index('--json')+1] == 'state':
    if int(os.environ['STATE_EXIT']): sys.exit(int(os.environ['STATE_EXIT']))
    state = p/'state-count'; n = int(state.read_text()) if state.exists() else 0
    state.write_text(str(n+1))
    if n > 0 and int(os.environ['FINAL_STATE_EXIT']): sys.exit(int(os.environ['FINAL_STATE_EXIT']))
    print(os.environ['INITIAL_STATE'] if n == 0 else os.environ['FINAL_STATE']); sys.exit(0)
if '--json' in args and args[args.index('--json')+1] == 'url':
    print('https://fixture.invalid/pr/1'); sys.exit(0)
if '--json' in args and args[args.index('--json')+1] == 'autoMergeRequest':
    print('null'); sys.exit(0)
if int(os.environ['API_EXIT']): sys.exit(int(os.environ['API_EXIT']))
counter = p/'count'; n = int(counter.read_text()) if counter.exists() else 0
counter.write_text(str(n+1))
rows = json.loads((p/'fixtures.json').read_text())
row = rows[min(n, len(rows)-1)]
print(row if isinstance(row, str) else json.dumps(row))
''')
            gh.chmod(0o755)
            sleep = bin_dir / 'sleep'
            sleep.write_text('#!/bin/sh\necho sleep >> "$FIXTURE_DIR/sleeps"\n')
            sleep.chmod(0o755)
            for name in ('git', 'curl', 'jq'):
                tool = bin_dir / name
                tool.write_text("#!/usr/bin/env python3\nimport os, pathlib, json, sys\np=pathlib.Path(os.environ['FIXTURE_DIR'])\nwith (p/'calls').open('a') as f: f.write(json.dumps(['fixture-'+pathlib.Path(sys.argv[0]).name]+sys.argv[1:])+'\\n')\nprint('{}')\n")
                tool.chmod(0o755)
            (base/'dev-mode').write_text('task_id: fixture-task\n')
            home = base / 'home' 
            (home / 'perfect21').mkdir(parents=True)
            (home / 'perfect21/zenithjoy-skills').symlink_to(ROOT)
            env = {**os.environ, 'PATH': str(bin_dir) + ':' + os.environ['PATH'],
                   'FIXTURE_DIR': str(base), 'API_EXIT': str(api_exit),
                   'STATE_EXIT': str(state_exit), 'HOME': str(home), 'INITIAL_STATE': initial_state,
                   'FINAL_STATE': final_state, 'FINAL_STATE_EXIT': str(final_state_exit)}
            command = ['bash', str(ROOT / 'scripts/ci-poll.sh'), '987654321', 'owned/fixture']
            if watchdog:
                text = (ROOT / 'engine-pr-watchdog/SKILL.md').read_text()
                blocks = text.split('```bash\n')
                block = next(b.split('```')[0] for b in blocks[1:] if 'MAX_FIXES=3' in b)
                block = block.replace('PR_NUMBER=<PR号>', 'PR_NUMBER=987654321')
                block = block.replace('REPO=<owner/repo>', 'REPO=owned/fixture')
                block = block.replace('WORKTREE_PATH=<worktree路径>', 'WORKTREE_PATH=/unused')
                block = block.replace('DEV_MODE_FILE=<.dev-mode文件路径>', 'DEV_MODE_FILE=' + str(base/'dev-mode'))
                # 隔离原命令块的计数文件，不修改控制流。
                block = block.replace('/tmp/watchdog-fix-count-', str(base) + '/watchdog-fix-count-')
                if cleanup:
                    block += '\n' + next(b.split('```')[0] for b in blocks[1:] if '# 读取 task_id' in b)
                command = ['bash', '-c', block]
            result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=5)
            calls = [json.loads(x) for x in (base/'calls').read_text().splitlines()]
            slept = (base/'sleeps').exists()
            return result, calls, slept

    def assert_unknown(self, value, **kwargs):
        result, calls, _ = self.run_entry([value], **kwargs)
        self.assertEqual(result.returncode, 12, result.stderr)
        self.assertNotIn('CI_GREEN', result.stderr)
        self.assertNotIn('已合并', result.stdout)
        self.assertFalse(any(c[:2] == ['pr', 'merge'] for c in calls))

    def test_api_failure_is_unknown(self):
        self.assert_unknown(snapshot(), api_exit=1)

    def test_malformed_and_missing_snapshots_are_unknown(self):
        for value in ['not json', '', {}, {'mergeStateStatus': 'CLEAN'}, snapshot([]),
                      snapshot([{}]), snapshot([check(status='COMPLETED', conclusion=None)]),
                      snapshot([check(status='MYSTERY')]), snapshot(merge='UNKNOWN')]:
            with self.subTest(value=value):
                self.assert_unknown(value)

    def test_failure_and_behind_preserve_exit_contract(self):
        for value, code in [(snapshot([check(conclusion='FAILURE')]), 10),
                            (snapshot([check(conclusion='CANCELLED')]), 10),
                            (snapshot(merge='BEHIND'), 11)]:
            with self.subTest(code=code, value=value):
                result, _, _ = self.run_entry([value])
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertNotIn('CI_GREEN', result.stderr)

    def test_real_green_uses_fields_not_check_name(self):
        result, _, slept = self.run_entry([snapshot([check(name='fail pending regression')])])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CI_GREEN', result.stderr)
        self.assertFalse(slept)

    def test_pending_must_wait_for_actual_green(self):
        for pending in [check(status='QUEUED', conclusion=None),
                        check(status='IN_PROGRESS', conclusion=None),
                        check(status='QUEUED', conclusion=''),
                        check(status='IN_PROGRESS', conclusion=''),
                        {'__typename': 'StatusContext', 'state': 'PENDING', 'context': 'lint'}]:
            with self.subTest(pending=pending):
                result, calls, slept = self.run_entry([snapshot([pending]), snapshot()])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(slept, 'pending不得直接报告绿色')
                self.assertGreaterEqual(len(calls), 2)
                self.assertIn('CI_GREEN', result.stderr)

    def test_legacy_status_context_success(self):
        result, _, _ = self.run_entry([snapshot([{'__typename':'StatusContext', 'state':'SUCCESS'}])])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_watchdog_unknown_must_not_merge(self):
        self.assert_unknown(snapshot(), api_exit=1, watchdog=True)

    def test_watchdog_initial_state_api_failure_must_not_claim_merged(self):
        self.assert_unknown(snapshot(), state_exit=1, watchdog=True)

    def test_closed_cleanup_never_records_a_successful_merge(self):
        result, calls, _ = self.run_entry([snapshot()], watchdog=True, cleanup=True,
                                         initial_state='CLOSED', final_state='CLOSED')
        self.assertEqual(result.returncode, 0, result.stderr)
        writes = [json.loads(c[c.index('-d')+1]) for c in calls if c[0] == 'fixture-curl']
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]['status'], 'failed')
        self.assertEqual(writes[0]['result']['merged'], False)
        self.assertEqual(writes[0]['result']['closed'], True)
        self.assertEqual(writes[0]['result'].get('handoff', {}).get('verdict'), 'FAIL')

    def test_cleanup_rechecks_state_before_any_mutation(self):
        for state, api_exit in [('OPEN', 0), ('', 0), ('UNKNOWN', 0), ('MERGED', 1)]:
            with self.subTest(state=state, api_exit=api_exit):
                result, calls, _ = self.run_entry([snapshot()], watchdog=True, cleanup=True,
                    initial_state='MERGED', final_state=state, final_state_exit=api_exit)
                self.assertEqual(result.returncode, 12, result.stderr)
                self.assertFalse(any(c[0] in ('fixture-git', 'fixture-curl') for c in calls))

    def test_verified_merged_cleanup_records_pass(self):
        result, calls, _ = self.run_entry([snapshot()], watchdog=True, cleanup=True,
                                         initial_state='MERGED', final_state='MERGED')
        self.assertEqual(result.returncode, 0, result.stderr)
        writes = [json.loads(c[c.index('-d')+1]) for c in calls if c[0] == 'fixture-curl']
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]['status'], 'completed')
        self.assertEqual(writes[0]['result']['merged'], True)
        self.assertEqual(writes[0]['result'].get('handoff', {}).get('verdict'), 'PASS')

    def test_watchdog_green_can_request_auto_merge(self):
        result, calls, _ = self.run_entry([snapshot()], watchdog=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(c[:2] == ['pr', 'merge'] for c in calls))


if __name__ == '__main__':
    unittest.main()
