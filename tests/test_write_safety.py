from __future__ import annotations

import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_harness_framework import SCRIPTS, SKILL, RepositoryFixture, run_script

sys.path.insert(0, str(SCRIPTS))
import manage_global_contract as contract


class WriteSafetyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = RepositoryFixture()
        self.root = self.fixture.root

    def tearDown(self):
        self.fixture.close()

    def initialize(self, tier="small"):
        return run_script(
            "initialize_harness.py",
            "--root",
            str(self.root),
            "--tier",
            tier,
            "--profile",
            "library-or-cli",
            "--confirm-new-repository",
            check=False,
        )

    def test_symlink_parent_creates_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory)
            (self.root / "docs").symlink_to(outside, target_is_directory=True)
            self.fixture.commit_all()
            self.assertEqual(self.initialize("growing").returncode, 2)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertFalse((self.root / "AGENTS.md").exists())

    def test_dangling_output_creates_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / "untouched.md"
            (self.root / "AGENTS.md").symlink_to(outside)
            self.fixture.commit_all()
            self.assertEqual(self.initialize().returncode, 2)
            self.assertFalse(outside.exists())

    def test_late_conflict_and_nonfile_create_nothing(self):
        for is_directory in (False, True):
            with self.subTest(is_directory=is_directory):
                target = self.root / "docs" / "quality.md"
                target.parent.mkdir(exist_ok=True)
                if is_directory:
                    target.mkdir()
                else:
                    target.write_text("Keep this")
                self.fixture.commit_all()
                self.assertEqual(self.initialize("growing").returncode, 2)
                self.assertFalse((self.root / "AGENTS.md").exists())
                self.assertFalse((self.root / "docs" / "architecture.md").exists())
                if is_directory:
                    target.rmdir()
                else:
                    self.assertEqual(target.read_text(), "Keep this")
                    target.unlink()

    def test_partial_output_cannot_bypass_mature_or_dirty_guard(self):
        target = self.root / "docs" / "PLANS.md"
        target.parent.mkdir()
        target.write_bytes((SKILL / "assets" / "PLANS.md.tmpl").read_bytes())
        self.fixture.commit_all()
        (self.root / "untracked.py").write_text("pass\n")
        self.assertNotEqual(self.initialize("large").returncode, 0)
        self.assertFalse((self.root / "AGENTS.md").exists())
        for index in range(25):
            (self.root / f"module_{index}.py").write_text("pass\n")
        self.fixture.commit_all()
        self.assertNotEqual(self.initialize("large").returncode, 0)
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_all_tiers_rerun_without_changing_bytes(self):
        for tier in ("small", "growing", "large"):
            with self.subTest(tier=tier):
                self.fixture.close()
                self.fixture = RepositoryFixture()
                self.root = self.fixture.root
                self.assertEqual(self.initialize(tier).returncode, 0)
                before = {p: p.read_bytes() for p in self.root.rglob("*.md")}
                self.assertEqual(self.initialize(tier).returncode, 0)
                self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_global_temp_collisions_and_permissions(self):
        target = self.root / "AGENTS.md"
        target.write_text("Keep this\n")
        target.chmod(0o600)
        other = self.root / "other"
        other.write_text("Untouched")
        collision = target.with_name(target.name + ".harness-engineering.tmp")
        collision.symlink_to(other)
        contract.install(target, contract.contract_text())
        self.assertEqual(other.read_text(), "Untouched")
        self.assertTrue(collision.is_symlink())
        self.assertFalse(target.is_symlink())
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        collision.unlink()
        collision.write_text("Still untouched")
        target.write_text("Reset\n")
        contract.install(target, contract.contract_text())
        self.assertEqual(collision.read_text(), "Still untouched")

    def test_failed_replace_preserves_target_and_cleans_own_temp(self):
        target = self.root / "AGENTS.md"
        target.write_text("Keep this\n")
        before = set(self.root.iterdir())
        with (
            patch.object(Path, "replace", side_effect=OSError("fixture failure")),
            self.assertRaises(OSError),
        ):
            contract.install(target, contract.contract_text())
        self.assertEqual(target.read_text(), "Keep this\n")
        self.assertEqual(set(self.root.iterdir()), before)

    def test_reversed_markers_are_malformed(self):
        self.assertEqual(
            contract.inspect(contract.END + contract.START, contract.contract_text()),
            "malformed",
        )


if __name__ == "__main__":
    unittest.main()
