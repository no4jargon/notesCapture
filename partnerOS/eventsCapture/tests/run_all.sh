#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "[tests] bash syntax"
bash -n setup.sh
bash -n scripts/materialize_notes.sh
bash -n scripts/process_inbox.sh

echo "[tests] python unit/integration tests"
python3 -m unittest discover -s tests -p 'test_*.py' -v
