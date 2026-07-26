# Authority Routing

Record authority by domain instead of forcing one system to govern the whole
project.

| Domain | Primary authority establishes |
| --- | --- |
| Product intent and acceptance | Intended behavior and acceptance criteria |
| Delivery commitments and work tracking | Owners, priority, state, dates, and commitments |
| Current implementation | What the checked-out, versioned source currently implements |
| Environment and release state | What is configured or deployed in a named environment |
| External-provider state | What the external system accepted, delivered, or currently reports |

Use one primary authority and optional corroborating sources for each applicable
domain. Omit inapplicable domains. Keep implementation authority as the Git
checkout at the repository root.

Follow external sources only when the repository or user explicitly links or
names them. Accept files, repository documents, trackers, Docs, spreadsheets,
and provider surfaces as references, but do not copy secrets, credentials,
private data, or large external documents into repository guidance.

Do not silently merge same-domain conflicts. Prefer an explicit freshness,
approval, or precedence rule already recorded by the project. Otherwise surface
the conflict and ask only when it materially changes the requested task.
Inaccessible external sources remain `Unverified`; incomplete alignment is
advisory and does not itself block unrelated work.
