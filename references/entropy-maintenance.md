# Entropy Maintenance

Garden when repository knowledge or patterns drift faster than ordinary task
work corrects them.

Read-only gardening may identify:

- broken repository-local links;
- unresolved template markers;
- stale markers with direct date or code evidence;
- duplicate or contradictory instructions;
- completed plans still presented as active;
- documented checks not invoked by CI;
- repeated local patterns that violate an existing invariant.

Do not infer semantic staleness from file age alone. Do not open cleanup work
for hypothetical inconsistency.

When implementation is requested, prefer a small correction to the source of
truth. Add a recurring or CI-backed check only after the same objective failure
has repeated and the check is stable, focused, and inexpensive. Human taste
belongs in guidance until it can be expressed as a clear invariant.
