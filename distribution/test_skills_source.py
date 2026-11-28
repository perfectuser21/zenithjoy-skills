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
    def test_102_dedup_negotiates_managed_link_without_weakening_identity(self):
        activity, _, _, _ = self.skills()
        path = next(p for p in activity if p.parent.name == "douyin-leadgen-activity-102-dedup")
        text = path.read_text()
        self.assertIn("`capabilities.open_video_resolve_link`", text)
        self.assertIn("`open-video VID EID --resolve-link`", text)
        self.assertIn("`open-video VID EID`", text)
        self.assertIn("`current-video-link`", text)
        self.assertIn("截图不能证明视频身份", text)
        self.assertIn("本VID记 `unknown`，不能认领", text)

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
        # Preserve the optional capability declaration; selected runtime repair
        # authority is checked separately and is never granted by this example.
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

    def test_leadgen_execution_proposals_use_contract_checker_and_shared_deadlines(self):
        activity, workflows, wrappers, _ = self.skills()
        for path in activity + workflows + wrappers:
            with self.subTest(path=path.relative_to(self.root)):
                body = path.read_text()
                # Capability documentation must not become selected retry authority.
                for required in ("checker_repair", "agent_recovery", "独立通用Checker", "执行提案", "deadline_ms", "cleanup_deadline_ms"):
                    self.assertIn(required, body)
                for obsolete in ("raw 回合原冻结上限仍为 1～64", "旧controller可能需要300000ms",
                                 "当前合同Activity预算上限600秒", "当前合同Activity预算上限300秒",
                                 "须包含 `out_delivery_result_verified` 硬探针", "最终仅原独立verify决定继续"):
                    self.assertNotIn(obsolete, body)
                self.assertIn("未知", body)

    def test_parent_methods_keep_activity_and_ordinary_handoff_boundaries(self):
        discovery = (self.base / "commander/skills/wf-douyin_video_discovery/SKILL.md").read_text()
        collect = (self.base / "skills/douyin-leadgen-activity-101-collect-videos/SKILL.md").read_text()
        self.assertNotIn("collect_videos 5.1.1", discovery)
        self.assertNotIn("显式加载冻结的 douyin-leadgen-102", discovery)
        self.assertIn("douyin-leadgen-activity-102-preflight", discovery)
        self.assertIn("douyin-leadgen-activity-102-cleanup", discovery)
        for body in (discovery, collect):
            self.assertNotIn("discovery_metrics_verified", body)
            self.assertIn("PG", body)
            self.assertIn("原件", body)
        for rel in ("skills/douyin-leadgen-101/SKILL.md", "commander/skills/wf-douyin_comment_scoring/SKILL.md"):
            body = (self.base / rel).read_text()
            self.assertIn("ordinary", body)
            self.assertIn("committed_partial_ids", body)
            self.assertIn("formal", body)
            self.assertNotIn("这些行不能据此提前评分", body)

    def test_preflight_start_does_not_require_execution_outputs(self):
        for number in (102, 104):
            body = (self.base / f"skills/douyin-leadgen-activity-{number}-preflight/SKILL.md").read_text()
            with self.subTest(number=number):
                self.assertIn("开始条件只核配置、冻结身份与截止", body)
                self.assertIn("登录态和取得锁的回执是执行后产物", body)
                self.assertIn("不把尚未生成的产物当作开始输入", body)
                self.assertIn("其他 owner", body)

    def test_cleanup_without_run_actions_requires_independent_absence_evidence(self):
        for number in (102, 104):
            body = (self.base / f"skills/douyin-leadgen-activity-{number}-cleanup/SKILL.md").read_text()
            with self.subTest(number=number):
                self.assertIn("不能以尚未生成的锁回执阻止开始收尾核对", body)
                self.assertIn("独立证明本run没有动作、在途请求、锁或租约", body)
                self.assertIn("不操作手机、不关闭应用、不领取或释放资源", body)
                self.assertIn("缺回执不等于没有动作", body)
                self.assertIn("未知保留", body)

    def test_preflight_reuses_frozen_run_and_original_acquire_receipt(self):
        for number in (102, 104):
            body = (self.base / f"skills/douyin-leadgen-activity-{number}-preflight/SKILL.md").read_text()
            with self.subTest(number=number):
                for text in ("宿主已正式分配并持久化的同一 Run", "Checker 独立读回本轮 Brain Task" if number == 102 else "独立 Brain 只读核对", "不另创建运行账本", "同一 run_tag 读回不是重复创建", "保留实际 acquire receipt", "身份冲突则停止"):
                    self.assertIn(text, body)

    def test_shared_preflight_hands_over_report_source_roles(self):
        body = (self.base / "skills/douyin-leadgen-activity-102-preflight/SKILL.md").read_text()
        for role in ("identity.frozen", "identity.company", "handoff.account", "handoff.local_acquire", "handoff.central_acquire"):
            self.assertIn(f"`{role}`", body)
        self.assertIn("执行 Agent 的 Brain 工具用于设备租约", body)
        self.assertIn("Checker 独立读回本轮 Brain Task", body)

    def test_cleanup_output_is_activity_stage_not_future_workflow_terminal(self):
        for number in (102, 104):
            body = (self.base / f"skills/douyin-leadgen-activity-{number}-cleanup/SKILL.md").read_text()
            with self.subTest(number=number):
                for text in ("本 Activity 只交本轮收尾阶段状态", "Workflow 真正终态只能在收尾通过后由宿主生成", "可核验账本和锁/租约原件"):
                    self.assertIn(text, body)
                if number == 104:
                    self.assertIn("原生在途或资源归属未知时，保留对应本人资源", body)
                    self.assertIn("保留原发送依据及必要的订单保护，不补发", body)
                    self.assertIn("设备锁仍按原合同安全归还", body)
                else:
                    self.assertIn("未知仍保留本人资源、未决状态及原发送依据", body)
                self.assertNotIn("最终真实业务状态", body)

    def test_shared_preflight_hands_off_original_tool_and_lock_readback_evidence(self):
        body = (self.base / "skills/douyin-leadgen-activity-102-preflight/SKILL.md").read_text()
        for text in ("保留宿主返回的本地与中央取得回执", "中央租约版本和独立状态读回", "不把它拼接成运行目录下的附件"):
            self.assertIn(text, body)

    def test_shared_cleanup_covers_only_real_resources_and_current_receipts(self):
        body = (self.base / "skills/douyin-leadgen-activity-102-cleanup/SKILL.md").read_text()
        for text in ("不要求另有收尾成功回执", "未发出认领且业务行无本轮租约", "实际传输回执和可读工件", "旧 finalize 自检"):
            self.assertIn(text, body)

    def test_101_delivery_keeps_full_rows_and_per_video_receipt_index(self):
        body = (self.base / "skills/douyin-leadgen-activity-101-collect-videos/SKILL.md").read_text()
        for text in ("逐VID交付", "`comment_count`", "完整 `discovery_metrics`", "inserted", "judgment_status", "include_handoff:true", "include_discovery_protection:true", "只在本run冻结工具明确支持该参数时调用", "不支持则报告缺口", "只读回执固定的 `inserted:false`", "证据索引", "实际扫描范围", "停止原因"):
            self.assertIn(text, body)
        self.assertIn("不能将页面 `comment_total` 填入", body)
        self.assertIn("不重放 discover", body)

    def test_101_final_video_rows_are_inline_with_original_evidence(self):
        body = (self.base / "skills/douyin-leadgen-activity-101-collect-videos/SKILL.md").read_text()
        for text in ("`outputs.Video`", "每行对象自身", "`video_url`", "唯一允许省略", "`discovery_metrics.evidence.xml`", "`proposal.evidence`", "不自行在 `receipts/` 写摘要", "`metrics_evidence_id`", "逐字沿用", "ENOENT", "同一原件", "不重做手机取链或 discover"):
            self.assertIn(text, body)
        for field in ("company_binding", "source_commit", "evidence_id", "comment_tier", "observed_at", "digest"):
            self.assertIn(field, body)

    def test_101_link_evidence_name_matches_metrics_input(self):
        body = (self.base / "skills/douyin-leadgen-activity-101-collect-videos/SKILL.md").read_text()
        for text in (
            'ui-evidence <run>-candidate1-link-t1-share',
            '<run>-candidate1-link-t1',
            'metrics_evidence_id',
            '分享链接',
            '链接已复制',
            'open-video VIDEO_ID EID',
        ):
            self.assertIn(text, body)

    def test_102_agent_qualification_uses_two_scoped_tools_and_original_evidence(self):
        body = (self.base / "skills/douyin-leadgen-activity-102-qualification/SKILL.md").read_text()
        for value in ("qualify-prepare", "qualify-submit", "dossier_sha256", "transcript_quote",
                      "frame_labels", "同一动作、同一次尝试", "原事务读回", "judge-response.json"):
            self.assertIn(value, body)

    def test_103_readback_uses_outbox_ids_and_preserves_single_score(self):
        mark = (self.base / "skills/douyin-leadgen-activity-103-mark-leads/SKILL.md").read_text()
        self.assertIn("bridge_readback", mark)
        self.assertIn("outbox", mark)
        self.assertIn("`ids`", mark)
        self.assertIn("不重新", mark)
        score = (self.base / "skills/douyin-leadgen-activity-103-scoring/SKILL.md").read_text()
        self.assertIn("转写", score)
        self.assertIn("单次评分", score)

    def test_frozen_opt_in_is_bound_to_new_activity_contract_versions(self):
        import re
        activity, _, _, _ = self.skills()
        expected = {'101-collect-videos': '5.6.4', '102-preflight': '2.6.4', '102-dedup': '3.3.5', '102-qualification': '3.6.3', '102-collection': '2.8.7', '102-cleanup': '2.6.4', '103-scoring': '2.10.2', '103-mark-leads': '3.10.2', '104-preflight': '5.3.2', '104-send-dm': '6.1.3', '104-write-back': '4.1.2', '104-cleanup': '3.5.2'}
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

    def test_collection_card_link_crosses_comment_panel_in_the_right_order(self):
        path = self.base / "skills/douyin-leadgen-activity-102-collection/SKILL.md"
        body = path.read_text()
        start = body.index("取链前退出评论面板")
        call = body.index("commenter-profile-card-link VID UID NICKNAME_B64 BODY_SHA EID", start)
        finish = body.index("取链后再次退出评论面板", call)
        after = body.index("current-video-link", finish)
        self.assertIn("back-evidence", body[start:call])
        self.assertIn("back-evidence", body[finish:after])
        self.assertIn("同一视频详情", body[start:call])
        self.assertIn("同一视频详情", body[finish:after])

    def test_discovery_screenshot_path_uses_observation_and_one_tap(self):
        path = self.base / "skills/douyin-leadgen-activity-101-collect-videos/SKILL.md"
        body = path.read_text()
        for field in ("video_page_screenshot", "cards_screenshot", "video_page_xml", "cards_xml"):
            self.assertIn(field, body)
        self.assertIn("若「视频」已选中就直接继续", body)
        self.assertIn("不根据控件树缺失推断还在综合页", body)
        self.assertIn("截图交付路径不调用 `search-video-tab`", body)
        self.assertIn("保留它们的原槽位，不补位或重新编号", body)
        self.assertIn("截图交付路径不调用会自行切换页签的 `search-video-cards`", body)

    def test_method_versions_and_all_workflow_dependency_rows_are_upgraded_together(self):
        import re
        activity, workflows, wrappers, commander = self.skills()
        def version(path):
            return re.search(r"^  ?version: (\S+)$|^version: (\S+)$", path.read_text(), re.M).group(0).split(": ")[1]
        expected_versions = {'douyin-leadgen-activity-101-collect-videos': '0.13.5', 'douyin-leadgen-activity-102-cleanup': '0.11.4', 'douyin-leadgen-activity-102-collection': '0.10.8', 'douyin-leadgen-activity-102-dedup': '0.8.8', 'douyin-leadgen-activity-102-preflight': '0.11.4', 'douyin-leadgen-activity-102-qualification': '0.9.4', 'douyin-leadgen-activity-103-mark-leads': '0.19.2', 'douyin-leadgen-activity-103-scoring': '0.19.2', 'douyin-leadgen-activity-104-cleanup': '0.7.2', 'douyin-leadgen-activity-104-preflight': '1.4.2', 'douyin-leadgen-activity-104-send-dm': '1.4.3', 'douyin-leadgen-activity-104-write-back': '1.2.2', 'douyin-leadgen-101': '0.12.17', 'wf-douyin_video_discovery': '0.12.17', 'douyin-leadgen-102': '0.13.29', 'wf-douyin_video_processing': '0.12.29', 'douyin-leadgen-103': '0.22.2', 'wf-douyin_comment_scoring': '0.20.2', 'douyin-leadgen-104': '0.9.5', 'wf-douyin_lead_outreach': '0.9.5'}
        for path in activity + workflows + wrappers:
            self.assertEqual(version(path), expected_versions[path.parent.name], path.parent.name)
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
                slot = row["activity_ref"].split(".")[-1]
                index_row = f'| `{slot}` | [{row["skill_name"]}](../{row["skill_name"]}/SKILL.md) | `{row["skill_version"]}` |'
                self.assertIn(index_row, workflow.read_text())
                seen.add(method.resolve())
        self.assertEqual(seen, {p.resolve() for p in activity})


if __name__ == "__main__":
    unittest.main()
