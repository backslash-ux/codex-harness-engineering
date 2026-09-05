from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-harness-engineering"


class DistributionTests(unittest.TestCase):
    def test_distribution_validator_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "validate_distribution.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("Distribution validation: PASS", result.stdout)

    def test_manifest_and_marketplace_share_identity(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        entry = marketplace["plugins"][0]
        self.assertEqual(manifest["name"], entry["name"])
        self.assertEqual(manifest["name"], "codex-harness-engineering")
        self.assertEqual(manifest["version"], "1.1.0")
        self.assertEqual(marketplace["name"], "backslash-ux")

    def test_release_archive_is_deterministic_and_minimal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="harness-release-") as directory:
            first = Path(directory) / "first.zip"
            second = Path(directory) / "second.zip"
            for output in (first, second):
                subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "tools" / "package_release.py"),
                        "--output",
                        str(output),
                    ],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                )
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                names = set(archive.namelist())

        prefix = "codex-harness-engineering/"
        self.assertIn(f"{prefix}.codex-plugin/plugin.json", names)
        self.assertIn(
            f"{prefix}skills/harness-engineering/SKILL.md",
            names,
        )
        self.assertIn(f"{prefix}LICENSE", names)
        self.assertFalse(any("/tests/" in name for name in names))
        self.assertFalse(any(name.endswith("README.md") for name in names))
        self.assertFalse(any("__pycache__" in name for name in names))


if __name__ == "__main__":
    unittest.main()
