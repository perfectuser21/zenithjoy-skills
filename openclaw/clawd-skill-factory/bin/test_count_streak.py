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


if __name__ == "__main__":
    unittest.main(verbosity=1)
