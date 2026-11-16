# Media-agent rename and single-container contract

The authorized 1.1 change renames seed-agent to media-agent and supervises Web,
scheduler and the configured media worker inside one Docker container. The old
media-agent repository is archived separately; it is never deleted or imported.

## Compatibility and safety

- `media-agent` and `seed-agent` commands share the same CLI; `seed_agent.*`
  imports resolve to canonical `media_agent.*` module objects, preserving model,
  exception and monkeypatch identity. Legacy environment keys, metrics, Web token
  header, state/audit/config paths and queue semantics remain unchanged.
- `app` is the unified mode. Legacy explicit scheduler, Web and media role modes
  remain available. A media-only role cannot use app to gain seed execution.
- The supervisor starts scheduler, optional Web, and media worker only when media
  is enabled. Any child exit fails the container; SIGTERM/SIGINT reach all owned
  process groups, with a 15-second grace then forced cleanup. Container stop grace
  must exceed this. Enabling media or Web requires an intentional container restart.
- Health checks are read-only and combine enabled role and Web evidence. Independent
  seed/media databases and worker/scheduler leases remain authoritative. One shared
  container does not provide per-process credential or filesystem isolation.
- One common media mount preserves the existing hardlink model; no copy fallback,
  source deletion, rescan, schema reset or old command replay is part of migration.

## Release and production gates

Run full tests, Ruff, hygiene, dependency audit, Compose validation and candidate
Linux image lifecycle/hardlink/health checks before publication. Verify exact
main/tag/OCI identity and both supported architectures. Keep 1.0 tags immutable.

Use only the homelab-agent typed migration controller for the production change.
Bind live source IDs, all template/config hashes, immutable image and deterministic
candidate XML. Preserve source containers stopped for rollback, backup durable
state/templates/autostart, fence single writers, reconcile exclusive phase receipts
before retry, verify actual supervisor children and health. Rollback stops the
owned target before restarting the preserved sources and never blindly restores a
potentially stale database backup. Deployment and client acceptance are separate.
