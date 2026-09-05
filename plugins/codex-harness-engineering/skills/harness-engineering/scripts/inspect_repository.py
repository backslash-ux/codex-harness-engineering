#!/usr/bin/env python3
"""Read-only repository harness inspection."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable
from pathlib import Path

import guidance
import harness_core as core

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".nuxt",
    ".playwright-mcp",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "playwright-report",
    "reports",
    "snapshots",
    "test-results",
}
ARTIFACT_PARTS = EXCLUDED_DIRS | {
    "artifacts",
    "cache",
    "caches",
    "recordings",
    "screenshots",
    "videos",
}
TEXT_SUFFIXES = {
    ".md",
    ".mdx",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
    ".sh",
    ".py",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".rb",
    ".go",
    ".rs",
}
LEVELS = {"absent": 0, "documented": 1, "executable": 2, "enforced": 3}
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PATH_REF_RE = re.compile(r"`([^`\n]+)`")
PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}|<TODO>|TBD_PLACEHOLDER", re.IGNORECASE)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_artifact(path: Path, root: Path) -> bool:
    return bool(set(path.relative_to(root).parts) & ARTIFACT_PARTS)


def walk_files(root: Path) -> list[Path]:
    return core.walk_files(root)


def read_text(path: Path, limit: int = 400_000) -> str:
    return core.read_text(path, limit)


def git_status(root: Path) -> str:
    return core.git_status(root)


def add_evidence(
    dimensions: dict[str, dict], dimension: str, level: str, evidence: str
) -> None:
    entry = dimensions[dimension]
    if LEVELS[level] > LEVELS[entry["level"]]:
        entry["level"] = level
    if evidence not in entry["evidence"]:
        entry["evidence"].append(evidence)


def local_links(
    agent_files: Iterable[Path], root: Path
) -> tuple[list[Path], list[str]]:
    resolved, broken, _external = core.local_links(agent_files, root)
    return resolved, broken


def discover_commands(root: Path, files: list[Path]) -> list[dict[str, str]]:
    return core.discover_commands(root, files)  # type: ignore[return-value]


def ci_files(files: list[Path], root: Path) -> list[Path]:
    return core.ci_files(files, root)


def command_is_ci_enforced(command: dict[str, str], ci_blocks: list[str]) -> bool:
    return core.command_is_ci_enforced(command, ci_blocks)


def classify(
    root: Path, files: list[Path], mode: str, scope: str = ".", fallbacks=()
) -> dict:
    names = [
        "Context and repository knowledge",
        "Architecture and enforceable invariants",
        "Verification routing",
        "Runtime and worktree legibility",
        "Review and recovery",
        "Governance and evidence boundaries",
        "Maintenance and entropy control",
    ]
    dimensions = {name: {"level": "absent", "evidence": []} for name in names}
    resolution = guidance.resolve(root, scope, fallbacks)
    agents = [root / path for path in resolution["selected_sources"]]
    linked, broken = local_links(agents, root)
    candidate_docs = list(dict.fromkeys(agents + linked))
    commands = core.discover_commands(root, files, agents)
    workflows = ci_files(files, root)
    ci_blocks = core.executable_ci_blocks(workflows)
    all_guidance = "\n".join(read_text(path) for path in candidate_docs)
    lower_guidance = all_guidance.lower()

    for path in agents:
        add_evidence(
            dimensions,
            names[0],
            "documented",
            f"`{rel(path, root)}` provides repository-local agent guidance",
        )
    for path in linked:
        add_evidence(
            dimensions,
            names[0],
            "documented",
            f"`{rel(path, root)}` is linked from repository guidance",
        )
    context_commands = [
        c
        for c in commands
        if re.search(r"context|doctor|onboard|agent", c["name"], re.IGNORECASE)
    ]
    for command in context_commands:
        level = (
            "enforced" if command_is_ci_enforced(command, ci_blocks) else "executable"
        )
        add_evidence(
            dimensions,
            names[0],
            level,
            f"{command['command']} is {'invoked by CI' if level == 'enforced' else 'runnable'}",
        )

    architecture_docs = [
        p
        for p in candidate_docs
        if p.suffix.lower() in {".md", ".mdx"}
        and (
            re.search(
                r"architect|system[-_ ]?map|boundary|design", p.name, re.IGNORECASE
            )
            or re.search(
                r"(?im)^#{1,3}\s+(architecture|system map|boundaries|dependency direction)",
                read_text(p),
            )
        )
    ]
    for path in dict.fromkeys(architecture_docs):
        add_evidence(
            dimensions,
            names[1],
            "documented",
            f"`{rel(path, root)}` documents architecture or boundaries",
        )
    boundary_commands = [
        c
        for c in commands
        if re.search(
            r"arch|boundary|layer|dependency|structure", c["name"], re.IGNORECASE
        )
    ]
    for command in boundary_commands:
        level = (
            "enforced" if command_is_ci_enforced(command, ci_blocks) else "executable"
        )
        add_evidence(
            dimensions,
            names[1],
            level,
            f"{command['command']} is {'invoked by CI' if level == 'enforced' else 'runnable'}",
        )
    quality_docs = [
        p
        for p in candidate_docs
        if re.search(
            r"quality|test|verification|review|contribut", p.name, re.IGNORECASE
        )
        or re.search(
            r"focused check|canonical command|verification", read_text(p), re.IGNORECASE
        )
    ]
    for path in dict.fromkeys(quality_docs):
        add_evidence(
            dimensions,
            names[2],
            "documented",
            f"`{rel(path, root)}` routes verification or review",
        )
    check_commands = [
        c
        for c in commands
        if re.search(
            r"test|check|lint|type|verify|validate|ci|build|smoke|e2e",
            c["name"],
            re.IGNORECASE,
        )
    ]
    for command in check_commands:
        level = (
            "enforced" if command_is_ci_enforced(command, ci_blocks) else "executable"
        )
        add_evidence(
            dimensions,
            names[2],
            level,
            f"{command['command']} is {'invoked by CI' if level == 'enforced' else 'runnable'}",
        )
    boundary_tests = [
        p
        for p in files
        if re.search(
            r"arch|boundary|layer|dependency|structure", rel(p, root), re.IGNORECASE
        )
        and re.search(r"\.(test|spec)\.", p.name, re.IGNORECASE)
    ]
    for path in boundary_tests:
        # A generic test command does not prove this particular file is reached.
        level = "executable"
        add_evidence(
            dimensions,
            names[1],
            level,
            f"`{rel(path, root)}` is a structural test"
            + (" reached by a CI-invoked test command" if level == "enforced" else ""),
        )

    runtime_docs = [
        p
        for p in candidate_docs
        if re.search(
            r"repeatable startup|worktree setup|isolated worktree|browser journey|"
            r"queryable (?:logs|metrics|traces)|docker compose up|"
            r"(?:npm|pnpm|yarn|bun) (?:run )?(?:dev|start|serve)|"
            r"health(?:check| endpoint)|local startup",
            read_text(p),
            re.IGNORECASE,
        )
    ]
    for path in runtime_docs:
        add_evidence(
            dimensions,
            names[3],
            "documented",
            f"`{rel(path, root)}` describes direct runtime or worktree feedback",
        )
    runtime_files = [
        p
        for p in files
        if not is_artifact(p, root)
        and (
            re.search(
                r"playwright\.config|cypress\.config|docker-compose|compose\.ya?ml",
                p.name,
            )
            or rel(p, root).startswith(("e2e/", "tests/e2e/", "scripts/worktree"))
        )
    ]
    runtime_commands = [
        c
        for c in commands
        if re.search(
            r"dev|start|serve|e2e|browser|smoke|worktree", c["name"], re.IGNORECASE
        )
    ]
    for path in runtime_files:
        add_evidence(
            dimensions,
            names[3],
            "executable",
            f"`{rel(path, root)}` is executable runtime feedback configuration or code",
        )
    for command in runtime_commands:
        level = (
            "enforced" if command_is_ci_enforced(command, ci_blocks) else "executable"
        )
        add_evidence(
            dimensions,
            names[3],
            level,
            f"{command['command']} is {'invoked by CI' if level == 'enforced' else 'runnable'}",
        )

    review_files = [
        p
        for p in files
        if rel(p, root).startswith(".github/")
        and re.search(r"pull_request_template|codeowners", p.name, re.IGNORECASE)
    ]
    plan_files = [
        p
        for p in candidate_docs + files
        if p.suffix.lower() in {".md", ".mdx"}
        and (
            re.search(
                r"plan|rollback|recovery|runbook|deploy|restore|uat",
                rel(p, root),
                re.IGNORECASE,
            )
            or re.search(
                r"(?im)^#{1,3}\s+.*(plan|rollback|recovery|restore|acceptance)",
                read_text(p),
            )
        )
    ]
    if re.search(
        r"self-review|independent review|pull request|rollback|recovery", lower_guidance
    ):
        add_evidence(
            dimensions,
            names[4],
            "documented",
            "Repository guidance defines review or recovery expectations",
        )
    for path in dict.fromkeys(review_files + plan_files):
        add_evidence(
            dimensions,
            names[4],
            "documented",
            f"`{rel(path, root)}` supports review, planning, or recovery",
        )

    if re.search(
        r"human approval|before merge|production|provider|evidence boundar|locally verified",
        lower_guidance,
    ):
        add_evidence(
            dimensions,
            names[5],
            "documented",
            "Repository-local guidance defines approval or evidence boundaries",
        )

    maintenance_docs = [
        p
        for p in candidate_docs
        if re.search(
            r"fresh|garden|entropy|technical debt|broken link|maintenance|"
            r"documentation upkeep|update the readme",
            read_text(p),
            re.IGNORECASE,
        )
    ]
    for path in maintenance_docs:
        add_evidence(
            dimensions,
            names[6],
            "documented",
            f"`{rel(path, root)}` describes repository maintenance",
        )
    maintenance_commands = [
        c
        for c in commands
        if re.search(r"doc|fresh|link|garden|debt|generated", c["name"], re.IGNORECASE)
    ]
    for command in maintenance_commands:
        level = (
            "enforced" if command_is_ci_enforced(command, ci_blocks) else "executable"
        )
        add_evidence(
            dimensions,
            names[6],
            level,
            f"{command['command']} is {'invoked by CI' if level == 'enforced' else 'runnable'}",
        )

    inherited = [
        f"`{path}` supplies inherited guidance; its presence does not raise portable repository maturity."
        for path in resolution["inherited_sources"]
    ]

    garden_findings: list[str] = []
    if mode == "garden":
        garden_findings.extend(f"Broken link: {item}" for item in broken)
        for path in candidate_docs:
            text = read_text(path)
            if PLACEHOLDER_RE.search(text):
                garden_findings.append(
                    f"Unresolved template marker: `{rel(path, root)}`"
                )
            if re.search(r"\b(stale|outdated|deprecated)\b", text, re.IGNORECASE):
                garden_findings.append(
                    f"Explicit stale marker requires review: `{rel(path, root)}`"
                )
        paragraphs: dict[str, str] = {}
        for path in agents:
            for paragraph in re.split(r"\n\s*\n", read_text(path)):
                normalized = re.sub(r"\s+", " ", paragraph.strip().lower())
                if len(normalized) < 120:
                    continue
                if normalized in paragraphs:
                    garden_findings.append(
                        f"Duplicate guidance: `{paragraphs[normalized]}` and `{rel(path, root)}`"
                    )
                else:
                    paragraphs[normalized] = rel(path, root)
        for command in maintenance_commands + boundary_commands:
            if not command_is_ci_enforced(command, ci_blocks):
                garden_findings.append(
                    f"Enforcement gap: {command['command']} is runnable but not invoked by CI"
                )

    priority = [names[0], names[5], names[2], names[4]]
    recommendation = "No change needed"
    for name in priority:
        if dimensions[name]["level"] == "absent":
            suggestions = {
                names[
                    0
                ]: "Add a concise root AGENTS.md that maps canonical commands, constraints, and sources of truth.",
                names[
                    5
                ]: "Document repository-local human gates and separate local, browser, Preview, Production, and provider evidence.",
                names[
                    2
                ]: "Document and expose the closest focused verification command for current change types.",
                names[
                    4
                ]: "Document self-review, risk-based independent review, and recovery expectations.",
            }
            recommendation = suggestions[name]
            break
    if recommendation == "No change needed" and broken:
        recommendation = (
            f"Repair the first broken repository-guidance link: {broken[0]}."
        )
    if (
        recommendation == "No change needed"
        and dimensions[names[1]]["level"] == "absent"
        and core.source_count(root) > 24
    ):
        recommendation = (
            "Document the implemented system boundaries and dependency direction."
        )
    if recommendation == "No change needed" and not re.search(
        r"self-review|self review", lower_guidance
    ):
        recommendation = (
            "Add one concise repository-local review rule requiring self-review for "
            "every change and one bounded independent review for runtime, data, "
            "security, authentication, migration, or release risk."
        )

    return {
        "root": str(root),
        "mode": mode,
        "guidance_resolution": guidance.public(resolution),
        "profile_diagnostics": core.profile_diagnostics(root, resolution["text"]),
        "git_status": git_status(root),
        "repository_local": {
            "agent_guidance": [rel(p, root) for p in agents],
            "linked_sources": [rel(p, root) for p in linked],
            "ci_files": [rel(p, root) for p in workflows],
            "discovered_commands": [c["command"] for c in commands],
            "command_evidence": commands,
        },
        "inherited_global_safeguards": inherited,
        "dimensions": dimensions,
        "remote_state": {
            "branch_protection": "Unverified",
            "merge_approvals": "Unverified",
            "deployment_state": "Unverified",
            "provider_policy": "Unverified",
        },
        "garden_findings": garden_findings,
        "smallest_recommended_improvement": recommendation,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Harness Engineering Assessment",
        "",
        f"- Mode: `{report['mode']}`",
        f"- Repository: `{report['root']}`",
        f"- Git status: `{report['git_status'] or 'clean'}`",
        "",
        "## Repository-local evidence",
        "",
    ]
    local = report["repository_local"]
    for key, values in local.items():
        if key == "command_evidence":
            continue
        label = key.replace("_", " ").title()
        lines.append(
            f"- {label}: " + (", ".join(f"`{v}`" for v in values) or "None found")
        )
    for command in local["command_evidence"]:
        sources = ", ".join(f"{s['source']}:{s['line']}" for s in command["sources"])
        lines.append(f"- Command provenance: `{command['canonical']}` — {sources}")
    lines.extend(["", "## Inherited global safeguards", ""])
    inherited = report["inherited_global_safeguards"]
    lines.extend(f"- {item}" for item in inherited)
    if not inherited:
        lines.append("- None observed")
    lines.extend(["", "## Independent maturity dimensions", ""])
    lines.extend(
        f"- Discovery limitation: {item}"
        for item in report["guidance_resolution"]["limitations"]
    )
    lines.extend(
        f"- Profile diagnostic: {item}" for item in report["profile_diagnostics"]
    )
    for name, entry in report["dimensions"].items():
        lines.append(f"### {name} — {entry['level'].title()}")
        lines.append("")
        if entry["evidence"]:
            lines.extend(f"- {item}" for item in entry["evidence"])
        else:
            lines.append("- No repository-local evidence found.")
        lines.append("")
    lines.extend(["## Remote state", ""])
    lines.append(
        "CI enforcement describes configured failure-propagating invocations, not required merge checks or a live CI result."
    )
    lines.extend(
        f"- {key.replace('_', ' ').title()}: {value}"
        for key, value in report["remote_state"].items()
    )
    if report["mode"] == "garden":
        lines.extend(["", "## Garden findings", ""])
        findings = report["garden_findings"]
        lines.extend(f"- {item}" for item in findings)
        if not findings:
            lines.append("- No mechanical drift found.")
    lines.extend(
        [
            "",
            "## Smallest recommended improvement",
            "",
            report["smallest_recommended_improvement"],
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=("audit", "garden"), default="audit")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    guidance.add_arguments(parser)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"repository does not exist: {root}")
    try:
        report = classify(
            root, walk_files(root), args.mode, args.scope, args.fallback_guidance
        )
    except (ValueError, OSError) as error:
        parser.error(str(error))
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
