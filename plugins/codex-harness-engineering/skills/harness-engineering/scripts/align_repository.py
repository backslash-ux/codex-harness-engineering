#!/usr/bin/env python3
"""Assess repository alignment without modifying the repository."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import harness_core as core

REQUIRED_CONCEPTS = {
    "project profile": r"project (?:profile|shape)|primary profile",
    "authority map": r"authority (?:map|by domain)|source(?:s)? of truth",
    "canonical commands": r"canonical commands|development and validation|setup commands",
    "evidence boundaries": r"evidence boundar|locally verified|local proof",
    "human gates": r"human gate|human approval|before merge|production.*approval",
    "done condition": r"done condition|done when|treat work as done",
}


def first_recommendation(missing: list[str], root: Path) -> str:
    if not (root / "AGENTS.md").exists():
        return "Add a concise root AGENTS.md that maps authorities, commands, constraints, and done condition."
    if missing:
        return f"Add or link one concise repository-local `{missing[0]}` contract."
    return "No change needed"


def assess(root: Path) -> dict:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"repository does not exist: {root}")
    profile, capabilities = core.detect_profile(root)
    exact_git_root = core.is_git_root(root)
    software = core.is_software_repository(root) or profile is not None
    agents = root / "AGENTS.md"
    agents_text = core.read_text(agents)
    files = core.walk_files(root) if exact_git_root else []
    commands = core.discover_commands(root, files) if exact_git_root else []
    linked: list[Path] = []
    broken: list[str] = []
    external: list[str] = []
    if agents.exists():
        linked, broken, external = core.local_links([agents], root)

    if not exact_git_root:
        status = "out-of-scope"
        missing = ["exact Git repository root"]
    elif not software and core.source_count(root) == 0 and not agents.exists():
        status = "needs-initialize"
        missing = ["root AGENTS.md", "project profile", "authority map"]
    elif not software:
        status = "out-of-scope"
        missing = ["software repository markers"]
    elif not agents.exists():
        status = "needs-upgrade"
        missing = list(REQUIRED_CONCEPTS)
    else:
        lower = agents_text.lower()
        missing = [
            concept
            for concept, pattern in REQUIRED_CONCEPTS.items()
            if not re.search(pattern, lower, re.IGNORECASE)
        ]
        if core.PLACEHOLDER_RE.search(agents_text):
            status = "needs-input"
        elif missing or broken:
            status = "needs-upgrade"
        else:
            status = "aligned"

    return {
        "status": status,
        "advisory": status != "aligned",
        "root": str(root),
        "git_root": exact_git_root,
        "software_repository": software,
        "profile": profile,
        "capabilities": capabilities,
        "authority": {
            "local_guidance": "AGENTS.md" if agents.exists() else None,
            "linked_local_sources": [core.rel(path, root) for path in linked],
            "explicit_external_sources": external,
            "external_source_state": "Unverified" if external else "Not applicable",
        },
        "discovered_commands": [item["canonical"] for item in commands],
        "command_evidence": commands,
        "missing_contracts": missing,
        "broken_links": broken,
        "smallest_recommended_improvement": first_recommendation(missing, root),
        "next_mode": {
            "aligned": None,
            "needs-initialize": "initialize",
            "needs-upgrade": "upgrade",
            "needs-input": "align after resolving project authority",
            "out-of-scope": None,
        }[status],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Repository Alignment",
        "",
        f"- Status: `{report['status']}`",
        f"- Repository: `{report['root']}`",
        f"- Git root: `{'yes' if report['git_root'] else 'no'}`",
        f"- Software repository: `{'yes' if report['software_repository'] else 'no'}`",
        f"- Primary profile: `{report['profile'] or 'not established'}`",
        "- Capability overlays: "
        + (
            ", ".join(f"`{item}`" for item in report["capabilities"])
            if report["capabilities"]
            else "None identified"
        ),
        "",
        "## Authority and routing",
        "",
        "- Root guidance: "
        + (
            f"`{report['authority']['local_guidance']}`"
            if report["authority"]["local_guidance"]
            else "None"
        ),
        "- Linked local sources: "
        + (
            ", ".join(
                f"`{item}`" for item in report["authority"]["linked_local_sources"]
            )
            if report["authority"]["linked_local_sources"]
            else "None"
        ),
        "- Explicit external sources: "
        + (
            ", ".join(report["authority"]["explicit_external_sources"])
            if report["authority"]["explicit_external_sources"]
            else "None"
        ),
        f"- External source state: {report['authority']['external_source_state']}",
        "",
        "## Alignment gaps",
        "",
    ]
    lines.extend(f"- {item}" for item in report["missing_contracts"])
    lines.extend(f"- Broken link: {item}" for item in report["broken_links"])
    if not report["missing_contracts"] and not report["broken_links"]:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Smallest recommended improvement",
            "",
            report["smallest_recommended_improvement"],
            "",
            (
                "Alignment is advisory. Continue the requested work unless an "
                "independent task ambiguity or approval gate requires user input."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    try:
        report = assess(args.root)
    except ValueError as error:
        parser.error(str(error))
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
