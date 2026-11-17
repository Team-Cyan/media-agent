# Independent Business Task Schedules

Status: completed locally after independent plan/code review and verification. Production remains unchanged.
Scope builds on the uncommitted 1.2 Cron feature; preserve all existing work.

## Intended outcome

Expose five understandable business schedules with inline Cron help and previews:

1. PT discovery/ranking/acquisition: `scheduler.cron`.
2. Routine tracker backfill and seed maintenance: `scheduler.maintenance_cron`.
3. Want source synchronization/search/acquisition: `scheduler.intent_search_cron`,
   truly independently due from PT discovery.
4. Media inventory: existing `media_import.scan_schedule`.
5. Media background processing window: `media_import.background_schedule`, using
   the same `{cron, timezone}` expression plus `window_minutes` (default 120,
   bounded 1..1440). It covers automatic pending-video work, poster/metadata and
   subtitle work; this window may start without running inventory.

## Compatibility and defaults

New fields absent/null retain existing deployment behavior. In particular absent
maintenance inherits the PT cycle, absent Want Cron retains legacy daily/every-cycle
behavior within PT cycles, and absent media background schedule leaves automatic
background work available as before. Checked-in examples explicitly use invalid
Cron `-` for every automatic business schedule. Invalid explicit expressions disable
the corresponding automatic task. No production configuration, tag, image or
release is modified by this task. Keep local version 1.2.0.

## Execution boundaries

One scheduler process and its existing lease serialize PT, routine maintenance
and Want tasks. Independent clocks do not create concurrent acquisition writers.
A due set may coalesce tasks in one run; record per-task claimed/completed/failed
evidence and isolate independent task errors (expiry failure still fences PT
acquisition). A Want-only or maintenance-only wake
must not discover/enqueue PT seeds. With PT disabled, valid Want/maintenance Cron
still wakes and executes its own task. Saving/observing a changed expression does
not execute a past slot. Missed slots collapse; claimed failures are not replayed
in a tight loop. Existing manual full-cycle triggers remain explicitly scoped and
available. Phase/status evidence identifies which tasks actually ran.

Media inventory observes new files at its own clock; it must not automatically
run enrichment or pending publication outside an explicit background window.
Split inventory from Engine.scan embedded recovery/process_pending/reconcile,
not merely the later enrichment flag. Background work uses the existing command
queue, leases, quotas and bounded batches. Window end is the original Cron slot
plus duration; late observation, restart or config reload never extends it.
Do not abruptly terminate file publication or HTTP requests at window close;
finish an already admitted bounded operation, then stop admitting more automatic
work. Manual queued actions remain explicit overrides for their own action only.
Persist activation/window information with existing supported operational evidence;
no schema migration or replay of uncertain commands. Disabled or closed windows
must not call automatic poster/subtitle providers or progress pending media work.

## Freeleech and cleanup safety

Admission must cover strictly beyond the second future opportunity that really
runs free-expiry protection, plus existing configured floors. Initially retain
PT-cycle expiry protection and make that protection an explicit phase of every PT
cycle, even when routine maintenance is separately scheduled. The expiry-only phase must cover at least the next real PT protection slot,
including the boundary margin. For example, daily PT with a 54-hour promotion
must not keep an incomplete download merely because six hours remain at its
second check while the old interval floor is only two hours. Calendar protection
applies only through existing managed incomplete billing-risk rules; never pass
that horizon into general cold-seed/capacity cleanup. Routine cold-seed
cleanup/backfill follows maintenance Cron. This keeps the second PT Cron horizon
truthful; the capacity/error guard remains an additional safety mechanism, not
an assumed substitute. If expiry protection cannot execute because pruning or its
necessary authority is disabled, reject finite automatic seed acquisition rather
than claiming a future cleanup guarantee. Existing category/HR/manual/media
protection remains unchanged; no broader deletion authority is introduced.

Recompute horizon and current configuration before token and each downloader add.
Authoritative unlimited free evidence retains existing semantics. Automatic Want
free acquisition without fresh promotion evidence stays fail-closed. Maintenance
retains its own thresholds; calendar expiry-only work cannot select completed
seeds or turn into ordinary cold-seed cleanup.

## UI and documentation

Show PT, routine maintenance and Want Cron separately on Scheduler. Show inventory
Cron and background window together on Media Library. Include explicit IANA zones,
help and next-two previews with distinct stable H identities. Background controls
show duration and explain boundary behavior and manual overrides. Remove the old
Want-dependent-on-main wording when independence is actually implemented.

## Verification

- Main clocks: PT disabled/Want enabled; PT disabled/maintenance enabled; co-due
  tasks serialized; no unintended phase; startup/change/restart/missed-slot
  behavior; legacy interval and manual trigger compatibility; waiting heartbeat.
- Finite free-seed horizon still uses the actual expiry-protection phase; invalid
  schedule or unavailable protection rejects acquisition before token/add;
  routine cleanup cannot broaden deletes or use the acquisition horizon.
- Media: closed/invalid background window suppresses automatic providers/pending
  jobs; inventory independent; background-only wake; opened window persists across
  restart and expires; manual actions stay action-scoped; admitted batch finishes.
- UI/config roundtrip, future previews/H/timezone, disabled checked-in defaults,
  existing legacy-field preservation and local browser verification.
- Targeted tests, complete repository suite, Ruff, JS parse, public hygiene, links.

## Limits

Cron/window control is not a guarantee of disk spin-down: config/path resolution,
health/state placement, playback, downloads and other services may touch storage.
Heartbeats, lease renewal, queue polling, provider backoff and capacity/error guard
remain internal safety loops. No live rollout or permission expansion is implied.

## Review record

Independent read-only review identified the protection-threshold counterexample
and confirmed scan/publication coupling. Both are mandatory acceptance cases.
Independent task failure isolation and fixed slot-based window end are included.
No remaining plan blocker was identified after incorporating these corrections.

## Execution outcome

All five business schedules and UI/config roundtrips are implemented. Independent
plan/code review findings were fixed with regressions: expiry-only next-check
threshold, two-phase multi-profile inventory at window close, legacy PT deadline
starvation, disabled maintenance at startup, and actual-category authority during
configuration changes. Co-due task isolation and waiting guard/heartbeat behavior
are covered. Full suite: 1513 passed, 1 skipped; Ruff, JS parse, repository hygiene
and local browser window save/time previews passed. Private verification artifacts
remain under ignored local runtime evidence. No commit, publication or production
operation was performed.
