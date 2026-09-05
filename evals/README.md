# Bounded skill evaluation

These development-only scenarios compare a pinned baseline and candidate with
the same locally selected model, effort, CLI, tools, and fixture contents. They
are excluded from the distributed skill. No model routing policy is prescribed.

Use `python3 tools/evaluate_skill.py --help`. Supply an output directory outside
the repository, an explicit model/effort, baseline and candidate refs, and every
installed harness SKILL.md path that must be disabled for the invocation.
`--prepare-only` creates the manifest and immutable source copies without agent
trials. The runner resumes its saved manifest and results rather than silently
re-running trials. `--retry CASE:VARIANT` uses one of six extra attempts and
retains earlier attempts. No automatic retries or scheduled service are added.

Each trial gets a clean Git fixture with a tracked native skill symlink. The
selected skill source is outside the writable fixture. Preflight verifies the
model-visible catalog contains exactly that harness version. Commands run with
workspace write permissions and network disabled; a read-only task must preserve
the fixture even though its sandbox permits writes. Authentication is reused;
credentials and global settings are not copied or modified.

## Acceptance and human review

All candidate mandatory checks must pass, and no scenario that passed for the
baseline may regress. Initial runs total 24, with at most six extra attempts.
Every trial has a five-minute timeout. Raw traces, final responses, changes,
permissions, elapsed time, usage and grader checks remain outside Git.

Review the final responses and relevant command output for every pair. Record
pass/fail and a concrete reason for each of these independent questions:

- Does the response establish the requested mode and stay within scope?
- Are factual claims supported by fixture files or executed checks?
- Does the comprehensive audit address every demonstrated material gap with
  impact/effort prioritization, while adequate repositories avoid invented work?
- Are local checks, configured CI, and unverified merge/provider policy distinct?
- Does the task complete without avoidable approvals, repeated scans or edits?

The script reports only deterministic acceptance. Record human review separately;
a deterministic pass alone never claims release acceptance. Time and tokens are
diagnostic, not statistically meaningful productivity claims. Baseline failures
are retained, not hidden by selective retries. Never relax graders just to pass.

Sources: [OpenAI skill evaluations](https://developers.openai.com/blog/eval-skills)
and [non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode).
