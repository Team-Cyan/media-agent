# Session Handoff

## Current Stage: 1.2.1 Published, Upgrade Pending

The selected rename, release, deployment and cleanup scope is complete. No new
feature work is implied by that closure. A subsequent authorized 1.2 milestone
implements five UI business schedules and second-slot freeleech safety in published
v1.2.1; production remains on 1.1.0 and its configuration is unchanged. See the Cron scheduling
contract and roadmap. Independent plan/code reviews resolved expiry-threshold,
multi-source inventory/window, legacy PT starvation and target-category hot-change
findings. Exact-source CI passed: 1514 tests, 1 skipped; local browser save/preview
verification passed. A later deployment attempt produced a validated backup.
DockerMan created the candidate, but the runtime boundary check prevented startup.
The original pinned image and template were restored. Before another deployment,
identify why DockerMan recreation differs from the original runtime boundary.
Do not replay historical migration commands.

The stable milestone published v1.0.0 at `7c815ca` after exact-revision CI.
The archival branch is `release/1.0`; the original dirty work remains preserved.
A documentation-only main follow-up records publication and historical CI receipts.
The 1.0.1 subtitle fix was also published at `f5e2205`. The 1.1.0 release at `309f1af` renames media-agent and unifies the container while
retaining state and legacy integration contracts. Exact-source CI, both platform
publication and the controlled single-container rollout passed. On 2026-11-17,
explicitly authorized cleanup removed the two stopped original containers and their
unused legacy image. Their DockerMan templates were archived, with application
state, media and recovery backups preserved. Recovery now requires recreating
the old roles from saved templates and pinned digests; old container IDs cannot
be restarted. The current target remained healthy and the template audit found
zero issues. Package Write access was repaired with explicit
approval and failed publication attempts remain retained. Consult the [rename contract](../specs/2026-11-16-single-container-rename.md)
and current versioned review for publication/deployment verification.
Use [closure plan](../plans/2026-11-15-v1-release-closure.md),
[release contract](../specs/2026-11-15-v1-release-contract.md) and
[review report](../reviews/2026-11-15-v1-release-review.md) for the current outcome.
The initial phase-1/phase-2 branch instructions formerly here are historical and
must not be used to select current code or replay live actions.

## Product And Deployment Boundaries

The shipped functions and verification levels live in the README support matrix;
the versioned roadmap records remaining acceptance and proposed work. Production identity must be read from the typed controller; publishing a release
does not upgrade that host.
Its finite media cohort was reconciled with originals retained, explicit extra
attachments and a retained alternate. Do not switch the selected source or replay
scans/migration/recovery writers from old instructions. Corpus details and receipts
are private local evidence. Subtitle provider results, available payloads, published
files, embedded coverage and downstream playback are distinct facts.

## Preservation

The original checkout and other worktrees contain unrelated work. The release owner
recorded each dirty path and disposition in ignored local release evidence. Old
harness/documentation proposals remain preserved for separate review; previously
integrated identity/hardlink changes must not be reapplied over newer code.
No open PR existed at initial inventory; prior PRs were merged.

## Safe Continuation

Read the current Git refs and exact-head checks before any new commit/tag action.
Keep `.seed-agent/state.db`, its access locks and audit evidence durable. Use the
[upgrade guide](upgrade-and-recovery.md) for backups and versioned replacement.
Production writes require the owning homelab typed controller, reviewed preview,
backup and rollback; release checks use isolated fixtures and containers.
