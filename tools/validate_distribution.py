#!/usr/bin/env python3
"""Validate the public marketplace, plugin, and skill distribution contracts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
PLUGIN = ROOT / "plugins" / "codex-harness-engineering"
MANIFEST = PLUGIN / ".codex-plugin" / "plugin.json"
SKILL = PLUGIN / "skills" / "harness-engineering"
SKILL_MD = SKILL / "SKILL.md"
OPENAI_YAML = SKILL / "agents" / "openai.yaml"

PLUGIN_NAME = "codex-harness-engineering"
SKILL_NAME = "harness-engineering"
MARKETPLACE_NAME = "backslash-ux"
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+\b"
)
FORBIDDEN_TEXT = (
    "/" + "Users" + "/",
    "gh" + "o_",
    "github" + "_pat_",
    "BEGIN " + "PRIVATE KEY",
)
IGNORED_PARTS = {".git", ".ruff_cache", "__pycache__", "dist"}


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.relative_to(ROOT)} is not valid JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(ROOT)} must contain a JSON object")
        return {}
    return value


def resolve_repo_path(raw: str) -> Path:
    return (ROOT / raw.removeprefix("./")).resolve()


def resolve_plugin_path(raw: str) -> Path:
    return (PLUGIN / raw.removeprefix("./")).resolve()


def validate_marketplace(errors: list[str]) -> None:
    data = load_json(MARKETPLACE, errors)
    if data.get("name") != MARKETPLACE_NAME:
        errors.append(f"marketplace name must be `{MARKETPLACE_NAME}`")

    plugins = data.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        errors.append("marketplace must expose exactly one plugin")
        return

    entry = plugins[0]
    if entry.get("name") != PLUGIN_NAME:
        errors.append(f"marketplace plugin must be `{PLUGIN_NAME}`")
    source = entry.get("source", {})
    if source.get("source") != "local":
        errors.append("marketplace plugin source must be `local`")
    raw_path = source.get("path")
    if not isinstance(raw_path, str) or resolve_repo_path(raw_path) != PLUGIN.resolve():
        errors.append("marketplace source path must resolve to the canonical plugin")
    policy = entry.get("policy", {})
    if policy.get("installation") != "AVAILABLE":
        errors.append("marketplace installation policy must be `AVAILABLE`")
    if policy.get("authentication") != "ON_INSTALL":
        errors.append("marketplace authentication policy must be `ON_INSTALL`")


def validate_manifest(errors: list[str]) -> None:
    data = load_json(MANIFEST, errors)
    if data.get("name") != PLUGIN_NAME:
        errors.append(f"plugin name must be `{PLUGIN_NAME}`")
    version = data.get("version")
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        errors.append("plugin version must use strict semantic versioning")
    if data.get("license") != "MIT":
        errors.append("plugin license must be `MIT`")
    if data.get("repository") != (
        "https://github.com/backslash-ux/codex-harness-engineering"
    ):
        errors.append("plugin repository URL is not canonical")

    author = data.get("author", {})
    if author.get("name") != "Gabriel Reynold":
        errors.append("plugin author name is not canonical")
    if "email" in author:
        errors.append("plugin metadata must not publish an author email")

    skills_path = data.get("skills")
    if (
        not isinstance(skills_path, str)
        or not skills_path.startswith("./")
        or resolve_plugin_path(skills_path) != (PLUGIN / "skills").resolve()
    ):
        errors.append("plugin skills path must resolve to `./skills/`")

    interface = data.get("interface", {})
    required_interface = {
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "capabilities",
        "websiteURL",
        "defaultPrompt",
    }
    missing = sorted(required_interface - set(interface))
    if missing:
        errors.append(f"plugin interface is missing: {', '.join(missing)}")
    prompts = interface.get("defaultPrompt", [])
    if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3:
        errors.append("plugin must provide one to three default prompts")
    elif any(not isinstance(item, str) or len(item) > 128 for item in prompts):
        errors.append(
            "plugin default prompts must be strings of at most 128 characters"
        )


def validate_skill(errors: list[str]) -> None:
    try:
        text = SKILL_MD.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read canonical SKILL.md: {exc}")
        return

    if not text.startswith("---\n"):
        errors.append("SKILL.md must begin with YAML frontmatter")
    frontmatter_end = text.find("\n---\n", 4)
    if frontmatter_end == -1:
        errors.append("SKILL.md frontmatter is not closed")
    else:
        frontmatter = text[4:frontmatter_end]
        if f"name: {SKILL_NAME}" not in frontmatter:
            errors.append(f"SKILL.md name must be `{SKILL_NAME}`")
        if not re.search(r"^description:\s*\S", frontmatter, re.MULTILINE):
            errors.append("SKILL.md must provide a non-empty description")

    if not OPENAI_YAML.is_file():
        errors.append("canonical skill is missing agents/openai.yaml")
    if (SKILL / "README.md").exists():
        errors.append("human-facing README must remain outside the skill bundle")


def validate_public_content(errors: list[str]) -> None:
    for required in (
        ROOT / "README.md",
        ROOT / "LICENSE",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
        ROOT / "AGENTS.md",
    ):
        if not required.is_file():
            errors.append(f"missing public repository file: {required.name}")

    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(ROOT)
        if "tests" not in relative.parts and EMAIL_RE.search(text):
            errors.append(f"{relative} contains a public email address")
        for forbidden in FORBIDDEN_TEXT:
            if forbidden in text:
                errors.append(
                    f"{relative} contains forbidden public text `{forbidden}`"
                )
        if path.suffix in {".json", ".yaml", ".yml"} and "[TODO:" in text:
            errors.append(f"{relative} contains an unresolved placeholder")


def validate() -> list[str]:
    errors: list[str] = []
    validate_marketplace(errors)
    validate_manifest(errors)
    validate_skill(errors)
    validate_public_content(errors)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Distribution validation: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Distribution validation: PASS")
    print(f"Marketplace: {MARKETPLACE_NAME}")
    print(f"Plugin: {PLUGIN_NAME}")
    print(f"Skill: {SKILL_NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
