# Changelog

## [0.4.0-rc1] - 2026-07-25

### Added (draft — merge proposal with rhuygen/harlequin-questdb)

- Connection pool with TCP keepalive and reconnect on transient PGWire failures
- Interactive catalog tree (db → schema → relation → column) with partition and designated-timestamp hints
- Catalog sidebar interactions (preview, insert columns, SHOW COLUMNS/PARTITIONS)
- QuestDB dialect completions plus bounded `functions()` introspection
- Query cancel (`IMPLEMENTS_CANCEL`)
- `docs/USER_GUIDE.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/MERGE_PROPOSAL.md`
- `docker-compose.yml` pinned to QuestDB 8.2.2
- Offline tests with pin fixtures

### Changed

- Safer `table_columns()` introspection (escaped string literals)
- Backward-compatible `QuestDBAdapter` / `username` kwarg aliases for 0.3.x users

## [0.3.3] - 2026-07-09

- PyPI project URLs (Repository, Documentation) — [rhuygen](https://github.com/rhuygen/harlequin-questdb)

## [0.3.2] - 2026-06-30

- Initial PyPI release
