#!/usr/bin/env python3
"""Fixture tests for the Capability (原 Golden Path) contract-layer skill guard."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "lint-gp-contract-layer.py"
SPEC = importlib.util.spec_from_file_location("lint_gp_contract_layer", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

EXPECTED = {
    "proposer:seven_contract_items",
    "proposer:nfr_classification",
    "reviewer:contract_attack",
    "reviewer:incident_comparison",
    "mapper:ledger_reference",
    "controller:contract_submission",
}

COMPLETE_FIXTURES = {
    "capability-proposer/SKILL.md": """
fr_summary lifelines_and_nfr yield_order external_commitment_changes
release_and_blast_radius success_and_close budget_guard
lifeline best_effort gp-contract-v<N>.json
""",
    "capability-reviewer/SKILL.md": """
GP_CONTRACT contract_attack
INCIDENT_CONTEXT incident_comparison unavailable
""",
    "capability-mapper/SKILL.md": """
golden_paths.journey_id journey_step_links 禁止复制合同正文
""",
    "capability-controller/SKILL.md": """
gp-contract-v<N>.json /golden-paths/$GP_ID/contracts pending_action_id
""",
}


def write_fixture(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_incomplete_fixtures_fail_every_rule() -> None:
    root = Path(tempfile.mkdtemp(prefix="gp-contract-lint-red-"))
    for relative_path in COMPLETE_FIXTURES:
        write_fixture(root, relative_path, "# intentionally incomplete\n")

    failures = MOD.lint(root)
    assert set(failures) == EXPECTED, failures


def test_complete_fixtures_pass() -> None:
    root = Path(tempfile.mkdtemp(prefix="gp-contract-lint-green-"))
    for relative_path, content in COMPLETE_FIXTURES.items():
        write_fixture(root, relative_path, content)

    assert MOD.lint(root) == []


test_incomplete_fixtures_fail_every_rule()
test_complete_fixtures_pass()
print("✅ GP contract-layer skill guard fixtures passed")
