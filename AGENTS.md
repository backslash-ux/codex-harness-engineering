# Codex Harness Engineering Repository Map

## Project identity

This repository publishes the `codex-harness-engineering` skills-only plugin and
the canonical `$harness-engineering` skill. The primary profile is
`library-or-cli`; the distribution has `deployable-runtime` and
`external-provider` capabilities.

## Authority map

| Domain | Primary authority | Corroborating source |
| --- | --- | --- |
| Product intent and acceptance | `plugins/codex-harness-engineering/skills/harness-engineering/SKILL.md` | `README.md` |
| Delivery commitments and work tracking | Explicitly named GitHub issues or release milestones | Current task plan |
| Current implementation | Git checkout at the repository root | Tests |
| Environment and release state | GitHub Actions, tags, and releases inspected directly | Local validation |
| External-provider state | GitHub API or rendered GitHub surface when explicitly in scope | Local Git state |

One authority never substitutes for another. Mark inaccessible provider state
`Unverified`.

## Repository map

- `.agents/plugins/marketplace.json` exposes the public Git marketplace.
- `plugins/codex-harness-engineering/.codex-plugin/plugin.json` defines the
  plugin identity and release version.
- `plugins/codex-harness-engineering/skills/harness-engineering/` is the only
  canonical skill source.
- `tests/` covers behavior and distribution contracts.
- `tools/` contains repository release validation and packaging.

## Canonical commands

Run the closest focused test first. Before release, run:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile \
  plugins/codex-harness-engineering/skills/harness-engineering/scripts/*.py \
  tests/*.py tools/*.py
python3 tools/validate_distribution.py
uvx ruff check \
  plugins/codex-harness-engineering/skills/harness-engineering/scripts \
  tests tools
```

Also run the installed OpenAI skill and plugin validators before packaging.

## Working rules

- Keep the public skill portable: no personal paths, project names, credentials,
  provider assumptions, or model-routing policy.
- Preserve existing CLI interfaces and advisory alignment semantics.
- Use a durable plan for release, migration, or trust-boundary changes.
- Self-review every change. Request one bounded independent review for runtime,
  data, security, migration, or release risk.
- Require explicit approval before merge, public repository creation, push,
  release publication, provider mutation, secrets, or destructive actions.

## Evidence boundaries

Keep implemented, locally verified, browser verified, Preview verified,
Production verified, provider verified, and unverified evidence distinct.
Never infer public release or provider state from local checks.

## Done condition

A change is complete when its focused tests pass, distribution validation
passes when packaging is affected, the diff contains no accidental or private
content, and the reported evidence matches what was actually verified.
