# Cron Scheduling

The 1.2 development line adds one-line Jenkins-style Cron controls. This feature
is not part of the deployed 1.1.0 image until a separate publication and upgrade.

## Five Business Schedules

| Task | Configuration | Automatic work |
| --- | --- | --- |
| PT discovery/acquisition | `scheduler.cron` | Discovery, ranking, expiry protection and enqueue |
| Routine seed maintenance | `scheduler.maintenance_cron` | Tracker backfill and routine cold-seed/capacity cleanup |
| Want workflow | `scheduler.intent_search_cron` | Source synchronization, search and configured acquisition |
| Media inventory | `media_import.scan_schedule` | Observe source files and update inventory |
| Media background window | `media_import.background_schedule` | Pending media analysis/import, interrupted publication recovery, reconcile, posters and subtitles |

The Scheduler page exposes the first three independent Cron controls. The Media
Library page exposes inventory and background controls. Each input has inline
help, explicit IANA timezone and future matching times. The background control
also shows `window_minutes` (1..1440, default 120) and the next window end.
Previews do not submit tasks, traverse media roots or contact providers.

PT, maintenance and Want have independent clocks but run serially under the same
scheduler lease. Disabling PT does not disable valid Want/maintenance schedules.
A co-due wake may run several tasks; each records claim and outcome evidence.
An unrelated task error does not discard a due Want opportunity. A failed expiry
protection phase still fences PT acquisition. Explicit manual full-cycle requests
retain their existing override semantics and do not grant new mutation authority.

Saving uses the existing revision-checked API and does not immediately execute a
past slot. Invalid strings (including `-` and an explicit empty string) disable
the associated automatic business task. Invalid timezones are rejected.

```yaml
scheduler:
  cron: "-"
  maintenance_cron: "-"
  intent_search_cron: "-"
  timezone: Asia/Shanghai
media_import:
  enabled: false
  scan_schedule:
    cron: "-"
    timezone: Asia/Shanghai
  background_schedule:
    cron: "-"
    timezone: Asia/Shanghai
    window_minutes: 120
```

All five checked-in example schedules are disabled. Production config is not
rewritten. Omitted/null fields preserve compatibility:

- Main Cron absent: keep the legacy PT interval. Independent Want/maintenance
  wakes do not postpone that PT deadline.
- Maintenance Cron absent: inherit PT cycles, including their stable H identity.
- Want Cron absent: retain daily/every-cycle synchronization/search/retry behavior
  within PT cycles.
- Inventory schedule absent: retain `media_import.interval_seconds`.
- Background schedule absent: retain continuously available automatic media work.

Untouched legacy fields remain absent/null when unrelated settings are saved.

## Background Window Semantics

A window starts at its Cron slot and ends after `window_minutes` of elapsed time.
For `0 3 * * *`, Asia/Shanghai and 120 minutes, automatic work can be admitted
from 03:00 until 05:00. Delayed observation, restart or reload cannot extend that
end. New/changed settings activate when first observed; they do not reopen a
window whose slot predates activation. Overlapping windows intentionally permit
continuous eligibility.

Inventory remains independent: all configured source inventories complete before
background processing is considered. A closed window prevents automatic recovery,
pending publication/import, reconciliation, poster and subtitle operations, even
when inventory is due. Jobs remain durable until a later window. Before each new
bounded operation the worker checks the window and queued commands; an already
admitted operation may finish safely rather than being killed at the boundary.

Manual commands override only their explicit action: manual scan retains its
scan/import behavior; manual subtitle work does not start poster processing or
open the general automatic window. Existing quotas, retry deadlines, root/config/
epoch fences and single-writer leases remain active.

## Expressions

The five fields are **minute hour day-of-month month day-of-week**. Sunday is
0 or 7. Numeric lists, ranges, `*`, `/` steps and Jenkins-style `H` are supported.
`H` uses a stable distinct identity for each task; its exact values need not match
an unrelated Jenkins job. Day-of-month and day-of-week are conjunctive when both
are specified. Seconds, years, `@` aliases, random `R`, multiline expressions,
`TZ=` prefixes and plugin extensions are not supported.

| Example | Meaning in the configured timezone |
| --- | --- |
| `0 * * * *` | Every hour at minute zero |
| `0 3 * * *` | Daily at 03:00 |
| `0 3 * * 0` | Sunday at 03:00 |
| `0 3 1 * *` | First day of each month at 03:00 |
| `H * * * *` | A stable minute of every hour |
| `H/15 * * * *` | Stable minute offsets at 15-minute steps |
| `-` | Automatic execution disabled |

A month without the selected date is skipped. Nonexistent daylight-saving local
times are skipped; repeated local times execute only at their first occurrence.
An expression without a possible date within the bounded eight-year search is
disabled. Jobs run when the process observes a due slot, not with a real-time
latency guarantee. New/changed schedules activate when observed and do not
immediately catch up an older slot. Media attempts persist their checkpoint so a
failure or restart cannot repeatedly replay a claimed slot. PT/maintenance/Want scheduling
restarts wait for future slots. Long work is not run concurrently to catch up every
missed slot. Explicit manual scans bypass the legacy interval gate.

## Freeleech Admission

For scheduled PT acquisition, a finite promotion must remain valid **strictly
past the second upcoming main scheduler slot**. This reserves one failed-cycle
buffer. The required minimum is the greater of the configured safety floor and
the remaining time to that second slot plus a one-second boundary margin, rounded
up to minutes. Month lengths, skipped dates, timezone and `H` use the same parser
as execution. It is not computed as twice the time to the first slot.

For example, at Monday 10:00 with daily 03:00, the next slots are Tuesday 03:00
and Wednesday 03:00. A promotion expiring Tuesday evening is rejected. The horizon
is refreshed before deferred-link token acquisition and before each downloader
add; elapsed time since the free-window observation is deducted. Finite scheduled
Cron candidates also require enabled expiry protection and existing mutable/delete
authority for the actual target category. A default-category switch or permission
revocation during the batch rejects acquisition. Missing future slots or unknown
expiry fail closed. Existing authoritative M-Team unlimited
promotion evidence follows its refreshed preflight path. This is an admission
buffer, not a guarantee of download speed or completion.

Every configured PT cycle retains a separate expiry-only protection phase even
when routine maintenance is not due. That phase covers at least the next real PT
protection slot plus the boundary margin and existing floors. For a daily cycle,
remaining six hours cannot be treated as safe merely because the old interval
floor is two hours. This calendar threshold is confined to the existing managed,
incomplete billing-risk classification, with a fresh state/category recheck.
It cannot select completed cold seeds or general capacity candidates. Routine
maintenance keeps its own thresholds; it does not receive the acquisition or
calendar expiry horizon. The omitted-field legacy interval path remains compatible.

Stored Want releases currently lack trustworthy fresh promotion timestamps.
Cron-driven automatic Want acquisition therefore rejects free/2xfree releases
before token acquisition until fresh evidence is available. Nonfree Want releases
and explicit/manual intent actions retain their existing contracts; they must not
be advertised as covered by scheduled PT freeleech admission.

## Disk Sleep And Safety Loops

The inventory Cron and explicit background window concentrate automatic media
work, but do not guarantee disk spin-down. Configuration/path canonicalization can
still resolve media paths; runtime state placement, playback, downloaders and other
services may access disks. A database-only pending-work gate avoids unnecessary
media health checks when no work is actionable.

Heartbeat, health, lease renewal, provider backoff, queue polling and the existing
qB capacity/error guard remain internal safety loops. The guard stays available
between business tasks, including when automatic full cycles are disabled; its
existing mutation authority and prune setting still apply. Put runtime state on
SSD when mechanical-disk sleep matters and verify actual I/O independently.

Syntax references: [Jenkins](https://www.jenkins.io/doc/book/pipeline/syntax/#cron-syntax)
and the [croniter parser](https://github.com/pallets-eco/croniter).
