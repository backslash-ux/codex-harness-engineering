from __future__ import annotations

import json
import sys
import unittest

from test_harness_framework import ROOT, SCRIPTS, RepositoryFixture

sys.path.insert(0, str(SCRIPTS))
import harness_core as core
import inspect_repository as inspector


class CommandEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = RepositoryFixture()
        self.root = self.fixture.root
        (self.root / "package.json").write_text(
            json.dumps({"scripts": {"test": "node --test"}})
        )
        self.workflow = self.root / ".github/workflows/ci.yml"
        self.workflow.parent.mkdir(parents=True)

    def tearDown(self):
        self.fixture.close()

    def check(self, run, job="", step="", defaults=""):
        self.workflow.write_text(
            defaults
            + "jobs:\n  test:\n"
            + job
            + "    steps:\n      - name: Tests\n"
            + step
            + "        run: "
            + run
            + "\n"
        )
        commands = core.discover_commands(self.root)
        root_test = next(
            c
            for c in commands
            if c["canonical"] == "npm run test" and c["working_directory"] == "."
        )
        return core.command_is_ci_enforced(root_test, []), root_test

    def test_direct_and_continued_commands(self):
        for run in (
            "npm run test",
            "'npm run test'",
            "|\n          npm run \\\n            test",
            ">-\n          npm run\n          test",
        ):
            with self.subTest(run=run):
                self.assertTrue(self.check(run)[0])

    def test_false_enforcement_regressions(self):
        cases = [
            ("echo 'npm run test'", "", "", ""),
            ("npm run test:unit", "", "", ""),
            ("npm run test || true", "", "", ""),
            ("npm run test", "    if: false\n", "", ""),
            ("npm run test", "", "        if: github.event_name == 'push'\n", ""),
            ("npm run test", "    continue-on-error: true\n", "", ""),
            ("npm run test", "", "        continue-on-error: true\n", ""),
            ("npm run test", "", "        working-directory: sub\n", ""),
            ("npm run test", "", "", "defaults:\n  run:\n    working-directory: sub\n"),
            ("npm run test", "", "        shell: bash {0}\n", ""),
            ("|\n          set +e\n          npm run test", "", "", ""),
            ("|\n          false\n          npm run test", "", "", ""),
            ("npm run ${{ inputs.command }}", "", "", ""),
        ]
        (self.root / "sub").mkdir()
        for args in cases:
            with self.subTest(args=args):
                self.assertFalse(self.check(*args)[0])

    def test_test_file_is_not_promoted_by_unrelated_ci(self):
        self.check("npm run test")
        (self.root / "unreachable-boundary.test.ts").write_text(
            "// not in test discovery"
        )
        report = inspector.classify(self.root, core.walk_files(self.root), "audit")
        self.assertEqual(
            report["dimensions"]["Architecture and enforceable invariants"]["level"],
            "executable",
        )

    def test_real_repository_commands_and_provenance(self):
        commands = core.discover_commands(ROOT)
        test = next(c for c in commands if "unittest discover" in c["canonical"])
        self.assertTrue(core.command_is_ci_enforced(test, []))
        self.assertGreaterEqual(len(test["sources"]), 2)
        self.assertTrue(all(s["line"] > 0 for s in test["sources"]))
        self.assertEqual(test["required_before_merge"], "Unverified")
        self.assertTrue(
            any("tools/validate_distribution.py" in c["canonical"] for c in commands)
        )

    def test_make_just_and_package_manager_preserved(self):
        (self.root / "Makefile").write_text("test:\n\tpython -m unittest\n")
        (self.root / "Justfile").write_text("check:\n    python -m unittest\n")
        commands = core.discover_commands(self.root)
        self.assertTrue(
            {"make test", "just check", "npm run test"}.issubset(
                {c["canonical"] for c in commands}
            )
        )

    def test_discovery_does_not_execute_commands(self):
        (self.root / "package.json").write_text(
            json.dumps({"scripts": {"test": "touch SHOULD_NOT_EXIST"}})
        )
        self.check("npm run test")
        self.assertFalse((self.root / "SHOULD_NOT_EXIST").exists())


if __name__ == "__main__":
    unittest.main()
