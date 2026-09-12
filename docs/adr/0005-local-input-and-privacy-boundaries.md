# Local Input and Privacy Boundaries

Status: Accepted

## Context

Issues #30, #33, and #38 ask for decisions on immutable staging, broader config
discovery, and telemetry. These decisions preserve the existing local CLI and
composite Action behavior.

## Artifact staging

Do not copy inputs into tool-managed staging. Continue streaming each artifact
through the no-follow descriptor boundary and checking its metadata before and
after hashing. Projects requiring cross-file consistency must use the
producer-owned generation marker in ADR 0004 and obey its writer protocol.

A sequential copy is not an atomic snapshot: a producer can change the second
shard after the first has been copied. Copying up to the selected-byte budget
also consumes runner disk, may expand sparse files, crosses filesystem capacity
boundaries, and creates cleanup obligations after interruption or disk failure.
Concurrent invocations would multiply those costs. Staging alone therefore adds
no cross-file guarantee that justifies owning caller data.

Per-file checks are conservative observations, not proof against an adversarial
producer capable of restoring metadata. Marker integrity depends on producer
cooperation. Callers needing stronger guarantees should provide a read-only
snapshot or immutable input directory and retain ownership of its lifecycle.
The CLI does not retry an unstable generation automatically; it fails while
preserving previous committed outputs. The caller finalizes inputs and retries.
There is no new staging state to recover, clean up, or roll back.

## Configuration discovery

Keep automatic discovery limited to `<model-directory>/aibom.toml`.

- Parent search is rejected because nested projects would inherit unrelated
  policy and behavior would depend on checkout placement.
- Alternate automatic filenames are rejected because they introduce ambiguity
  without adding capability: callers already have explicit `--config`.
- Environment-variable configuration is rejected because invisible process
  state makes local and CI runs difficult to reproduce and can carry secrets.

Explicit flags override config; explicit `--config` overrides discovery; absent
target-root config uses existing defaults. Invalid selected config fails rather
than falling back to another candidate. The Action passes explicit config or
lets the CLI apply the same target-root rule. Its transport environment variables
are adapter inputs, not a general CLI environment-config discovery mechanism.

## Telemetry

The CLI and composite Action do not implement product telemetry, phone-home
requests, analytics identifiers, or usage-report endpoints. This is a durable
default and supported product boundary, not an MVP experiment.

Caller-requested summaries, warnings, BOMs, and terminal output are local output.
GitHub stores workflow logs according to the caller repository's settings; those
logs are hosted platform behavior, not a telemetry service run by this project.
Action setup still downloads its toolchain and dependencies as documented.

Any future opt-in telemetry proposal requires a separate product and privacy
decision covering consent, exact fields, endpoint ownership, retention, deletion,
redaction, and offline behavior. This ADR does not authorize such implementation.

## Verification and compatibility

No CLI flags, output schemas, permissions, input reads, or network behavior
change. Existing config discovery, marker-race, unstable artifact, and redaction
tests remain the executable contract. Review collection/export imports and call
paths for network clients when changing these boundaries; a static scan alone
does not prove absence of all indirect network effects.
