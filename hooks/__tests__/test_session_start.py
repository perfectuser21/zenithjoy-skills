"""Exercise the installed hook protocol with isolated, delayed Brain responses."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


HOOK = Path(__file__).resolve().parents[1] / "session-start.sh"


class SessionContextTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.marker = self.root / "injected"
        self.calls = self.root / "requests"
        self.script = self.root / "session-start.sh"
        text = HOOK.read_text().replace(
            'SESSION_MARKER="/tmp/.cecelia-session-${PPID}.injected"',
            'SESSION_MARKER="$HOOK_TEST_MARKER"',
        )
        self.script.write_text(text)
        curl = self.root / "curl"
        curl.write_text("""#!/usr/bin/env python3
import json, os, sys, time
def log(event):
    with open(os.environ['HOOK_TEST_CALLS'], 'a') as f:
        f.write(json.dumps({'url': sys.argv[-1], 'event': event, 'at': time.monotonic()}) + '\\n')
log('start')
time.sleep(float(os.environ.get('HOOK_TEST_DELAY', '0')))
log('end')
mode = os.environ.get('HOOK_TEST_MODE', 'online')
if mode == 'offline':
    sys.exit(28)
if mode == 'malformed':
    print('not-json')
elif 'pending-resume' in sys.argv[-1]:
    print(json.dumps({'pending': [{'title': '接力验收', 'items': [{'title': '核对证据'}]}]}))
elif 'in_progress' in sys.argv[-1]:
    print(json.dumps([{'title': '正在核对技能', 'priority': 'P1', 'task_type': 'research'}]))
else:
    print(json.dumps([{'title': '排队工作', 'priority': 'P2'}]))
""")
        curl.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.root) + os.pathsep + os.environ['PATH'],
                        HOOK_TEST_MARKER=str(self.marker), HOOK_TEST_CALLS=str(self.calls))

    def tearDown(self):
        self.temp.cleanup()

    def run_hook(self, mode="online", delay="0"):
        env = dict(self.env, HOOK_TEST_MODE=mode, HOOK_TEST_DELAY=delay)
        start = time.monotonic()
        result = subprocess.run(["bash", str(self.script)], input="{}", text=True,
                                capture_output=True, cwd=self.root, env=env, timeout=5)
        return result, time.monotonic() - start

    def assert_queries_overlap(self):
        events = [json.loads(line) for line in self.calls.read_text().splitlines()]
        starts = [e["at"] for e in events if e["event"] == "start"]
        ends = [e["at"] for e in events if e["event"] == "end"]
        self.assertEqual(len(starts), 3)
        self.assertLess(max(starts), min(ends), "All reads must begin before any read finishes")

    def test_context_and_once_per_session(self):
        first, _ = self.run_hook()
        self.assertEqual(first.returncode, 0, first.stderr)
        output = json.loads(first.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "UserPromptSubmit")
        for expected in ("正在核对技能", "排队工作", "接力验收", "核对证据"):
            self.assertIn(expected, output["additionalContext"])
        count = len(self.calls.read_text().splitlines())
        second, _ = self.run_hook()
        self.assertEqual(second.returncode, 0)
        self.assertEqual(second.stdout, "")
        self.assertEqual(len(self.calls.read_text().splitlines()), count)

    def test_offline_queries_overlap_and_stay_silent(self):
        result, elapsed = self.run_hook("offline", "0.35")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assert_queries_overlap()

    def test_online_queries_overlap(self):
        result, elapsed = self.run_hook("online", "0.35")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("接力验收", json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"])
        self.assert_queries_overlap()

    def test_bad_response_does_not_block_session(self):
        result, _ = self.run_hook("malformed")
        self.assertEqual(result.returncode, 0, result.stderr)
        if result.stdout:
            self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"],
                             "UserPromptSubmit")


if __name__ == "__main__":
    unittest.main()
