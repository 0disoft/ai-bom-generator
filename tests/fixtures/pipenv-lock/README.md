# Pipenv Lock Fixture

This publication-safe fixture mirrors Pipenv's documented `Pipfile.lock`
specification 6 shape. It covers default and develop groups, exact registry
pins, source-name resolution, hashes, extras, explicit and shorthand PEP 508
markers, Git references, remote files, and editable local paths.

The values are synthetic, URLs use reserved `.invalid` domains, and parsing is
offline. Group membership is treated as lockfile organization rather than proof
that the caller selected a group.

Shape references:

- https://pipenv.pypa.io/en/stable/pipfile.html
- https://github.com/pypa/pipfile#examples-spec-v6
