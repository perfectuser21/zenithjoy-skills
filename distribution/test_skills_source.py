"""Behavioral checks for pinned, generated business-repository skill files."""
import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import sys
import os


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

    def test_official_child_support_is_pinned_materialized_and_tamper_rejected(self):
        root = Path(__file__).resolve().parents[1]
        self.catalog = json.loads((root / "distribution/catalog.json").read_text())
        entries = self.catalog["profiles"]["zenithjoy"]["files"]
        relative = "services/phone-adb-controller/skills/leadgen-official-child-host.md"
        support = next(e for e in entries if e["path"] == relative)
        for entry in entries:
            target = self.source / entry["source"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root / entry["source"]).read_bytes())
        self.write_catalog()
        self.commit_source()
        lock = json.loads((self.workspace / ".skills-source.json").read_text())
        lock["profile"] = "zenithjoy"
        (self.workspace / ".skills-source.json").write_text(json.dumps(lock))
        self.module.install(self.workspace, self.source)
        self.assertEqual((self.workspace / relative).read_bytes(), (root / support["source"]).read_bytes())
        self.module.verify(self.workspace, self.source)
        (self.source / support["source"]).write_bytes(b"unapproved actor compatibility")
        with self.assertRaisesRegex(ValueError, "source checksum mismatch"):
            self.module.install(self.workspace, self.source)
        self.assertEqual((self.workspace / relative).read_bytes(), (root / support["source"]).read_bytes())

    def test_cecelia_bootstrap_restores_dev_without_reviving_retired_packages(self):
        # Exercise the real catalog, bootstrap and pinned loader in a fresh
        # business workspace. The fixture commit pins candidate bytes without
        # requiring the working source repository to be committed first.
        root = Path(__file__).resolve().parents[1]
        self.catalog = json.loads((root / "distribution/catalog.json").read_text())
        entries = self.catalog["profiles"]["cecelia"]["files"]
        for entry in entries:
            target = self.source / entry["source"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root / entry["source"]).read_bytes())
        self.write_catalog()
        self.commit_source()
        lock = json.loads((self.workspace / ".skills-source.json").read_text())
        lock["profile"] = "cecelia"
        (self.workspace / ".skills-source.json").write_text(json.dumps(lock))
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=True)
        subprocess.run(["git", "-C", str(self.workspace), "config", "core.hooksPath", "/dev/null"], check=True)
        subprocess.run(["git", "-C", str(self.workspace), "add", ".skills-source.json"], check=True)
        subprocess.run(["git", "-C", str(self.workspace), "-c", "user.name=Fixture", "-c",
                        "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
                        "commit", "-qm", "pinned Cecelia source"], check=True)
        bootstrap = Path(__file__).with_name("bootstrap.py")
        for command in ["install", "verify"]:
            result = subprocess.run([sys.executable, str(bootstrap), command,
                                     "--workspace", str(self.workspace), "--source", str(self.source)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.workspace / "packages/engine").exists())
        self.assertFalse((self.workspace / "packages/quality").exists())
        restored = self.workspace / ".claude/skills/dev/SKILL.md"
        self.assertEqual(restored.read_bytes(), (root / "dev/SKILL.md").read_bytes())
        self.assertIn("coding_workflow", restored.read_text())
        self.assertNotIn("packages/engine/", restored.read_text())
        self.assertFalse((restored.parent / "steps").exists())
        read = subprocess.run([sys.executable, str(bootstrap), "cat", "--workspace", str(self.workspace),
                               "--source", str(self.source), "--path", ".claude/skills/dev/SKILL.md"],
                              capture_output=True)
        self.assertEqual(read.returncode, 0, read.stderr)
        self.assertEqual(read.stdout, (root / "dev/SKILL.md").read_bytes())

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

    def test_removed_entrypoints_are_pruned_without_discarding_local_edits(self):
        self.module.install(self.workspace, self.source)
        target = self.workspace / self.entry["path"]
        self.catalog["profiles"]["example"]["files"] = []
        self.write_catalog()
        self.commit_source()
        target.write_text("local edit")
        with self.assertRaisesRegex(ValueError, "modified"):
            self.module.install(self.workspace, self.source)
        self.assertEqual(target.read_text(), "local edit")
        target.write_bytes(self.payload)
        self.assertEqual(self.module.install(self.workspace, self.source), 0)
        self.assertFalse(target.exists())

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

    def test_git_reference_reader_uses_the_reference_lock_not_the_working_copy(self):
        bootstrap = Path(__file__).with_name("bootstrap.py")
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=True)
        (self.workspace / ".git/fixture-hooks").mkdir()
        subprocess.run(["git", "-C", str(self.workspace), "config", "core.hooksPath",
                        str(self.workspace / ".git/fixture-hooks")], check=True)
        subprocess.run(["git", "-C", str(self.workspace), "add", ".skills-source.json"], check=True)
        subprocess.run(["git", "-C", str(self.workspace), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
                        "commit", "-qm", "business lock"], check=True)
        (self.workspace / ".skills-source.json").write_text("broken working copy")
        command = [sys.executable, str(bootstrap), "cat", "--workspace", str(self.workspace),
                   "--source", str(self.source), "--ref", "HEAD", "--path", self.entry["path"]]
        result = subprocess.run(command, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, self.payload)

    def test_cached_checkout_preserves_bytes_with_windows_autocrlf_enabled(self):
        cache = self.workspace / ".skills-source"
        subprocess.run(["git", "init", "-q", str(cache)], check=True)
        subprocess.run(["git", "-C", str(cache), "config", "core.autocrlf", "true"], check=True)
        revision = json.loads((self.workspace / ".skills-source.json").read_text())["revision"]
        subprocess.run(["git", "-C", str(cache), "fetch", "-q", str(self.source), revision], check=True)
        command = [sys.executable, str(Path(__file__).with_name("bootstrap.py")), "install",
                   "--workspace", str(self.workspace)]
        result = subprocess.run(command, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.workspace / self.entry["path"]).read_bytes(), self.payload)

    def test_shell_loader_restores_an_archive_without_business_git_metadata(self):
        scripts = self.workspace / "scripts"
        scripts.mkdir()
        (scripts / "skills-source.py").write_bytes(Path(__file__).with_name("bootstrap.py").read_bytes())
        env = os.environ.copy()
        env["SKILLS_SOURCE_DIR"] = str(self.source)
        result = subprocess.run(["bash", str(Path(__file__).with_name("ensure.sh")), str(self.workspace)],
                                env=env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.workspace / ".git").exists())
        self.assertEqual((self.workspace / self.entry["path"]).read_bytes(), self.payload)

    def test_ssh_identity_is_written_with_lf_for_windows_openssh(self):
        spec = importlib.util.spec_from_file_location("bootstrap", Path(__file__).with_name("bootstrap.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, "write_identity"), "SSH identity bytes need explicit newline handling")
        key = "-----BEGIN TEST KEY-----\r\nfixture\r\n-----END TEST KEY-----\r\n"
        path = module.write_identity(self.root, key)
        self.assertEqual(path.read_bytes(), b"-----BEGIN TEST KEY-----\nfixture\n-----END TEST KEY-----\n")


class PhoneDependencyTests(DistributionTests):
    def configure_runtime_dependency(self):
        self.entry["path"] = ".skills-runtime/android-publish/SKILL.md"
        self.write_catalog()
        self.commit_source()

    def test_phone_routes_have_fixed_runtime_documents(self):
        root = Path(__file__).resolve().parents[1]
        profile = json.loads((root / "distribution/catalog.json").read_text())["profiles"]["zenithjoy"]
        routes = json.loads((root / "business-skills/zenithjoy/.agents/skills/multi-platform-publish/references/catalog.json").read_text())
        required = {"android-publish/SKILL.md"}
        for route in routes["routes"]:
            phone = route["channels"].get("phone", {})
            for key in ("source", "instruction"):
                resource = phone.get(key, {})
                if resource.get("root") == "skills":
                    required.add(resource["path"])
        files = {entry["path"]: entry for entry in profile["files"]}
        for resource in required:
            entry = files.get(".skills-runtime/" + resource)
            self.assertIsNotNone(entry, resource + " is not pinned for runtime")
            self.assertEqual(entry["source"], resource)
            self.assertEqual(hashlib.sha256((root / resource).read_bytes()).hexdigest(), entry["sha256"])
        runtime_sources = {e["source"] for e in profile["files"] if e["path"].startswith(".skills-runtime/")}
        self.assertTrue(required.issubset(runtime_sources))

    def test_all_existing_route_skill_dependencies_are_distributed(self):
        root = Path(__file__).resolve().parents[1]
        profile = json.loads((root / "distribution/catalog.json").read_text())["profiles"]["zenithjoy"]
        routes = json.loads((root / "business-skills/zenithjoy/.agents/skills/multi-platform-publish/references/catalog.json").read_text())
        required = {"android-publish/SKILL.md"}
        for route in routes["routes"]:
            for channel in route["channels"].values():
                for key in ("source", "instruction"):
                    resource = channel.get(key, {})
                    if resource.get("root") == "skills":
                        required.add(resource["path"])
        files = {entry["path"]: entry for entry in profile["files"]}
        missing = set()
        for resource in required:
            if not (root / resource).is_file():
                missing.add(resource)
                continue
            self.assertIn(".skills-runtime/" + resource, files, resource)
        self.assertEqual(missing, {"kuaishou-publisher/SKILL.md", "toutiao-publisher/SKILL.md",
                                   "xiaohongshu-publisher/SKILL.md"},
                         "Existing catalog contains archived sources; do not restore them silently")

    def test_runtime_missing_or_modified_dependency_is_rejected(self):
        self.configure_runtime_dependency()
        self.module.install(self.workspace, self.source)
        target = self.workspace / self.entry["path"]
        target.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.module.verify(self.workspace, self.source)
        self.module.install(self.workspace, self.source)
        target.write_text("unverified runtime edits")
        with self.assertRaisesRegex(ValueError, "modified"):
            self.module.verify(self.workspace, self.source)
        with self.assertRaisesRegex(ValueError, "modified"):
            self.module.install(self.workspace, self.source)

    def test_two_release_workspaces_keep_their_own_runtime_bytes(self):
        self.configure_runtime_dependency()
        self.module.install(self.workspace, self.source)
        old_source = self.root / "old-source"
        subprocess.run(["git", "clone", "-q", str(self.source), str(old_source)], check=True)
        old_workspace = self.root / "old-workspace"
        old_workspace.mkdir()
        (old_workspace / ".skills-source.json").write_bytes((self.workspace / ".skills-source.json").read_bytes())
        self.module.install(old_workspace, old_source)
        (self.source / "example.md").write_bytes(b"# Improved skill\n")
        self.entry["sha256"] = hashlib.sha256(b"# Improved skill\n").hexdigest()
        self.write_catalog()
        self.commit_source()
        self.module.install(self.workspace, self.source)
        self.assertEqual((old_workspace / self.entry["path"]).read_bytes(), self.payload)
        self.assertEqual((self.workspace / self.entry["path"]).read_bytes(), b"# Improved skill\n")
        self.module.verify(old_workspace, old_source)
        self.module.verify(self.workspace, self.source)


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
            for entry in profile.get("retired_files", []):
                self.assertEqual(entry["status"], "retired-business-distribution")
                self.assertNotIn(entry["path"], files, "Retired outputs must not be restored")
                path = (root / entry["source"]).resolve()
                self.assertTrue(path.is_relative_to(root))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry["sha256"], entry["source"])
                sources.add(path)
        for path in (root / "business-skills").rglob("*"):
            if path.is_file():
                self.assertIn(path.resolve(), sources, str(path))



class CommanderRecoveryContractTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]
    base = root / "business-skills/zenithjoy/services/phone-adb-controller"

    def skills(self):
        activity = sorted((self.base / "skills").glob("douyin-leadgen-activity-*/SKILL.md"))
        workflows = [self.base / f"skills/douyin-leadgen-{n}/SKILL.md" for n in range(101, 105)]
        wrappers = [p for p in (self.base / "commander/skills").glob("wf-douyin_*/SKILL.md")
                    if p.parent.name != "wf-douyin_video_publish"]
        commander = self.base / "commander/skills/workflow-commander/SKILL.md"
        self.assertEqual((len(activity), len(workflows), len(wrappers)), (12, 4, 4))
        return activity, workflows, wrappers, commander

    def test_recovery_policy_is_explicit_and_identical_across_frozen_methods(self):
        # Parse the normative structured example, rather than treating a prose
        # mention or a dependency's policy as authorization for this method.
        import re
        activity, workflows, wrappers, commander = self.skills()
        for path in activity + workflows + wrappers + [commander]:
            with self.subTest(path=path.relative_to(self.root)):
                text = path.read_text()
                blocks = re.findall(r'<!-- agent-recovery-policy -->\n```json\n(.*?)\n```', text, re.S)
                self.assertEqual(len(blocks), 1, "Missing unambiguous frozen opt-in policy")
                policy = json.loads(blocks[0])
                self.assertEqual(policy, {"agent_recovery": {"max_additional_turns": 1}})
                self.assertIs(type(policy["agent_recovery"]["max_additional_turns"]), int)

    def test_frozen_opt_in_is_bound_to_new_activity_contract_versions(self):
        import re
        activity, _, _, _ = self.skills()
        expected = {"101-collect-videos": "5.1.1", "102-preflight": "2.3.0",
                    "102-dedup": "3.2.1", "102-qualification": "3.4.2",
                    "102-collection": "2.7.2", "102-cleanup": "2.3.0",
                    "103-scoring": "2.8.0", "103-mark-leads": "3.9.0",
                    "104-preflight": "5.0.1", "104-send-dm": "6.0.2",
                    "104-write-back": "4.0.1", "104-cleanup": "3.2.1"}
        for path in activity:
            with self.subTest(method=path.parent.name):
                actual = re.search(r"^  activity_version: (\S+)$", path.read_text(), re.M)[1]
                self.assertEqual(actual, expected[path.parent.name.removeprefix("douyin-leadgen-activity-")])

    def test_104_send_method_requires_frozen_exact_order_scope(self):
        path = self.base / "skills/douyin-leadgen-activity-104-send-dm/SKILL.md"
        body = path.read_text()
        for required in ("飞书 record_id", "comment_id", "公司", "来源", "不领取旁单", "未匹配则拒发"):
            self.assertIn(required, body)
        for required in ("company_queue", "exact", "LEADGEN_OUTREACH_MODE", "LEADGEN_OUTREACH_SCOPE_FILE"):
            self.assertIn(required, body)

    def test_method_versions_and_all_workflow_dependency_rows_are_upgraded_together(self):
        import re
        activity, workflows, wrappers, commander = self.skills()
        def version(path):
            return re.search(r"^  ?version: (\S+)$|^version: (\S+)$", path.read_text(), re.M).group(0).split(": ")[1]
        upgraded_methods = {'douyin-leadgen-activity-102-preflight': '0.8.0', 'douyin-leadgen-activity-101-collect-videos': '0.8.0', 'douyin-leadgen-activity-102-dedup': '0.7.0', 'douyin-leadgen-activity-102-qualification': '0.7.0', 'douyin-leadgen-activity-102-collection': '0.8.0', 'douyin-leadgen-activity-102-cleanup': '0.8.0', 'douyin-leadgen-activity-103-scoring': '0.16.0', 'douyin-leadgen-activity-103-mark-leads': '0.16.0'}
        for path in activity:
            expected = "0.11.1" if path.parent.name in {"douyin-leadgen-activity-103-scoring", "douyin-leadgen-activity-103-mark-leads"} else "0.5.1" if path.parent.name == "douyin-leadgen-activity-102-collection" else "0.5.1" if path.parent.name == "douyin-leadgen-activity-101-collect-videos" else "1.2.2" if path.parent.name == "douyin-leadgen-activity-104-send-dm" else "1.0.1" if path.parent.name in {"douyin-leadgen-activity-104-preflight", "douyin-leadgen-activity-104-write-back"} else "0.4.1" if path.parent.name.startswith("douyin-leadgen-activity-102-") else "0.3.1"
            expected = upgraded_methods.get(path.parent.name, expected)
            self.assertEqual(version(path), expected, path.parent.name)
        for path in workflows + wrappers:
            expected = "0.15.0" if path.parent.name in {"douyin-leadgen-103", "wf-douyin_comment_scoring"} else "0.7.2" if path.parent.name in {"douyin-leadgen-104", "wf-douyin_lead_outreach"} else "0.9.0" if path.parent.name in {"douyin-leadgen-101", "wf-douyin_video_discovery"} else "0.9.0" if path.parent.name in {"douyin-leadgen-102", "wf-douyin_video_processing"} else "0.4.1"
            expected = {"douyin-leadgen-101": "0.10.0", "douyin-leadgen-102": "0.10.0", "douyin-leadgen-103": "0.18.0", "wf-douyin_video_processing": "0.10.0", "wf-douyin_video_discovery": "0.10.0", "wf-douyin_comment_scoring": "0.16.0"}.get(path.parent.name, expected)
            self.assertEqual(version(path), expected, path.parent.name)
        self.assertEqual(version(commander), "2.2.0")
        versions = {path.parent.name: version(path) for path in activity + workflows + wrappers + [commander]}
        for path in activity + workflows + wrappers + [commander]:
            for name, mentioned in re.findall(r"(douyin-leadgen-[a-z0-9-]+)@(\d+\.\d+\.\d+)", path.read_text()):
                self.assertEqual(mentioned, versions[name], f"Stale prose dependency in {path}")
        seen = set()
        for workflow in workflows:
            manifest = json.loads((workflow.parent / "references/activity-methods.json").read_text())
            for row in manifest["activities"]:
                method = self.base / Path(row["skill_path"]).relative_to("services/phone-adb-controller")
                self.assertEqual(row["skill_version"], version(method))
                seen.add(method.resolve())
        self.assertEqual(seen, {p.resolve() for p in activity})


if __name__ == "__main__":
    unittest.main()
