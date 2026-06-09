# Project Overview

## What media-agent Is

`media-agent` is a Docker-first media library import/linking tool for NAS and homelab deployments.

It is:

- a standalone repo and Docker image,
- a completed-media scanner,
- a TMDB-first metadata matcher,
- a Plex/Jellyfin/Emby-friendly naming engine,
- a dry-run-first file linker,
- a small Web UI for reviewing uncertain matches,
- an auditable scheduler for media organization.

It is not:

- a PT discovery engine,
- an upload farming optimizer,
- a torrent cleanup system,
- a full MoviePilot clone,
- a broad plugin marketplace,
- a media server.

## Product Shape

The v1 product loop is:

1. Scan configured source folders.
2. Identify candidate video files.
3. Infer media type from profile: movie, tv, or anime.
4. Query TMDB for movie or TV metadata.
5. Score candidate matches.
6. Auto-plan high-confidence imports.
7. Put medium/low-confidence matches into a review queue.
8. Build target library paths.
9. Dry-run or execute hardlink/symlink actions.
10. Persist audit, import state, and review decisions.

This is intentionally separate from `seed-agent`.

## Relationship To seed-agent

`seed-agent` owns everything up to downloader enqueue and PT/downloader policy:

- Want List ingestion,
- tracker search,
- candidate ranking,
- qBittorrent enqueue,
- upload strategy,
- cleanup protection and deletion policy.

`media-agent` starts after files exist on disk:

- source folder scan,
- metadata match,
- path naming,
- hardlink/symlink/copy policy,
- media library import audit.

Future integration can consume `seed-agent` state as optional evidence, but this repo must not depend on `seed-agent` internals.

## Core Concepts

### Profile

A profile defines one import lane:

- `name`
- `type`: `movie`, `tv`, or `anime`
- `source`
- `target`
- link policy
- naming policy
- schedule policy

Each media type can have multiple profiles. For example, one movie source for qB downloads and another for manually staged files.

### Source

The source is the completed-download folder to scan. It may contain files or directories. Source paths are operator-local and should stay in uncommitted config.

The source is never deleted by media-agent.

### Target

The target is the Plex/Jellyfin/Emby library root. Media-agent creates target directories and links files into them when execution is enabled.

### Match

A match is a candidate metadata identity from TMDB. It records:

- TMDB id,
- media type,
- title,
- year,
- season/episode when applicable,
- confidence,
- evidence,
- selected state.

### Import Action

An import action links or copies one source file to one target path. It records:

- source path,
- target path,
- link mode,
- metadata match,
- dry-run vs execute,
- result,
- conflict information.

## Current Design Decisions

- Project name: `media-agent`.
- First capability name: media linker/importer.
- Metadata source: TMDB first.
- Matching mode: semi-automatic.
- High-confidence matches can be planned automatically.
- Uncertain matches are shown in Web UI with multiple selectable TMDB candidates.
- Movie collections should create a collection root folder when TMDB collection data is available and enabled.
- TV and anime always use series root folders with season subfolders.
- Hardlink is preferred.
- Symlink fallback is configurable.
- Copy is not a default v1 behavior.
- File mutations remain dry-run by default.

## Runtime Surfaces To Build Later

- CLI:
  - `media-agent import-run-once`
  - `media-agent import-schedule`
  - `media-agent review`
  - `media-agent web`
- Docker image:
  - `ghcr.io/team-cyan/media-agent`
- Config:
  - `config/config.yaml`
  - `local/secrets/tmdb.api-key`
- State:
  - `.media-agent/state.db`
  - `.media-agent/audit.jsonl`

## Safety Expectations

- No delete operation in v1.
- No overwrite without explicit future design.
- No hidden copy fallback that doubles disk usage.
- No execution unless an execute flag/config is explicit.
- Every source/target path should be normalized and checked for traversal issues.
- Hardlink failures should explain whether the likely cause is cross-device linking, permission, missing source, or existing target.
- Web UI must clearly distinguish planned, executed, failed, and review-required items.

## Documentation Strategy

Use docs in layers:

- README for humans and high-level orientation.
- `AGENTS.md` for AI session routing.
- `docs/ai/` for reusable AI knowledge.
- `docs/specs/` for durable product/design decisions.
- `docs/plans/` for implementation sequencing.
- `docs/operations/` for operator setup and handoff notes.
- `docs/roadmap.md` for current priority and future work.
