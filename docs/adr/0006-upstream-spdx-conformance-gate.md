# Upstream SPDX conformance gate

Status: Accepted

## Decision

Use `spdx3-validate>=0.0.7,<1`, a validator recommended by the
[SPDX model project](https://github.com/spdx/spdx-3-model/blob/develop/serialization/jsonld/validation.md),
for both upstream JSON Schema structure and SHACL semantics. This is a CI-only
verification dependency, not a runtime dependency. Stable updates within the
declared major range are selected at gate execution and the resolved version
is recorded in its output. A new major requires a deliberate policy change.
SPDX vocabulary/context/schema target remains the released 3.0.1 specification.

The bounded wrapper accepts no caller paths. It reads only synthetic checked-in
fixtures and generates synthetic sparse/complete previews in a temporary
directory. Network access is limited by purpose to installing verification
dependencies and retrieving public SPDX context/schema/model documents. No
user BOMs or private model evidence are sent to an online validation service.
Each validator subprocess has a 90-second timeout; the whole gate has a
ten-minute limit. Retrieval errors fail the gate; they are never passing skips.

## Proven scope

- Minimal reference: Core CreationInfo, Organization and SpdxDocument plus an
  AI AIPackage, using canonical serialized names and profile identifiers.
- Complete reference: the above plus Software File/Package and a Core
  `contains` relationship. Complete means complete **fixture**, not every field
  or relationship in every SPDX profile.
- Both reference inputs and their JSON import/re-serialization roundtrips must
  pass upstream JSON Schema and SHACL checks.
- Removing required `CreationInfo.created` must produce an attributed rejection.
- Actual CLI outputs from sparse and complete projects must retain
  `aiBom:conformance=partial` and be rejected by the upstream gate. This negative
  baseline makes the current compatibility gap executable, rather than claiming
  that a passing local preview schema proves upstream conformance.

## Evidence and mapping boundaries

Reference creation dates are explicitly declared synthetic test data, not
observed model creation or release dates. Production collectors do not invent
timestamps, creators, suppliers or dataset facts. SPDX permits source-derived
creation dates for reproducibility; adopting one in production still requires
a trustworthy declared/observed source and a documented compatibility change.

The existing normalized model remains exporter-independent. Core/Software/AI
fixture primitives and containment are covered; Dataset, Build, Security and
licensing relationship mappings are not. Raw declared license text remains a
preview extension, never a concluded license. Missing versions remain preview
`NOASSERTION` text, not an assertion of an upstream license or element identity.
Human-declared metadata remains distinct from tool-observed paths and hashes.

## Promotion boundary

This decision establishes the upstream gate, not a production exporter upgrade.
Do not rename current preview fields, discard evidence, or set conformance to
full just to pass it. A future mapper change must replace the expected-preview-
rejection checks with positive checks for actual CLI output, add invalid
relationship/license/source cases for the expanded scope, and document migration
for existing preview consumers. The open design is retained in the mapping
follow-up proposal, not silently approved by this ADR.

## Recovery

A validator or upstream-service failure blocks the conformance job and requires
diagnosis. Do not disable the gate, convert network failures into expected
invalid fixtures, or claim a new export contract. Existing offline CLI behavior
and CycloneDX validation remain independent of this CI-only service dependency.
