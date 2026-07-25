# harlequin-questdb

Harlequin adapter for [QuestDB](https://questdb.io/) over **PGWire** (PostgreSQL wire protocol). Connect on port **8812** to the pinned image **`questdb/questdb:8.2.2`**.

## Install

```bash
pip install harlequin harlequin-questdb
```

### Release candidate (local wheel)

Before PyPI publish, install from a built wheel in a clean venv:

```bash
uv build
pip install ./dist/harlequin_questdb-*.whl
```

See [`PUBLISH.md`](PUBLISH.md) for the maintainer build and upload runbook.

## Connect

```bash
harlequin --adapter questdb \
  --host 127.0.0.1 \
  --port 8812 \
  --user admin \
  --password quest \
  --dbname qdb \
  --sslmode disable
```

Or pass a libpq connection string:

```bash
harlequin --adapter questdb \
  "host=127.0.0.1 port=8812 user=admin password=quest dbname=qdb sslmode=disable"
```

### Quickstart server

```bash
docker compose up -d
```

(`docker-compose.yml` in this package pins **`questdb/questdb:8.2.2`** on **8812**.)

## Authentication (development only)

> **Development only — not for production.** QuestDB's default `admin` / `quest` credentials are for local development on pin **8.2.2** only. Harlequin does **not** auto-supply a password; pass **`--password quest`** (or embed it in `CONN_STR`). Do not commit `.env` files or production secrets.

## Catalog sidebar hints

After creating tables, the Harlequin catalog tree uses QuestDB meta functions (`tables()`, `table_columns()`, `functions()`):

| Label | Meaning |
|-------|---------|
| **`t·DAY`** | Table partitioned by `DAY` |
| **`ts★`** | Designated timestamp column |

See [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) for smoke DDL and introspection SQL.

## Time-series quickstart

```sql
SELECT ts, sensor, count() AS n
FROM _harlequin_smoke
SAMPLE BY 1h;

SELECT s.ts, s.sensor, e.event
FROM _harlequin_smoke s
ASOF JOIN _harlequin_smoke_events e ON (id);

SELECT *
FROM _harlequin_smoke
LATEST ON ts PARTITION BY sensor;
```

Full recipes and seed data: [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md).

## Known limitations

Views, indexes, export/copy, multi-version pin, lexer, cancel behavior, and PGWire grid OID notes are documented in [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md).

## More documentation

- [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) — install, auth, PGWire limits, catalog hints, time-series recipes
- [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) — v1 gaps and honest stubs
- [`EXTRACT.md`](EXTRACT.md) — publishing this tree to a community GitHub repo
- [`PUBLISH.md`](PUBLISH.md) — PyPI build, RC wheel install, secrets policy
