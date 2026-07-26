from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = (
    ROOT / "plugins" / "codex-harness-engineering" / "skills" / "harness-engineering"
)
SCRIPTS = SKILL / "scripts"


def run_script(
    name: str, *args: str, check: bool = True
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


class RepositoryFixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="harness-v1-")
        self.root = Path(self.temporary.name).resolve()
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "fixture@example.test")
        git(self.root, "config", "user.name", "Harness Fixture")

    def commit_all(self, message: str = "fixture") -> None:
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", message)

    def close(self) -> None:
        self.temporary.cleanup()


class HarnessFrameworkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = RepositoryFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def align(self) -> dict:
        result = run_script(
            "align_repository.py",
            "--root",
            str(self.fixture.root),
            "--format",
            "json",
        )
        return json.loads(result.stdout)

    def initialize(
        self, tier: str = "small", *extra: str
    ) -> subprocess.CompletedProcess:
        return run_script(
            "initialize_harness.py",
            "--root",
            str(self.fixture.root),
            "--tier",
            tier,
            "--confirm-new-repository",
            *extra,
        )

    def inspect(self, mode: str = "audit") -> dict:
        result = run_script(
            "inspect_repository.py",
            "--root",
            str(self.fixture.root),
            "--mode",
            mode,
            "--format",
            "json",
        )
        return json.loads(result.stdout)

    def test_empty_git_repository_needs_initialize(self) -> None:
        report = self.align()
        self.assertEqual(report["status"], "needs-initialize")
        self.assertEqual(report["next_mode"], "initialize")

    def test_initialized_empty_repository_aligns_from_declared_profile(self) -> None:
        self.initialize(
            "small",
            "--profile",
            "library-or-cli",
            "--authority",
            "product=https://example.test/spec",
        )
        report = self.align()
        self.assertEqual(report["status"], "aligned")
        self.assertEqual(report["profile"], "library-or-cli")
        self.assertEqual(
            report["authority"]["explicit_external_sources"],
            ["https://example.test/spec"],
        )
        self.assertEqual(report["authority"]["external_source_state"], "Unverified")

    def test_initializer_requires_exact_git_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="not-git-") as directory:
            result = run_script(
                "initialize_harness.py",
                "--root",
                directory,
                "--tier",
                "small",
                "--confirm-new-repository",
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact root of a Git repository", result.stderr)

    def test_package_manager_detection_uses_configured_manager(self) -> None:
        (self.fixture.root / "package.json").write_text(
            json.dumps(
                {
                    "packageManager": "yarn@4.9.2",
                    "scripts": {"test": "vitest run"},
                    "dependencies": {"react": "19.0.0"},
                }
            ),
            encoding="utf-8",
        )
        self.fixture.commit_all()
        self.initialize("small")
        agents = (self.fixture.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("`yarn test`", agents)
        self.assertIn("`web-application`", agents)
        self.assertNotIn("`pnpm test`", agents)

    def test_python_and_swift_profiles_are_detected(self) -> None:
        (self.fixture.root / "pyproject.toml").write_text(
            '[project]\nname = "fixture"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )
        self.fixture.commit_all()
        self.assertEqual(self.align()["profile"], "library-or-cli")

        self.fixture.close()
        self.fixture = RepositoryFixture()
        (self.fixture.root / "Package.swift").write_text(
            "// swift-tools-version: 6.0\n", encoding="utf-8"
        )
        self.fixture.commit_all()
        report = self.align()
        self.assertEqual(report["profile"], "native-application")
        self.assertIn("user-interface", report["capabilities"])

    def test_root_agents_is_not_reported_as_linked_from_itself(self) -> None:
        self.initialize("small", "--profile", "library-or-cli")
        report = self.inspect()
        self.assertEqual(report["repository_local"]["linked_sources"], [])

    def test_evidence_labels_do_not_prove_runtime_legibility(self) -> None:
        self.initialize("small", "--profile", "library-or-cli")
        report = self.inspect()
        runtime = report["dimensions"]["Runtime and worktree legibility"]
        self.assertEqual(runtime["level"], "absent")
        self.assertEqual(report["smallest_recommended_improvement"], "No change needed")

    def test_ci_comment_does_not_enforce_but_run_step_does(self) -> None:
        (self.fixture.root / "package.json").write_text(
            json.dumps(
                {
                    "packageManager": "npm@11.0.0",
                    "scripts": {"test": "node --test"},
                }
            ),
            encoding="utf-8",
        )
        workflow = self.fixture.root / ".github" / "workflows" / "ci.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text(
            "jobs:\n  test:\n    steps:\n      # npm run test\n      - run: echo skipped\n",
            encoding="utf-8",
        )
        self.fixture.commit_all()
        self.initialize("small")
        first = self.inspect()["dimensions"]["Verification routing"]
        self.assertEqual(first["level"], "executable")
        workflow.write_text(
            "jobs:\n  test:\n    steps:\n      - run: npm run test\n",
            encoding="utf-8",
        )
        second = self.inspect()["dimensions"]["Verification routing"]
        self.assertEqual(second["level"], "enforced")

    def test_growing_fixture_does_not_invent_maintenance_work(self) -> None:
        self.initialize("growing", "--profile", "service-or-worker")
        report = self.inspect()
        self.assertEqual(report["smallest_recommended_improvement"], "No change needed")
        garden = self.inspect("garden")
        self.assertEqual(garden["mode"], "garden")
        self.assertEqual(garden["garden_findings"], [])

    def test_unresolved_authority_conflict_returns_needs_input(self) -> None:
        self.initialize("small", "--profile", "library-or-cli")
        agents = self.fixture.root / "AGENTS.md"
        agents.write_text(
            agents.read_text(encoding="utf-8") + "\nAUTHORITY_CONFLICT\n",
            encoding="utf-8",
        )
        self.assertEqual(self.align()["status"], "needs-input")

    def test_nested_guidance_is_preserved_and_initializer_refuses(self) -> None:
        nested = self.fixture.root / "src" / "AGENTS.md"
        nested.parent.mkdir()
        nested.write_text("# Existing guidance\n", encoding="utf-8")
        result = run_script(
            "initialize_harness.py",
            "--root",
            str(self.fixture.root),
            "--tier",
            "small",
            "--confirm-new-repository",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested AGENTS.md exists", result.stderr)
        self.assertEqual(nested.read_text(encoding="utf-8"), "# Existing guidance\n")

    def test_mature_repository_without_architecture_gets_one_architecture_gap(
        self,
    ) -> None:
        for index in range(25):
            (self.fixture.root / f"module_{index}.py").write_text(
                f"VALUE = {index}\n", encoding="utf-8"
            )
        (self.fixture.root / "AGENTS.md").write_text(
            """# Agent Map

## Project shape
Primary profile: `library-or-cli`.

## Authority map
Current implementation authority is this Git checkout.

## Canonical commands
Use `python -m unittest`.

## Evidence boundaries
Local proof is separate from Production and provider proof.

## Human gates
Require human approval before merge.

## Done condition
Done when focused validation passes.

Self-review every change and record recovery risk.
""",
            encoding="utf-8",
        )
        self.fixture.commit_all()
        report = self.inspect()
        self.assertEqual(
            report["smallest_recommended_improvement"],
            "Document the implemented system boundaries and dependency direction.",
        )


class GlobalContractTests(unittest.TestCase):
    def test_install_is_idempotent_and_preserves_existing_guidance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="global-contract-") as directory:
            target = Path(directory) / "AGENTS.md"
            target.write_text("# Existing\n\nKeep this.\n", encoding="utf-8")
            first = run_script(
                "manage_global_contract.py",
                "--target",
                str(target),
                "--install",
                "--confirm",
            )
            second = run_script(
                "manage_global_contract.py",
                "--target",
                str(target),
                "--install",
                "--confirm",
            )
            checked = run_script(
                "manage_global_contract.py",
                "--target",
                str(target),
                "--check",
            )
            content = target.read_text(encoding="utf-8")
        self.assertIn("Global contract: installed", first.stdout)
        self.assertIn("Global contract: unchanged", second.stdout)
        self.assertIn("Global contract: installed", checked.stdout)
        self.assertTrue(content.startswith("# Existing\n\nKeep this."))
        self.assertEqual(content.count("harness-engineering:global-contract:start"), 1)

    def test_divergent_managed_content_is_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="global-contract-") as directory:
            target = Path(directory) / "AGENTS.md"
            target.write_text(
                """<!-- harness-engineering:global-contract:start -->
changed
<!-- harness-engineering:global-contract:end -->
""",
                encoding="utf-8",
            )
            result = run_script(
                "manage_global_contract.py",
                "--target",
                str(target),
                "--install",
                "--confirm",
                check=False,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing to replace divergent managed content", result.stdout)


if __name__ == "__main__":
    unittest.main()
