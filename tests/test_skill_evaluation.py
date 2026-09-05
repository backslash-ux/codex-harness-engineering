from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_harness_framework import ROOT, SCRIPTS

sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(SCRIPTS))
import align_repository
import evaluate_skill as evaluation


class SkillEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name).resolve()
        self.skill = self.base / "source/harness-engineering"
        self.skill.mkdir(parents=True)
        (self.skill / "SKILL.md").write_text(
            "---\nname: harness-engineering\ndescription: fixture\n---\n"
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_twelve_unique_scenarios_and_isolated_new_repo(self):
        cases = json.loads((ROOT / "evals/scenarios.json").read_text())
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({c["id"] for c in cases}), 12)
        root = self.base / "fixture"
        evaluation.fixture(root, self.skill, "initialize")
        self.assertEqual(align_repository.assess(root)["status"], "needs-initialize")
        self.assertEqual(
            evaluation.command(["git", "status", "--porcelain"], root).stdout, ""
        )

    def test_preflight_requires_exactly_one_selected_skill(self):
        root = self.base / "fixture"
        evaluation.fixture(root, self.skill, "align")
        text = f"- harness-engineering: fixture (file: {self.skill}/SKILL.md)"
        manifest = {"model": "fixture", "effort": "fixture", "disabled_skills": []}
        with patch.object(
            evaluation,
            "command",
            return_value=SimpleNamespace(stdout=json.dumps([text])),
        ):
            self.assertEqual(
                evaluation.preflight(root, self.skill, manifest)["harness_entries"], 1
            )
        with (
            patch.object(
                evaluation,
                "command",
                return_value=SimpleNamespace(stdout=json.dumps([text, text])),
            ),
            self.assertRaises(ValueError),
        ):
            evaluation.preflight(root, self.skill, manifest)

    def test_preflight_resolves_current_cli_skill_root_aliases(self):
        root = self.base / "fixture"
        evaluation.fixture(root, self.skill, "align")
        text = f"- `r7` = `{self.skill.parent}`\n- harness-engineering: fixture (file: r7/harness-engineering/SKILL.md)"
        manifest = {"model": "fixture", "effort": "fixture", "disabled_skills": []}
        with patch.object(
            evaluation,
            "command",
            return_value=SimpleNamespace(stdout=json.dumps([text])),
        ):
            self.assertEqual(
                evaluation.preflight(root, self.skill, manifest)["harness_entries"], 1
            )

    def test_grader_rejects_edits_in_readonly_task(self):
        root = self.base / "fixture"
        evaluation.fixture(root, self.skill, "align")
        before = evaluation.snapshot(root)
        (root / "unauthorized.txt").write_text("wrong")
        result = evaluation.grade(
            {"id": "align", "commands": [], "changes": []},
            root,
            before,
            evaluation.snapshot(root),
            [],
            "done",
            0,
        )
        self.assertFalse(result["checks"]["changes_in_scope"])

    def test_mcp_disable_overrides_do_not_create_quoted_server_names(self):
        values = evaluation.overrides(
            {
                "effort": "fixture",
                "disabled_skills": [],
                "disabled_mcp": ["example-server"],
            }
        )
        self.assertIn("mcp_servers.example-server.enabled=false", values)
        self.assertNotIn('mcp_servers."example-server".enabled=false', values)

    def test_misleading_ci_requires_correct_evidence(self):
        root = self.base / "fixture"
        evaluation.fixture(root, self.skill, "misleading-ci")
        state = evaluation.snapshot(root)
        event = {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": "python3 inspect_repository.py",
                "aggregated_output": json.dumps(
                    {"dimensions": {"Verification routing": {"level": "enforced"}}}
                ),
            },
        }
        result = evaluation.grade(
            {
                "id": "misleading-ci",
                "commands": ["inspect_repository.py"],
                "changes": [],
            },
            root,
            state,
            state,
            [event],
            "Looks fine",
            0,
        )
        self.assertFalse(result["checks"]["no_false_ci_enforcement"])

    def test_infrastructure_failure_does_not_establish_comparison_acceptance(self):
        records = [
            {
                "case": "align",
                "variant": "baseline",
                "attempt": 1,
                "returncode": 1,
                "passed": False,
            },
            {
                "case": "align",
                "variant": "candidate",
                "attempt": 1,
                "returncode": 0,
                "passed": True,
            },
        ]
        result = evaluation.assessment([{"id": "align"}], records)
        self.assertTrue(result["candidate_deterministic_acceptance"])
        self.assertFalse(result["comparison_complete"])

    def test_latest_attempt_wins_independently_of_file_enumeration_order(self):
        records = [
            {
                "case": "align",
                "variant": "baseline",
                "attempt": 2,
                "returncode": 0,
                "passed": True,
            },
            {
                "case": "align",
                "variant": "baseline",
                "attempt": 1,
                "returncode": 1,
                "passed": False,
            },
            {
                "case": "align",
                "variant": "candidate",
                "attempt": 1,
                "returncode": 0,
                "passed": True,
            },
        ]
        result = evaluation.assessment([{"id": "align"}], records)
        self.assertTrue(result["comparison_complete"])


if __name__ == "__main__":
    unittest.main()
