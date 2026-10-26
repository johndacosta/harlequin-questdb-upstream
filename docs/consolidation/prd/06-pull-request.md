# PRD: Open the consolidation pull request

Id: `pr-06-pull-request`. Requires: `pr-05-reviews`.

## Outcome

One open pull request targets repository `rhuygen/harlequin-questdb`. The diff contains this integration: version `0.4.0` of package `harlequin-questdb`, the contract, the pool, the catalog, the docs, and the lock. The PR text points at `docs/consolidation/PR_LIST.md` and names only that repository and package as the distribution.

A fork-based pull request is the right shape when the publisher account does not have direct push rights. Merging unrelated git histories is not part of this item.

## 0.3.x behavior that must survive

The PR branch is the tree that passes the contract tests. Opening the PR does not retarget the package name, the entry point, or the repository URL.

## How to test

`gh pr view` (or `gh pr create` output) shows an open pull request whose base repository is `rhuygen/harlequin-questdb` and whose head contains the integration commits. Capture that output. If `gh` cannot create the PR, the attempt log is the evidence and this item stays unmet.

## Out of scope

Merging the pull request. Publishing the package. Closing coordination issues in other repositories. Force-pushing.
