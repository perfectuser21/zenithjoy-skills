#!/usr/bin/env python3
"""Guard the four Capability (原 Golden Path) skills' shared contract-layer protocol."""

from __future__ import annotations

import sys
from pathlib import Path


RULES = {
    "capability-proposer/SKILL.md": {
        "proposer:seven_contract_items": [
            "fr_summary",
            "lifelines_and_nfr",
            "yield_order",
            "external_commitment_changes",
            "release_and_blast_radius",
            "success_and_close",
            "budget_guard",
        ],
        "proposer:nfr_classification": [
            "lifeline",
            "best_effort",
            "gp-contract-v<N>.json",
        ],
    },
    "capability-reviewer/SKILL.md": {
        "reviewer:contract_attack": ["GP_CONTRACT", "contract_attack"],
        "reviewer:incident_comparison": [
            "INCIDENT_CONTEXT",
            "incident_comparison",
            "unavailable",
        ],
    },
    "capability-mapper/SKILL.md": {
        "mapper:ledger_reference": [
            "golden_paths.journey_id",
            "journey_step_links",
            "禁止复制合同正文",
        ],
    },
    "capability-controller/SKILL.md": {
        "controller:contract_submission": [
            "gp-contract-v<N>.json",
            "/golden-paths/$GP_ID/contracts",
            "pending_action_id",
        ],
    },
}


def lint(root: Path) -> list[str]:
    failures: list[str] = []
    for relative_path, rule_groups in RULES.items():
        path = root / relative_path
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for failure_code, markers in rule_groups.items():
            missing = [marker for marker in markers if marker not in text]
            if missing:
                failures.append(failure_code)
    return failures


def main() -> int:
    root = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[3]
    )
    failures = lint(root)
    for failure_code in failures:
        relative_path = next(
            path
            for path, groups in RULES.items()
            if failure_code in groups
        )
        text = (
            (root / relative_path).read_text(encoding="utf-8")
            if (root / relative_path).is_file()
            else ""
        )
        missing = [
            marker
            for marker in RULES[relative_path][failure_code]
            if marker not in text
        ]
        print(f"{failure_code}: missing {', '.join(missing)}")
    if failures:
        return 1
    print("✅ Golden Path contract-layer skill guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
