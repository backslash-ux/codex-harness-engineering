# Maturity Evidence

Assess each dimension independently. Do not total, average, rank, or convert the
result into a badge.

| Level | Required evidence |
| --- | --- |
| Absent | No repository-local evidence was found. |
| Documented | Versioned repository guidance describes the behavior. |
| Executable | A runnable command, test, script, or directly inspectable runtime surface implements the behavior. |
| Enforced | A supported CI invocation propagates the relevant check's failure, or a directly verified remote policy enforces it. Configured CI is distinct from a live result and a required merge gate. |

Inherited personal guidance can reduce operator risk but does not raise a
repository's portable maturity level. Report it in a separate
`Inherited global safeguards` section.

## Independent dimensions

### Context and repository knowledge

Look for concise `AGENTS.md` maps, authority by domain, linked sources of truth,
path routing, product contracts, project profiles, and canonical commands. File
presence without usable routing is weak evidence.

### Architecture and enforceable invariants

Look for a current-system map, trust boundaries, dependency direction, provider
interfaces, structural tests, and boundary checks. Do not describe planned
components as implemented.

### Verification routing

Look for change-type-to-check guidance and runnable focused checks. Count
enforcement only when CI invokes the relevant command.

### Runtime and worktree legibility

Look for repeatable startup, isolated worktree setup, directly queryable logs or
metrics, executable browser journeys, or other live feedback. Ignore stored
reports, screenshots, recordings, snapshots, and caches.

### Review and recovery

Look for self-review expectations, risk-based independent review, PR evidence
contracts, rollback or recovery steps, and resumable execution records.

### Governance and evidence boundaries

Look for repository-local approval gates, explicit external-source routing, and
separation of local, browser, Preview, Production, and provider proof. Remote
policies and linked external sources remain unverified until inspected directly.

### Maintenance and entropy control

Look for broken-link or freshness checks, ownership, debt tracking, completed
plan handling, repeated-failure capture, and CI-backed maintenance rules.

## Recommendation rule

Default to one improvement for routine alignment: the smallest change closing
the first material gap. For an explicitly comprehensive audit, report all
demonstrated material gaps with impact/effort priorities. Prefer guidance before mechanics. Recommend
a mechanical check only when the rule is objective, repeatedly violated, and
cheap to run. If no current gap justifies change, report `No change needed`.
