# PRD: 0.4.0 package contract

Id: `pr-01-contract`. Requires: none.

## Outcome

Package `harlequin-questdb` in repository `rhuygen/harlequin-questdb` is version `0.4.0`. The entry point stays `questdb = harlequin_questdb:QuestDBAdapter` and loads the class named `QuestDBAdapter`. The repository URL stays `https://github.com/rhuygen/harlequin-questdb`.

Dependencies are `harlequin>=2.5,<3` and `psycopg` with both the `binary` and `pool` extras, bounded `>=3.2.0,<4`.

Pure connection decisions live in `resolve_connect_config` and are what `QuestDBAdapter` stores and later passes to the pool:

- Omitted password resolves to `quest`. The CLI option default is also `quest`.
- The CLI option remains `username` (`-u`, default `admin`). The constructor accepts `username` and a `user` alias. When both are set, `user` wins.
- Host default is `localhost` on the option and at runtime. Port default is `8812`. Database default is `qdb`. When no connection string is given, `sslmode` defaults to `disable`.
- A non-empty connection string is the source for host, port, user, password, dbname, and sslmode. Defaults for those keys are not copied into pool kwargs, so they cannot override the string. psycopg treats keyword parameters as overrides, which is why the defaults stay out of kwargs.
- `connection_id` built from options includes the user and omits the password. A password present in a connection string is removed from the id.
- More than one connection string raises `HarlequinConnectionError` before a socket opens.
- Statement execution passes `prepare=False`.

## 0.3.x behavior that must survive

- `harlequin -a questdb` with no password still uses `quest`.
- `--username` / the `username` keyword still selects the user.
- A positional connection string still supplies host, user, and password.
- Queries still use the simple query protocol (`prepare=False`), as in 0.3.3.
- `connection_id` still identifies the user for catalog and history caching, and it does not embed the password.
- Help text and runtime still default the host to `localhost`.

## How to test

Default `pytest` (marker `live` excluded) constructs `QuestDBAdapter` and calls `resolve_connect_config` / `resolved_params` / `connection_id` with no server. It loads entry point group `harlequin.adapter`, name `questdb`, and asserts the loaded class is `QuestDBAdapter`. A fake cursor records `prepare=False` from the real `execute` method. `tests/test_contract.py` is the suite.

## Out of scope

Publishing to PyPI. A second package name. Renaming the entry point. ILP ingestion, a custom lexer, or Postgres parity.
