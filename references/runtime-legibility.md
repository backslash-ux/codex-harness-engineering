# Runtime Legibility

Add runtime feedback only when acceptance depends on behavior that static checks
cannot disprove.

Prefer, in order:

1. an existing focused unit or integration command;
2. an existing local startup and one critical journey;
3. isolated worktree startup when concurrent changes collide;
4. browser automation for real user-facing behavior;
5. queryable logs, traces, or metrics when they are necessary to evaluate the
   acceptance criterion.

Executable feedback means an agent can start, drive, query, or re-run it.
Generated screenshots, reports, recordings, snapshots, coverage, caches, and
historical logs are evidence artifacts, not executable feedback.

Keep environment evidence separate:

- local process and test results;
- browser-observed journey;
- Preview deployment;
- Production deployment;
- external provider receipt or state.

Do not install a telemetry stack or browser harness speculatively. Add the
smallest feedback loop that resolves a demonstrated verification gap.
