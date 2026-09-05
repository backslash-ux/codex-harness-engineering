"""Run a bounded, resumable baseline/candidate skill comparison outside Git."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "plugins/codex-harness-engineering/skills/harness-engineering"
CONTRACT = """# Fixture Agent Map

Primary profile: `library-or-cli`.

## Authority map
Product acceptance: this task. Implementation: the Git checkout.

## Canonical commands
```bash
python3 -m unittest discover -s tests -v
```

## Evidence boundaries
Local proof does not establish CI, deployment, or provider proof.

## Human gates
Require human approval before merge or external changes.

## Done condition
Complete the requested scope, run its focused check, and self-review.
Do not add speculative tooling. Independent review is required for security risk.
"""


def command(args, cwd=ROOT, timeout=30):
    return subprocess.run(
        args, cwd=cwd, text=True, capture_output=True, check=True, timeout=timeout
    )


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def host_snapshot():
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    paths = [home / name for name in ("config.toml", "AGENTS.md", "AGENTS.override.md")]
    return {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        if path.exists()
        else None
        for path in paths
    }


def configured_mcp():
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    config = home / "config.toml"
    text = config.read_text() if config.exists() else ""
    return [
        quoted or bare
        for quoted, bare in re.findall(
            r'^\[mcp_servers\.(?:"([^\"]+)"|([A-Za-z0-9_-]+))\]\s*$', text, re.MULTILINE
        )
    ]


def source_copy(ref, destination):
    sha = command(
        ["git", "rev-parse", "--verify", "--end-of-options", ref + "^{commit}"]
    ).stdout.strip()
    names = command(
        ["git", "ls-tree", "-r", "--name-only", sha, "--", PREFIX]
    ).stdout.splitlines()
    for name in names:
        relative = Path(name).relative_to(PREFIX)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(
            subprocess.check_output(["git", "show", f"{sha}:{name}"], cwd=ROOT)
        )
        target.chmod(0o444)
    for directory in sorted(
        (p for p in destination.rglob("*") if p.is_dir()), reverse=True
    ):
        directory.chmod(0o555)
    destination.chmod(0o555)
    return sha


def fixture(root, skill, case):
    root.mkdir(parents=True)
    link = root / ".agents/skills/harness-engineering"
    link.parent.mkdir(parents=True)
    link.symlink_to(skill, target_is_directory=True)
    if case != "initialize":
        (root / "main.py").write_text("VALUE = 1\n")
        (root / "tests").mkdir()
        (root / "tests/test_smoke.py").write_text(
            "import unittest\nfrom main import VALUE\n\nclass Smoke(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(VALUE, 1)\n"
        )
    if case not in {"initialize", "established"}:
        (root / "AGENTS.md").write_text(CONTRACT)
    if case == "established":
        for index in range(25):
            (root / f"module_{index}.py").write_text("VALUE = 1\n")
    if case in {"misleading-ci", "audit"}:
        (root / "package.json").write_text(
            json.dumps({"scripts": {"test": "node --test"}})
        )
        workflow = root / ".github/workflows/ci.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text(
            'name: CI\non: [push, pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo "npm run test"\n'
        )
    if case in {"garden", "audit"}:
        with (root / "AGENTS.md").open("a") as stream:
            stream.write("\nSee [current system](docs/missing.md).\n")
    if case == "override":
        (root / "AGENTS.md").write_text(
            "AUTHORITY_CONFLICT\nPrimary profile: `web-application`.\n"
        )
        (root / "AGENTS.override.md").write_text(CONTRACT)
    if case == "conflict":
        with (root / "AGENTS.md").open("a") as stream:
            stream.write("\nPrimary profile: `service-or-worker`.\n")
    if case == "activate":
        target = root / "user-guidance/AGENTS.md"
        target.parent.mkdir()
        target.write_text("# Existing preferences\n\nKeep this exact sentence.\n")
        target.chmod(0o600)
    command(["git", "init", "-q"], root)
    command(["git", "add", "."], root)
    command(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture",
            "commit",
            "-qm",
            "fixture",
        ],
        root,
    )


def snapshot(root):
    result = {}
    for current, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in names + [d for d in dirs if (Path(current) / d).is_symlink()]:
            path = Path(current) / name
            data = (
                os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
            )
            result[path.relative_to(root).as_posix()] = {
                "sha256": hashlib.sha256(data).hexdigest(),
                "mode": stat.S_IMODE(path.lstat().st_mode),
                "symlink": path.is_symlink(),
            }
    return result


def overrides(manifest):
    disabled = ",".join(
        "{path=" + json.dumps(p) + ",enabled=false}"
        for p in manifest["disabled_skills"]
    )
    values = [
        "-c",
        "skills.config=[" + disabled + "]",
        "-c",
        "model_reasoning_effort=" + json.dumps(manifest["effort"]),
        "-c",
        "sandbox_workspace_write.network_access=false",
        "-c",
        'web_search="disabled"',
        "-c",
        'shell_environment_policy.set.PYTHONDONTWRITEBYTECODE="1"',
    ]
    for name in manifest.get("disabled_mcp", []):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError("evaluation requires simple MCP configuration identifiers")
        values.extend(["-c", "mcp_servers." + name + ".enabled=false"])
    return values


def preflight(root, skill, manifest):
    result = command(
        [
            manifest.get("codex_binary", "codex"),
            "-C",
            str(root),
            "-m",
            manifest["model"],
            *overrides(manifest),
            "-c",
            "projects={" + json.dumps(str(root)) + '={trust_level="trusted"}}',
            "debug",
            "prompt-input",
            "Skill catalog preflight.",
        ],
        root,
        timeout=60,
    )
    text = "\n".join(strings(json.loads(result.stdout)))
    paths = re.findall(
        r"^- [^\n]*harness-engineering[^\n]*\(file: ([^\n]+SKILL\.md)\)",
        text,
        re.MULTILINE,
    )
    aliases = dict(re.findall(r"^- `(r\d+)` = `([^`]+)`", text, re.MULTILINE))
    expanded = []
    for path in paths:
        first, separator, rest = path.partition("/")
        expanded.append(
            Path(aliases[first]) / rest
            if separator and first in aliases
            else Path(path)
        )
    resolved = {str(path.resolve()) for path in expanded}
    if resolved != {str((skill / "SKILL.md").resolve())} or len(paths) != 1:
        raise ValueError(
            f"catalog preflight must show exactly the selected skill; observed {len(paths)} entries"
        )
    return {
        "catalog_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "harness_entries": len(paths),
    }


def report_objects(events):
    for event in events:
        item = event.get("item", {})
        if item.get("type") != "command_execution":
            continue
        text = item.get("aggregated_output", "")
        for start in (m.start() for m in re.finditer(r"\{", text)):
            try:
                value, _ = json.JSONDecoder().raw_decode(text[start:])
            except ValueError:
                continue
            if isinstance(value, dict) and ("dimensions" in value or "status" in value):
                yield value


def grade(case, root, before, after, events, final, returncode):
    changed = sorted(
        key for key in set(before) | set(after) if before.get(key) != after.get(key)
    )
    commands = [
        event.get("item", {}).get("command", "")
        for event in events
        if event.get("item", {}).get("type") == "command_execution"
    ]
    executed = "\n".join(commands)
    checks = {
        "completed": returncode == 0,
        "changes_in_scope": set(changed).issubset(case["changes"]),
    }
    if case["commands"]:
        checks["expected_command"] = any(
            name in executed and "python" in executed for name in case["commands"]
        )
    else:
        checks["no_harness_invocation"] = not any(
            name in executed
            for name in (
                "harness-engineering/SKILL.md",
                "align_repository.py",
                "inspect_repository.py",
                "initialize_harness.py",
            )
        )
    reports = list(report_objects(events))
    identifier = case["id"]
    if identifier == "routine":
        checks["requested_edit"] = "VALUE = 2" in (root / "main.py").read_text()
        checks["focused_test_passes"] = (
            subprocess.run(
                ["python3", "-B", "-m", "unittest", "discover", "-s", "tests"],
                cwd=root,
                capture_output=True,
                check=False,
            ).returncode
            == 0
        )
    if identifier == "translation":
        checks["correct_translation"] = "selamat pagi" in final.lower()
    if identifier == "initialize":
        target = root / "AGENTS.md"
        checks["contract_created"] = (
            target.is_file() and "library-or-cli" in target.read_text()
        )
    if identifier == "override":
        checks["effective_guidance"] = any(
            r.get("status") == "aligned" and r.get("profile") == "library-or-cli"
            for r in reports
        ) or (
            "library-or-cli" in final
            and "AGENTS.override.md" in final
            and "aligned" in final.lower()
        )
    if identifier == "conflict":
        checks["conflict_reported"] = (
            any(r.get("status") == "needs-input" for r in reports)
            or "conflict" in final.lower()
        )
    if identifier == "misleading-ci":
        relevant = [r for r in reports if "dimensions" in r]
        checks["no_false_ci_enforcement"] = bool(relevant) and all(
            r["dimensions"]["Verification routing"]["level"] != "enforced"
            for r in relevant
        )
        if not relevant:
            checks["no_false_ci_enforcement"] = bool(
                re.search(
                    r"not (?:ci[- ]?)?enforced|not executed|only (?:prints|echoes)|does not (?:execute|run)",
                    final,
                    re.IGNORECASE,
                )
            )
    if identifier == "audit":
        checks["seven_dimensions"] = any(
            len(r.get("dimensions", {})) == 7 for r in reports
        ) or all(
            word in final.lower()
            for word in (
                "context",
                "architecture",
                "verification",
                "runtime",
                "review",
                "governance",
                "maintenance",
            )
        )
    if identifier == "garden":
        checks["broken_link_reported"] = "missing.md" in final or any(
            "missing.md" in str(r.get("garden_findings", [])) for r in reports
        )
    if identifier == "activate":
        target = root / "user-guidance/AGENTS.md"
        text = target.read_text()
        checks["preserved_existing"] = "Keep this exact sentence." in text
        checks["managed_block_once"] = (
            text.count("harness-engineering:global-contract:start") == 1
        )
        checks["preserved_permissions"] = stat.S_IMODE(target.stat().st_mode) == 0o600
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "changed_files": changed,
        "git_status": command(["git", "status", "--porcelain"], root).stdout,
    }


def trial(output, manifest, case, variant, attempt):
    directory = output / "trials" / f"{case['id']}-{variant}-{attempt}"
    directory.mkdir(parents=True)
    write_json(
        directory / "result.json",
        {
            "case": case["id"],
            "variant": variant,
            "attempt": attempt,
            "passed": False,
            "infrastructure_error": "incomplete trial",
        },
    )
    root, skill = directory / "fixture", output / "sources" / variant
    fixture(root, skill, case["id"])
    before = snapshot(root)
    write_json(directory / "before.json", before)
    try:
        write_json(directory / "preflight.json", preflight(root, skill, manifest))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        result = {
            "case": case["id"],
            "variant": variant,
            "attempt": attempt,
            "passed": False,
            "infrastructure_error": str(error),
        }
        write_json(directory / "result.json", result)
        return result
    argv = [
        manifest.get("codex_binary", "codex"),
        "-a",
        "never",
        "-m",
        manifest["model"],
        *overrides(manifest),
        "-c",
        "projects={" + json.dumps(str(root)) + '={trust_level="trusted"}}',
        "exec",
        "--ephemeral",
        "--sandbox",
        "workspace-write",
        "--json",
        "-C",
        str(root),
        "-o",
        str(directory / "final.txt"),
        case["prompt"],
    ]
    started = time.monotonic()
    with (
        (directory / "events.jsonl").open("w") as stdout,
        (directory / "stderr.txt").open("w") as stderr,
    ):
        process = subprocess.Popen(
            argv,
            cwd=root,
            stdout=stdout,
            stderr=stderr,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            code = 124
    events = []
    for line in (directory / "events.jsonl").read_text().splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    final_path = directory / "final.txt"
    final = final_path.read_text() if final_path.exists() else ""
    after = snapshot(root)
    result = dict(
        grade(case, root, before, after, events, final, code),
        case=case["id"],
        variant=variant,
        attempt=attempt,
        returncode=code,
        seconds=round(time.monotonic() - started, 2),
        usage=[e.get("usage") for e in events if e.get("type") == "turn.completed"],
    )
    write_json(directory / "after.json", after)
    write_json(directory / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-ref", default="5fc35fe")
    parser.add_argument("--candidate-ref", default="HEAD")
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", required=True)
    parser.add_argument(
        "--codex-bin",
        default="codex",
        help="CLI executable to freeze for both variants.",
    )
    parser.add_argument("--disable-skill", action="append", default=[])
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--retry", metavar="CASE:VARIANT")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.is_relative_to(ROOT):
        parser.error("evaluation output must be outside the repository")
    if (
        output.exists()
        and any(output.iterdir())
        and not (output / "manifest.json").is_file()
    ):
        parser.error("new evaluation output must be empty")
    output.mkdir(parents=True, exist_ok=True)
    scenarios = json.loads((ROOT / "evals/scenarios.json").read_text())
    path = output / "manifest.json"
    if path.exists():
        manifest = json.loads(path.read_text())
        if (
            manifest["model"] != args.model
            or manifest["effort"] != args.effort
            or manifest["cli"]
            != command(
                [manifest.get("codex_binary", "codex"), "--version"]
            ).stdout.strip()
        ):
            parser.error("resumed evaluation must retain model, effort and CLI")
        if (
            manifest["host_snapshot"] != host_snapshot()
            or manifest["scenarios_sha256"]
            != hashlib.sha256((ROOT / "evals/scenarios.json").read_bytes()).hexdigest()
        ):
            parser.error(
                "host configuration/guidance or scenarios changed since preparation"
            )
    else:
        manifest = {
            "model": args.model,
            "effort": args.effort,
            "codex_binary": shutil.which(args.codex_bin) or args.codex_bin,
            "cli": command([args.codex_bin, "--version"]).stdout.strip(),
            "disabled_skills": args.disable_skill,
            "disabled_mcp": configured_mcp(),
            "host_snapshot": host_snapshot(),
            "max_trials": 30,
            "scenarios_sha256": hashlib.sha256(
                (ROOT / "evals/scenarios.json").read_bytes()
            ).hexdigest(),
            "baseline": source_copy(args.baseline_ref, output / "sources/baseline"),
            "candidate": source_copy(args.candidate_ref, output / "sources/candidate"),
        }
        write_json(path, manifest)
    if args.prepare_only:
        print(path)
        return 0
    previous = [
        json.loads(p.read_text()) for p in (output / "trials").glob("*/result.json")
    ]
    extra = sum(r["attempt"] > 1 for r in previous)
    if args.retry and extra >= 6:
        parser.error("six extra attempts exhausted")
    if args.retry and args.retry not in {
        f"{s['id']}:{v}" for s in scenarios for v in ("baseline", "candidate")
    }:
        parser.error("unknown retry case:variant")
    for case in scenarios:
        for variant in ("baseline", "candidate"):
            if host_snapshot() != manifest["host_snapshot"]:
                parser.error("host configuration changed during comparison")
            matches = [
                r
                for r in previous
                if r["case"] == case["id"] and r["variant"] == variant
            ]
            if args.retry:
                if args.retry != f"{case['id']}:{variant}":
                    continue
            elif matches:
                continue
            if len(previous) >= 30:
                parser.error("30-trial budget exhausted")
            attempt = max((r["attempt"] for r in matches), default=0) + 1
            print(f"Starting {case['id']} {variant} attempt {attempt}", flush=True)
            result = trial(output, manifest, case, variant, attempt)
            previous.append(result)
            print(json.dumps(result), flush=True)
    write_json(output / "results.json", previous)
    latest = {(r["case"], r["variant"]): r for r in previous}
    accepted = all(
        latest.get((s["id"], "candidate"), {}).get("passed", False) for s in scenarios
    )
    print(
        json.dumps(
            {
                "candidate_deterministic_acceptance": accepted,
                "human_review": "required",
                "trials": len(previous),
            }
        )
    )
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
