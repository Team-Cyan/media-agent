# AGENTS.md

This file is the repository entrypoint for coding agents.

Keep this file short. Treat it as routing, not the full knowledge base.

## Read Order

For most tasks, read in this order:

1. `docs/ai/project-overview.md`
2. `docs/roadmap.md`
3. The relevant spec under `docs/specs/`
4. `docs/operations/session-handoff.md` only if the task depends on recent unfinished work
5. A matching plan under `docs/plans/` only when implementing a planned change

Do not start by reading every document.

## Repository Model

- `media-agent`: standalone project for media library import/linking.
- `seed-agent`: separate project for PT discovery, downloader strategy, Want List, qB scheduling, and cleanup policy.
- This repo owns completed-media organization only: scanning source folders, matching media metadata, naming Plex/Jellyfin-ready paths, and linking into library folders.

## Working Rules

- Keep AI-facing docs in English.
- Reply to the human user in Chinese unless they ask for another language.
- Prefer small, well-bounded sessions.
- Do not import `seed-agent` code directly. Integration should happen through explicit state files, qB/Transmission APIs, or future documented handoff formats.
- Keep secrets in gitignored local files such as `local/secrets/`.
- File-system mutations must be dry-run by default.
- Never delete source downloads in this project.
- Hardlink/symlink/copy actions must write audit records with source path, target path, metadata id, link mode, and result.

## Product Boundary

This project is not a downloader strategy engine and not a PT tracker automation tool.

Do not add:

- M-Team search or PT candidate scoring,
- upload farming strategy,
- qB cleanup policy,
- torrent deletion,
- broad plugin marketplace,
- unrestricted shell execution.

Those stay outside this repo.

## Useful Docs

- `docs/ai/project-overview.md`
- `docs/specs/2026-06-09-media-agent-product-boundary.md`
- `docs/operations/docker-image-runtime.md`
- `config/example.yaml`
