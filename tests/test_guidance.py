from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_harness_framework import ROOT, SCRIPTS, RepositoryFixture, run_script

sys.path.insert(0, str(SCRIPTS))
import align_repository as align
import guidance
import harness_core as core
import inspect_repository as inspector
import validate_harness as validator

CONTRACT = """# Agent Map
Primary profile: `service-or-worker`.
## Authority map
Implementation is the Git checkout.
## Canonical commands
Use `python -m unittest`.
## Evidence boundaries
Local proof does not prove provider state.
## Human gates
Human approval before merge.
## Done condition
Done when focused checks pass. Self-review every change.
"""


class GuidanceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = RepositoryFixture()
        self.root = self.fixture.root
        (self.root / "go.mod").write_text("module example.test/service\n")

    def tearDown(self):
        self.fixture.close()

    def test_override_precedence_and_declared_go_profile(self):
        (self.root / "AGENTS.md").write_text("AUTHORITY_CONFLICT")
        (self.root / "AGENTS.override.md").write_text(CONTRACT)
        report = align.assess(self.root)
        self.assertEqual(report["status"], "aligned")
        self.assertEqual(report["profile"], "service-or-worker")
        self.assertEqual(report["authority"]["local_guidance"], "AGENTS.override.md")
        self.assertTrue(validator.validate(self.root)["valid"])

    def test_empty_override_and_explicit_fallback(self):
        (self.root / "AGENTS.override.md").write_text("\n")
        (self.root / "GUIDE.md").write_text(CONTRACT)
        self.assertEqual(
            align.assess(self.root, fallbacks=["GUIDE.md"])["status"], "aligned"
        )
        self.assertEqual(align.assess(self.root)["status"], "needs-upgrade")
        with self.assertRaises(ValueError):
            guidance.resolve(self.root, fallbacks=["../OUTSIDE.md"])

    def test_nested_scope_and_profile_conflict(self):
        (self.root / "AGENTS.md").write_text(CONTRACT)
        nested = self.root / "services" / "one"
        nested.mkdir(parents=True)
        (nested / "AGENTS.override.md").write_text(
            "Primary profile: `web-application`.\n"
        )
        self.assertEqual(align.assess(self.root)["status"], "aligned")
        report = align.assess(self.root, "services/one")
        self.assertEqual(report["status"], "needs-input")
        self.assertIsNone(report["profile"])
        self.assertEqual(
            report["guidance_resolution"]["selected_sources"],
            ["AGENTS.md", "services/one/AGENTS.override.md"],
        )
        self.assertFalse(validator.validate(self.root, "services/one")["valid"])
        self.assertTrue(
            inspector.classify(
                self.root, core.walk_files(self.root), "audit", "services/one"
            )["profile_diagnostics"]
        )
        with self.assertRaises(ValueError):
            guidance.resolve(self.root, "..")

    def test_concrete_profile_mismatch_preserves_declaration(self):
        (self.root / "AGENTS.md").write_text(CONTRACT)
        (self.root / "Package.swift").write_text("// swift-tools-version: 6.0\n")
        report = align.assess(self.root)
        self.assertEqual(report["profile"], "service-or-worker")
        self.assertTrue(report["profile_diagnostics"])

    def test_codex_home_and_inherited_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / "AGENTS.override.md").write_text("Global safeguards\n")
            (home / "AGENTS.md").write_text(CONTRACT)
            with patch.dict(os.environ, {"CODEX_HOME": directory}):
                report = inspector.classify(
                    self.root, core.walk_files(self.root), "audit"
                )
                self.assertEqual(
                    report["guidance_resolution"]["inherited_sources"],
                    [str(home / "AGENTS.override.md")],
                )
                self.assertEqual(
                    report["dimensions"]["Governance and evidence boundaries"]["level"],
                    "absent",
                )

    def test_current_repository_has_consistent_concept_checks(self):
        self.assertEqual(align.assess(ROOT)["missing_contracts"], [])
        self.assertEqual(validator.validate(ROOT)["warnings"], [])

    def test_initializer_preserves_competing_guidance(self):
        (self.root / "AGENTS.override.md").write_text(CONTRACT)
        self.fixture.commit_all()
        result = run_script(
            "initialize_harness.py",
            "--root",
            str(self.root),
            "--tier",
            "small",
            "--confirm-new-repository",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertEqual((self.root / "AGENTS.override.md").read_text(), CONTRACT)

    def test_all_readonly_modes_preserve_content_permissions_and_status(self):
        (self.root / "AGENTS.md").write_text(CONTRACT)
        (self.root / "AGENTS.md").chmod(0o600)
        self.fixture.commit_all()

        def snapshot():
            files = {
                str(p.relative_to(self.root)): (
                    p.read_bytes(),
                    stat.S_IMODE(p.stat().st_mode),
                )
                for p in self.root.rglob("*")
                if p.is_file() and ".git" not in p.parts
            }
            status = subprocess.check_output(
                ["git", "-C", str(self.root), "status", "--porcelain"]
            )
            return files, status

        before = snapshot()
        for name, extra in [
            ("align_repository.py", []),
            ("validate_harness.py", []),
            ("inspect_repository.py", ["--mode", "audit"]),
            ("inspect_repository.py", ["--mode", "garden"]),
        ]:
            with self.subTest(name=name, extra=extra):
                run_script(
                    name,
                    "--root",
                    str(self.root),
                    "--scope",
                    ".",
                    "--format",
                    "json",
                    *extra,
                )
                self.assertEqual(snapshot(), before)


if __name__ == "__main__":
    unittest.main()
