# Contributing to notesCapture

## Workflow

Use a PR-first workflow for meaningful changes.

Expected flow:
1. create a branch
2. add or update tests first when behavior changes
3. make the smallest safe change
4. run:
   ```bash
   ./tests/run_all.sh
   ```
5. open a pull request
6. wait for GitHub Actions `PR checks`
7. merge only after checks pass

## What to test

Every PR should preserve or intentionally update tests around:
- raw ingress handling
- canonical append behavior
- `notes.txt` materialization
- producer-specific behavior that can be tested safely

## Current automated coverage

`./tests/run_all.sh` verifies:
- bash syntax for setup scripts
- `materialize_notes.sh`
- `process_inbox.sh`
- `quicknote.swift` typechecking when `swiftc` is available

## Merge policy

Recommended GitHub settings:
- protect `main`
- require pull requests
- require the `PR checks` status check

Workflow file:
- `.github/workflows/pr-checks.yml`
