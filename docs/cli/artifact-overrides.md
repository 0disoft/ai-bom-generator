# Artifact Selection Overrides

Status: Accepted

Discovery remains opt-in. `--discover-artifacts` enables default patterns and
`--no-discover-artifacts` disables them; explicit include patterns remain active.
Omitting both flags preserves `[artifacts].discovery` or its default of false.

Valid CLI values override valid config values, then fixed defaults apply.
Invalid selected config is rejected before CLI overrides are applied.

| Config under `[artifacts.limits]` | CLI flag | Default and hard ceiling |
| --- | --- | --- |
| `matches_per_pattern` | `--max-artifact-matches` | 256 |
| `single_file_bytes` | `--max-artifact-bytes` | 17179869184 |
| `total_bytes` | `--max-total-artifact-bytes` | 26843545600 |
| `visited_entries` | `--max-scan-entries` | 100000 |

All values are positive integers. Zero, negative, fractional, boolean, unknown,
and over-ceiling values are rejected. Values represent bytes, not GiB strings.
Raising a configured lower value is permitted only up to the hard ceiling.
Lower match limits discard an entire over-budget pattern; size limits skip the
affected artifact. Traversal overflow discards all artifact matches. Warnings
participate in the existing fail-on-warning policy.

The composite Action consumes these config fields through the normal loader.
No new Action inputs or permissions are added. Config schema v1 gains an optional
`artifacts.limits` object; older generators reject it rather than silently ignoring
limits, so using these fields requires the release that introduces them.

This decision resolves #29. Overrides only narrow bounded collection; they do
not authorize automatic dependency discovery, network access, or hidden caching.
