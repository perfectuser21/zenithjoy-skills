"""按退役清单定位只读档案；缺清单、越界或摘要不符时不接受档案。"""
import hashlib
import json
from pathlib import Path


def resolve_skill_source(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    active = root / relative_path
    if active.is_file():
        return active
    for manifest in sorted((root / "_archive").glob("*/manifest.json"), reverse=True):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        for entry in data.get("entries", []):
            if entry.get("original_path") != relative_path:
                continue
            archived = (root / entry["archive_path"]).resolve()
            if not archived.is_relative_to(root / "_archive") or not archived.is_file():
                continue
            if hashlib.sha256(archived.read_bytes()).hexdigest() == entry.get("sha256"):
                return archived
    return active


if __name__ == "__main__":
    import sys
    print(resolve_skill_source(Path.cwd(), sys.argv[1]))
