# Merge proposal: `harlequin-questdb` consolidation

| Field | Value |
|-------|-------|
| **Status** | Draft — seeking alignment before merge |
| **Authors** | [John DaCosta](https://github.com/johndacosta) (proposal), [Rik Huygen](https://github.com/rhuygen) (canonical maintainer) |
| **Target repo** | [`rhuygen/harlequin-questdb`](https://github.com/rhuygen/harlequin-questdb) |
| **Draft implementation** | [`johndacosta/harlequin-questdb`](https://github.com/johndacosta/harlequin-questdb) branch [`consolidate/enhanced-adapter-v0.4.0`](https://github.com/johndacosta/harlequin-questdb/tree/consolidate/enhanced-adapter-v0.4.0) |
| **Proposed version** | `0.4.0` (draft tagged `0.4.0-rc1` on the branch above) |
| **Tracking** | [rhuygen/harlequin-questdb#3](https://github.com/rhuygen/harlequin-questdb/issues/3) |

## Executive summary

Rik published the first community `harlequin-questdb` package on PyPI and opened the correct Harlequin integration ([`tconbeer/harlequin` #975](https://github.com/tconbeer/harlequin/pull/975)) and docs PR ([`tconbeer/harlequin-web` #146](https://github.com/tconbeer/harlequin-web/pull/146)).

John developed a deeper QuestDB adapter in parallel on a Harlequin fork, extracted it to a standalone package, and opened a duplicate docs PR ([#147](https://github.com/tconbeer/harlequin-web/pull/147)).

**This document proposes:**

1. Keep **`rhuygen/harlequin-questdb`** and the PyPI distribution name as the single canonical project.
2. Merge John's enhancements into that repo via PR (backward-compatible with 0.3.x).
3. Release **0.4.0** on PyPI, refresh #975's lockfile, and land **one** harlequin-web docs page.

John is **not** proposing a competing PyPI package or a second `harlequin[questdb]` extra PR.

## Problem statement

Without consolidation we have:

- Two GitHub repos (`rhuygen/harlequin-questdb`, `johndacosta/harlequin-questdb`)
- Two harlequin-web docs PRs ([#146](https://github.com/tconbeer/harlequin-web/pull/146), [#147](https://github.com/tconbeer/harlequin-web/pull/147)) — both blocked on Vercel fork authorization, not content review
- Harlequin maintainer feedback on #975 waiting on docs + verifiable PyPI metadata ([comment](https://github.com/tconbeer/harlequin/pull/975#issuecomment-4847476709))

## Goals

- [ ] One canonical repo and PyPI package
- [ ] One harlequin optional-extra PR (#975, refreshed)
- [ ] One harlequin.sh adapter docs page
- [ ] Backward compatibility for 0.3.x users (`QuestDBAdapter`, default password, `username` kwarg)
- [ ] Clear contributor credits on PyPI, GitHub, and harlequin.sh

## Non-goals (v1 consolidation)

- Merging adapter code into Harlequin core (adapter guide requires a separate package)
- ILP ingestion, custom QuestDB lexer, or full Postgres-adapter parity
- Resolving Vercel fork-auth without `tconbeer/harlequin-web` maintainer help

## Proposed solution

### Architecture (unchanged from adapter guide)

```text
harlequin-questdb (PyPI)  →  harlequin.adapter entry point "questdb"
harlequin[questdb] extra  →  depends on harlequin-questdb (harlequin #975)
harlequin.sh docs         →  community adapter page (harlequin-web #146 + updates)
```

### What the draft branch adds over 0.3.3

| Area | 0.3.3 (current PyPI) | 0.4.0 draft |
|------|----------------------|-------------|
| Connection | Single `psycopg.connect` | `psycopg_pool` + TCP keepalive + reconnect |
| Catalog | Flat table list | Interactive `db → schema → relation → column` tree |
| Metadata hints | — | Partition labels (`t·DAY`), designated timestamp (`ts★`) |
| Completions | — | Dialect tokens + bounded `functions()` |
| Cancel | — | `IMPLEMENTS_CANCEL` |
| SQL safety | Unescaped `table_columns()` args | Escaped string literals |
| Docs | README | README + `USER_GUIDE.md` + `KNOWN_LIMITATIONS.md` |
| Tests | Template (live DB) | Offline pin fixtures + contract tests |
| Dev stack | `docker-compose.yml` | Pinned `questdb/questdb:8.2.2` |

### Backward compatibility (implemented in draft)

| 0.3.x surface | 0.4.0 behavior |
|---------------|----------------|
| Entry point `harlequin_questdb:QuestDBAdapter` | `QuestDBAdapter` alias in `__init__.py` |
| CLI kwarg `username` | Accepted; maps to `user` |
| Default password `quest` | `pool_kwargs.setdefault("password", "quest")` |
| `harlequin -a questdb` with local defaults | Unchanged |

## File-by-file merge map

| Path | Action |
|------|--------|
| `src/harlequin_questdb/adapter.py` | Replace with draft; keep compat shims |
| `src/harlequin_questdb/catalog.py` | **Add** (new) |
| `src/harlequin_questdb/completions.py` | **Add** (new) |
| `src/harlequin_questdb/interactions.py` | **Add** (new) |
| `src/harlequin_questdb/cli_options.py` | Merge — superset of both option sets |
| `src/harlequin_questdb/__init__.py` | Export both naming conventions |
| `tests/test_adapter.py` | Expand with offline tests + `tests/data/pin_meta.json` |
| `docs/USER_GUIDE.md` | **Add** |
| `docs/KNOWN_LIMITATIONS.md` | **Add** |
| `docker-compose.yml` | **Add** |
| `CHANGELOG.md` | Merge histories |
| `README.md` | Merge install/upgrade sections from both |
| `pyproject.toml` | `psycopg[pool]`, `harlequin>=2.5,<3`; keep entry point path |

## Upstream PR plan

| PR | Owner | Next step |
|----|-------|-----------|
| [harlequin #975](https://github.com/tconbeer/harlequin/pull/975) | Rik | Rebase; `uv lock` against `harlequin-questdb==0.4.0`; re-request review |
| [harlequin-web #146](https://github.com/tconbeer/harlequin-web/pull/146) | Rik | Add `repoMap` entry, USER_GUIDE links, dual install instructions |
| [harlequin-web #147](https://github.com/tconbeer/harlequin-web/pull/147) | John | **Close** — superseded by unified docs effort |

Tom's #975 blocker: docs on harlequin.sh + verifiable PyPI source. Rik addressed PyPI URLs in 0.3.3; docs remain the gating item.

## Release checklist (post-merge)

1. Merge draft into `rhuygen/harlequin-questdb` `main`
2. Tag `v0.4.0` and publish to PyPI
3. Refresh harlequin #975 lockfile
4. Update harlequin-web #146 (or maintainer cherry-pick onto `tconbeer/harlequin-web`)
5. John removes in-tree adapter from Harlequin fork (`feature/questdb-support`)

## How to review the draft

```bash
git clone https://github.com/johndacosta/harlequin-questdb.git
cd harlequin-questdb
git checkout consolidate/enhanced-adapter-v0.4.0
uv sync --group dev
uv run pytest tests/test_adapter.py -v
uv build
```

Optional smoke test (requires Docker):

```bash
docker compose up -d
harlequin -a questdb --host 127.0.0.1 --port 8812 --user admin --password quest --dbname qdb
```

## How to respond

Please comment on **[rhuygen/harlequin-questdb#3](https://github.com/rhuygen/harlequin-questdb/issues/3)** or reply on [harlequin #975](https://github.com/tconbeer/harlequin/pull/975).

**Open questions for Rik:**

1. Add John as co-maintainer on repo + PyPI?
2. One 0.4.0 PR vs staged PRs (catalog → pool → completions)?
3. Prefer `QuestDB*` or `HarlequinQuestDb*` class names going forward?
4. Who asks Tom to cherry-pick harlequin-web docs (Vercel fork auth)?

## License

Both implementations are MIT. John acknowledges Harlequin's MIT license and does not claim exclusive ownership of the merged contribution.
