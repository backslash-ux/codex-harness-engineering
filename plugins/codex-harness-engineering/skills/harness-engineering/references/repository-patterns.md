# Repository Knowledge Patterns

Use the repository's existing structure and vocabulary. These tiers describe
capabilities, not mandatory filenames.

## Small

Use a concise root `AGENTS.md` as the map:

- primary project profile and demonstrated capability overlays;
- authority by domain, with implementation rooted in the Git checkout;
- project layout and source of truth;
- canonical local commands;
- hard constraints and approval gates;
- focused verification and done condition.

Add a project brief only when product intent is not already durable. Do not add
nested guidance, a plan system, custom checks, or runtime infrastructure.

## Growing

Add an architecture map when the repository has multiple domains, services,
data stores, trust boundaries, or provider integrations. Add a quality/review
router when different change types require materially different checks.

Link these sources from `AGENTS.md`. Keep the map concise and factual. Prefer
existing names such as `SYSTEM_MAP.md`, `CONTRIBUTING.md`, or `docs/testing.md`
over introducing parallel documents.

Follow external sources only when the repository or user explicitly links or
names them. Record the reference and evidence boundary without copying the
external system into the repository.

## Large

Add only the capabilities justified by real scale or repeated friction:

- path-to-context routing and scoped guidance;
- structural boundary and documentation freshness checks;
- durable execution plans with decisions, progress, validation, and recovery;
- reproducible worktree setup;
- direct runtime feedback for critical journeys;
- recovery checkpoints and debt/entropy maintenance.

Nested guidance, custom linters, observability, and CI checks are conditional.
Use demonstrated repository needs to justify them; do not copy another project's
structure without an applicable requirement.

## Lowest useful layer

When a failure repeats:

1. fix the immediate task;
2. record the missing fact or workflow in the nearest repository source;
3. add a mechanical check only if the invariant is objective and enforceable;
4. change a reusable skill or global guidance only when the lesson generalizes
   across repositories.
