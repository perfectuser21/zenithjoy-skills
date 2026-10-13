"""档案完整性与越界保护；未登记的文件不能替代现行技能。"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from archived_skill_source import resolve_skill_source

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary).resolve()
    archive = root / "_archive/2026-10-13/example/SKILL.md"
    archive.parent.mkdir(parents=True)
    archive.write_text("历史技能", encoding="utf-8")
    original = "example/SKILL.md"
    manifest = archive.parents[1] / "manifest.json"
    entry = {"original_path": original, "archive_path": str(archive.relative_to(root)),
             "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
    assert resolve_skill_source(root, original) == root / original
    manifest.write_text(json.dumps({"entries": [entry]}))
    assert resolve_skill_source(root, original) == archive
    archive.write_text("被修改的档案", encoding="utf-8")
    assert resolve_skill_source(root, original) == root / original
    entry["archive_path"] = "../../outside/SKILL.md"
    manifest.write_text(json.dumps({"entries": [entry]}))
    assert resolve_skill_source(root, original) == root / original
    active = root / original
    active.parent.mkdir()
    active.write_text("现行技能", encoding="utf-8")
    assert resolve_skill_source(root, original) == active
print("退役档案完整性与路径保护通过")
