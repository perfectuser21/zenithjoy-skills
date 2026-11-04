"""执行实际Skill Bash及同release helper；GitHub/git为边界夹具，Brain为本人HTTP。"""
import copy
import http.server
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
TASK = '11111111-1111-4111-8111-111111111111'
HEAD = 'a' * 40
REPO = 'perfectuser21/cecelia'


class CandidateReceiptTest(unittest.TestCase):
    def run_entry(self, mode='ok'):
        with tempfile.TemporaryDirectory(prefix='engine-ship-owned-') as tmp:
            base = Path(tmp)
            release = base / 'fixed release'
            shutil.copytree(ROOT / 'engine-ship', release / 'engine-ship', ignore=shutil.ignore_patterns('__pycache__'))
            loaded = base / 'installed' / 'engine-ship'
            loaded.parent.mkdir()
            loaded.symlink_to(release / 'engine-ship', target_is_directory=True)
            skill = loaded / 'SKILL.md'
            text = skill.read_text()
            block = re.search(r'```bash\n(# engine-ship candidate receipt\n.*?)```', text, re.S)
            self.assertIsNotNone(block, '真实Skill缺候选回执入口，不能以旧completed回调充交付')
            commands = block.group(1)
            if mode == 'wrong-version':
                (release / 'engine-ship/SKILL.md').write_text(text.replace('version: 17.0.0', 'version: 0.0.0'))
            if mode == 'missing-helper':
                (release / 'engine-ship/scripts/record-candidate.py').unlink()
            if mode == 'escaped-helper':
                helper = release / 'engine-ship/scripts/record-candidate.py'
                outside = base / 'wrong.py'
                outside.write_text("raise Exception('cross release executed')")
                helper.unlink()
                helper.symlink_to(outside)
            facts = base / 'facts.json'
            facts.write_text(json.dumps({'facts': ['已修复当前CLI回归'], 'evidence': [{'path': '/tmp/owned-result.json', 'sha256': 'b' * 64}]}))
            bindir = base / 'bin'
            bindir.mkdir()
            gh = bindir / 'gh'
            gh.write_text("""#!/usr/bin/env python3
import json,os,sys,pathlib
p=pathlib.Path(os.environ['OWNED_FIXTURE']);m=os.environ['OWNED_MODE']
with (p/'calls').open('a') as f:f.write(json.dumps(['gh']+sys.argv[1:])+'\\n')
if m=='gh-error':sys.exit(1)
if m=='bad-pr-json':print('{broken');sys.exit(0)
print(json.dumps({'number':7,'url':'https://github.com/perfectuser21/cecelia/pull/7','headRefOid':('c'*40 if m=='wrong-head' else 'a'*40),'state':{'closed':'CLOSED','merged':'MERGED','unknown':'UNKNOWN'}.get(m,'OPEN')}))
""")
            gh.chmod(0o755)
            git = bindir / 'git'
            git.write_text("#!/bin/sh\ncase \"$*\" in 'rev-parse HEAD') printf '%s\\n' '"+HEAD+"';; 'status --porcelain') exit 0;; *) exit 91;; esac\n")
            git.chmod(0o755)
            curl = bindir / 'curl'
            curl.write_text('#!/bin/sh\necho forbidden-curl >> "$OWNED_FIXTURE/calls"\nexit 91\n')
            curl.chmod(0o755)
            current = {'id': TASK, 'status': 'in_progress', 'result': {'unrelated': {'keep': True}}}
            trace = []
            class Handler(http.server.BaseHTTPRequestHandler):
                def log_message(self, *_args):
                    pass
                def send_json(self, value, code=200):
                    self.send_response(code)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(value).encode())
                def do_GET(self):
                    trace.append({'method': 'GET', 'path': self.path})
                    out = copy.deepcopy(current)
                    if mode == 'wrong-task': out['id'] = 'bad'
                    if mode == 'terminal-task': out['status'] = 'completed'
                    if mode == 'readback-mismatch' and len(trace) > 1: out['result']['ship_candidate']['head_sha'] = 'c' * 40
                    self.send_json(out)
                def do_PATCH(self):
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    trace.append({'method': 'PATCH', 'path': self.path, 'body': body})
                    if mode == 'patch-error': return self.send_json({'error': 'fixture rejected'}, 500)
                    current['result'].update(body.get('result', {}))
                    self.send_json(current)
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                replacements = {
                    '<本次实际加载的SKILL.md绝对路径>': str(skill),
                    '<Task UUID>': TASK, '<owner/repo>': REPO, '<PR号>': '7',
                    '<当前候选完整HEAD>': HEAD, '<执行者>': 'codex:owned-review',
                    '<事实证据JSON绝对路径>': str(facts),
                    '<Brain API根地址>': 'http://127.0.0.1:' + str(server.server_port),
                }
                for key, value in replacements.items(): commands = commands.replace(shlex.quote(key), shlex.quote(value))
                env = {**os.environ, 'PATH': str(bindir)+os.pathsep+os.environ['PATH'], 'OWNED_FIXTURE':str(base), 'OWNED_MODE': mode, 'PYTHONDONTWRITEBYTECODE':'1'}
                result = subprocess.run(['bash','-euo','pipefail','-c',commands],cwd=base,env=env,capture_output=True,text=True,timeout=15)
            finally:
                server.shutdown(); server.server_close(); thread.join()
            return result, trace, current, (base/'calls').read_text() if (base/'calls').exists() else ''

    def test_open_candidate_real_receipt_without_terminal_claim(self):
        r, trace, state, calls = self.run_entry()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([x['method'] for x in trace], ['GET','PATCH','GET'])
        body = trace[1]['body']
        self.assertEqual(set(body), {'result'})
        self.assertEqual(set(body['result']), {'ship_candidate'})
        candidate = state['result']['ship_candidate']
        for key,value in {'head_sha':HEAD,'pr_url':'https://github.com/'+REPO+'/pull/7','actor':'codex:owned-review','stage':'candidate','merged':False}.items(): self.assertEqual(candidate[key],value)
        self.assertTrue(candidate['facts']); self.assertTrue(candidate['evidence'])
        self.assertEqual(state['status'],'in_progress')
        self.assertEqual(state['result']['unrelated'],{'keep':True})
        self.assertNotIn('PASS',json.dumps(candidate))
        self.assertNotIn('forbidden-curl',calls)

    def test_unknown_or_terminal_pr_never_writes_candidate(self):
        for mode in ['gh-error','bad-pr-json','wrong-head','closed','merged','unknown']:
            with self.subTest(mode=mode):
                r,trace,_,_ = self.run_entry(mode)
                self.assertNotEqual(r.returncode,0,r.stdout)
                self.assertFalse(any(x['method']=='PATCH'for x in trace))

    def test_task_identity_or_write_failure_does_not_report_success(self):
        for mode in ['wrong-task','terminal-task','patch-error','readback-mismatch']:
            with self.subTest(mode=mode):
                r,_,_,_ = self.run_entry(mode)
                self.assertNotEqual(r.returncode,0,r.stdout)
                self.assertNotIn('CANDIDATE_RECORDED',r.stdout)

    def test_invalid_release_fails_before_any_external_boundary(self):
        for mode in ['wrong-version','missing-helper','escaped-helper']:
            with self.subTest(mode=mode):
                r,trace,_,calls = self.run_entry(mode)
                self.assertNotEqual(r.returncode,0,r.stdout)
                self.assertEqual(trace,[])
                self.assertEqual(calls,'')

    def test_legacy_callback_cannot_mark_unmerged_task_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);binary=p/'curl';binary.write_text('#!/bin/sh\necho called >> "$HOME/calls"\nexit 0\n');binary.chmod(0o755)
            r=subprocess.run(['bash',str(ROOT/'dev/scripts/callback-brain-task.sh'),'--task-id',TASK,'--pr','7','--branch','cp-owned'],env={**os.environ,'PATH':str(p)+os.pathsep+os.environ['PATH'],'HOME':tmp},cwd=tmp,capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)
            self.assertFalse((p/'calls').exists())

if __name__ == '__main__': unittest.main()
