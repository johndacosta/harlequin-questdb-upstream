# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-10-24

### Added

- Connection pool with TCP keepalive, a pre-checkout check, and reconnect on a dead PGWire session. This expands the idle reconnect added in 0.3.0.
- Query cancel (`IMPLEMENTS_CANCEL`).
- Lazy catalog tree (database, schema, relation, column) with partition labels such as `t·DAY` and a designated-timestamp marker (`ts★`).
- Catalog interactions: preview, insert columns, `SHOW COLUMNS`, and `SHOW PARTITIONS`.
- QuestDB dialect completions and a bounded `functions()` lookup.
- CLI options `--dbname`, `--connect-timeout`, and `--sslmode`. The constructor accepts `user` as an alias of `username`.
- `docs/USER_GUIDE.md`, `docs/KNOWN_LIMITATIONS.md`, and a dev-only `docker-compose.yml` pinned to QuestDB 8.2.2.
- John DaCosta as a co-author. Copyright for Rik Huygen stays on the license.

### Changed

- Minimum Harlequin version is 2.5. Installations on older Harlequin stay on the 0.3.x line.
- `psycopg` now depends on both the `binary` and `pool` extras (`>=3.2.0,<4`).
- When a connection string is present, it supplies host, port, user, password, dbname, and sslmode. Those defaults are not applied on top of the string.

### Fixed

- Relation names passed to `table_columns()` are escaped, including embedded single quotes.
- Connection errors redact a `password=` token echoed by the driver. `connection_id` omits the password.

## [0.3.3] - 2026-07-09

### Added

- Repository and Documentation links under `[project.urls]` in `pyproject.toml`.

## [0.3.2] - 2026-06-30

### Changed

- Lowered the minimum required Python version from 3.12 to 3.10, in line with Harlequin itself.

## [0.3.1] - 2026-06-29

- Updated the README file

## [0.3.0] - 2026-06-29

### Fixed

- Automatic reconnection when QuestDB closes an idle connection. `QuestDBConnection` now stores the DSN and transparently reconnects on `OperationalError` before retrying the query.

## [0.2.0] - 2026-06-29

### Added

- `connection_id` property on `QuestDBAdapter` for stable catalog and history caching.

## [0.1.0] - 2026-06-27

### Added

- Initial adapter implementation connecting to QuestDB via the PostgreSQL wire protocol (`psycopg`).
- CLI options: `--host`, `--port`, `--username`, `--password` with QuestDB defaults.
- Catalog browser populated via QuestDB's `tables()` and `table_columns()` SQL functions.
- Type label mappings for QuestDB-native types (catalog) and PostgreSQL wire protocol OIDs (query results).

[Unreleased]: https://github.com/rhuygen/harlequin-questdb/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/rhuygen/harlequin-questdb/compare/v0.3.3...v0.4.0
[0.3.3]: https://github.com/rhuygen/harlequin-questdb/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/rhuygen/harlequin-questdb/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/rhuygen/harlequin-questdb/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/rhuygen/harlequin-questdb/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rhuygen/harlequin-questdb/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/rhuygen/harlequin-questdb/releases/tag/v0.1.0
