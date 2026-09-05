"""Conservative, non-executing command and GitHub Actions evidence extraction.

This recognizes a bounded block-mapping YAML and direct-shell-command subset.
It is deliberately not a YAML evaluator, shell interpreter, or CI policy client.
"""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

CONTROL_WORDS = {
    "if",
    "then",
    "else",
    "elif",
    "fi",
    "for",
    "while",
    "until",
    "do",
    "done",
    "case",
    "esac",
    "exit",
    "return",
    "exec",
    "eval",
    "source",
    ".",
    "set",
    "cd",
    "export",
    "trap",
    "false",
    "true",
    "!",
    "function",
}
KEY = re.compile(r"^(\s*)(-\s+)?([A-Za-z0-9_.-]+):(?:\s+(.*))?$")


def shell_commands(text: str) -> tuple[list[list[str]], bool]:
    """Return direct argv lines; any unsupported shell flow taints the block."""
    text = re.sub(r"\\\r?\n\s*", " ", text)
    commands = []
    supported = True
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            tokens = shlex.split(line, comments=True)
        except ValueError:
            supported = False
            continue
        if not tokens:
            continue
        if (
            re.search(r"[;&|<>`$(){}]", line)
            or tokens[0] in CONTROL_WORDS
            or "=" in tokens[0]
        ):
            supported = False
        commands.append(tokens)
    return commands, supported


def identity(argv: list[str], cwd: str = ".") -> tuple[str, ...]:
    tokens = list(argv)
    if not tokens:
        return ()
    if tokens[0] in {"python", "python3"}:
        tokens[0] = "python"
    if tokens[0] == "npm" and len(tokens) > 1 and tokens[1] == "test":
        tokens.insert(1, "run")
    if tokens[0] in {"pnpm", "yarn"} and len(tokens) > 2 and tokens[1] == "run":
        tokens.pop(1)
    if tokens[0] == "uvx" and len(tokens) > 1 and tokens[1] == "ruff":
        tokens.pop(0)
    return (cwd, *tokens)


def workflow_runs(path: Path, root: Path) -> list[dict]:
    """Read simple GitHub jobs/steps while retaining inherited safety settings."""
    if not path.relative_to(root).as_posix().startswith(".github/workflows/"):
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    nodes: dict[tuple[str, ...], tuple[str, int]] = {}
    stack: list[tuple[int, str]] = []
    item_counts: dict[tuple[str, ...], int] = {}
    unsupported = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if "\t" in line[: len(line) - len(line.lstrip())]:
            unsupported = True
        match = KEY.match(line)
        if not match:
            if re.match(r"^\s*-\s+[\"'A-Za-z0-9]", line) and not any(
                key == "steps" for _, key in stack
            ):
                index += 1
                continue
            # Flow collections, quoted keys, aliases and unknown YAML shapes
            # are outside the supported metadata subset.
            unsupported = True
            index += 1
            continue
        indent = len(match.group(1))
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if match.group(2):
            parent = tuple(key for _, key in stack)
            count = item_counts.get(parent, 0)
            item_counts[parent] = count + 1
            stack.append((indent, f"@{count}"))
            indent += len(match.group(2))
        key, value = match.group(3), (match.group(4) or "").strip()
        route = tuple(key for _, key in stack) + (key,)
        if route in nodes:
            unsupported = True
        line_number = index + 1
        index += 1
        if value in {"|", "|-", "|+", ">", ">-", ">+"}:
            body = []
            while index < len(lines):
                child = lines[index]
                if child.strip() and len(child) - len(child.lstrip()) <= indent:
                    break
                body.append(child.strip())
                index += 1
            nodes[route] = (
                " ".join(body) if value.startswith(">") else "\n".join(body),
                line_number,
            )
        else:
            if value.startswith(("&", "*", "!")) or key == "<<":
                unsupported = True
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            nodes[route] = (value, line_number)
            if not value:
                stack.append((indent, key))

    def get(route: tuple[str, ...], default: str = "") -> str:
        return nodes.get(route, (default, 0))[0]

    runs = []
    for route, (body, number) in nodes.items():
        if (
            len(route) != 5
            or route[0] != "jobs"
            or route[2] != "steps"
            or route[-1] != "run"
        ):
            continue
        job, step = route[:2], route[:4]
        conditions = [get(job + ("if",)), get(step + ("if",))]
        tolerated = [
            get(job + ("continue-on-error",)),
            get(step + ("continue-on-error",)),
        ]
        shell = get(
            step + ("shell",),
            get(
                job + ("defaults", "run", "shell"),
                get(("defaults", "run", "shell"), "bash"),
            ),
        )
        working = get(
            step + ("working-directory",),
            get(
                job + ("defaults", "run", "working-directory"),
                get(("defaults", "run", "working-directory"), "."),
            ),
        )
        try:
            resolved = (root / working).resolve()
            working = resolved.relative_to(root.resolve()).as_posix()
            cwd_supported = resolved.is_dir() and not any(c in working for c in "$*{}")
        except (OSError, ValueError):
            cwd_supported = False
        argv_lines, shell_supported = shell_commands(body)
        shell_ok = shell in {
            "bash",
            "sh",
            "bash --noprofile --norc -eo pipefail {0}",
            "sh -e {0}",
        }
        conditional = any(conditions)
        failure_propagates = (
            not unsupported
            and shell_supported
            and shell_ok
            and cwd_supported
            and not conditional
            and all(value in {"", "false"} for value in tolerated)
            and not get(job + ("uses",))
        )
        runs.append(
            {
                "source": path.relative_to(root).as_posix(),
                "line": number,
                "working_directory": working,
                "text": body,
                "argv": argv_lines,
                "syntax_supported": not unsupported
                and shell_supported
                and shell_ok
                and cwd_supported,
                "conditional": conditional,
                "failure_propagates": failure_propagates,
                "limitations": []
                if failure_propagates
                else [
                    "Conditional, non-blocking, or unsupported workflow/shell metadata; enforcement is unverified."
                ],
            }
        )
    return runs


def documented_commands(path: Path, root: Path) -> list[dict]:
    """Read shell examples only inside explicitly named command sections."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    active_depth = None
    fence = False
    pending = ""
    start = 0
    results = []
    for number, line in enumerate(lines, 1):
        heading = re.match(r"^(#{1,6})\s+(.+)", line)
        if heading and not fence:
            depth, title = len(heading.group(1)), heading.group(2)
            if active_depth is not None and depth <= active_depth:
                active_depth = None
            if re.search(
                r"canonical commands|development and validation|setup commands|develop and validate|^validate$",
                title,
                re.IGNORECASE,
            ):
                active_depth = depth
        if line.strip().startswith("```"):
            fence = not fence
            continue
        if active_depth is None:
            continue
        examples = [line.strip()] if fence else re.findall(r"`([^`]+)`", line)
        for example in examples:
            if not pending:
                start = number
            pending += example
            if pending.endswith("\\"):
                pending = pending[:-1] + " "
                continue
            commands, supported = shell_commands(pending)
            for argv in commands if supported else []:
                if is_check_command(argv, root):
                    results.append(
                        {
                            "text": pending,
                            "argv": argv,
                            "source": path.relative_to(root).as_posix(),
                            "line": start,
                            "working_directory": ".",
                            "kind": "documented",
                        }
                    )
            pending = ""
    return results


def is_check_command(argv: list[str], root: Path) -> bool:
    if not argv:
        return False
    executable = argv[0]
    if executable in {"python", "python3"}:
        return (
            len(argv) > 2
            and argv[1] == "-m"
            and argv[2]
            in {"unittest", "pytest", "py_compile", "compileall", "ruff", "tox"}
        ) or (
            len(argv) > 1
            and argv[1].endswith(".py")
            and (root / argv[1]).resolve().is_relative_to(root.resolve())
            and (root / argv[1]).is_file()
        )
    if executable in {"npm", "pnpm", "yarn", "bun"}:
        tokens = argv[1:]
        if tokens and tokens[0] == "run":
            tokens = tokens[1:]
        try:
            package = json.loads((root / "package.json").read_text())
            return bool(
                tokens and isinstance(package.get("scripts", {}).get(tokens[0]), str)
            )
        except (OSError, ValueError, AttributeError):
            return False
    if executable in {"make", "just"}:
        return (root / ("Makefile" if executable == "make" else "Justfile")).is_file()
    return executable in {"ruff", "pytest"} or argv[:2] == ["uvx", "ruff"]


def enrich(
    commands: list[dict], root: Path, docs: list[Path], runs: list[dict]
) -> list[dict]:
    """Merge existing manifest discovery with documented and CI invocations."""
    found: dict[tuple[str, ...], dict] = {}

    def insert(argv: list[str], canonical: str, name: str, source: dict, legacy=None):
        cwd = source.get("working_directory", ".")
        key = identity(argv, cwd)
        if key not in found:
            found[key] = legacy or {
                "name": name,
                "command": canonical,
                "invocations": [canonical],
                "source": source["source"],
                "canonical": canonical,
            }
            found[key] = dict(
                found[key], argv=argv, working_directory=cwd, sources=[], ci_evidence=[]
            )
        if source not in found[key]["sources"]:
            found[key]["sources"].append(source)

    for command in commands:
        argv = shlex.split(str(command["canonical"]))
        insert(
            argv,
            str(command["canonical"]),
            str(command["name"]),
            {
                "source": command["source"],
                "line": command.get("line", 1),
                "working_directory": ".",
                "kind": "manifest_or_script",
            },
            command,
        )
    for path in docs:
        for source in documented_commands(path, root):
            insert(source["argv"], source["text"], command_name(source["argv"]), source)
    for run in runs:
        for argv in run["argv"]:
            if run["syntax_supported"] and is_check_command(
                argv, root / run["working_directory"]
            ):
                insert(
                    argv,
                    shlex.join(argv),
                    command_name(argv),
                    {
                        "source": run["source"],
                        "line": run["line"],
                        "working_directory": run["working_directory"],
                        "kind": "ci",
                    },
                )
    for command in found.values():
        key = identity(command["argv"], command["working_directory"])
        for run in runs:
            matches = any(
                identity(argv, run["working_directory"]) == key for argv in run["argv"]
            )
            referenced = str(command["canonical"]) in run["text"]
            if matches or referenced:
                command["ci_evidence"].append(
                    {
                        "source": run["source"],
                        "line": run["line"],
                        "working_directory": run["working_directory"],
                        "status": "invoked"
                        if matches and run["syntax_supported"]
                        else "referenced",
                        "failure_propagates": bool(
                            matches and run["failure_propagates"]
                        ),
                        "limitations": run["limitations"],
                    }
                )
        command["required_before_merge"] = "Unverified"
    return list(found.values())


def command_name(argv: list[str]) -> str:
    if argv[0] in {"python", "python3"} and len(argv) > 1:
        if argv[1] == "-m" and len(argv) > 2:
            return argv[2]
        return Path(argv[1]).stem
    if argv[0] == "uvx" and len(argv) > 1:
        return " ".join(argv[1:3])
    return " ".join(argv[:2])


def is_enforced(command: dict) -> bool:
    return any(
        e["status"] == "invoked" and e["failure_propagates"]
        for e in command.get("ci_evidence", [])
    )
