# 1.2 Cron Release Review

Date: 2026-11-17. Scope: five independent business schedules, background media
windows and finite-freeleech protection after the published 1.1.0 source.

## Reviewed behavior

Independent read-only release review found no remaining confirmed blocker after
reviewing the current implementation and regression coverage. Earlier plan/code
findings were fixed: next-real-check expiry threshold, multi-profile inventory
completion at window close, legacy PT deadline starvation, disabled maintenance
on startup, and current authority for the actual enqueue category during hot edits.
The detailed contract is [Cron scheduling](../operations/cron-scheduling.md).

- PT, routine maintenance and Want clocks share one lease without requiring PT
  discovery to wake the other tasks. Invalid expressions disable automatic tasks.
- Explicit media background windows gate recovery, publication, media analysis,
  posters and subtitles; inventory remains separately scheduled. Window end is
  fixed to the Cron slot, and in-flight bounded operations finish safely.
- Finite scheduled PT acquisition covers the second future protection slot.
  Expiry-only protection covers the next actual check and cannot select completed
  cold seeds. Token and per-add admission recheck current target-category authority.
- Omitted new fields retain legacy behavior. Checked-in examples disable all five
  business schedules; production settings must not be replaced with those defaults.
- The state schema is unchanged. Existing root/config/epoch/lease and category
  authority fences remain. Cron/window controls do not guarantee disk spin-down.

## Verification and release gates

Full local suite: 1513 passed, 1 skipped. Ruff, JavaScript syntax, public repository
hygiene and documentation links passed. Local browser checks verified independent
controls, persistence and window start/end previews. Dependency audit found no
known vulnerabilities at execution; Compose validation passed in the Linux CLI.

The published [v1.2.1 release](https://github.com/Team-Cyan/media-agent/releases/tag/v1.2.1)
points to `4814503898d1f7fbd884569ad4ef4d2addac3ccc`.
[Exact-source CI](https://github.com/Team-Cyan/media-agent/actions/runs/44166000044)
passed with 1514 tests and 1 skipped; [multi-platform publication](https://github.com/Team-Cyan/media-agent/actions/runs/44167293327)
succeeded and the registry digest was verified as
`sha256:a7025273fe9358ff260d53be4b98ce6d36f49d9229aa190629282734fc9286bd`.
The patch captures the health observation clock after the state snapshot and retains
the genuine-future timestamp guard. Production remains on 1.1.0 pending upgrade.
A controlled deployment validated durable backups before candidate creation.
The runtime boundary check prevented candidate startup. Recovery restored the
prior pinned image and DockerMan template. Production Cron settings were preserved.
No historical migration or scan/queue command is replayed for release validation.

## Limits

Stored Want free releases still lack fresh promotion timestamps; Cron automatic
free/2xfree Want acquisition remains fail-closed until that evidence is available.
Authoritative unlimited scheduled PT evidence retains its existing preflight
semantics. Whole-library subtitle coverage, full-film timing and downstream client
playback remain unaccepted beyond prior bounded evidence. The independent release
review was static; test/build/runtime results belong to their execution receipts.
