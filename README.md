# partnerOS

This repo is now organized with the active capture app nested at:

```txt
partnerOS/eventsCapture/
```

## Current app

The working notes capture system lives in:

```txt
partnerOS/eventsCapture
```

Compatibility wrappers remain at the repo root for:
- `./setup.sh`
- `./bin/notesCapture`
- `./scripts/process_inbox.sh`
- `./scripts/materialize_notes.sh`
- `./scripts/commit_ingress.py`
- `./scripts/backfill_entries_to_journal.py`
- `./scripts/repartition_journal.py`
- `./tests/run_all.sh`
- `./hammerspoon/init.lua`

So existing local paths and Dropbox-backed flows keep working while the codebase lives under the new nested layout.

## Runtime data

The Dropbox-backed data directory is unchanged:

```txt
/Users/anujshah/Library/CloudStorage/Dropbox/notesCapture-data
```

That means current capture/import/materialization flows continue to operate against the same live data.

## eventsAgents setup

The new analysis layer lives at:

```txt
partnerOS/eventsAgents/
```

### Local environment setup for OpenAI-backed analysis

The repo now includes a local-only environment pattern for the analyst layer:
- `.env.local` stores local secrets like `OPENAI_API_KEY`
- `.envrc` loads `.env.local` and exports those variables into the shell
- `.env.local` is gitignored

If you use `direnv`, run:

```bash
direnv allow
```

Then the following variables become available automatically inside the repo:
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

If you do not use `direnv`, you can still load them manually:

```bash
source .envrc
```

### Running the time-use analyst

Example commands:

```bash
PYTHONPATH=partnerOS/eventsAgents/src \
python3 -m events_agents.cli \
  --state-dir partnerOS/eventsAgents/state \
  time-use build \
  --data-dir /Users/anujshah/Library/CloudStorage/Dropbox/notesCapture-data \
  --week 2026-03-23

PYTHONPATH=partnerOS/eventsAgents/src \
python3 -m events_agents.cli \
  --state-dir partnerOS/eventsAgents/state \
  time-use report \
  --data-dir /Users/anujshah/Library/CloudStorage/Dropbox/notesCapture-data \
  --week 2026-03-23

PYTHONPATH=partnerOS/eventsAgents/src \
python3 -m events_agents.cli \
  --state-dir partnerOS/eventsAgents/state \
  time-use ask \
  --data-dir /Users/anujshah/Library/CloudStorage/Dropbox/notesCapture-data \
  --week 2026-03-23 \
  "Where did my time go last week?"
```

## Main project docs

See:
- `partnerOS/eventsCapture/README.md`
- `partnerOS/eventsCapture/docs/architecture-v2.md`
- `partnerOS/eventsCapture/docs/capture-event-v1.md`
- `partnerOS/eventsAgents/README.md`
- `partnerOS/eventsAgents/docs/code-tour.md`
