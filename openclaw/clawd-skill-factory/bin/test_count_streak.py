#!/usr/bin/env python3
"""count_streak 的规则测试（决策 5826ddd7 / 6ec463c3 / 1b469079）。

运行：python3 openclaw/clawd-skill-factory/bin/test_count_streak.py
"""
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("count_streak", os.path.join(_HERE, "count_streak.py"))
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)


def run(i, verdict, skill="flow@1.2.0", slice_="abc123", inp=None, external=None):
    return {"id": "r%02d" % i, "created_at": "2026-10-08T00:%02d:00Z" % i, "skill": skill,
            "slice_digest": slice_, "input": inp if inp is not None else "kw%d" % i,
            "verdict": verdict, "external_cause": external}


class StreakRules(unittest.TestCase):
    def test_clean_passes_count(self):
        r = cs.count_streak([run(i, "pass") for i in range(1, 11)], k=10)
        self.assertEqual(r["streak"], 10)
        self.assertTrue(r["reached"])

    def test_below_k_not_reached(self):
        r = cs.count_streak([run(i, "pass") for i in range(1, 4)], k=10)
        self.assertEqual(r["streak"], 3)
        self.assertFalse(r["reached"])

    def test_fail_resets(self):
        runs = [run(1, "pass"), run(2, "pass"), run(3, "fail"), run(4, "pass")]
        r = cs.count_streak(runs, k=10)
        self.assertEqual(r["streak"], 1)
        self.assertEqual(r["reset_by"]["run"], "r03")

    def test_external_cause_is_void_not_reset(self):
        runs = [run(1, "pass"), run(2, "fail", external="手机掉线"), run(3, "pass")]
        r = cs.count_streak(runs, k=10)
        self.assertEqual(r["streak"], 2)
        self.assertEqual(r["voided"], ["r02"])
        self.assertIsNone(r["reset_by"])

    def test_version_change_resets(self):
        runs = [run(1, "pass", skill="flow@1.1.0"), run(2, "pass", skill="flow@1.2.0")]
        r = cs.count_streak(runs, k=10)
        self.assertEqual(r["streak"], 1)
        self.assertEqual(r["current"]["skill"], "flow@1.2.0")
        self.assertIn("版本", r["reset_by"]["reason"])

    def test_slice_digest_change_resets(self):
        runs = [run(1, "pass", slice_="old"), run(2, "pass", slice_="new")]
        r = cs.count_streak(runs, k=10)
        self.assertEqual(r["streak"], 1)
        self.assertIn("处置表", r["reset_by"]["reason"])

    def test_duplicate_input_not_counted(self):
        runs = [run(1, "pass", inp="同一个词"), run(2, "pass", inp="同一个词")]
        r = cs.count_streak(runs, k=10)
        self.assertEqual(r["streak"], 1)
        self.assertEqual(r["duplicate_input"], ["r01"])

    def test_pending_run_does_not_count_or_reset(self):
        runs = [run(1, "pass"), run(2, None)]
        r = cs.count_streak(runs, k=10)
        self.assertEqual(r["streak"], 1)
        self.assertEqual(r["pending"], ["r02"])

    def test_missing_skill_or_input_not_counted(self):
        runs = [run(1, "pass"), run(2, "pass", inp="")]
        r = cs.count_streak(runs, k=10)
        self.assertEqual(r["streak"], 1)
        self.assertEqual(r["unverifiable"], ["r02"])

    def test_empty(self):
        r = cs.count_streak([], k=10)
        self.assertEqual(r["streak"], 0)
        self.assertFalse(r["reached"])


class ParseParams(unittest.TestCase):
    def test_parse_block(self):
        body = ("前言\n【执行参数】\n执行Agent：skill-factory\n阶段：验证\n计数阶段任务：abc-123\n"
                "Skill：flow@1.2.0\n输入：关键词A\n处置表片指纹：deadbeef\n【执行参数结束】\n其他：不算")
        p = cs.parse_params(body)
        self.assertEqual(p["阶段"], "验证")
        self.assertEqual(p["计数阶段任务"], "abc-123")
        self.assertEqual(p["skill"], "flow@1.2.0")
        self.assertEqual(p["输入"], "关键词A")
        self.assertEqual(p["处置表片指纹"], "deadbeef")
        self.assertNotIn("其他", p)

    def test_half_width_colon(self):
        p = cs.parse_params("【执行参数】\nSkill: flow@2.0.0\n【执行参数结束】")
        self.assertEqual(p["skill"], "flow@2.0.0")


def _run_task(tid, created, inp):
    body = "【执行参数】\n阶段：验证\nSkill：flow@1.2.0\n输入：%s\n处置表片指纹：abc\n【执行参数结束】" % inp
    return {"id": tid, "task_type": "qiumi_task", "created_at": created, "payload": {"qiumi_source": {"body": body}}}


def _audit_task(tid, src, created, verdict, external=None):
    return {"id": tid, "task_type": "audit", "created_at": created, "payload": {"source_task_id": src},
            "result": {"verification": {"verdict": verdict, "external_cause": external}}}


class CollectRuns(unittest.TestCase):
    """跑场机到 Brain 链路很慢（全量拉取 1～2 MB 要一两分钟），只许走 chain + 逐张取。"""

    def setUp(self):
        self.tasks = {
            "r1": _run_task("r1", "2026-10-08T01:00:00Z", "词1"),
            "r2": _run_task("r2", "2026-10-08T02:00:00Z", "词2"),
            "a1": _audit_task("a1", "r1", "2026-10-08T01:30:00Z", "pass"),
            "a2": _audit_task("a2", "r2", "2026-10-08T02:30:00Z", "fail", external="手机掉线"),
        }
        self.calls = []

    def get(self, path):
        self.calls.append(path)
        if path == "/tasks/S/chain":
            return {"children": [{"id": k, "task_type": v["task_type"]} for k, v in self.tasks.items()]}
        if path.startswith("/tasks/") and path[len("/tasks/"):] in self.tasks:
            return self.tasks[path[len("/tasks/"):]]
        raise AssertionError("不该请求: " + path)

    def test_pairs_runs_with_audits_via_chain(self):
        runs = cs.collect_runs(self.get, "S")
        self.assertEqual([r["id"] for r in runs], ["r1", "r2"])
        self.assertEqual(runs[0]["verdict"], "pass")
        self.assertEqual(runs[1]["external_cause"], "手机掉线")
        self.assertEqual(runs[0]["input"], "词1")

    def test_no_full_scan_by_default(self):
        cs.collect_runs(self.get, "S")
        self.assertFalse([c for c in self.calls if "task_type=" in c], "默认不得全量扫描")

    def test_run_without_audit_is_pending(self):
        del self.tasks["a2"]
        runs = cs.collect_runs(self.get, "S")
        self.assertIsNone(runs[1]["verdict"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
