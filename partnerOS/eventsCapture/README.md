# eventsCapture

`eventsCapture` is the capture app nested inside the broader `partnerOS` repository layout.

Repo location:

```txt
partnerOS/eventsCapture/
```

## What it is

A fast capture tool on macOS with a journal-first storage model.

Current behavior:
- `Option + Space` opens a quick note window on Mac
- `Command + Enter` saves
- notes are committed into a canonical journal
- `views/notes.txt` is materialized from the journal
- mobile capture can join the same timeline through Dropbox

Key design choices:
- `views/notes.txt` is a generated view
- producers are append-only capture clients
- canonical storage is journal-based
- `entries/` exists only as an optional historical migration source

## Current architecture

Working layers:
1. capture
   - Mac hotkey popup via `ingress/local/`
   - iPhone Shortcut via `ingress/dropbox/`
2. canonical storage
   - committed events appended to `journal/YYYY/MM/DD.ndjson`
3. generated views
   - `views/notes.txt` materialized from `journal/`
4. optional migration input
   - `entries/` can be backfilled once into `journal/`, then removed

Flow:
- Mac helper writes a raw capture file into `ingress/local/`
- mobile clients write plain text files into `ingress/dropbox/`
- the committer validates and appends canonical events into `journal/`
- the materializer reads `journal/` and regenerates `views/notes.txt`

## Setup

From the repo root:

```bash
git clone git@github.com:no4jargon/notesCapture.git
cd notesCapture
./setup.sh
```

The repo-root `./setup.sh` wrapper delegates to:

```txt
partnerOS/eventsCapture/setup.sh
```

## Data layout

Dropbox-backed example:

```txt
<Dropbox>/notesCapture-data/
├── ingress/
│   ├── dropbox/
│   └── local/
├── journal/
├── rejects/
├── state/
└── views/
```

Folder meaning:
- `ingress/` → producer staging area
- `journal/` → canonical committed event log
- `entries/` → optional historical migration source only
- `rejects/` → invalid payload quarantine
- `state/` → importer state such as dedupe markers
- `views/` → generated read models including `views/notes.txt`

## Usage

### Mac
- press `Option + Space`
- type your note
- press `Command + Enter`

### iPhone / iPad
After setup, open:

```txt
partnerOS/eventsCapture/mobile/ios/SHORTCUT_SETUP.txt
```

Basic model:
- iPhone Shortcut asks for text or dictation
- it saves a plain `.txt` file into the Dropbox `ingress/dropbox/`
- your Mac automatically commits it into `journal/`
- `views/notes.txt` is regenerated from the journal

## Future direction

The long-term producer contract is different:
- producers emit `capture-event-v1` payloads
- all producers write raw capture requests into `ingress/`
- producers do not know about Dropbox, `entries/`, or generated views

See:
- `docs/architecture-v2.md`
- `docs/capture-event-v1.md`

## Development

From the repo root:

```bash
./tests/run_all.sh
```

Or directly inside the nested app:

```bash
cd partnerOS/eventsCapture
./tests/run_all.sh
```

## Project structure

```txt
notesCapture/
├── .github/
├── partnerOS/
│   └── eventsCapture/
│       ├── config/
│       ├── docs/
│       ├── hammerspoon/
│       ├── mobile/
│       ├── scripts/
│       ├── tests/
│       ├── quicknote.swift
│       ├── setup.sh
│       └── README.md
├── bin/                  # compatibility wrapper
├── hammerspoon/          # compatibility wrapper
├── scripts/              # compatibility wrappers
├── tests/                # compatibility wrapper
└── setup.sh              # compatibility wrapper
```
