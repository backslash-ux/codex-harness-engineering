---
name: harness-engineering
description: Activate, align, initialize, audit, upgrade, or garden Codex-first software-repository harnesses using repository-local authority maps, adaptive project profiles, progressive context, focused verification, runtime legibility, evidence boundaries, and entropy control. Use when creating a software repository, entering an unaligned repository, changing project authorities or architecture, assessing agent readiness, installing the user-level repository alignment rule, or making a sustainable harness improvement.
---

# Harness Engineering

Build repository-local conditions that let Codex make reliable progress without
turning process into the product. Keep versioned repository artifacts as the
durable implementation system of record. Treat external trackers, documents,
environments, and providers as separate domain authorities.

## Select exactly one mode

- **activate** — check or explicitly install the managed user-level alignment
  rule. Preserve unrelated guidance and refuse divergent managed content.
- **align** — inspect one software repository without editing. Return
  `aligned`, `needs-initialize`, `needs-upgrade`, `needs-input`, or
  `out-of-scope`, plus at most one material recommendation.
- **initialize** — create the minimum applicable contract for a genuinely new
  Git repository.
- **audit** — inspect without editing and report seven independent evidence
  dimensions.
- **upgrade** — audit first, then implement one explicitly authorized,
  sustainable improvement.
- **garden** — inspect without editing for demonstrated documentation,
  planning, or enforcement drift.

Default to `align` when a repository-lifecycle request does not name a mode.
Default to `audit` for an explicit maturity assessment. Never combine a
read-only mode with repository mutation.

Incomplete alignment is advisory. Continue the requested task and report one
gap unless an independent product ambiguity or approval gate requires input.

## Establish the contract

Confirm the repository root, checkout, environment, task class, constraints,
authorities, and done condition. Read the root and nearest applicable
`AGENTS.md`, then only linked sources needed for the task. Preserve existing
names and conventions.

Read [authority-routing.md](references/authority-routing.md) when product,
delivery, implementation, environment, or provider authority must be resolved.
Read [project-profiles.md](references/project-profiles.md) when selecting a
primary profile or capability overlay.

Follow external trackers, documents, spreadsheets, and providers only when the
repository or user explicitly links or names them. Mark inaccessible state
`Unverified`; never copy secrets or private data into guidance.

## Activate

Check a selected user-level guidance file:

```bash
python3 scripts/manage_global_contract.py \
  --target <user-level-AGENTS.md> \
  --check
```

Install only after the user explicitly authorizes that target:

```bash
python3 scripts/manage_global_contract.py \
  --target <user-level-AGENTS.md> \
  --install \
  --confirm
```

Do not install hooks, automations, custom agents, or external integrations.

## Align

Run:

```bash
python3 scripts/align_repository.py \
  --root <repository> \
  --format <markdown|json>
```

Use `initialize` for a new Git repository and propose `upgrade` for an
established repository. Do not mutate during alignment. Ordinary tasks in an
aligned repository read local guidance without repeating a full audit.

Re-align on first entry, missing root guidance, or a material change to project
shape, authorities, tooling, architecture, release flow, or trust boundaries.
Do not add scheduled scans or a central portfolio registry.

## Audit or garden

Capture `git status --short --branch`, then run:

```bash
python3 scripts/inspect_repository.py \
  --root <repository> \
  --mode <audit|garden> \
  --format <markdown|json>
```

Follow repository-local links reported by the inspector and validate ambiguous
findings against the smallest live source. Apply the independent evidence
levels in [maturity-evidence.md](references/maturity-evidence.md); never
aggregate them into a score.

Generated reports, caches, coverage, snapshots, recordings, screenshots, and
test-result directories are not executable feedback. A check is `enforced`
only when CI executes the relevant command. Treat remote policies, deployments,
and provider state as `Unverified` unless inspected directly. Re-run Git status
and confirm read-only modes made no changes.

## Initialize

Read [repository-patterns.md](references/repository-patterns.md) and choose the
smallest justified tier:

- **small** — concise root agent map, profile, authorities, canonical commands,
  evidence boundaries, human gates, and done condition;
- **growing** — small plus an existing or justified architecture map and
  quality/review router;
- **large** — growing plus durable execution plans, scoped routing, direct
  runtime feedback, recovery, and justified enforcement.

Run:

```bash
python3 scripts/initialize_harness.py \
  --root <repository> \
  --tier <small|growing|large> \
  --confirm-new-repository \
  [--profile <profile>] \
  [--capability <overlay>] \
  [--authority <domain>=<reference>] \
  [--corroborating <domain>=<reference>]
```

Repeat capability and authority flags as needed. The initializer requires the
exact root of a Git repository, refuses conflicting or established projects,
preserves existing guidance, and is idempotent. Use the project-brief flags
together only when product intent is not already durable.

Validate with:

```bash
python3 scripts/validate_harness.py \
  --root <repository> \
  --format <markdown|json>
```

Review generated statements against the live repository. Never describe planned
components as implemented or create nested guidance, custom lint rules,
observability, or CI speculatively.

## Upgrade and operate

Audit first and close the first material capability gap at the lowest useful
layer. Preserve existing filenames and linked sources. Validate links and the
nearest affected command, then self-review the diff.

Use [runtime-legibility.md](references/runtime-legibility.md) only when static
checks cannot disprove acceptance. Use
[entropy-maintenance.md](references/entropy-maintenance.md) only after a
repeated failure or evidenced drift.

For ordinary implementation:

1. establish task class, authorities, scope, constraints, and done condition;
2. read the smallest live sources;
3. choose lightweight or durable planning based on risk and duration;
4. make the smallest reversible change;
5. run the closest focused validation, then only required profile-specific
   runtime, browser, deployment, or provider checks;
6. self-review and request one bounded independent review only for material
   runtime, data, security, authentication, migration, or release risk;
7. report implemented, local, browser, Preview, Production, provider, and
   unverified evidence separately;
8. encode repeated friction at the lowest durable layer.

Keep model routing, concurrency, and delegation in user configuration.

## Human gates and reporting

Stop for human approval before merge, Production or provider mutation, secrets
or privilege changes, destructive actions, material cost, or external
communication. Never equate local, browser, Preview, Production, or provider
evidence.

Finish with the selected mode, outcome, repository-local evidence, inherited
global safeguards, validation performed, one smallest improvement or
`No change needed`, and remaining unverified state.
