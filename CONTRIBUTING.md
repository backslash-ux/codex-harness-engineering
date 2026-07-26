# Contributing

Contributions should improve a demonstrated repository workflow without turning
process into the product.

## Before opening a change

1. Describe the repository category and concrete failure or gap.
2. Prefer the smallest reusable improvement over project-specific policy.
3. Preserve advisory alignment, repository-local implementation authority, and
   distinct local, browser, Preview, Production, and provider evidence.
4. Do not add hooks, telemetry, custom agents, external integrations, or
   enforcement without a demonstrated need and explicit scope.

## Validate

Run:

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

For behavior changes, add the smallest fixture that demonstrates the changed
requirement or regression. Documentation-only changes do not require tests when
the existing validation is sufficient.

By contributing, you agree that your contribution is licensed under the MIT
License that covers this repository. No contributor license agreement is
required.
