#!/usr/bin/env python3
"""Validate an adaptive repository harness without modifying it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import guidance
import harness_core as core


def local_links(source: Path, root: Path) -> tuple[list[Path], list[str]]:
    linked, broken, _external = core.local_links([source], root)
    errors = []
    for item in broken:
        prefix = f"{source.relative_to(root)} -> "
        target = item.removeprefix(prefix)
        if target.endswith(" (outside repository)"):
            errors.append(
                f"{source.relative_to(root)} links outside the repository: "
                f"{target.removesuffix(' (outside repository)')}"
            )
        else:
            errors.append(f"{source.relative_to(root)} has a broken link: {target}")
    return linked, errors


def validate(root: Path, scope: str = ".", fallbacks=()) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    inspected: list[str] = []
    resolution = guidance.resolve(root, scope, fallbacks)
    sources = [root / path for path in resolution["selected_sources"]]
    if not sources:
        errors.append("Missing root AGENTS.md or selected override/fallback guidance")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "inspected": inspected,
            "guidance_resolution": guidance.public(resolution),
        }

    queue = list(sources)
    seen: set[Path] = set()
    while queue:
        source = queue.pop(0)
        if source in seen:
            continue
        seen.add(source)
        inspected.append(source.relative_to(root).as_posix())
        text = source.read_text(encoding="utf-8", errors="replace")
        if core.PLACEHOLDER_RE.search(text):
            errors.append(f"Unresolved template marker in {source.relative_to(root)}")
        if source in sources and len(text.splitlines()) > 150:
            warnings.append(
                f"{source.relative_to(root)} exceeds 150 lines; keep it a concise map"
            )
        linked, link_errors = local_links(source, root)
        errors.extend(link_errors)
        # Follow only Markdown sources linked from the current guidance graph.
        queue.extend(
            path
            for path in linked
            if path.suffix.lower() in {".md", ".mdx"} and path not in seen
        )

    for concept in guidance.missing_concepts(resolution["text"]):
        warnings.append(f"Selected guidance does not explicitly map `{concept}`")
    diagnostics = core.profile_diagnostics(root, resolution["text"])
    if len(guidance.declared_profiles(resolution["text"], core.PROFILES)) > 1:
        errors.extend(diagnostics)
    else:
        warnings.extend(diagnostics)

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "inspected": inspected,
        "guidance_resolution": guidance.public(resolution),
    }


def markdown(report: dict) -> str:
    lines = [
        "# Harness Validation",
        "",
        f"- Result: {'PASS' if report['valid'] else 'FAIL'}",
        "- Inspected: " + (", ".join(f"`{p}`" for p in report["inspected"]) or "None"),
        "",
        "## Errors",
        "",
    ]
    lines.extend(f"- {item}" for item in report["errors"])
    if not report["errors"]:
        lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in report["warnings"])
    if not report["warnings"]:
        lines.append("- None")
    lines.extend(
        f"- Discovery limitation: {item}"
        for item in report["guidance_resolution"]["limitations"]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    guidance.add_arguments(parser)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"repository does not exist: {root}")
    try:
        report = validate(root, args.scope, args.fallback_guidance)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown(report), end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
