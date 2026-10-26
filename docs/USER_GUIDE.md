# QuestDB adapter — user guide

Harlequin connects to [QuestDB](https://questdb.io/) over PGWire on port **8812**. This package is `harlequin-questdb` from repository `rhuygen/harlequin-questdb`.

## Install and connect

```bash
uv tool install harlequin --with harlequin-questdb
harlequin -a questdb
```

That command uses host `localhost`, port `8812`, user `admin`, and password `quest`. An omitted password is `quest`. Pass `--password` when the server password is different.

```bash
harlequin -a questdb \
  --host 127.0.0.1 \
  --port 8812 \
  --username admin \
  --password quest \
  --dbname qdb \
  --sslmode disable
```

Or pass one libpq connection string. The string's host, user, and password are the ones used. Defaults are not written over them. A `connect_timeout` in the string is also how long the adapter waits for a pooled connection:

```bash
harlequin -a questdb \
  "host=127.0.0.1 port=8812 user=admin password=secret dbname=qdb"
```

The CLI user flag is `--username`. Code that constructs `QuestDBAdapter` may pass `username` or `user`. When both are set, `user` wins.

## Local server

`docker-compose.yml` pins `questdb/questdb:8.2.2` and publishes `127.0.0.1:8812`. Those credentials are the development defaults (`admin` / `quest`), not production guidance.

```bash
docker compose up -d
harlequin -a questdb --host 127.0.0.1
```

The published host default remains `localhost`. Pass `--host 127.0.0.1` when that compose file is bound only on IPv4 localhost.

## Catalog labels

| Label | Meaning |
| --- | --- |
| `t·DAY` | Table partitioned by `DAY` |
| `mv·MONTH` | Materialized view partitioned by `MONTH` |
| `ts★` | Designated timestamp column |

The sidebar menu can preview rows, insert column names, and open `SHOW COLUMNS` or `SHOW PARTITIONS` in a buffer.

Short type labels that shipped in 0.3.x are unchanged. `INT` is still `##`, `DATE` is still `dt`, and wire OID 23 is still `##`.

## Time-series examples

```sql
SELECT ts, sensor, count() AS n
FROM readings
SAMPLE BY 1h;
```

```sql
SELECT s.ts, s.sensor, e.event
FROM readings s
ASOF JOIN events e ON (id);
```

```sql
SELECT *
FROM readings
LATEST ON ts PARTITION BY sensor;
```

## PGWire limits

QuestDB over PGWire is not full PostgreSQL. `dbname` is accepted by libpq and ignored by QuestDB. SSL is usually off until the server enables it. The editor completions include QuestDB clauses such as `SAMPLE BY` and `ASOF JOIN`.

ILP ingestion is outside this adapter. Use QuestDB's ILP clients for high-throughput writes.
