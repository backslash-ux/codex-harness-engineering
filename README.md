# Codex Harness Engineering

A portable Codex skill for making software repositories easier for agents and
humans to understand, change, verify, and maintain.

It turns harness engineering into a practical repository-alignment protocol:
start with the smallest useful contract, keep implementation knowledge
repository-local, follow external authorities only when explicitly linked, and
separate local evidence from Preview, Production, and provider evidence.

## What it does

The `$harness-engineering` skill supports six mutually exclusive modes:

- `activate` checks or explicitly installs the user-level alignment rule.
- `align` performs an advisory, read-only first-entry assessment.
- `initialize` creates the smallest suitable contract for a new Git repository.
- `audit` reports seven independent evidence dimensions without scoring them.
- `upgrade` makes one explicitly authorized, sustainable improvement.
- `garden` finds demonstrated drift in guidance, links, plans, and enforcement.

It supports web applications, services and workers, libraries and CLIs, native
applications, and multi-surface platforms. Capability overlays route attention
to UI, persistent data, external providers, background jobs, deployable
runtimes, and sensitive data without imposing speculative tooling.

## Requirements

- Codex with skill support
- Git
- Python 3.10 or newer

The skill has no runtime Python dependencies and installs no hooks, telemetry,
custom agents, automations, or external integrations.

## Install the standalone skill

Ask Codex:

```text
Use $skill-installer to install harness-engineering from
backslash-ux/codex-harness-engineering at
plugins/codex-harness-engineering/skills/harness-engineering, ref v1.0.0.
```

Start a new Codex task after installation if the skill does not appear
immediately.

## Install the plugin

Add the tagged Git marketplace and install the skills-only plugin:

```bash
codex plugin marketplace add \
  backslash-ux/codex-harness-engineering \
  --ref v1.0.0

codex plugin add codex-harness-engineering@backslash-ux
```

The plugin and standalone installation expose the same canonical
`$harness-engineering` skill.

## Use it

```text
Use $harness-engineering to align this repository.
```

```text
Use $harness-engineering to audit this repository without changing it.
```

```text
Use $harness-engineering to initialize a small library repository.
```

Alignment is advisory. It never independently blocks the requested work.
Existing ambiguity, security, release, provider, destructive-action, and human
approval gates still apply.

## Develop and validate

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

Build the deterministic plugin archive with:

```bash
python3 tools/package_release.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution expectations and
[SECURITY.md](SECURITY.md) for private vulnerability reporting.

## Acknowledgements

This independent community project was inspired by Ryan Lopopolo's OpenAI
article,
[Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/).
It is not affiliated with or endorsed by OpenAI.

## License

[MIT](LICENSE)
