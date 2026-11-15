# Upgrade And Recovery

Use a version tag and verified immutable image digest. A registry publication does
not upgrade a host. Apply the same image digest to seed and media roles.

## Before Replacement

1. Read the target release notes and current configuration guide. Record current
   image digest, version, role configuration and mounted state paths privately.
2. Stop all seed/media/Web writers. Preserve config, secrets, state, audit and
   database sidecars together with their permissions; do not delete WAL/SHM files
   from an open database or copy only an open main DB file as a backup.
3. Use the prior image's `state-backup --config <config> --output <backup>` and
   `state-backup-verify --backup <backup>` for seed state. Use
   `media-state-backup --config <config> --output <backup>` for media state.
   Keep receipts/digests with private backups outside the container layer.
4. Test the replacement on copies with isolated fixture paths. Healthcheck and
   read-only views are the first checks; scans, recovery and migrations can write.

## 1.0 Compatibility

The 0.29.2 media schema is version 5. The 1.0 milestone adds no media-schema reset
or mandatory replay. A schema-5 deployment must not rerun schema-4 migration.
Older media schema-4 installations require the explicit offline v5 migration,
verified backup hash and store epoch described in the media guide; do not let a
new image initialize replacement empty state. Other older installations must
review intervening release notes before upgrading.

Seed state follows the existing additive StateStore migrations. 1.0 also fixes
permission enforcement so concurrent SQLite connections keep native file locks;
this does not diagnose earlier operational failures. Existing private-file and
runtime-identity requirements remain in force.

## Replacement And Verification

Set the verified digest in the host's deployment configuration, validate Compose
or the Unraid template, and replace using that platform's normal update path.
On Unraid use DockerMan/ComposeMan through the owning controller. Check actual
version/revision, both role health results and read-only state counts before
resuming scheduled writes. Never enqueue/prune or import production media merely
to test a release. Inspect failed health evidence before retrying writers.

## Rollback

Keep the old image and backup until acceptance. Stop every writer before rollback.
An image downgrade alone does not reverse a schema change: restore the verified
matching state/config backup through the documented restore preview and execute
workflow. Preserve newer evidence separately; do not overwrite it blindly.
Media restore changes its epoch and invalidates stale queued previews/claims.
Re-preview deliberate operations after restore. Avoid replaying uncertain external
mutations; reconcile receipts and downloader state first.

## First Evaluation

Use `config/example.yaml`, placeholder credentials and an isolated workspace.
The Compose example is an operator deployment template: it enables scheduled
execution, so review `SEED_AGENT_EXECUTE`, pruning and media import policy before
starting it. Set execute false for initial evaluation and leave optional providers
unconfigured. Configure the Web token and a trusted network/reverse proxy before
exposing the operator console. See the Web guide for its exact token boundary.
