# Contributing to notesCapture

## Development method

Use a PR-first workflow for all meaningful changes.

Expected flow:
1. create a branch
2. make the smallest safe change possible
3. add or update tests first when behavior is changing
4. run:
   ```bash
   ./tests/run_all.sh
   ```
5. open a pull request
6. wait for GitHub Actions `PR checks` to pass
7. only then merge

## What must be tested

Every PR should preserve or explicitly update tests around these steps:
- ingestion from raw inputs
- canonical append behavior
- materialization into `notes.txt`
- any producer-specific behavior that can be tested safely

## Current automated coverage

`./tests/run_all.sh` currently verifies:
- bash syntax for setup scripts
- `materialize_notes.sh`
- `process_inbox.sh`
- `quicknote.swift` typechecking when `swiftc` is available

## Merge policy

Recommended GitHub repository setting:
- protect `main`
- require pull requests before merging
- require the `PR checks` status check to pass

The workflow file is already included in:
- `.github/workflows/pr-checks.yml`

If branch protection is not yet enabled in GitHub settings, do that next so failing PRs cannot be merged.
