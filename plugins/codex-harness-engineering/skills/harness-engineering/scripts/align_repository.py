#!/usr/bin/env python3
"""Assess repository alignment without modifying the repository."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import guidance
import harness_core as core

REQUIRED_CONCEPTS = guidance.CONCEPTS


def first_recommendation(missing: list[str], root: Path) -> str:
    if not (root / "AGENTS.md").exists():
        return "Add a concise root AGENTS.md that maps authorities, commands, constraints, and done condition."
    if missing:
        return f"Add or link one concise repository-local `{missing[0]}` contract."
    return "No change needed"


def assess(root: Path, scope: str = ".", fallbacks=()) -> dict:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"repository does not exist: {root}")
    resolution = guidance.resolve(root, scope, fallbacks)
    agents_text = resolution["text"]
    sources = [root / path for path in resolution["selected_sources"]]
    profile, capabilities = core.detect_profile(root, agents_text)
    declared = guidance.declared_profiles(agents_text, core.PROFILES)
    profile_diagnostics = core.profile_diagnostics(root, agents_text)
    exact_git_root = core.is_git_root(root)
    software = core.is_software_repository(root) or profile is not None
    files = core.walk_files(root) if exact_git_root else []
    commands = core.discover_commands(root, files, sources) if exact_git_root else []
    linked: list[Path] = []
    broken: list[str] = []
    external: list[str] = []
    if sources:
        linked, broken, external = core.local_links(sources, root)

    if not exact_git_root:
        status = "out-of-scope"
        missing = ["exact Git repository root"]
    elif not software and core.source_count(root) == 0 and not sources:
        status = "needs-initialize"
        missing = ["root AGENTS.md", "project profile", "authority map"]
    elif len(declared) > 1:
        status = "needs-input"
        missing = ["unambiguous primary project profile"]
    elif not software:
        status = "out-of-scope"
        missing = ["software repository markers"]
    elif not sources:
        status = "needs-upgrade"
        missing = list(REQUIRED_CONCEPTS)
    else:
        missing = guidance.missing_concepts(agents_text)
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
            "local_guidance": resolution["selected_sources"][0] if sources else None,
            "linked_local_sources": [core.rel(path, root) for path in linked],
            "explicit_external_sources": external,
            "external_source_state": "Unverified" if external else "Not applicable",
        },
        "discovered_commands": [item["canonical"] for item in commands],
        "command_evidence": commands,
        "guidance_resolution": guidance.public(resolution),
        "profile_diagnostics": profile_diagnostics,
        "missing_contracts": missing,
        "broken_links": broken,
        "smallest_recommended_improvement": (
            "Resolve conflicting primary profile declarations."
            if len(declared) > 1
            else f"Add or link one concise repository-local `{missing[0]}` contract."
            if sources and missing
            else f"Repair the first broken repository-guidance link: {broken[0]}."
            if broken
            else "Resolve the unresolved authority or template marker."
            if status == "needs-input"
            else "No change needed"
            if sources
            else first_recommendation(missing, root)
        ),
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
    lines.extend(
        f"- Profile diagnostic: {item}" for item in report["profile_diagnostics"]
    )
    lines.extend(
        f"- Discovery limitation: {item}"
        for item in report["guidance_resolution"]["limitations"]
    )
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
    guidance.add_arguments(parser)
    args = parser.parse_args()
    try:
        report = assess(args.root, args.scope, args.fallback_guidance)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
