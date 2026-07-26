# Project Profiles

Choose one primary profile and only the capability overlays demonstrated by the
repository. Profiles route attention and validation; they do not mandate files,
tools, infrastructure, or dependencies.

## Primary profiles

- **web-application** — browser-facing application, public site, CMS, or web UI.
- **service-or-worker** — API, scheduled process, queue consumer, integration, or
  background service.
- **library-or-cli** — reusable library, command-line tool, SDK, or focused
  developer utility.
- **native-application** — platform-native desktop or mobile application.
- **multi-surface-platform** — repository with multiple independently runnable
  apps, packages, services, or deployment surfaces.

## Capability overlays

- **user-interface** — require rendered behavior checks when static validation
  cannot prove acceptance.
- **persistent-data** — route schema, migration, authorization, backup, and
  recovery risks explicitly.
- **external-provider** — separate local adapter behavior from provider receipt
  or state.
- **background-jobs** — inspect queueing, retries, idempotency, leases, and
  observability where applicable.
- **deployable-runtime** — keep local, Preview, Production, and rollback evidence
  distinct.
- **sensitive-data** — surface privacy, tenant, authorization, retention, and
  redaction boundaries.

Infer only from concrete manifests, paths, configuration, or repository
guidance. If the repository is genuinely empty and no profile was supplied,
record the profile as not established and resolve it before substantial
implementation.
