# Ordered PR list

Distribution: repository `rhuygen/harlequin-questdb`, package `harlequin-questdb`.

This list is the sequence for dropping a second distribution and landing the QuestDB adapter work only in that repository and package. One GitHub pull request carries the sequence. The items below are the review order, not separate packages.

| Order | Id | PRD | Requires |
| --- | --- | --- | --- |
| 1 | pr-01-contract | [prd/01-contract.md](prd/01-contract.md) | none |
| 2 | pr-02-pool | [prd/02-pool.md](prd/02-pool.md) | pr-01-contract |
| 3 | pr-03-catalog | [prd/03-catalog.md](prd/03-catalog.md) | pr-01-contract, pr-02-pool |
| 4 | pr-04-docs-lock | [prd/04-docs-lock.md](prd/04-docs-lock.md) | pr-01-contract, pr-02-pool, pr-03-catalog |
| 5 | pr-05-reviews | [prd/05-reviews.md](prd/05-reviews.md) | pr-04-docs-lock |
| 6 | pr-06-pull-request | [prd/06-pull-request.md](prd/06-pull-request.md) | pr-05-reviews |

States and the done-transition rule live in [STATE_MACHINE.md](STATE_MACHINE.md).
