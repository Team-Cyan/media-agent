# Roadmap

Version groups are planning targets, not dates or commitments. Code and tests own
implementation facts; deployment, corpus coverage and client acceptance are separate.

## Current Stage — 1.2.1 Published, Production Upgrade Pending

The v1.1.0 rename, single-container publication, controlled Unraid deployment and
explicitly authorized predecessor cleanup are complete. The current target stayed
healthy; the post-cleanup DockerMan template audit reported zero issues. Recovery
templates and backups remain; removed container IDs require recreation rather
than restart. See the [release review](reviews/2026-11-16-single-container-review.md).
The 1.1 release scope is closed. The published 1.2.1 release adds UI Cron
controls and second-future-slot freeleech protection; production remains on 1.1.0
pending upgrade.
The candidates below require a new scope decision; remaining corpus/client
acceptance limits are not claimed complete.

## Shipped 1.0

- Docker-first image, Compose and Unraid templates, configurable runtime identity,
  role health, CLI and operator Web console.
- RSS fallback and M-Team discovery/enrichment; Torznab intent search; explainable
  scoring, deferred download-token resolution and tracker backoff.
- qBittorrent reference adapter and contract-tested Transmission adapter;
  category-bound cleanup, add-only media categories, budgets and execute gates.
- Want List source ingestion, identity aliases, ranking/rejection/selection,
  persistent search cadence and enqueue claims shared by CLI/Web/scheduler.
- SQLite lifecycle state, scheduler leases, redacted audit/runtime events,
  backup/restore controls and bounded operational read models.
- Mixed-source movie/TV/animation routing, independent completion/identity facts,
  reviewed hardlink publication, explicit extras attachment and source variants,
  stale source/epoch/target fencing and lost-response reconciliation.
- Optional subtitle discovery with quotas and payload validation; reviewed local
  SRT staging/preview/import; subtitle progress distinguishes discovery, payload,
  publication and embedded evidence.

The last recorded pre-1.0 controlled deployment verified a finite media cohort,
retained all originals, published reviewed extras and local SRTs, and retained an
alternate without changing the selected source. This is bounded evidence, not
approval of future imports or proof of complete subtitle/client acceptance.
Private corpus identities, counts and receipts belong in ignored runtime evidence.

## 1.0.1 Subtitle Correction

Automatic top-five full-subtitle selection was published in 1.0.1: exact work/language candidates no longer require identical
release filenames; real cue timing and text checks gate automatic publication.
Five is a hard automatic cap, with quotas, deduplication and existing identity
fences retained. The immutable 1.0.0 release remains unchanged.

## Shipped 1.1: Single-Container Rename

The product is now `media-agent`. One supervisor runs Web, scheduler and the
configured media worker; legacy CLI/import names, environment keys, metrics and
`.seed-agent` state paths remain compatible. Publication and controlled single-container deployment passed; verification and
client acceptance limits remain separate in the versioned review.

## Shipped 1.2.1: Cron Controls

- Shared Jenkins-style five-field Cron with stable H, timezone, inline UI help and
  future execution previews for five business schedules: PT, routine maintenance,
  independent Want, media inventory and media background windows.
- Invalid expressions disable automatic tasks; checked-in defaults are disabled,
  with existing production configurations and legacy schedules preserved.
- Finite scheduled PT acquisitions cover the second future protection cycle;
  fresh checks bind the actual target category before token and each add.
  Expiry-only protection covers the next real check without broad cold-seed cleanup.
- Media inventory is separate from window-bound processing and publication.
- Plan and code review findings are resolved; exact-source CI: 1514 passed, 1 skipped.
- Existing health, queue, retry and capacity guards remain internal safety loops.
- Health observation captures the clock after the state snapshot while retaining
  rejection of genuinely future timestamps.
- See [contract and limits](operations/cron-scheduling.md). Production deployment
  remains pending.

## Candidate Acceptance And Operations

- Broader fake-provider/downloader scheduler-cycle and Web preview integration
  coverage beyond the existing phase-order, run-ID and state-transaction tests.
- Evidence-led client library visibility, subtitle selection/timing and playback
  acceptance; a reproducible representative corpus rather than global claims.
- Real-provider Want List ID/title/year/season/episode acceptance where credentials
  and explicit acquisition scope are available.
- Richer read-only operations/audit summaries, tracker edit diff previews and
  focused mobile/accessibility improvements.
- Read-only joined upload/headroom analysis before tuning retention or eviction.

## Candidate 1.3: Provider And Media Robustness

- Additional subtitle archive/format support, numbering/sync/retiming review and
  provider failure/quota handling after measured corpus evidence.
- Better source-adapter export compatibility and additional downloader/provider
  implementations behind current contracts.
- Further bounded recovery and scheduling coverage, with single-writer and
  reservation/race evidence before parallelizing mutations.

No automatic RAR extraction, automatic retiming, universal provider delivery or
whole-library playback acceptance is promised by 1.0.

## Potential 2.0: Compatibility Decisions Required

- A broad plugin/kernel architecture or changed state/config API could justify a
  major release only with a concrete compatibility/migration contract.
- Multi-user remote administration would require an explicit authentication,
  authorization and deployment redesign; the current trusted-operator console
  does not promise this boundary.

These are options, not selected implementation work. Cloud migration, a dashboard-first rewrite and browser-login strategy remain
outside this release.

## References

- [Support matrix](../README.md#verification-and-limits)
- [Media contract](ai/modules/media-import.md)
- [Provider kernel research](specs/2026-07-06-provider-kernel-roadmap.md)
- [Historical integration plan](plans/2026-10-24-media-product-delivery.md)
- [1.0 closure](plans/2026-11-15-v1-release-closure.md)
