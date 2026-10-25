# PRD: Docs, changelog, license, lock

Id: `pr-04-docs-lock`. Requires: `pr-01-contract`, `pr-02-pool`, `pr-03-catalog`.

## Outcome

README, `docs/USER_GUIDE.md`, and `docs/KNOWN_LIMITATIONS.md` say that an omitted password is `quest`. They document `--username`, the `user` constructor alias, and that a connection string wins over default host, user, password, dbname, and sslmode.

`CHANGELOG.md` keeps 0.1.0 through 0.3.3, including the 0.3.0 idle-reconnect note, and adds 0.4.0.

`LICENSE` keeps `Copyright (c) 2023 Rik Huygen` and adds John DaCosta. It does not replace Rik Huygen with Ted Conbeer.

`uv.lock` editable package version matches `pyproject.toml` (`0.4.0`). Regeneration keeps existing environment markers, including `exceptiongroup` 1.3.1's `typing-extensions` marker `python_full_version < '3.13'`.

`docker-compose.yml` is a dev-only QuestDB 8.2.2 file bound to `127.0.0.1:8812`. It is not a second distribution. The published host default remains `localhost`; the guide tells the reader to pass `--host 127.0.0.1` when the compose port is bound only on that address.

Staging `dist/` wheels, `__pycache__`, `EXTRACT.md`, `PUBLISH.md`, and `RELEASE_v0.1.0.md` are not added to this repository.

## 0.3.x behavior that must survive

- Install and upgrade instructions still target package `harlequin-questdb`.
- The documented no-flag command still matches the `quest` / `admin` / `localhost` / `8812` contract.
- Changelog sections 0.1.0 through 0.3.3 stay present, including 0.3.0 reconnect.

## How to test

Read `README.md`, `docs/USER_GUIDE.md`, `CHANGELOG.md`, and `LICENSE` against the contract. After `uv lock`, assert the editable version equals `pyproject.toml` and the `exceptiongroup` marker line is still present. `tests/test_contract.py` covers the runtime side of the sentences the docs make.

## Out of scope

Uploading to PyPI. Rewriting historical changelog entries. Deleting the local staging checkout.
