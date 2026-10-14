#!/usr/bin/env python3
"""防止执行规矩回退到已退役入口、自报晋级或直写投影。"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
class CommanderRules(unittest.TestCase):
    def read(self, path): return (ROOT / path).read_text()
    def test_lifecycle_keeps_skill_and_uses_evidence(self):
        text = self.read('workflow-lifecycle/SKILL.md')
        self.assertNotIn('SOP 同步删掉该条', text)
        self.assertNotIn('第 3 次 → 开 dev 单', text)
        self.assertIn('execution_role', text)
        self.assertIn('独立核验', text)
    def test_solidify_has_available_independent_contract(self):
        text = self.read('skill-solidify/SKILL.md')
        self.assertNotRegex(text, r'(?:用|通过|不适用[^\n]*)[^\n]*`?code-verify')
        for field in ['implementation', 'environment', 'execution_role', 'verification_ref']:
            self.assertIn(field, text)
        self.assertIn('run-verify', text)
        self.assertFalse('先跑满' in text, '不得以默认次数作为固化评估前置门槛')
        self.assertFalse('reached=true' in text, '次数只能做证据统计')
        self.assertFalse('不足 K 条 → `status=rejected`' in text, '证据不足不得单靠次数拒绝评估')
    def test_brain_is_not_knowledge_body(self):
        text = self.read('db-update/SKILL.md')
        self.assertNotIn('所有写入先走 Brain API', text)
        self.assertNotIn('所有文档走这里', text)
        for name in ['Knowledge_Reference', 'Knowledge_Operational', 'Insights']:
            self.assertIn(name, text)
    def test_notion_does_not_write_projections(self):
        text = self.read('notion/SKILL.md')
        self.assertNotRegex(text, r'parent:\s*\{database_id:\s*env\.NOTION_(?:ISSUES|NOTES)_DB')
        self.assertIn('/api/brain/strategic-decisions', text)
        self.assertIn('Knowledge_Operational', text)

if __name__ == '__main__': unittest.main()
