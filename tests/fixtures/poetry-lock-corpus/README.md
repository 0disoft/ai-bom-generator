# Poetry Lock Compatibility Corpus

These publication-safe fixtures preserve representative Poetry lockfile shapes
without copying package records, credentials, or private repository data.

## Upstream Shapes

- `poetry-2.0.lock` mirrors the lock version 2.0 structure emitted by Poetry
  1.3.x: package records use `category`, package-level `files`, and optional
  source tables.
- `poetry-2.1.lock` mirrors the lock version 2.1 structure emitted by Poetry
  2.0.x: package records use `groups`, and `markers` may be either one string or
  a table keyed by dependency group.

The shape references are Poetry's own versioned locker implementation and test
fixtures:

- https://github.com/python-poetry/poetry/blob/1.3.2/src/poetry/packages/locker.py
- https://github.com/python-poetry/poetry/blob/1.3.2/poetry.lock
- https://github.com/python-poetry/poetry/blob/2.0.0/src/poetry/packages/locker.py
- https://github.com/python-poetry/poetry/blob/2.0.0/tests/packages/test_locker.py

## Safety And Scope

- Names, versions, URLs, revisions, and hashes are synthetic.
- URLs use reserved `.invalid` domains.
- The fixtures are parsed offline and never resolved or downloaded.
- Dependency groups remain selection metadata. The parser does not claim that
  a group was selected.
- Equal group markers can be represented as one package marker. Conflicting
  group markers produce a partial-parse issue and no fabricated combined marker.
