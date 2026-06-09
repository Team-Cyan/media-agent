# Roadmap

## Current State

`media-agent` is a new standalone repo. The initial Docker/CI/runtime scaffold
exists, but real scan, match, link, review, and Web UI behavior is not
implemented yet.

The goal of this bootstrap is to preserve the product boundary and handoff context before implementation begins.

## P0 - Project Bootstrap

- [x] Create repo entry docs.
- [x] Define product boundary separate from `seed-agent`.
- [x] Define v1 config shape.
- [x] Define safety defaults.
- [x] Define AI session read order and handoff docs.
- [x] Add Python package scaffold and CLI validation commands.
- [x] Add Dockerfile and entrypoint.
- [x] Add GitHub CI and GHCR publish workflows.
- [x] Add Docker image runtime and publishing notes.

## P0 - Runtime Foundation

- Implement typed config models.
- Add structured logging and redaction helpers.
- Initialize `.media-agent/state.db`.
- Append `.media-agent/audit.jsonl` records for planned actions.
- Add fixture-based tests for representative movie, TV, and anime paths.

## P0 - Media Import Core

- Parse config profiles for `movie`, `tv`, and `anime`.
- Scan source folders for video files.
- Represent scan candidates in local state.
- Query TMDB using a secret reference.
- Score TMDB matches.
- Generate target paths.
- Produce dry-run import plans.

## P0 - File Link Execution

- Implement hardlink execution.
- Implement optional symlink fallback.
- Detect cross-device hardlink failures.
- Refuse overwrites by default.
- Persist audit records for every planned and executed action.

## P0 - Review Queue

- Store uncertain TMDB matches.
- Expose candidate choices.
- Allow manual selection.
- Re-run import planning after user selection.

## P1 - Scheduler And Web UI

- Add `import-schedule`.
- Add health/heartbeat output.
- Add Web UI for scan status, pending review, import preview, and execution.
- Keep execution explicit and visible.

## P1 - Library Refresh

- Add optional Plex library refresh.
- Later consider Jellyfin/Emby refresh.
- Keep refresh configuration separate from file linking.

## P1 - Anime And Series Polish

- Add anime-specific season/episode offset handling.
- Add aliases for common anime naming mismatches.
- Add manual season mapping.

## P2 - Integration

- Optional read-only consumption of `seed-agent` state as evidence.
- Optional qB/Transmission read-only path discovery.
- Optional import history export.

## Deferred / Not In Scope

- PT tracker search.
- Download candidate scoring.
- qB cleanup/deletion.
- Auto-reseed.
- Broad plugin marketplace.
- Full MoviePilot replacement.
