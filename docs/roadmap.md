# Roadmap

## Current State

`media-agent` is a new standalone repo. The initial Docker/CI/runtime scaffold
exists, and `import-run-once` now provides a working local MVP:

- scan enabled source folders for video files,
- parse common movie and episode filenames,
- enrich movie and TV titles through TMDB when local secrets are configured,
- generate dry-run import plans,
- write SQLite state and JSONL audit,
- create hardlinks or symlinks only when `--execute` is explicit.

The Web UI now exposes status, pending review, recent actions, dry scan, and
execute triggers. Rich manual candidate selection is still not implemented.

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

- [x] Implement typed config models.
- Add structured logging and redaction helpers.
- [x] Initialize `.media-agent/state.db`.
- [x] Append `.media-agent/audit.jsonl` records for planned and executed actions.
- [x] Add fixture-based tests for representative movie and TV paths.
- [x] Add fixture-based tests for anime paths.
- [x] Add runtime-status and heartbeat healthcheck support.

## P0 - Media Import Core

- [x] Parse config profiles for `movie`, `tv`, and `anime`.
- [x] Scan source folders for video files.
- [x] Represent planned import actions in local state.
- [x] Query TMDB using a secret reference.
- [x] Score TMDB movie and TV search results.
- [x] Generate target paths from filename guesses.
- [x] Produce dry-run import plans.

## P0 - File Link Execution

- [x] Implement hardlink execution.
- [x] Implement optional symlink fallback for cross-device hardlink failures.
- [x] Detect cross-device hardlink failures.
- [x] Refuse overwrites by default.
- [x] Persist audit records for every planned and executed action.

## P0 - Review Queue

- [x] Store uncertain filename/TMDB matches as pending review items.
- Expose candidate choices.
- Allow manual selection.
- Re-run import planning after user selection.

## P1 - Scheduler And Web UI

- [x] Add `import-schedule`.
- [x] Add health/heartbeat output.
- [x] Add Web UI for scan status, pending review, import preview, and execution.
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
