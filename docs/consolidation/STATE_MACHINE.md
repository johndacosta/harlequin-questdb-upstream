# Consolidation state machine

This file is the PR workflow only. It is not runtime state inside the adapter.

Repository: `rhuygen/harlequin-questdb`. Package: `harlequin-questdb`.

## Rule

An item may be marked `done` only when every id in `requires` is already `done`. A `pending` or `in_progress` item does not satisfy a dependency.

Allowed states: `pending`, `in_progress`, `done`.

## Items

| id | requires | state |
| --- | --- | --- |
| pr-01-contract | | done |
| pr-02-pool | pr-01-contract | done |
| pr-03-catalog | pr-01-contract, pr-02-pool | done |
| pr-04-docs-lock | pr-01-contract, pr-02-pool, pr-03-catalog | done |
| pr-05-reviews | pr-04-docs-lock | done |
| pr-06-pull-request | pr-05-reviews | done |

## Transitions

1. `pr-01-contract` has no dependencies. It may move to `done` on its own.
2. `pr-02-pool` waits for `pr-01-contract`.
3. `pr-03-catalog` waits for `pr-01-contract` and `pr-02-pool`.
4. `pr-04-docs-lock` waits for `pr-01-contract`, `pr-02-pool`, and `pr-03-catalog`.
5. `pr-05-reviews` waits for `pr-04-docs-lock`.
6. `pr-06-pull-request` waits for `pr-05-reviews`. It is `done` only when a pull request is open against `rhuygen/harlequin-questdb` and the diff contains this integration. That pull request is https://github.com/rhuygen/harlequin-questdb/pull/4.
