# Harness Engineering v1.1.0

Status: active. Baseline: `5fc35fe`. One combined release with independently
reviewable commits. Preserve Python 3.10+, no runtime dependencies, advisory
alignment, existing CLI flags/exit conventions/JSON fields, and seven dimensions.

## Delivery and acceptance

1. Harden initialization destinations, no-op guards, exclusive writes, and global
   contract replacement. Reproduce boundaries with disposable fixtures.
2. Discover canonical commands with provenance; conservatively distinguish CI
   references, invocations, failure propagation, and unverified merge requirements.
3. Share scoped override/fallback guidance discovery and explicit-profile handling.
4. Add twelve development-only agent scenarios and a bounded baseline/candidate
   comparison; repair policy wording and portability.
5. Prepare version 1.1.0, deterministic archives, release notes, and exact GitHub
   governance update/restoration payloads.

Run focused regressions after each subsystem, then complete tests, compilation,
Ruff, distribution and installed OpenAI validators. Obtain one independent review
of write boundaries and evidence classification. Run 24 sequential agent trials
with five-minute limits and at most six additional trials. Candidate mandatory
checks must pass without scenario regressions; human review assesses grounding
and unnecessary work. Store raw traces and security reproductions outside Git.

## Locked decisions

- Standard-library implementation; a conservative shell/CI subset, not a general
  interpreter. Unsupported syntax remains uncertain.
- Existing report fields remain; provenance and guidance resolution are additive.
- Optional scoped/fallback guidance arguments; no complete host config emulation.
- Freeze model, effort, CLI, and tool settings for the live comparison without
  committing personal routing policy or changing installed skills/user guidance.
- Main policy: PRs, both existing Python checks, current branch before merge,
  no force pushes/deletion/admin bypass, zero additional approving reviewers.
- No scheduled evaluations, telemetry, extra merge queue, or global setup edits.

## Evidence and gates

Local implementation/validation, agent trials, CI, provider configuration,
publication, and installed version are separate evidence. Push, merge, provider
changes, tagging, publication, and installation require their named authorization;
prepare concrete reviewable changes before that gate. No provider action is
inferred from local success. Security reporting follows the root SECURITY.md.

## Recovery and progress

Keep commits independently revertible. Record unexpected partial writes honestly;
do not promise a filesystem transaction. Preserve provider settings before changes.
For a release defect suspend affected mutation commands and make a corrective
patch rather than recommending the vulnerable baseline.

- Started: clean baseline confirmed; implementation branch created.
- Safety: eight targeted regressions and the fourteen original framework tests
  pass locally. Exclusive output creation, destination preflight, complete no-op
  detection, unique replacement files, permission preservation, and marker-order
  diagnostics implemented.
- Audit evidence: six focused tests pass, including misleading command text,
  conditions, ignored errors, working-directory mismatches, actual repository
  discovery, provenance, and unrelated structural tests. The existing framework
  checks still pass. CI metadata extraction supports a bounded GitHub subset;
  unsupported workflow syntax cannot establish enforcement.
- Guidance: eight focused tests and original framework tests pass. Read-only
  commands share override/scope/fallback resolution and concept checks; explicit
  profile declarations take precedence and conflicts are surfaced. Alternate
  Codex home evidence remains separate. CLI regression snapshots preserve bytes,
  modes, and Git status.
- Independent review: three additional CI false positives were reproduced and
  fixed (flow metadata, default Windows/unknown shells, shell-mutating builtins).
  The reviewer reran original reproductions and nine focused CI tests and found
  no remaining blocker in the bounded write-boundary/CI review. This is not agent
  evaluation or release acceptance.
- Candidate: version 1.1.0 and release checklist prepared. All 46 initial tests
  passed locally on Python 3.10 and 3.13; compilation, Ruff, distribution and
  installed OpenAI skill/plugin validators passed. Two release archive builds
  produced identical SHA-256 hashes.
- Live comparison started. Initial CLI/model incompatibility prevented model
  processing; the failed attempt was retained. An already installed compatible
  bundled CLI is frozen for processed trials, with one extra attempt consumed.
  Added native skill-root alias handling and invocation-only fixture trust.
  Two incidental CLI-created trust entries were removed without changing other
  configuration content. First baseline/candidate alignment pair passed.
- Provider update/restoration payloads and current policy snapshot prepared
  outside Git. Main remains unprotected; no provider mutation, push, publication,
  or installation has occurred.
- Final local matrix: 48 tests pass on both Python 3.10 and 3.13; Ruff,
  compilation, and distribution validation pass. Current skill content matches
  the frozen candidate and the installed baseline remains unchanged.
- Seven completed agent pairs pass (14 processed trials plus one retained CLI
  incompatibility failure). Shared host configuration changed after the audit
  pair, so the runner correctly halted. Model/effort remained unchanged; the
  complete tool configuration equivalence is not established. Awaiting the
  user's choice to disclose an environment split for the remaining five pairs
  or leave live acceptance incomplete; no further trials run in the meantime.
- Evaluation summary now selects retries by attempt number, not filesystem
  enumeration order, and cannot count a failed infrastructure run as a completed
  comparison. Two focused regression tests added. All 50 tests pass locally on
  Python 3.10 and 3.13; Ruff and distribution validation also pass.
- Next: complete remaining agent trials and rubric review, then report evidence
  and obtain the distinct provider/push/merge/publication authorizations.
