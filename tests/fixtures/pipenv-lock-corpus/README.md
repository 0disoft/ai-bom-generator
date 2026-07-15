# Pipenv Lock Compatibility Corpus

These lockfiles were generated from the same bounded public `Pipfile` by two
exact Pipenv releases:

- `pipenv-2023.12.1.lock`: Pipenv 2023.12.1
- `pipenv-2026.6.2.lock`: Pipenv 2026.6.2

The input declares `attrs==24.2.0` in `default` with a Python marker and
`idna==3.10` in `develop`. Both packages and all hashes refer to public PyPI
artifacts. No private indexes, credentials, local paths, or customer data are
used.

At capture time, both producer versions emitted byte-identical specification 6
lockfiles. Keeping both files makes that compatibility result explicit and lets
a reviewed regeneration show which producer first changes shape.

## Regeneration

`tools/generate_pipenv_compatibility_corpus.ts` embeds the public input, runs
both exact Pipenv releases in separate temporary directories, validates the
specification and expected groups, and writes the lockfiles only after both
runs succeed.

The workspace command contract exposes this as
`ai_bom_generator_generate_pipenv_compatibility_corpus`. Regeneration requires
network access to PyPI and must be followed by review of package versions,
hashes, markers, sources, and the resulting diff.

Upstream references:

- https://pypi.org/project/pipenv/2023.12.1/
- https://pypi.org/project/pipenv/2026.6.2/
- https://pipenv.pypa.io/en/stable/pipfile.html

