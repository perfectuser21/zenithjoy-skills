#!/usr/bin/env python3
"""Restore pinned skill documents/resources; business implementation stays local."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tempfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def within(root, relative):
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts or "\\" in relative or not parts.parts:
        raise ValueError("unsafe path: " + relative)
    path = root.joinpath(*parts.parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("escaping path: " + relative)
    if path.is_symlink():
        raise ValueError("symlink path: " + relative)
    return path


def read_profile(workspace, source):
    lock = json.loads((workspace / ".skills-source.json").read_text())
    if lock.get("version") != 1 or lock.get("repository") != "perfectuser21/zenithjoy-skills":
        raise ValueError("unsupported skills lock")
    actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if actual != lock["revision"]:
        raise ValueError("source revision does not match lock")
    # A matching HEAD is insufficient if a local checkout has edited distribution files.
    raw = subprocess.check_output(["git", "-C", str(source), "show", "HEAD:distribution/catalog.json"])
    catalog_path = source / "distribution/catalog.json"
    if catalog_path.read_bytes() != raw:
        raise ValueError("modified source catalog")
    catalog = json.loads(raw)
    if catalog.get("version") != 1:
        raise ValueError("unsupported catalog version")
    profile = catalog["profiles"][lock["profile"]]
    return lock, profile["files"]


def prepare(workspace, source):
    lock, entries = read_profile(workspace, source)
    seen = set()
    prepared = []
    for entry in entries:
        if entry["path"] in seen:
            raise ValueError("duplicate output path: " + entry["path"])
        seen.add(entry["path"])
        target = within(workspace, entry["path"])
        origin = within(source, entry["source"])
        payload = origin.read_bytes()
        if digest(payload) != entry["sha256"]:
            raise ValueError("source checksum mismatch: " + entry["source"])
        prepared.append((entry, target, payload))
    return lock, prepared


def install(workspace, source):
    workspace, source = Path(workspace).resolve(), Path(source).resolve()
    lock, prepared = prepare(workspace, source)
    state_path = workspace / ".skills-source-state.json"
    previous = json.loads(state_path.read_text()).get("files", {}) if state_path.exists() else {}
    current_paths = {entry["path"] for entry, _, _ in prepared}
    obsolete = []
    for relative, expected in previous.items():
        if relative in current_paths:
            continue
        target = within(workspace, relative)
        if target.exists():
            if digest(target.read_bytes()) != expected:
                raise ValueError("locally modified obsolete generated file: " + relative)
            obsolete.append(target)
    # Complete preflight before writing any target: no partially restored tree on bad data/local edits.
    for entry, target, payload in prepared:
        if target.exists():
            current = digest(target.read_bytes())
            if current not in {entry["sha256"], previous.get(entry["path"])}:
                raise ValueError("locally modified generated file: " + entry["path"])
    for entry, target, payload in prepared:
        target.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp = tempfile.mkstemp(prefix=".skill-", dir=target.parent)
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(payload)
            os.chmod(tmp, 0o755 if entry["mode"] == "100755" else 0o644)
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    for target in obsolete:
        target.unlink()
    state_path.write_text(json.dumps({"revision": lock["revision"], "files": {
        e["path"]: e["sha256"] for e, _, _ in prepared}}, indent=2) + "\n")
    return len(prepared)


def verify(workspace, source):
    _, prepared = prepare(Path(workspace).resolve(), Path(source).resolve())
    for entry, target, payload in prepared:
        if not target.is_file() or target.read_bytes() != payload:
            raise ValueError("missing or modified generated file: " + entry["path"])
    return len(prepared)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["install", "verify"])
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    try:
        count = {"install": install, "verify": verify}[args.command](args.workspace, args.source)
        print(f"{args.command}: {count} skill source files verified")
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
