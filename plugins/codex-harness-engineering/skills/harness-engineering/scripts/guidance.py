"""Explicit, scoped guidance discovery without emulating host configuration."""

from __future__ import annotations

import os
import re
from pathlib import Path

CONCEPTS = {
    "project profile": r"project (?:profile|shape)|primary profile",
    "authority map": r"authority (?:map|by domain)|source(?:s)? of truth",
    "canonical commands": r"canonical commands|development and validation|setup commands",
    "evidence boundaries": r"evidence boundar|locally verified|local proof",
    "human gates": r"human gate|human approval|before merge|production.*approval",
    "done condition": r"done condition|done when|treat work as done",
}


def filenames(fallbacks=()) -> list[str]:
    names = ["AGENTS.override.md", "AGENTS.md"]
    for name in fallbacks:
        if not name or name in {".", ".."} or Path(name).name != name or "\\" in name:
            raise ValueError("fallback guidance must be a filename, not a path")
        if name not in names:
            names.append(name)
    return names


def first_nonempty(directory: Path, names: list[str], boundary: Path | None = None):
    for name in names:
        path = directory / name
        if not path.exists() and not path.is_symlink():
            continue
        if boundary and not path.resolve().is_relative_to(boundary):
            raise ValueError(f"guidance escapes repository: {path}")
        if not path.is_file():
            raise ValueError(f"guidance is not a readable file: {path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        if text.strip():
            return path, text
    return None, ""


def resolve(root: Path, scope: str = ".", fallbacks=()) -> dict:
    root = root.resolve()
    if Path(scope).is_absolute():
        raise ValueError("scope must be a repository-relative directory")
    target = (root / scope).resolve()
    if not target.is_relative_to(root) or not target.is_dir():
        raise ValueError("scope must resolve to a directory inside the repository")
    names = filenames(fallbacks)
    directories = [root]
    for part in target.relative_to(root).parts:
        directories.append(directories[-1] / part)
    selected, texts = [], []
    for directory in directories:
        path, text = first_nonempty(directory, names, root)
        if path:
            selected.append(path.relative_to(root).as_posix())
            texts.append(text)
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    inherited, _ = first_nonempty(home, names[:2])
    return {
        "scope": target.relative_to(root).as_posix(),
        "selected_sources": selected,
        "inherited_sources": [str(inherited)] if inherited else [],
        "fallback_filenames": list(fallbacks),
        "limitations": [
            "Host config files and host-specific context truncation are not emulated; supply custom fallback filenames explicitly.",
            "Inherited guidance does not establish repository-local maturity.",
        ],
        "text": "\n\n".join(texts),
    }


def public(resolution: dict) -> dict:
    return {key: value for key, value in resolution.items() if key != "text"}


def missing_concepts(text: str) -> list[str]:
    return [
        name
        for name, pattern in CONCEPTS.items()
        if not re.search(pattern, text, re.IGNORECASE)
    ]


def declared_profiles(text: str, profiles) -> list[str]:
    pattern = (
        r"primary(?: project)? profile\s*(?::|is)\s*`?("
        + "|".join(map(re.escape, profiles))
        + r")\b"
    )
    return list(
        dict.fromkeys(
            value.lower() for value in re.findall(pattern, text, re.IGNORECASE)
        )
    )


def add_arguments(parser) -> None:
    parser.add_argument(
        "--scope",
        default=".",
        help="Repository-relative directory whose effective guidance is assessed.",
    )
    parser.add_argument(
        "--fallback-guidance", action="append", default=[], metavar="FILENAME"
    )
