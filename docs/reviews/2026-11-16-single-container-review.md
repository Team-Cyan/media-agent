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


## Publication And Controlled Rollout (2026-11-17)

The immutable `v1.1.0` and archival `release/1.1` point to
`309f1af2141beec994f1bab8f3d1bd9d665aa15f`. The archival `release/1.0` pointer was
advanced to its last published patch, `f5e2205`; no published tag was moved.
[Exact-source CI](https://github.com/Team-Cyan/media-agent/actions/runs/43970243185),
[Pages](https://github.com/Team-Cyan/media-agent/actions/runs/43970238922) and
[GitHub Release](https://github.com/Team-Cyan/media-agent/actions/runs/43971483102)
passed. The [release](https://github.com/Team-Cyan/media-agent/releases/tag/v1.1.0)
is published and its temporary image-publication warning has been removed after
registry and published-image checks passed.

Registry tags `v1.1.0`, `1.1.0` and `1.1` resolve to:
`sha256:da25e39efdab93f65a57d938c7b83c05ee6ff5752ba819355bd3f69403efcf4b`.
Both linux/amd64 and linux/arm64 configs report version `1.1.0` and the exact
release revision above, with the canonical media-agent source label. Manifests:

- amd64: `sha256:69eb2a80bfe258433a4b660d218b05fa1f0a3358974ac04150dccd92b3d6b554`
- arm64: `sha256:f9cc632c656494fc04ff3cee4e0735e73878307f08cd981dc0b378d2aafa9104`

The published arm64 image passed descriptor-hardlink checks under UID/GID
1000:100 and all-role/Web health, then exited 0 on SIGTERM. The controlled amd64
production rollout used the same immutable index digest through homelab-agent.
The controller extension passed 75 related tests with three platform-specific
skips, including 13 focused migration/wiring checks and isolated Linux PHP fault
cases. Independent review resolved partial-prepare recovery, pull failure,
lost-start response, queued-command and process-identity blockers before apply.

The production prepare plan verified durable config/state/audit/template and
legacy-template backups, disabled conflicting autostart entries, stopped the
original pair, and created the new container stopped. A separate approved start
plan checked queue/config/epoch fences, started the target, verified its PID1
supervisor and three configured role children under the runtime owner, and only
then activated autostart. Post-block backup and model refresh completed. Final
readback confirmed healthy target, stopped original containers, matching phase
receipts, unchanged config/schema/epoch and unchanged source/import/artifact/job/
command/review counts. No scan, migration, import or subtitle command was submitted
for validation. Original containers, media and durable state remain retained;
rollback uses receipts rather than a blind database restore.

DockerMan audit found no target-container drift. Four existing unmasked media
credential-reference path warnings remain on the retained stopped worker template;
its metadata was preserved for recovery rather than changed under this rollout.
The homelab controller extension remains local with that repository's unrelated
working changes; this application release does not include or publish them.
Private receipts and exact deployment details remain in ignored evidence.
Client library visibility, full-film subtitle timing and downstream playback are
still separate acceptance gaps; server health does not establish them.

## Rename Publication Failure Diagnosis

Both the [main publication](https://github.com/Team-Cyan/media-agent/actions/runs/43970920650/attempts/1)
and [tag publication](https://github.com/Team-Cyan/media-agent/actions/runs/43971483094/attempts/1)
first attempts built both platforms successfully but failed on GHCR upload with
`permission_denied: write_package`. The existing package remained associated with
the archived legacy repository, whose Actions access did not authorize the newly
renamed source repository. This was package access, not a test/build failure.

After explicit user approval, only the new repository's Actions received Write
access to this package; existing legacy access and image versions were retained.
No new Admin grant, credential rotation, history rewrite or artifact deletion was
performed. Both failed jobs were rerun as attempt 2 and succeeded:
[main](https://github.com/Team-Cyan/media-agent/actions/runs/43970920650/attempts/2),
[tag](https://github.com/Team-Cyan/media-agent/actions/runs/43971483094/attempts/2).
The failed attempts remain available. No tests, security gates or failure
notifications were weakened. Earlier CI causes and expired-log limitations remain
in the [1.0 investigation](2026-11-15-ci-failure-investigation.md).

## Milestone Closure And Authorized Cleanup (2026-11-17)

The release, rename, supervised deployment and predecessor cleanup milestone is
complete. The typed high-risk cleanup removed the two exact stopped source
containers and their unused legacy image, archived both DockerMan templates and
preserved application state, media and recovery backups. Current target health
and boundary checks passed; the template audit reported zero issues, superseding
the four historical warnings on the old worker template. Post-block backup and
model refresh completed. Recovery of old roles now requires recreation from saved
templates and pinned digests; the removed container IDs cannot be restarted.

Local Apple Container cleanup removed five old containers and fifteen old image
references. Durable bind-file hashes remained unchanged; the current published
image and shared tooling were retained. Cleanup controller verification passed
65 targeted tests, including isolated Linux/PHP fault fixtures. Private identities
and receipts remain in ignored local evidence.

This closes the selected delivery phase and moves the release into maintenance.
It does not complete the separate whole-library subtitle, full-film timing or
client playback acceptance described above, or select a new feature milestone.
