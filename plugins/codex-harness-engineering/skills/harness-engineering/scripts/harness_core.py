"""Shared read-only primitives for portable repository harness tooling."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

import command_evidence
import guidance

PROFILES = (
    "web-application",
    "service-or-worker",
    "library-or-cli",
    "native-application",
    "multi-surface-platform",
)
CAPABILITIES = (
    "user-interface",
    "persistent-data",
    "external-provider",
    "background-jobs",
    "deployable-runtime",
    "sensitive-data",
)
AUTHORITY_DOMAINS = (
    "product",
    "delivery",
    "implementation",
    "environment",
    "provider",
)
AUTHORITY_LABELS = {
    "product": "Product intent and acceptance",
    "delivery": "Delivery commitments and work tracking",
    "implementation": "Current implementation",
    "environment": "Environment and release state",
    "provider": "External-provider state",
}

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
SOURCE_SUFFIXES = {
    ".c",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
}
SOFTWARE_MARKERS = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Package.swift",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Gemfile",
    "composer.json",
}
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PATH_REF_RE = re.compile(r"`([^`\n]+)`")
URL_RE = re.compile(r"https?://[^\s<>|]+")
PLACEHOLDER_RE = re.compile(
    r"\{\{[^}]+\}\}|<TODO>|TBD_PLACEHOLDER|\bAUTHORITY_CONFLICT\b",
    re.IGNORECASE,
)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_text(path: Path, limit: int = 400_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def is_artifact(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return bool(set(parts) & ARTIFACT_PARTS)


def walk_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        base = Path(current)
        for name in sorted(names):
            path = base / name
            if path.is_symlink() or is_artifact(path, root):
                continue
            if path.suffix.lower() in TEXT_SUFFIXES or name in {
                "AGENTS.md",
                "Makefile",
                "Justfile",
                "CODEOWNERS",
                "Dockerfile",
            }:
                files.append(path)
    return files


def git_root(root: Path) -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return Path(result.stdout.strip()).resolve()
    except OSError:
        return None


def is_git_root(root: Path) -> bool:
    resolved = root.resolve()
    return git_root(resolved) == resolved


def git_status(root: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--branch"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "Not a Git repository"


def source_count(root: Path) -> int:
    count = 0
    for path in root.rglob("*"):
        if (
            not path.is_file()
            or path.is_symlink()
            or is_artifact(path, root)
            or path.suffix.lower() not in SOURCE_SUFFIXES
        ):
            continue
        count += 1
    return count


def is_software_repository(root: Path) -> bool:
    if any((root / marker).exists() for marker in SOFTWARE_MARKERS):
        return True
    if any(root.glob("*.xcodeproj")) or any(root.glob("*.csproj")):
        return True
    return source_count(root) > 0


def package_manager(root: Path) -> str:
    package = root / "package.json"
    if package.exists():
        try:
            configured = json.loads(read_text(package)).get("packageManager", "")
            if isinstance(configured, str) and configured:
                manager = configured.split("@", 1)[0]
                if manager in {"npm", "pnpm", "yarn", "bun"}:
                    return manager
        except json.JSONDecodeError:
            pass
    lockfiles = (
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("bun.lock", "bun"),
        ("bun.lockb", "bun"),
        ("package-lock.json", "npm"),
        ("npm-shrinkwrap.json", "npm"),
    )
    for filename, manager in lockfiles:
        if (root / filename).exists():
            return manager
    return "npm"


def package_invocation(manager: str, script: str) -> str:
    if manager in {"pnpm", "yarn"}:
        return f"{manager} {script}"
    if manager == "bun":
        return f"bun run {script}"
    return f"npm run {script}"


def discover_commands(
    root: Path,
    files: list[Path] | None = None,
    guidance_sources: list[Path] | None = None,
) -> list[dict[str, object]]:
    files = files if files is not None else walk_files(root)
    commands: list[dict[str, object]] = []
    package = root / "package.json"
    if package.exists():
        try:
            scripts = json.loads(read_text(package)).get("scripts", {})
            manager = package_manager(root)
            for name, value in scripts.items():
                if not isinstance(value, str):
                    continue
                invocation = package_invocation(manager, name)
                commands.append(
                    {
                        "name": name,
                        "command": f"package script `{name}`: {value}",
                        "invocations": [invocation],
                        "source": "package.json",
                        "canonical": invocation,
                    }
                )
        except (json.JSONDecodeError, OSError):
            pass
    for filename in ("Makefile", "Justfile"):
        path = root / filename
        if not path.exists():
            continue
        for match in re.finditer(r"(?m)^([A-Za-z0-9_.-]+)\s*:(?![=])", read_text(path)):
            name = match.group(1)
            invocation = f"make {name}" if filename == "Makefile" else f"just {name}"
            commands.append(
                {
                    "name": name,
                    "command": f"{filename} target `{name}`",
                    "invocations": [invocation],
                    "source": filename,
                    "canonical": invocation,
                }
            )
    for path in files:
        relative = rel(path, root)
        if relative.startswith(("scripts/", "bin/")) and path.suffix.lower() in {
            ".sh",
            ".py",
            ".js",
            ".mjs",
            ".ts",
        }:
            commands.append(
                {
                    "name": path.stem,
                    "command": f"script `{relative}`",
                    "invocations": [relative, f"./{relative}"],
                    "source": relative,
                    "canonical": f"./{relative}",
                }
            )
    docs = [
        path
        for path in files
        if path.name
        in {"AGENTS.md", "AGENTS.override.md", "README.md", "CONTRIBUTING.md"}
    ]
    if guidance_sources is not None:
        linked, _, _ = local_links(guidance_sources, root)
        docs = list(
            dict.fromkeys(
                guidance_sources + [p for p in linked if p.suffix in {".md", ".mdx"}]
            )
        )
    runs = [
        run
        for path in ci_files(files, root)
        for run in command_evidence.workflow_runs(path, root)
    ]
    return command_evidence.enrich(commands, root, docs, runs)


def canonical_command_lines(root: Path) -> list[str]:
    preferred = ("dev", "test", "check", "lint", "typecheck", "build")
    commands = discover_commands(root)
    selected = [item for item in commands if item["name"] in preferred]
    if not selected:
        selected = commands[:6]
    if selected:
        return [
            f"- `{item['canonical']}` — discovered from `{item['source']}`."
            for item in selected
        ]
    return [
        (
            "- No canonical commands are defined yet. Update this section when "
            "the first runnable surface is added."
        )
    ]


def local_links(
    sources: Iterable[Path], root: Path
) -> tuple[list[Path], list[str], list[str]]:
    resolved: list[Path] = []
    broken: list[str] = []
    external: list[str] = []
    root_resolved = root.resolve()
    for source in sources:
        source_resolved = source.resolve()
        text = read_text(source)
        for raw in LINK_RE.findall(text):
            target = raw.split("#", 1)[0].strip().strip("<>")
            if not target or target.startswith(("mailto:", "#")):
                continue
            if "://" in target:
                if target not in external:
                    external.append(target)
                continue
            candidate = (source.parent / target).resolve()
            try:
                candidate.relative_to(root_resolved)
            except ValueError:
                broken.append(f"{rel(source, root)} -> {raw} (outside repository)")
                continue
            if candidate == source_resolved:
                continue
            if candidate.exists():
                if candidate.is_file() and candidate not in resolved:
                    resolved.append(candidate)
            else:
                broken.append(f"{rel(source, root)} -> {raw}")
        for raw in PATH_REF_RE.findall(text):
            target = raw.strip().rstrip(".,;:")
            if (
                " " in target
                or "://" in target
                or not ("/" in target or target.lower().endswith((".md", ".mdx")))
            ):
                continue
            candidate = (source.parent / target).resolve()
            try:
                candidate.relative_to(root_resolved)
            except ValueError:
                continue
            if candidate == source_resolved:
                continue
            if candidate.is_file() and candidate not in resolved:
                resolved.append(candidate)
            elif candidate.is_dir():
                for child in sorted(candidate.glob("*")):
                    if (
                        child.is_file()
                        and child.resolve().is_relative_to(root_resolved)
                        and child.suffix.lower() in {".md", ".mdx"}
                        and child.resolve() != source_resolved
                        and child not in resolved
                    ):
                        resolved.append(child)
        for raw in URL_RE.findall(text):
            target = raw.rstrip(").,;")
            if target not in external:
                external.append(target)
    return resolved, broken, external


def ci_files(files: Iterable[Path], root: Path) -> list[Path]:
    result = []
    for path in files:
        relative = rel(path, root)
        if relative.startswith((".github/workflows/", ".circleci/")) or relative in {
            ".gitlab-ci.yml",
            "azure-pipelines.yml",
            "Jenkinsfile",
        }:
            result.append(path)
    return result


def executable_ci_blocks(paths: Iterable[Path]) -> list[str]:
    blocks: list[str] = []
    run_re = re.compile(r"^(\s*)(?:-\s*)?run\s*:\s*(.*)$")
    for path in paths:
        lines = read_text(path).splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]
            if line.lstrip().startswith("#"):
                index += 1
                continue
            match = run_re.match(line)
            if not match:
                index += 1
                continue
            indent = len(match.group(1))
            value = match.group(2).strip()
            if value not in {"|", ">", "|-", ">-", "|+", ">+"}:
                blocks.append(value)
                index += 1
                continue
            index += 1
            body: list[str] = []
            while index < len(lines):
                child = lines[index]
                if child.strip() and len(child) - len(child.lstrip()) <= indent:
                    break
                if not child.lstrip().startswith("#"):
                    body.append(child.strip())
                index += 1
            blocks.append("\n".join(body))
    return blocks


def command_is_ci_enforced(
    command: dict[str, object], ci_blocks: Iterable[str]
) -> bool:
    # Legacy argument retained; bare command strings cannot establish metadata
    # such as conditions, working directories, or tolerated failures.
    return command_evidence.is_enforced(command)


def detect_profile(
    root: Path, guidance_text: str | None = None
) -> tuple[str | None, list[str]]:
    package: dict = {}
    package_path = root / "package.json"
    if package_path.exists():
        try:
            package = json.loads(read_text(package_path))
        except json.JSONDecodeError:
            package = {}
    dependencies = {
        **package.get("dependencies", {}),
        **package.get("devDependencies", {}),
    }
    dep_names = set(dependencies)
    native = (root / "Package.swift").exists() or any(root.glob("*.xcodeproj"))
    monorepo = (
        (root / "pnpm-workspace.yaml").exists()
        or (root / "turbo.json").exists()
        or (root / "nx.json").exists()
        or ((root / "apps").is_dir() and (root / "packages").is_dir())
    )
    web_frameworks = {
        "next",
        "react",
        "vue",
        "svelte",
        "astro",
        "@remix-run/react",
        "vite",
    }
    service_frameworks = {
        "express",
        "fastify",
        "hono",
        "koa",
        "nestjs",
        "@nestjs/core",
    }
    python_text = " ".join(
        read_text(root / filename)
        for filename in ("pyproject.toml", "requirements.txt")
        if (root / filename).exists()
    ).lower()
    if monorepo:
        profile = "multi-surface-platform"
    elif native:
        profile = "native-application"
    elif dep_names & web_frameworks:
        profile = "web-application"
    elif dep_names & service_frameworks or re.search(
        r"\b(fastapi|flask|django|celery)\b", python_text
    ):
        profile = "service-or-worker"
    elif is_software_repository(root):
        profile = "library-or-cli"
    else:
        profile = None

    capabilities: list[str] = []
    if profile in {"web-application", "native-application", "multi-surface-platform"}:
        capabilities.append("user-interface")
    if any(
        (root / marker).exists()
        for marker in ("prisma", "supabase", "migrations", "alembic", "drizzle")
    ):
        capabilities.append("persistent-data")
    if any(
        (root / marker).exists()
        for marker in ("providers", "connectors", "integrations", "adapters")
    ):
        capabilities.append("external-provider")
    if any(
        (root / marker).exists()
        for marker in ("workers", "worker", "jobs", "queues", "tasks")
    ):
        capabilities.append("background-jobs")
    if any(
        (root / marker).exists()
        for marker in (
            "Dockerfile",
            "docker-compose.yml",
            "compose.yml",
            "compose.yaml",
            "vercel.json",
            "wrangler.toml",
        )
    ):
        capabilities.append("deployable-runtime")
    guidance_text = (
        read_text(root / "AGENTS.md") if guidance_text is None else guidance_text
    )
    guidance_lower = guidance_text.lower()
    if re.search(
        r"\b(pii|personal data|sensitive data|rls|tenant isolation)\b", guidance_lower
    ):
        capabilities.append("sensitive-data")
    declared = guidance.declared_profiles(guidance_text, PROFILES)
    if declared:
        profile = declared[0] if len(declared) == 1 else None
    for capability in CAPABILITIES:
        if re.search(rf"`?{re.escape(capability)}`?", guidance_lower):
            capabilities.append(capability)
    return profile, list(dict.fromkeys(capabilities))


def profile_diagnostics(root: Path, text: str) -> list[str]:
    declared = guidance.declared_profiles(text, PROFILES)
    if len(declared) > 1:
        return ["Conflicting primary profiles: " + ", ".join(declared)]
    inferred, _ = detect_profile(root, "")
    if declared and inferred not in {None, "library-or-cli", declared[0]}:
        return [
            f"Declared profile {declared[0]} differs from concrete detected signals ({inferred}); declaration preserved."
        ]
    return []


def parse_key_value(
    values: Iterable[str], allowed: Iterable[str]
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    allowed_set = set(allowed)
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"expected DOMAIN=REFERENCE: {raw}")
        key, value = raw.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key not in allowed_set:
            raise ValueError(f"unknown authority domain `{key}`")
        if not value or "\n" in value:
            raise ValueError(f"authority reference is empty or invalid for `{key}`")
        result.setdefault(key, []).append(value)
    return result


def markdown_escape(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", " ")


def format_authority_reference(value: str) -> str:
    escaped = markdown_escape(value)
    if value.startswith(("http://", "https://")):
        return f"<{escaped}>"
    if "/" in value or value.lower().endswith(
        (".md", ".mdx", ".yaml", ".yml", ".json")
    ):
        return f"`{escaped}`"
    return escaped


def authority_rows(
    primary: dict[str, list[str]], corroborating: dict[str, list[str]]
) -> str:
    domains = [
        domain
        for domain in AUTHORITY_DOMAINS
        if domain in primary or domain in corroborating or domain == "implementation"
    ]
    rows = [
        "| Domain | Primary authority | Corroborating sources |",
        "| --- | --- | --- |",
    ]
    for domain in domains:
        main = primary.get(domain, [])
        support = corroborating.get(domain, [])
        rows.append(
            "| "
            + markdown_escape(AUTHORITY_LABELS[domain])
            + " | "
            + (
                "; ".join(format_authority_reference(item) for item in main)
                if main
                else "Not established"
            )
            + " | "
            + (
                "; ".join(format_authority_reference(item) for item in support)
                if support
                else "None"
            )
            + " |"
        )
    return "\n".join(rows)
