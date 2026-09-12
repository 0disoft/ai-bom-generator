# Maintainer, Support, and Recovery Policy

Status: Accepted

## Ownership and support

The maintainer is GitHub account `0disoft` (Rodisoft). There is no designated
backup maintainer or on-call rotation. Support is best effort with no response
time SLA. Public reproducible bugs belong in GitHub Issues; suspected security
problems belong in GitHub Private Vulnerability Reporting, following SECURITY.md.
If the maintainer is unavailable, pin a known-good exact release and retain a
local copy of generated evidence. Do not assume an escalation service exists.

Security fixes target the latest released compatible 0.x version. Older exact
versions remain reproducible references, not separately maintained support lines.
Breaking CLI, config, Action, or output changes require a documented versioning
decision and migration notes. SPDX output remains a partial preview.

## Severity and first response

| Class | Examples | First response |
| --- | --- | --- |
| Critical | Credential disclosure, unintended input modification | Stop publishing/sharing affected output; report privately; revoke exposed credentials at their owner |
| High | Incorrect digest, mixed generations, invalid exporter output | Stop affected generation; preserve non-secret reproduction; pin last verified exact release |
| Normal | Recoverable CLI/Action regression or compatibility failure | File minimal reproduction; use supported alternate workflow; fix in a patch |
| Enhancement | New formats or convenience behavior | Assess separately from incident response |

## Merge and release gates

Require passing CI for supported Python versions, managed-runtime smoke on
Ubuntu/macOS/Windows, and CodeQL for the proposed commit before release.
Clarissimi remains advisory; it does not replace these checks. At the policy
review, GitHub reported no rulesets, `main.protected=false`, and no repository
variables. These are maintainer process gates, not a claim of platform enforcement.
Recheck live settings before changing them; a solo maintainer may configure
protection when there is a workable recovery path for unavailable checks.

## Broken-release recovery

Never retarget or delete an immutable exact release tag. Record the affected
version and symptom in release notes; publish a corrected patch after regression
validation. If installing a bad package would harm users, the maintainer may yank
that exact PyPI release with a reason. Yanking discourages ordinary resolution;
it does not remove already installed copies or reliably prevent explicit pins.
Do not unpublish normal releases as a rollback mechanism.

For the Action, first run exact-version external smoke on the chosen known-good
target, verify package/release identity, then move mutable `v0` to that target
and run mutable-channel smoke. This does not publish a package. Consumers pinned
to the bad exact version must explicitly change their pin. A forward fix is
preferred when no tested prior target exists.

## Retention and recovery ownership

Maintain source, synthetic fixtures, lockfiles, schemas, and reviewed release notes
in Git. Keep published GitHub release assets and PyPI distributions; do not impose
automatic deletion. They are distribution records, not backups of user data.
Caller output, input snapshots, uploaded artifacts, and GitHub workflow-log
retention belong to the caller. The tool stores no dataset backups or telemetry.
Diagnostic reports must be reviewed/redacted before sharing and may be deleted
by their owner after incident resolution. Do not delete live coordination locks.

The maintainer owns registry account recovery and Trusted Publisher repair.
Recover accounts through provider recovery mechanisms; never add long-lived PyPI
tokens to source or ordinary CI. Restore a release build from its immutable source,
locked environment, schemas and fixtures, then compare artifacts and rerun checks.
An unavailable registry blocks publication; it does not justify reusing a version.

## Table-top verification

For a patch emitting incorrect digests: identify its exact release and failed
fixture, stop promotion, select the last verified target, run exact external smoke,
then roll back `v0` and verify mutable smoke. Warn exact-pin consumers and assess
PyPI yanking. Add the reproducer, fix the hash boundary, validate, and release a
new patch. Retain the original release identity throughout. No database restore,
hosted-service failover, or user-dataset backup is part of this procedure.
