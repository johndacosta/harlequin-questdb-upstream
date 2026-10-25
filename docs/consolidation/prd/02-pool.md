# PRD: Pool, keepalive, reconnect, cancel

Id: `pr-02-pool`. Requires: `pr-01-contract`.

## Outcome

`QuestDBConnection` uses a `psycopg_pool.ConnectionPool` (`min_size=1`, `max_size=5`, `num_workers=1`) with TCP keepalive defaults (`keepalives`, `keepalives_idle=30`, `keepalives_interval=10`, `keepalives_count=6`) only for keys the connection string does not already set. A check callback runs `select 1` before a pooled connection is handed out. The libpq socket is an integer file descriptor; the probe sets `TCP_USER_TIMEOUT` to 5 seconds on that descriptor and does not call `gettimeout()`. `autocommit` is on.

A failed open closes the pool with a timeout that covers one in-flight libpq dial. That dial is the keyword `connect_timeout` when set, otherwise the connection string's `connect_timeout`, and never below libpq's 2 second floor. The pool's own wait may be shorter. One worker keeps that join to a single dial.

Reconnect expands the 0.3.0 idle retry. Before a query, a closed main connection is replaced. `execute` reconnects once and retries when the connection object is closed, when the socket raises `BrokenPipeError` or `ConnectionResetError`, or when the error text contains a dead-session phrase such as `server closed the connection` or `connection lost`. A message that only happens to contain the separate words `connection` and `closed` is not retried, so a failed statement is not run twice. The 0.3.0 changelog entry stays; the pool is an expansion of that retry, not the first time reconnect existed.

`QuestDBAdapter.IMPLEMENTS_CANCEL` is true. `cancel` calls `cancel_safe` on the main connection. Connection errors shown to the user redact `password=<secret>` so a conninfo fragment in a driver message is not repeated in full.

## 0.3.x behavior that must survive

- A closed connection is still replaced and the query retried, which 0.3.0 did for `OperationalError` on a closed session.
- `prepare=False` still applies on the retried attempt.
- Keepalive defaults must not overwrite keepalive keys the user set in a connection string.
- Identity defaults must not appear in pool kwargs when a connection string was given (`pr-01-contract`).

## How to test

`tests/test_contract.py` builds `QuestDBConnection` with a fake pool, drives real `execute` and `cancel`, and asserts one retry, `prepare=False`, keepalive gap-fill, bounded pool construction (`num_workers=1`), and password redaction. `test_check_runs_select_1_on_libpq_socket_fd` calls the shipped `_check` with an integer libpq socket and asserts `select 1` runs and the descriptor stays open. `test_failed_connect_reaps_pool_workers` constructs the real pool against `127.0.0.1:1` and asserts its worker threads are gone when the error returns. No live QuestDB.

## Out of scope

Tuning pool size beyond the bounds above. An open-ended performance program. Changing the 0.3.0 changelog wording.
