"""Creation tests use disposable repositories and installation homes only."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]


class CreationLocationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.repo = self.root / 'central'
        self.repo.mkdir()
        self.env = {**os.environ, 'HOME': str(self.home)}
        for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE'):
            self.env.pop(key, None)
        self.git(self.repo, 'init', '-q')
        self.git(self.repo, 'config', 'core.hooksPath', '/dev/null')
        self.git(self.repo, 'remote', 'add', 'origin', 'git@github.com:perfectuser21/zenithjoy-skills.git')
        target = self.repo / 'skill-creator/scripts'
        target.mkdir(parents=True)
        for name in ('create-skill.sh', 'register-skill.sh'):
            shutil.copyfile(SCRIPTS / name, target / name)
        self.git(self.repo, 'add', '.')
        self.git(self.repo, '-c', 'user.name=Fixture', '-c', 'user.email=f@f', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')
        self.work = self.root / 'work'
        self.git(self.repo, 'worktree', 'add', '-qb', 'cp-test', str(self.work))

    def git(self, cwd, *args):
        return subprocess.run(['git', '-C', str(cwd), *args], env=self.env, check=True, capture_output=True)

    def run_script(self, name, *args, cwd=None):
        return subprocess.run(['bash', str(self.work / 'skill-creator/scripts' / name), *args],
                              cwd=cwd or self.work, env=self.env, capture_output=True, text=True)

    def test_creation_has_central_body_and_reference_only_installation(self):
        result = self.run_script('create-skill.sh', 'new-skill', 'Quoted "description"', 'complex')
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue((self.work / 'new-skill/SKILL.md').is_file())
        self.assertTrue((self.work / 'new-skill/scripts').is_dir())
        link = self.home / '.claude/skills/new-skill'
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), (self.work / 'new-skill').resolve())
        self.assertFalse((self.home / '.claude/skills-registry.local.json').exists())

    def test_business_cwd_is_rejected_before_writing(self):
        business = self.root / 'business'
        business.mkdir()
        self.git(business, 'init', '-q')
        result = self.run_script('create-skill.sh', 'wrong-skill', 'description', cwd=business)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((business / 'wrong-skill').exists())
        self.assertFalse((self.work / 'wrong-skill').exists())
        self.assertFalse((self.home / '.claude').exists())

    def test_invalid_name_and_type_never_create_anything(self):
        for args in (('../escape', 'description'), ('valid-name', 'description', 'unknown')):
            result = self.run_script('create-skill.sh', *args)
            self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / '.claude').exists())
        self.assertFalse((self.work / 'valid-name').exists())
        self.assertFalse((self.root / 'escape').exists())

    def test_registration_is_idempotent_and_preserves_existing_body(self):
        source = self.work / 'existing'
        source.mkdir()
        (source / 'SKILL.md').write_text('body')
        for classification in ('personal', 'core'):
            result = self.run_script('register-skill.sh', classification, 'existing', 'description', str(source))
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((source / 'SKILL.md').read_text(), 'body')
        self.assertTrue((self.home / '.claude/skills/existing').is_symlink())
        self.assertFalse((self.home / 'perfect21').exists())

    def test_main_checkout_is_rejected(self):
        result = self.run_script('create-skill.sh', 'wrong-skill', 'description', cwd=self.repo)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.repo / 'wrong-skill').exists())

    def test_existing_installation_is_preserved_before_body_creation(self):
        existing = self.home / '.claude/skills/new-skill'
        existing.mkdir(parents=True)
        (existing / 'keep').write_text('local')
        result = self.run_script('create-skill.sh', 'new-skill', 'description')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((existing / 'keep').read_text(), 'local')
        self.assertFalse((self.work / 'new-skill').exists())

    def test_register_core_only_links_central_source_and_rejects_external(self):
        source = self.work / 'existing'
        source.mkdir()
        (source / 'SKILL.md').write_text('body')
        result = self.run_script('register-skill.sh', 'core', 'existing', 'description', str(source))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue((self.home / '.claude/skills/existing').is_symlink())
        self.assertNotIn('engine/skills', result.stdout)
        external = self.root / 'external'
        external.mkdir()
        (external / 'SKILL.md').write_text('outside')
        result = self.run_script('register-skill.sh', 'personal', 'external', 'description', str(external))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / '.claude/skills/external').exists())


if __name__ == '__main__':
    unittest.main()
