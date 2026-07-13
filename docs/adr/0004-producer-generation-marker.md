# Producer Generation Marker Contract

Status: Accepted on 2026-07-13
Owner: UNASSIGNED

## Context

The collector proves that each artifact is stable while its descriptor is
hashed. That does not prove that multiple model shards, dependency files, and
Git evidence belong to one producer generation. Comparing timestamps or reading
one opaque marker before and after collection is also insufficient: a producer
could mutate governed files while leaving the old marker unchanged until the
end of its write.

## Decision

Add an optional `[generation].marker` producer generation marker.
The marker is caller-owned input inside the target root. The CLI never creates,
updates, or repairs it.

The proposed marker is a bounded JSON object:

```json
{
  "schema_version": "1",
  "generation": "producer-owned opaque identifier",
  "state": "complete"
}
```

The producer protocol is:

1. Atomically replace the marker with `state: "writing"` before changing any
   governed input.
2. Write and finalize all governed model and evidence files.
3. Atomically replace the marker with a new generation and `state: "complete"`.

The collector protocol is:

1. Resolve the configured marker through the existing target-root, no-symlink,
   no-follow file policy.
2. Read at most 4 KiB and require schema version 1, a non-empty generation, and
   `state: "complete"` before collecting governed inputs.
3. Collect and hash the selected evidence normally.
4. Reopen and validate the marker after all governed reads.
5. Accept the run only when both complete marker snapshots are byte-equivalent.

The raw producer generation is not copied into output. Normalized evidence and
exporters may expose the SHA-256 digest of the canonical marker plus its
target-root-relative source path so consumers can compare runs without leaking
an opaque producer value.

Without a configured marker, current collection behavior remains compatible and
must not claim cross-file generation consistency.

## Alternatives

- **Compare file metadata before and after the whole run:** rejected because a
  producer can replace different files between observations and still produce a
  set that never existed as one generation.
- **Read one opaque marker before and after collection:** rejected because the
  producer may leave the old marker in place while writes are active.
- **Copy all inputs into tool-managed immutable staging:** deferred because it
  duplicates multi-gigabyte artifacts, changes storage requirements, and makes
  the CLI responsible for caller data lifecycle.
- **Use Git commit identity as the generation:** rejected because large model
  artifacts and generated checkpoints are commonly outside Git.

## Boundary And Data Ownership

- The marker and governed inputs belong to the caller and producer.
- The CLI reads but never mutates the target model directory.
- The contract adds no network access, locking of producer processes, artifact
  upload, or tool-managed staging.
- A producer that does not enter `writing` before mutation is outside the
  guarantee; the CLI cannot infer protocol compliance from timestamps.

## Failure And Recovery

- Configured marker missing, unsafe, oversized, malformed, or not complete at
  the first read: fail before collection and preserve the previous committed
  output set.
- Marker missing, unsafe, malformed, not complete, or changed at the second
  read: collector failure and preserve the previous committed output set.
- Recovery is caller-driven: wait for the producer to publish a complete marker
  and retry. The CLI does not repair producer state.

## Compatibility

The config field is optional, so unconfigured projects retain current behavior.
Adding the field, normalized digest, warning or error codes, and exporter
properties is a public capability change and requires a minor release when the
proposal is approved and implemented.

## Validation Needed Before Merge

- Positive fixture with one stable complete generation.
- Deterministic failures for initial `writing`, final `writing`, generation
  change, malformed JSON, oversize input, symlink, and target-root escape.
- A race fixture that switches the marker to `writing` before replacing one of
  two shards and proves no mixed BOM is committed.
- CycloneDX and SPDX AI mapping tests for marker digest and source provenance.
- CLI and GitHub Action tests proving previous outputs are preserved on marker
  failure.

## Approval Record

The owner approved implementation on 2026-07-13 with `[generation].marker`, the
documented JSON shape, the 4 KiB limit, invalid-input classification for the
initial read, collector-failure classification for the final read, and digest-
only exporter properties.
