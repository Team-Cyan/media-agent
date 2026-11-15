# Seed-agent 1.0.0 release closure plan

Status: executed; v1.0.0 published and exact-revision checks passed. Date: 2026-11-15.
Outcomes and bounded gaps: `docs/reviews/2026-11-15-v1-release-review.md` and
`docs/reviews/2026-11-15-ci-failure-investigation.md`.
Owning spec: `docs/specs/2026-11-15-v1-release-contract.md`.

## Objective and authorization

Close the current development stage, review the entire repository, remove personal
configuration and exposed secrets from distributable surfaces, document the actual
product, and publish the first stable 1.0.0 release. The user explicitly authorizes
necessary fixes, documentation, commits, main integration, push, tag and release.
Execute in a fresh chat with a clean checkout, preserving existing dirty work.
This planning chat prepares and dispatches; it does not perform the full review.

The user's requested order is: finish current work, full repository review and
privacy audit, refresh implemented features and future roadmap, publish 1.0.0,
then investigate release CI and the recurring historical failure notifications.
Required pre-publication checks still apply. A known failing safety check cannot
be deferred until after publication; detailed historical CI triage can be last.

## Verified starting evidence and refresh requirements

- Main baseline: `19da1ed10e8a71dd60b498297be19a3a606a1eb5` (docs closure).
- Deployed code/tag v0.29.2: `6cea7999f1406efb3d1cbf4655ed59ad5c1856cc`.
- Main CI run 43617467922 succeeded, including tests, lint, dependency audit,
  image build, hardlink/descriptor checks and container smoke healthcheck.
- v0.29.2 tag Docker Publish and GitHub Release succeeded. These successes do
  not explain older failure emails; do not dismiss those reports.
- The finite media cohort has been reconciled with originals retained, reviewed
  extras published and an alternate retained without changing the selected primary.
  Private counts, identities and receipts remain in ignored operational evidence.
- Reviewed local SRT publications were physically verified. This does not establish
  full-library subtitle delivery, full-film timing or downstream playback.
- Original checkout is on an older branch with unrelated modified/untracked
  code, CI and docs. Other worktrees also exist. Never reset/stash/delete them
  or blindly stage all changes. Read live Git state before choosing a baseline.
- README and the old session handoff contain outdated product descriptions.
  Verify current behavior from code/tests and evidence, not historical labels.

Refresh remote refs, current workflows and runtime only as needed. Keep private
runtime details and audit findings in ignored local evidence, not public docs.

## Work packages and gates

### 1. Inventory, preservation and current-stage closure

1. Read AGENTS, shared instructions, release process and this spec. Inventory
   branches/worktrees, dirty paths, open PRs/reviews and active related chats.
   Coordinate with owners before shared mutations. One release owner/writer.
2. Use an isolated clean checkout from verified main. Record commit and a
   preservation manifest for existing dirty work without copying secret values
   into public records. Never adopt all old changes as release content.
3. Classify every outstanding patch/review as already integrated, still useful
   and explicitly reviewed, deferred with reason, or superseded. Resolve relevant
   review comments with code/test evidence; document unrelated work left intact.
4. Reconcile current-stage claims and remove stale acceptance statements. Do not
   replay library writers, old scans, migrations or worker recovery operations.

Deliverable: local preservation receipt and a public, sanitized closure summary.
Gate: every outstanding item has a disposition and no concurrent writer conflict.

### 2. Full repository review and fixes

Create a coverage matrix spanning all tracked paths and these subsystems:
configuration/secrets; discovery/RSS/M-Team/Torznab; scoring/tracker strategy;
downloaders/budgets/cleanup; intents/Want List; scheduler/backoff; state/audit;
CLI/API/auth/Web UI; media identity/completion/import/extras/variants/subtitles;
filesystem/locking/migration/recovery; Docker/Compose/Unraid; tests/dependencies;
workflows/release automation; documentation/examples/licenses/assets.

Read contracts with their code and tests. Focus on correctness, data loss,
authorization, injection/path traversal, idempotency/lost responses, concurrency,
resource exhaustion, compatibility and operator clarity. Separate fixture,
integration, runtime and client acceptance. Use scoped independent review for
high-risk changes under applicable delegation rules. Fix release blockers and
meaningful supported-path bugs with focused regression checks; avoid broad
rewrites and new feature expansion. Track severity, evidence, disposition and
validation. Review the final integrated diff after fixes.

Gate: no unresolved critical/high findings or known supported-path data-loss,
secret exposure or authorization bugs. Lower findings have bounded impact and
an explicit decision; do not assert that a full review proves absence of bugs.

### 3. Privacy and supply-chain audit before any public push

Audit the tracked tree, Git history reachable from public refs, GitHub-visible
PR/issue/release text and accessible Actions logs/artifacts, plus package/image
build context and final layers. Include personal names/account IDs/watchlists,
private hosts/IPs/paths, library inventories, live capacities, tokens/cookies/API
keys/passkeys and downloader credentials. Distinguish harmless placeholders and
public upstream URLs from genuine personal runtime data. Verify ignored files
are actually untracked and excluded from Docker context; ignore patterns alone
are not proof. Run the existing public-repository checker and a suitable history
secret scanner, with redacted outputs. Do not print candidate secret values.

Sanitize examples/docs to portable placeholders or secret references without
breaking usability. Remove leaked values from new distributable content. If a
real historical credential is found, stop new exposure, report only location/type,
prepare a concrete revocation/rotation and history/artifact cleanup plan. Do not
rewrite remote history, destroy evidence, delete releases/artifacts or silently
rotate credentials without specific authorization for that action. A leaked
active secret remains a blocker until containment is verified. Record audited
surfaces, tools, refs, dates, limitations and remediation; avoid absolute claims.

### 4. Product docs and versioned roadmap

Update README, project overview, operator/setup/config/media guides, module
contracts affected by fixes, release process, changelog, session handoff and
roadmap. Replace stale statements rather than adding contradictory appendices.
Provide an implemented-feature/support matrix with real verification levels,
safe quick start, state/backup/upgrade guidance, trust/auth boundaries, known
limitations and troubleshooting. No private deployment details in examples.

Reorganize roadmap into shipped 1.0 scope, candidate 1.1/1.2 improvements and
potential 2.0 changes. Choose groups from actual unfinished items, not invented
promises or dates. Advanced subtitle archive/retiming/provider work, richer
client acceptance and other unfinished functionality must remain honestly scoped.
Version labels are planning targets, not commitments. User-requested 1.0 does
not mean completing every historic roadmap item or renaming the product.

### 5. 1.0.0 validation, integration and publication

1. Follow release-process; use bump script to set all version metadata/lockfile
   consistently to 1.0.0. Write milestone release notes across shipped functions,
   upgrade/migration implications, compatibility and limitations. Do not label a
   destructive reset or a cosmetic version bump as stability evidence.
2. Run public hygiene, full tests, Ruff, dependency audit and the workflow's
   Compose/build/candidate-image/hardlink/health smoke checks. Add checks for
   meaningful review fixes. Ensure tests do not contact live downloaders or
   providers or mutate production media.
3. Integrate reviewed commits to main without overwriting concurrent work.
   Push main and inspect exact-head checks. Resolve pre-existing failures that
   affect release validity; never disable jobs/tests to obtain a green badge.
4. Publish immutable v1.0.0 at the tested commit after checks pass; create
   release/1.0 according to repository policy. Verify GHCR version tags/digest,
   OCI version/revision/platform, release notes and source/tag alignment.
5. Reconcile any lost push/tag response by reading remote refs; no blind retry
   of uncertain external writers. Never move an already published tag silently.

Production deployment is not implied by publishing this new release. Earlier
0.29.2 deployment is complete. If a 1.0 NAS upgrade is desired, prepare the exact
controller preview/backup/rollback and confirm that specific rollout scope before
execution; do not replay old manifests or mutate qB/library to validate release.

### 6. Final CI investigation (including recurring historical notifications)

After 1.0 code push/publication, inspect all relevant workflows for that exact
commit/tag and investigate recent historical failures (initially 30 days, widen
if needed). Prefer GitHub Actions evidence; only read CI notification email if
needed to disambiguate which runs the user means. Never send mail.

Group each failure by workflow, ref/SHA, run/attempt, first failing step, redacted
error, reproducibility, root cause and fix. Distinguish actual test/build bugs,
security/dependency findings, flaky infrastructure/network/rate limits, cancelled
or superseded runs, duplicate push/tag triggers, permissions and release races.
Do not infer a cause from email subject or a later green run. Fix workflow/test/
packaging defects with bounded changes and verify the affected path. For transient
errors rerun only with evidence, preserving the failed attempt. Do not suppress
failure notifications or loosen safeguards as the fix.

If post-tag fixes change shipped behavior, issue 1.0.1 under normal policy; never
rewrite 1.0.0. Workflow-only fixes may retain version when artifact behavior is
unchanged, but verify exact-head checks and artifact identity. End with the
failed-run inventory, root causes, fixes and successful verification links.

## Completion report and handoff

Publish a sanitized review report under `docs/reviews/` with coverage, findings,
fix commits, deferred issues and limitations. Keep raw evidence ignored/local.
Final report: main/tag/release and image identity; CI results and failure causes;
privacy scope/remediation; supported 1.0 functions; future roadmap; deployment
status; preserved dirty work; any remaining user action. Link primary evidence.
Do not mark release complete with failing required checks or unresolved blockers.
