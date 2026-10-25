# Known limitations

Limits of package `harlequin-questdb` on QuestDB 8.2.2. Install and catalog labels are in [USER_GUIDE.md](USER_GUIDE.md).

| Topic | Limit |
| --- | --- |
| Views | `tables()` on this pin reports `BASE TABLE` or `MATERIALIZED VIEW`. A regular SQL view is not given a separate `v` label. The catalog does not open a view-definition buffer. |
| Indexes | The `indexed` flag from `table_columns()` is not shown. There is no index menu. |
| Export | This adapter does not implement Harlequin's export path. Harlequin 2.5 ignores the deprecated `COPY_FORMATS` attribute. Use QuestDB's own export tools for bulk extracts. |
| Versions | Developed against QuestDB 8.2.2. Other versions are best-effort. Meta-function columns can differ. |
| Lexer | There is no QuestDB-specific syntax highlighter. Dialect help is completions, the catalog, and this doc set. |
| Cancel | Cancel calls `cancel_safe`. It may not stop every long-running query. |
| Checkout | Before a pooled connection is handed out, `select 1` runs with a 5 second socket timeout. A half-open socket fails that probe instead of waiting out TCP keepalives. |
| Results grid | Several QuestDB types share one PGWire OID. OID 1043 is labeled `s` for STRING, SYMBOL, and GEOHASH in the grid. Catalog labels from `table_columns()` are the precise names. |
| SHOW PARTITIONS | The sidebar inserts `SHOW PARTITIONS` text. Confirm that statement on the server version you run. |

An omitted password is `quest`, matching the 0.3.x release. That default is for local development.
