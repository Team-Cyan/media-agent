# Project Overview

## What `media-agent` Is

`media-agent` is a Docker-first PT automation app for personal NAS and homelab
deployments.

It is:

- a Docker image and Compose-oriented runtime,
- a config-first strategy runner,
- a CLI and Web operator tool,
- an auditable automation layer over PT discovery and downloader actions,
- an intent-driven acquisition and guarded media-organization product.

It is not:

- a full MoviePilot clone,
- a general media server,
- a browser-login automation project.

## Product Shape

The single-container supervisor runs acquisition/seed, Web and configured media roles
as independent child processes. Existing CLI role modes remain compatible:

1. PT upload strategy loop
   - discover candidates,
   - score them,
   - enqueue them to the configured downloader,
   - review managed torrents,
   - prune cold managed torrents,
   - record audit decisions.

2. Resource intent loop
   - ingest or add intents,
   - sync configured Douban, IMDb, Letterboxd, and Telegram Want List sources,
   - merge repeated wants by reliable external ID aliases,
   - search candidate releases,
   - rank releases,
   - reject unwanted choices,
   - enqueue an explicit candidate for ambiguous choices,
   - enqueue the chosen result through the same downloader path.

3. Media organization loop
   - independent completion and metadata identity evidence,
   - reviewed hardlinks, explicit extras and retained source variants,
   - optional provider subtitles and reviewed local SRT publication,
   - durable worker commands, health, identity fencing and recovery.

See the README support matrix for verification levels and acceptance gaps. The Web
console is a supported operator surface, with a trusted deployment boundary.

## Core Runtime Surfaces

- CLI: `src/media_agent/cli.py`
- Docker image: `Dockerfile`
- Container entrypoint: `docker/entrypoint.sh`
- Publish workflow: `.github/workflows/docker-publish.yml`
- Config: `src/media_agent/config.py`
- Models: `src/media_agent/models.py`
- State store: `src/media_agent/state.py`
- Audit: `src/media_agent/audit.py`
- Architecture snapshot: `docs/architecture.md`

## Release Discipline

- Published Docker image behavior must have an intentional version decision
  before commit, push, or release.
- Code fixes and operational fixes bump the patch slot by `0.0.1`.
- New features bump the minor slot by `0.1.0`.
- Documentation-only changes may keep the version unchanged unless they are part
  of an operator handoff or deployment release.
- When bumping, keep `VERSION`, `Dockerfile`, `pyproject.toml`,
  `src/media_agent/__init__.py`, and `CHANGELOG.md` aligned.
- After pushing a release intended for Unraid, verify the GHCR tag or manifest
  before touching the live host. Pulling `latest` too early can leave the host
  on the previous digest while the GitHub Action is still publishing.
- A DockerMan-managed Unraid install must be updated through Unraid's template
  update path, not by hand-written `docker rm && docker run` recreation. Manual
  recreation detaches the container from DockerMan metadata and hides the normal
  update status in the Unraid UI.

## Current Site Story

- `nexusphp`: RSS-first with richer feed fields
- `mteam`: RSS discovery, API-key detail enrichment, and API-driven discovery
  plus API-backed intent search

Important nuance:

- RSS must stay in the codebase because it is useful for other sites and fallback flows.
- M-Team API discovery is the preferred authenticated path when an API key is configured.
- Intent search can be Remux-first through generic search keywords and can
  prefer season packs or individual episodes through `want_decision.series_search_mode`.
- Torznab is available as the first non-M-Team intent search provider, while
  M-Team remains the reference authenticated tracker API path.

## Current Downloader Story

- qBittorrent is the live operations baseline and reference downloader.
- Transmission is available as a contract-tested second downloader through
  `download_client.type: transmission`.
- Mutations should stay dry-run first.
- Downloader state remains the operational source of truth.
- `media-agent` local state explains policy and intent lifecycle.
- Category policies separate mutable seed pools from add-only media pools.
- Logical budget pools and downloader-reported free disk headroom affect enqueue
  rejection and cleanup visibility.
- A `mutable` qB category is the operator-granted management boundary. When the
  user explicitly authorizes the seed category, current and future torrents in
  that category may be managed by the agent; tags remain audit/search metadata,
  not delete authority outside the category.
- Large manual cleanup requests should still start from a live candidate list
  with category, age, size, and state, then record the exact executed hash set.

## Current Durable Files

- `.seed-agent/state.db`
- `.seed-agent/audit.jsonl`
- `local/inbox/*`
- `local/secrets/*`

## Documentation Strategy

Use docs in layers:

- README for humans and high-level orientation
- root `AGENTS.md` for agent entry routing
- `.agents/` for repo-local agent assets
- `docs/ai/` for shared AI session efficiency
- `docs/specs/` for durable product/design decisions
- `docs/plans/` for implementation sequencing
- `docs/operations/` for operator procedures
- `docs/roadmap.md` for current state and next work
- `docs/ai/icon-design.md` for the shared `media-agent` /
  `material-agent` icon geometry, palette, export, and validation standard

## Session Guidance

For most sessions, the model should not need to read the full history. Read:

1. this file,
2. the relevant module doc(s),
3. the roadmap item,
4. only then the matching spec or handoff note if needed.
