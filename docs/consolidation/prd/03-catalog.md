# PRD: Catalog, completions, interactions

Id: `pr-03-catalog`. Requires: `pr-01-contract`, `pr-02-pool`.

## Outcome

The catalog is a lazy tree: database, schema, relation, column. Relation labels use the staging hints: a table partitioned by `DAY` is `t·DAY`; a materialized view partitioned by `MONTH` is `mv·MONTH`; partition `NONE` stays `t` or `mv`. A designated timestamp column appends `★` to the short type (`ts★`).

`table_columns('...')` string literals go through `escape_quest_literal` (single quotes doubled). Identifiers go through `quote_quest_identifier` (double quotes doubled). Column order is the server order, not alphabetical.

Short type labels that 0.3.x already assigned stay as they were, including `INT` → `##`, `DATE` → `dt`, `BYTE` → `#`, `BINARY` → `bin`, `LONG256` → `##`, `IPv4` → `ip`, OID 23 → `##`, and OID 1184 → `tstz`. The OID map is not shrunk. Extra native types that 0.3.x did not label may be added.

Completions add QuestDB dialect tokens and a bounded `functions()` lookup (length under 48, limit 4000). If introspection fails, the static list is still returned.

Context-menu interactions: preview (`select * ... limit 100`), insert columns at the cursor, `SHOW COLUMNS`, and `SHOW PARTITIONS`.

`tables()` on the supported pin returns `MATERIALIZED VIEW` or `BASE TABLE`. A `VIEW` branch exists for a future `table_type` value and does not run against the current SQL. Regular views are not described as detected.

## 0.3.x behavior that must survive

- Result-grid and catalog short labels for types 0.3.x already mapped.
- Introspection still uses QuestDB `tables()` and `table_columns()`, not `pg_catalog`.
- A quote in a relation name cannot break out of the `table_columns` string literal.

## How to test

`tests/test_catalog.py` drives real catalog items, `short_questdb_type`, `table_columns_sql`, and `_get_relation_columns` with a fake cursor. Fixture: `tests/data/pin_meta.json`. `tests/test_completions.py` drives `base_questdb_completions` and `get_completions`. No live QuestDB.

## Out of scope

ILP ingestion. A QuestDB lexer. Full Postgres-adapter parity. Index introspection. Export via `COPY_FORMATS` (Harlequin 2.5 ignores that attribute). Claiming that ordinary SQL views are labeled `v` on current `tables()` output.
