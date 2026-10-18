"""Behavioral checks for pinned, generated business-repository skill files."""
import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import sys


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.source = self.root / "source"
        self.workspace.mkdir()
        self.source.mkdir()
        self.payload = b"# Real skill\n"
        (self.source / "example.md").write_bytes(self.payload)
        self.entry = {"path": "skills/example/SKILL.md", "source": "example.md",
                      "sha256": hashlib.sha256(self.payload).hexdigest(), "mode": "100644"}
        self.catalog = {"version": 1, "profiles": {"example": {"files": [self.entry]}}}
        self.write_catalog()
        loader = Path(__file__).with_name("skills_source.py")
        if loader.exists():
            (self.source / "distribution/skills_source.py").write_bytes(loader.read_bytes())
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        # Fixture repositories contain data, not project changes or project hooks.
        (self.source / ".git/fixture-hooks").mkdir()
        subprocess.run(["git", "-C", str(self.source), "config", "core.hooksPath",
                        str(self.source / ".git/fixture-hooks")], check=True)
        self.commit_source()
        spec = importlib.util.spec_from_file_location("skills_source", Path(__file__).with_name("skills_source.py"))
        if not spec.origin or not Path(spec.origin).exists():
            self.fail("Pinned skill loader has not been implemented")
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def write_catalog(self):
        (self.source / "distribution").mkdir(exist_ok=True)
        (self.source / "distribution/catalog.json").write_text(json.dumps(self.catalog))

    def commit_source(self):
        subprocess.run(["git", "-C", str(self.source), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.source), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
                        "commit", "-qm", "fixture"], check=True)
        revision = subprocess.check_output(["git", "-C", str(self.source), "rev-parse", "HEAD"], text=True).strip()
        lock = {"version": 1, "repository": "perfectuser21/zenithjoy-skills",
                "revision": revision, "profile": "example",
                "loader_sha256": hashlib.sha256((self.source / "distribution/skills_source.py").read_bytes()).hexdigest()}
        (self.workspace / ".skills-source.json").write_text(json.dumps(lock))

    def test_install_restores_original_path_and_checks_content(self):
        self.assertEqual(self.module.install(self.workspace, self.source), 1)
        restored = self.workspace / self.entry["path"]
        self.assertEqual(restored.read_bytes(), self.payload)
        self.assertEqual(self.module.verify(self.workspace, self.source), 1)
        self.assertEqual(self.module.install(self.workspace, self.source), 1)

    def test_local_edit_is_never_overwritten(self):
        self.module.install(self.workspace, self.source)
        restored = self.workspace / self.entry["path"]
        restored.write_text("local edit")
        with self.assertRaisesRegex(ValueError, "modified"):
            self.module.install(self.workspace, self.source)
        self.assertEqual(restored.read_text(), "local edit")

    def test_corrupt_source_fails_before_any_output_is_written(self):
        self.catalog["profiles"]["example"]["files"].append(
            {**self.entry, "path": "skills/second/SKILL.md", "sha256": "0" * 64})
        self.write_catalog()
        self.commit_source()
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.module.install(self.workspace, self.source)
        self.assertFalse((self.workspace / self.entry["path"]).exists())

    def test_path_escape_and_symlink_escape_are_rejected(self):
        self.entry["path"] = "../outside.md"
        self.write_catalog()
        self.commit_source()
        with self.assertRaisesRegex(ValueError, "path"):
            self.module.install(self.workspace, self.source)
        self.entry["path"] = "linked/SKILL.md"
        self.write_catalog()
        self.commit_source()
        (self.workspace / "linked").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "path"):
            self.module.install(self.workspace, self.source)

    def test_source_must_match_pinned_commit(self):
        lock = json.loads((self.workspace / ".skills-source.json").read_text())
        lock["revision"] = "0" * 40
        (self.workspace / ".skills-source.json").write_text(json.dumps(lock))
        with self.assertRaisesRegex(ValueError, "revision"):
            self.module.install(self.workspace, self.source)

    def test_bootstrap_checks_loader_before_running_it(self):
        bootstrap = Path(__file__).with_name("bootstrap.py")
        self.assertTrue(bootstrap.exists(), "Business bootstrap has not been implemented")
        command = [sys.executable, str(bootstrap), "install", "--workspace", str(self.workspace),
                   "--source", str(self.source)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.workspace / self.entry["path"]).read_bytes(), self.payload)
        loader = self.source / "distribution/skills_source.py"
        loader.write_text("raise RuntimeError('MUST NOT EXECUTE')")
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("loader checksum", result.stderr)
        self.assertNotIn("MUST NOT EXECUTE", result.stderr)


class CatalogTests(unittest.TestCase):
    def test_every_distributed_resource_is_present_and_matches_its_digest(self):
        root = Path(__file__).resolve().parents[1]
        catalog = json.loads((root / "distribution/catalog.json").read_text())
        sources = set()
        for name, profile in catalog["profiles"].items():
            files = {entry["path"]: entry for entry in profile["files"]}
            self.assertEqual(len(files), len(profile["files"]), name)
            self.assertFalse(set(files).intersection(profile["runtime_files"]), name)
            for entry in files.values():
                path = (root / entry["source"]).resolve()
                self.assertTrue(path.is_relative_to(root))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry["sha256"], entry["source"])
                sources.add(path)
            self.assertEqual({e["path"] for e in profile["entrypoints"]},
                             {path for path in files if path.endswith("/SKILL.md")})
        for path in (root / "business-skills").rglob("*"):
            if path.is_file():
                self.assertIn(path.resolve(), sources, str(path))


if __name__ == "__main__":
    unittest.main()
