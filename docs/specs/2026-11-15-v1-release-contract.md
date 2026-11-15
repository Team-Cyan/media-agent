# Seed-agent 1.0.0 release contract

Status: approved objective, implementation/review pending in a fresh execution chat.
Plan: `docs/plans/2026-11-15-v1-release-closure.md`.

## Product promise

1.0.0 is the first stable milestone of the existing Docker-first self-hosted
product: resource discovery/acquisition, conservative downloader/seed operations,
Want List, operator UI and guarded media-library organization. Confirm each
supported capability from code and tests before documenting it as supported.
A stable milestone may retain clearly documented optional/best-effort features;
it cannot conceal supported-path safety defects or falsely promise all-provider
subtitle delivery. No new branding, cloud migration or broad feature expansion.

## Invariants

- Config remains portable and secret-reference based. No personal deployment
  config, credentials or runtime state enters GitHub or the shipped image.
- Preserve RSS fallback, downloader category authority, budgets and protected
  torrents. No live enqueue/prune/delete for release testing.
- Preserve SQLite/audit evidence and source files. Completion, media identity,
  parent attachment and selected source remain independent explicit facts.
- A mixed source directory is not authoritative movie/TV type evidence.
- Six confirmed featurettes stay attached; Joker 2 stays on selected 2160p,
  retaining 1080p. Do not switch sources during review or smoke tests.
- Never replay uncertain or historical scans, migrations, claims or submissions.
  Observe receipts/live state and preserve the single-writer boundary.
- Provider results, downloaded payload, published external subtitles, embedded
  coverage and downstream playback remain separate evidence categories.
- Preserve unrelated working trees and edits; integrate only understood changes.

## Required outputs

1. A repository-wide review coverage matrix and finding/disposition report.
2. Privacy/history/build-distribution audit scope, redacted findings and verified
   remediation; no known active exposed secret at release completion.
3. Current feature/support matrix and usable portable installation/upgrade docs.
4. Reconciled roadmap separating shipped 1.0 from proposed later minor/major work.
5. Consistent 1.0.0 metadata, reviewed main commit, immutable v1.0.0 tag, release
   notes, archival release branch and verifiable container publication.
6. Required checks passing at the relevant exact commit/tag, plus a substantive
   diagnosis of recurring historical CI failures and verified bounded fixes.
7. Explicit deployment status and honest remaining acceptance gaps.

## Release acceptance

| Area | Acceptance evidence |
| --- | --- |
| Work preservation | Initial dirty-work inventory and final reconciliation; no unrelated loss |
| Review | Every tracked subsystem covered; critical/high blockers resolved; lower risks dispositioned |
| Privacy | Current tree, reachable history, GitHub-visible release/build surfaces and shipped image audited; findings redacted and contained |
| Behavior | Full tests/lint plus focused meaningful regressions and Docker/Compose/hardlink/health checks |
| Documentation | Feature matrix matches implementation; stale handoff corrected; no fake completion claims |
| Publication | Tested SHA equals tag/release/OCI revision; GHCR tags and platform verified |
| CI | Exact-head required jobs pass; historical failures categorized with supporting run evidence |
| Operations | No unintended production/library/downloader mutations; production rollout stated separately |

A scanner's clean result is bounded evidence, not proof that no private data has
ever existed. An unavailable log or inaccessible surface must be reported as a
coverage gap. Genuine secret exposure requires concrete containment, not merely
removing the current literal. History rewrites and credential rotation retain
their own authorization boundaries.

## Out of scope and later versions

Do not complete all historical features merely to justify the version number.
Potential later work can include broader subtitle formats/archives and timing,
provider robustness, richer operations/client acceptance and additional adapters,
subject to actual roadmap review. Do not invent delivery dates or assign 2.0
without explaining the compatibility or architecture boundary. Do not implement
Codex Cloud migration or new external services as part of this release.
