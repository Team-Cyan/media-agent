# 1.1 Rename And Single-Container Review

Date: 2026-11-16. Scope: rename and supervisor changes after the published 1.0.1
source, building on the repository-wide 1.0 review and retained CI investigation.

## Coverage And Findings

All canonical application modules were compared against the prior package after
normalizing import/branding replacements. The behavioral delta is the supervisor;
state locations and metric names were explicitly preserved. CLI/config/state,
Web/auth/assets, deployment templates, release workflows, tests and metadata were
reviewed for compatibility. No open PR remains at inventory. Original dirty-work
preservation hashes and the separately archived legacy repository remain local.

| Finding | Disposition and evidence |
| --- | --- |
| Default app bypassed media-only role restriction | Fixed before publication; legacy media deployment cannot launch scheduler. |
| Old import namespace loaded duplicate model/exception types | Lazy aliases now return canonical module objects; identity, metadata, globals and no-eager-CLI tests pass. |
| Old explicit Docker CLI prefix was rejected | Both console prefixes retain exact argument boundaries and role checks. |
| Mechanical rename broke old Web token header | Old and new headers are accepted with existing Bearer support; authorization remains enforced. |
| Deployment examples still described two containers | Unified Compose/DockerMan app, multi-role health, restart budget and stop grace; legacy worker is marked incompatible with concurrent app. |
| UI preference key changed unnecessarily | Original storage key retained for existing users. |

Independent application review challenged role boundaries, imports and process
cleanup. PID1 child failure is fatal; process groups receive shutdown signals and
are reaped. Media and scheduler retain their independent existing leases. A
shared container intentionally shares credentials/mounts; it is not per-process
security isolation. Enabling/disabling roles requires an intentional restart.

## Verification

- Full local suite: 1459 passed, 1 skipped; Ruff passed.
- Dependency audit: no known vulnerabilities at execution.
- Candidate Linux arm64 image built successfully. Real PID1 supervisor, scheduler,
  Web and media worker observed; each child runs UID 1000, role/Web health passes.
- Descriptor-based hardlink race passed under UID/GID 1000:100; foreground Linux
  app passed all-role health and exited 0 on SIGTERM. Public hygiene passed.
- Gitleaks scanned the staged distributable tree and found two already-classified
  candidates: test authorization-redaction data and a static tracker client
  protocol-signing constant. Neither is an operator/account credential. Findings
  and original redacted scanner exit status are retained; no scanner rule was
  weakened. The prior history audit documents the same classifications.
- Runtime media-state directories and local deployment env files are now explicitly
  ignored and forbidden by the hygiene checker; image context excludes media state.
- Exact commit CI, publication and production evidence remain separate gates.
- Initial fixture attempts with incomplete config/heartbeat were rejected; they
  do not represent production failures. A Mac-only smoke reached all-role health
  but cleanup returned EPERM; Linux lifecycle evidence is the deployment gate.

## Distribution And Operations

Published 1.0 tags remain immutable. New images use the media-agent repository;
existing CLI/import/environment/state/API metric compatibility remains explicit.
The 1.0 privacy/history audit retains its documented coverage limitations; new
tracked content and image context are checked again before public push.

Production migration requires the separate reviewed homelab-agent typed lifecycle:
immutable image, live source IDs, hashes, deterministic XML, durable backups,
source-stop fencing, phase receipts, autostart handling and rollback. Publication
alone establishes no deployment or client acceptance. No historical commands,
scans, schema migration or media mutations are replayed for release validation.

Full-library subtitle coverage, full-film timing and downstream playback remain
unaccepted beyond the bounded evidence recorded in prior reports. Historical CI
causes and expired-log limitations remain in the 1.0 CI investigation; a later
passing workflow does not explain an old failure.
