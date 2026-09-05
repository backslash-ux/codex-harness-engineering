#!/usr/bin/env python3
"""Safely initialize the minimum harness for a genuinely new repository."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import harness_core as core

TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def discover_commands(root: Path) -> list[str]:
    return core.canonical_command_lines(root)


def render(template: Path, values: dict[str, str]) -> str:
    text = template.read_text(encoding="utf-8")
    missing = sorted(set(TOKEN_RE.findall(text)) - set(values))
    if missing:
        raise ValueError(f"missing template values: {', '.join(missing)}")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    if TOKEN_RE.search(text):
        raise ValueError(f"unresolved template marker in {template.name}")
    return text.rstrip() + "\n"


def current_system(root: Path) -> str:
    visible = [
        p.name
        for p in sorted(root.iterdir())
        if p.name not in {".git", "AGENTS.md", "docs"}
    ]
    if not visible:
        return (
            "The repository has no implemented application components yet. "
            "Update this map as the first runnable surface is introduced."
        )
    return (
        "The repository currently exposes these top-level sources or configuration "
        f"entries: {', '.join(f'`{name}`' for name in visible[:12])}. Verify their "
        "runtime roles before expanding this map."
    )


def preflight_outputs(root: Path, outputs: dict[Path, str]) -> None:
    """Check the complete write set, including dangling links, before any write."""
    for path, content in outputs.items():
        relative = path.relative_to(root)
        current = root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError(f"refusing symlink destination or parent: {current}")
            if current != path and current.exists() and not current.is_dir():
                raise ValueError(f"destination parent is not a directory: {current}")
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"destination escapes repository: {path}")
        if path.exists() and (
            not path.is_file()
            or path.read_text(encoding="utf-8", errors="replace") != content
        ):
            raise ValueError(f"refusing to overwrite conflicting file: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--tier", choices=("small", "growing", "large"), required=True)
    parser.add_argument("--confirm-new-repository", action="store_true")
    parser.add_argument("--include-project-brief", action="store_true")
    parser.add_argument("--project-goal")
    parser.add_argument("--primary-users")
    parser.add_argument("--success-condition")
    parser.add_argument("--profile", choices=core.PROFILES)
    parser.add_argument(
        "--capability",
        action="append",
        default=[],
        choices=core.CAPABILITIES,
        help="Repeat for each demonstrated capability overlay.",
    )
    parser.add_argument(
        "--authority",
        action="append",
        default=[],
        metavar="DOMAIN=REFERENCE",
    )
    parser.add_argument(
        "--corroborating",
        action="append",
        default=[],
        metavar="DOMAIN=REFERENCE",
    )
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"repository does not exist: {root}")
    if not args.confirm_new_repository:
        parser.error("initialization requires --confirm-new-repository")
    if not core.is_git_root(root):
        parser.error(
            "initialization requires the exact root of a Git repository; "
            "initialize Git first or use alignment for an established workspace"
        )
    try:
        primary_authorities = core.parse_key_value(
            args.authority, core.AUTHORITY_DOMAINS
        )
        corroborating_authorities = core.parse_key_value(
            args.corroborating, core.AUTHORITY_DOMAINS
        )
    except ValueError as error:
        parser.error(str(error))
    primary_authorities.setdefault(
        "implementation", ["Git checkout at the repository root"]
    )

    brief_values = (args.project_goal, args.primary_users, args.success_condition)
    if args.include_project_brief and not all(brief_values):
        parser.error(
            "--include-project-brief requires --project-goal, --primary-users, "
            "and --success-condition"
        )
    if not args.include_project_brief and any(brief_values):
        parser.error("product brief values require --include-project-brief")

    existing_agents = list(root.rglob("AGENTS.md"))
    intended = [root / "AGENTS.md"]
    if args.tier in {"growing", "large"}:
        intended.extend(
            [root / "docs" / "architecture.md", root / "docs" / "quality.md"]
        )
    if args.tier == "large":
        intended.append(root / "docs" / "PLANS.md")
    if args.include_project_brief:
        intended.append(root / "docs" / "project-brief.md")

    # An identical prior initialization is allowed to reach the idempotency check.
    if existing_agents and root / "AGENTS.md" not in existing_agents:
        parser.error("nested AGENTS.md exists; use upgrade mode instead")

    assets = Path(__file__).resolve().parent.parent / "assets"
    project_name = root.name.replace("-", " ").replace("_", " ").title()
    links = []
    if args.tier in {"growing", "large"}:
        links.extend(
            [
                "- [Architecture](docs/architecture.md) — implemented system and boundaries.",
                "- [Quality and review](docs/quality.md) — focused checks and evidence routing.",
            ]
        )
    if args.tier == "large":
        links.append(
            "- [Execution plans](docs/PLANS.md) — durable complex-work contract."
        )
    if args.include_project_brief:
        links.append(
            "- [Project brief](docs/project-brief.md) — durable product intent."
        )
        primary_authorities.setdefault("product", ["docs/project-brief.md"])
    if not links:
        links.append(
            "- `AGENTS.md` is the current repository map. Add linked sources only when "
            "the repository gains real complexity."
        )

    commands = "\n".join(discover_commands(root))
    detected_profile, detected_capabilities = core.detect_profile(root)
    profile = args.profile or detected_profile
    profile_text = f"`{profile}`" if profile else "Not established"
    capabilities = list(dict.fromkeys(args.capability or detected_capabilities))
    capability_text = (
        ", ".join(f"`{item}`" for item in capabilities)
        if capabilities
        else "None identified"
    )
    outputs: dict[Path, str] = {
        root / "AGENTS.md": render(
            assets / "AGENTS.md.tmpl",
            {
                "PROJECT_NAME": project_name,
                "PROJECT_PROFILE": profile_text,
                "CAPABILITY_PROFILES": capability_text,
                "AUTHORITY_ROWS": core.authority_rows(
                    primary_authorities, corroborating_authorities
                ),
                "CONTEXT_LINKS": "\n".join(links),
                "CANONICAL_COMMANDS": commands,
            },
        )
    }
    if args.tier in {"growing", "large"}:
        outputs[root / "docs" / "architecture.md"] = render(
            assets / "architecture.md.tmpl",
            {"CURRENT_SYSTEM": current_system(root)},
        )
        outputs[root / "docs" / "quality.md"] = render(
            assets / "quality.md.tmpl",
            {"CHECK_ROUTER": commands},
        )
    if args.tier == "large":
        outputs[root / "docs" / "PLANS.md"] = render(assets / "PLANS.md.tmpl", {})
    if args.include_project_brief:
        outputs[root / "docs" / "project-brief.md"] = render(
            assets / "project-brief.md.tmpl",
            {
                "PROJECT_GOAL": args.project_goal,
                "PRIMARY_USERS": args.primary_users,
                "SUCCESS_CONDITION": args.success_condition,
            },
        )

    try:
        preflight_outputs(root, outputs)
    except (ValueError, OSError) as error:
        print(error)
        return 2
    missing = [path for path in outputs if not path.exists()]
    if missing and core.source_count(root) > 24:
        parser.error(
            "repository appears established; use explicitly requested upgrade mode"
        )
    if missing and core.git_status(root).splitlines()[1:]:
        parser.error(
            "new repository has uncommitted changes; use a clean checkout or upgrade mode"
        )

    created = []
    unchanged = []
    try:
        for path, content in outputs.items():
            if path not in missing:
                unchanged.append(path)
                continue
            preflight_outputs(root, {path: content})
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as stream:
                created.append(path)
                stream.write(content)
    except (ValueError, OSError) as error:
        print(f"Initialization stopped: {error}")
        for path in created:
            print(f"Created (may be incomplete): {path.relative_to(root)}")
        print(
            "Existing files were not rolled back; inspect newly created files before retrying."
        )
        return 2

    print(f"Initialized `{args.tier}` harness at {root}")
    for path in created:
        print(f"Created: {path.relative_to(root)}")
    for path in unchanged:
        print(f"Unchanged (already identical): {path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
