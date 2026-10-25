# harlequin-questdb

A [Harlequin](https://harlequin.sh) adapter for [QuestDB](https://questdb.io), connecting via QuestDB's PostgreSQL wire protocol.

The package name is `harlequin-questdb`. The source repository is [rhuygen/harlequin-questdb](https://github.com/rhuygen/harlequin-questdb).

## Installation

```bash
uv tool install harlequin --with harlequin-questdb
```

Or with pip:

```bash
pip install harlequin-questdb
```

## Upgrading

To upgrade Harlequin, the adapter, or both, run:

```bash
uv tool upgrade harlequin --with harlequin-questdb
```

This upgrades `harlequin` to the latest compatible version and refreshes `harlequin-questdb` at the same time. Run the same command regardless of which package was bumped. This release requires Harlequin 2.5 or newer.

## Usage

Connect to a local QuestDB instance using the defaults (host `localhost`, port `8812`, user `admin`, password `quest`):

```bash
harlequin -a questdb
```

An omitted password is `quest`. Pass `--password` when the server uses a different one.

```bash
harlequin -a questdb --host myserver --port 8812 --username myuser --password mypassword
```

A libpq connection string supplies host, user, and password on its own. Defaults for those fields are not applied on top of the string:

```bash
harlequin -a questdb "host=myserver port=8812 user=myuser password=mypassword dbname=qdb"
```

The constructor also accepts `user` as an alias of `username`. The CLI flag remains `--username` (`-u`).

## Connection options

| Option | Short | Default | Description |
| --- | --- | --- | --- |
| `--host` | `-h` | `localhost` | QuestDB host name or IP address |
| `--port` | `-p` | `8812` | PostgreSQL wire protocol port |
| `--username` | `-u` | `admin` | QuestDB username |
| `--password` | | `quest` | QuestDB password. Omitted values use `quest`. |
| `--dbname` | `-d` | `qdb` | Libpq database field. QuestDB ignores logical database names. |
| `--connect-timeout` | | | Seconds before connect fails |
| `--sslmode` | | `disable` | PGWire SSL mode when no connection string is given |

`docker-compose.yml` publishes QuestDB 8.2.2 on `127.0.0.1:8812` for local development. If `localhost` resolves to an IPv6 address that the bind does not cover, pass `--host 127.0.0.1`.

## Catalog

The sidebar is a database → schema → relation → column tree. A table partitioned by day is labeled `t·DAY`. A designated timestamp column is labeled with a star, for example `ts★`.

Details, time-series examples, and limits are in [docs/USER_GUIDE.md](docs/USER_GUIDE.md) and [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md).
