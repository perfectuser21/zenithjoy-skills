"""实际dev示例Bash→本人HTTP；验证调用方提供路由身份，不触生产账本。"""
import http.server
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
TASK = '11111111-1111-4111-8111-111111111111'


class TaskRegistrationTest(unittest.TestCase):
    def execute_example(self, task_type, mode="ok"):
        body = (ROOT / 'dev/SKILL.md').read_text().split('---', 2)[2]
        candidates = [block for block in re.findall(r'```bash\n(.*?)```', body, re.S)
                      if 'POST localhost:5221/api/brain/tasks' in block
                      and '\\"task_type\\": \\"' + task_type + '\\"' in block]
        self.assertEqual(len(candidates), 1, '必须执行唯一当前建单示例，而非历史changelog')
        trace = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_args): pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                # 边界夹具模拟无目标repo checkout的Brain；不能依赖服务器git fallback。
                is_claim = self.path.endswith('/claim')
                valid = is_claim or (isinstance(payload.get('branch'), str)
                    and payload['branch'].startswith('cp-')
                    and re.fullmatch('[0-9a-f]{40}', payload.get('base_sha', '')))
                code = 200 if valid else 500
                trace.append({'path': self.path, 'body': payload, 'status': code})
                self.send_response(code); self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'id': TASK} if valid else
                    {'error': 'routing_evidence_unavailable'}).encode())
        with tempfile.TemporaryDirectory(prefix='dev-entry-owned-') as tmp:
            fixture = Path(tmp)
            git = ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false']
            subprocess.run(git + ['init', '-q', '-b', 'cp-owned-registration'], cwd=fixture, check=True)
            subprocess.run(git + ['-c', 'user.name=Owned fixture', '-c', 'user.email=owned@example.invalid',
                'commit', '-q', '--allow-empty', '-m', 'owned routing evidence'], cwd=fixture, check=True)
            head = subprocess.check_output(git + ['rev-parse', 'HEAD'], cwd=fixture, text=True).strip()
            expected_repo = 'perfectuser21/' + ('cecelia' if task_type == 'coding_workflow' else 'zenithjoy-workspace')
            remote = 'https://github.com/' + ('other/wrong' if mode == 'wrong-repo' else expected_repo)
            subprocess.run(git + ['remote', 'add', 'origin', remote], cwd=fixture, check=True)
            subprocess.run(git + ['update-ref', 'refs/remotes/origin/main', head], cwd=fixture, check=True)
            block = candidates[0]
            replacements = {'<当前cp分支>': '' if mode == 'missing-branch' else 'cp-owned-registration', '<真实origin/main完整SHA>': 'b' * 40 if mode == 'fake-sha' else head,
                            '<真实目标仓绝对路径>': str(fixture), '<目标仓真实开发基准ref或完整SHA>': 'b' * 40 if mode == 'fake-sha' else 'refs/remotes/origin/main',
                            '<id>': TASK, '<格子>': 'skill_distribution'}
            for old, new in replacements.items(): block = block.replace(old, new)
            block = re.sub(r'<[^>]+>', 'owned-value', block)
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                # 唯一改写网络地址：保留源示例正文、真实curl以及实际请求JSON。
                block = block.replace('localhost:5221', 'http://127.0.0.1:' + str(server.server_port))
                env = {**os.environ, 'http_proxy': '', 'https_proxy': '', 'ALL_PROXY': '', 'NO_PROXY': '*'}
                if mode == 'git-error':
                    bindir = fixture / 'bin'; bindir.mkdir()
                    fake = bindir / 'git'; fake.write_text('#!/bin/sh\nexit 91\n'); fake.chmod(0o755)
                    env['PATH'] = str(bindir) + os.pathsep + env['PATH']
                result = subprocess.run(['bash', '-euo', 'pipefail', '-c', block], cwd=fixture,
                                        env=env, capture_output=True, text=True, timeout=10)
            finally:
                server.shutdown(); server.server_close(); thread.join()
        if mode != 'ok':
            self.assertNotEqual(result.returncode, 0, '错误Git/缺分支/假SHA必须在发请求前拒绝')
            self.assertEqual(trace, [], '无可信路由身份不能POST或claim')
            return trace
        self.assertEqual(result.returncode, 0, result.stderr)
        create = trace[0]
        self.assertEqual(create['path'], '/api/brain/tasks')
        self.assertEqual(create['status'], 200, '示例缺base/branch会依赖服务器checkout并触发真实已证500')
        payload = create['body']
        self.assertEqual(payload['branch'], 'cp-owned-registration')
        self.assertEqual(payload['base_sha'], head)
        self.assertTrue(payload['repo_hint']); self.assertTrue(payload['map_scope_hint'])
        self.assertEqual(payload['mutation_intent'], 'write')
        self.assertEqual(payload['change_kind'], 'capability_change')
        self.assertNotIn('orchestrator', payload)
        self.assertNotIn('orchestrator', payload['payload'])
        self.assertNotIn('harness_runtime', payload['payload'])
        self.assertNotIn('routing_receipt_id', payload['payload'])
        return trace

    def test_current_coding_workflow_example_supplies_real_routing_identity(self):
        trace = self.execute_example('coding_workflow')
        self.assertEqual(len(trace), 1)
        self.assertTrue(trace[0]['body']['payload']['coding_workflow'])

    def test_current_headed_example_preserves_manual_string_and_immediate_claim(self):
        trace = self.execute_example('dev')
        self.assertEqual(len(trace), 2)
        self.assertEqual(trace[0]['body']['payload']['headed_manual'], 'true')
        self.assertEqual(trace[1]['path'], '/api/brain/tasks/' + TASK + '/claim')
        self.assertEqual(trace[1]['body']['claimer'], 'interactive-dev-skill')

    def test_untrusted_routing_context_never_sends_any_request(self):
        for task_type in ('coding_workflow', 'dev'):
            for mode in ('git-error', 'missing-branch', 'fake-sha', 'wrong-repo'):
                with self.subTest(task_type=task_type, mode=mode):
                    self.execute_example(task_type, mode)


if __name__ == '__main__': unittest.main()
