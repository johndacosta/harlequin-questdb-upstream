# PRD: Adversarial, security, performance, and best-practices reviews

Id: `pr-05-reviews`. Requires: `pr-04-docs-lock`.

## Outcome

Four distinct review passes read the integration: adversarial, security, performance, and best practices. Each blocking defect in this integration is fixed in the tree. A finding that is not a defect in this integration is listed under Out of scope in this PRD with a reason, after the reviews have been written.

The passes are recorded outside the package, one write-up each. They are not a second distribution.

## 0.3.x behavior that must survive

Review fixes must not drop the contract in `pr-01-contract`: entry point, `quest` password, `username`, connection-string precedence, `prepare=False`, connection id, host default `localhost`, retained changelog, and license names.

## How to test

Re-run the default pytest suite, ruff, and mypy after any blocking fix. The contract tests are the regression net.

## Out of scope

The four passes were adversarial, security, performance, and best practices. Blocking findings from those passes were fixed in this tree before the pull request: connection-string redaction for URI userinfo, spaced `password =`, and libpq backslash escapes; retry only on a closed connection or a dead-session phrase; a `connect_timeout` inside a connection string bounds the pool wait; a missing `connect_timeout` is filled so libpq does not keep its long default dial; the checkout `select 1` uses a 5 second socket timeout (`CHECK_SOCKET_TIMEOUT`, covered by `test_check_restores_the_socket_timeout`). A failed connect used to return while pool workers were still blocked in `connect()`, because `close()` joins for 5 seconds and a dial can be longer. The pool now uses one worker and waits out that one dial before the error returns (`test_failed_connect_reaps_pool_workers`).

These review notes are not defects to fix in this integration:

- User queries still buffer the full simple-query result before `set_limit`. Harlequin's cursor API fetches, then the grid applies the limit. Changing that protocol is a different project.
- Opening one relation still runs one `table_columns()` query. The catalog is lazy on purpose. Prefetching every relation is out of scope.
- `connection_id` can still contain non-password libpq fields such as certificate paths. `password` and `sslpassword` are omitted. Stripping file paths is out of scope.
- A whitespace-only connection string is treated as omitted. That is the same as passing no string.
- PyPI upload, ILP ingestion, a custom lexer, Postgres parity, export, and edits to other repositories stay out of scope.
