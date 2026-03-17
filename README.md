# notesCapture

A lightweight, local-first capture tool for a much larger long-term personal system.

`notesCapture` is not meant to be just another notes app. It is a gateway module into a decade-scale, agentic personal architecture built around a simple idea:

- capture first
- structure later
- keep the raw record durable
- let agents build derived views on top

The long-term goal is to support:
- productivity
- reflection
- health pattern awareness
- relationship memory
- future writing and social expression

## Core philosophy

The system should survive tool churn, platform churn, and life changes.
So the architecture uses boring primitives:

- plain text files
- local folders
- append-only style capture
- derived views
- thin clients
- replaceable agents

The most important design choice is this:

- **`notes.txt` is a generated view**
- **canonical memory should be append-only**
- **producers should be write-only capture modules**

Today, canonical memory lives in immutable entry files.
The long-term target is a transport-agnostic append-only event journal.

That makes it easier to support Mac, iPhone, Dropbox, and later Windows, Android, web, browsers, watches, sensors, and agentic systems without making one shared text file the fragile write target.

## Current architecture

`notesCapture` currently has three working layers:

1. **capture clients**
   - Mac hotkey popup via `ingress/local/`
   - iPhone Shortcut via `ingress/dropbox/`
   - future Android / Windows clients can use the same transitional ingress contract

2. **current canonical storage**
   - one note = one immutable text file in `entries/`

3. **materialized view**
   - `notes.txt` is rebuilt from canonical entries

There is also a transitional raw-ingress layer:
- `ingress/local/` is the active Mac producer path
- `ingress/dropbox/` is the active mobile producer path
- the Mac importer converts raw submissions into canonical entries
- `notes.txt` is then regenerated automatically

## Target architecture

The long-term target is:

- many write-only producers
- transport-specific ingress adapters
- one append-only canonical journal
- generated views and indexes on top

That future design is documented here:
- `docs/architecture-v2.md`
- `docs/capture-event-v1.md`

## Features

- `Option + Space` opens a quick note window on Mac
- `Command + Enter` saves a note
- `Enter` inserts a new line
- `Command + Shift + 7` toggles bullet formatting
- `Esc` closes the window
- notes are merged into one timestamped `notes.txt`
- mobile notes can flow into the same timeline through Dropbox

## One-command setup after clone

Clone the repo, then run:

```bash
./setup.sh
```

That one command will:
- install Hammerspoon if needed
- compile the Mac helper
- choose a data directory
  - Dropbox if available
  - otherwise local repo data
- create the storage folders
- configure Hammerspoon
- install a background sync/import job
- start Hammerspoon
- generate iPhone Dropbox shortcut instructions

## Quick start

```bash
git clone git@github.com:no4jargon/notesCapture.git
cd notesCapture
./setup.sh
```

## Development workflow

This repo now follows a PR-first workflow.

Before opening or merging a PR, run:

```bash
./tests/run_all.sh
```

The same test suite runs in GitHub Actions on every PR.

See also:
- `CONTRIBUTING.md`
- `.github/workflows/pr-checks.yml`

## Data layout

By default, setup uses Dropbox if available:

```txt
<Dropbox>/notesCapture-data/
├── entries/
├── ingress/
│   ├── dropbox/
│   └── local/
├── legacy/
└── notes.txt
```

If Dropbox is not available, setup falls back to:

```txt
<repo>/data/
```

### What each folder means

- `entries/` → current canonical immutable note files
- `ingress/` → transport-specific staging area for append-only producers
- `notes.txt` → generated readable timeline
- `legacy/` → archived pre-entry notes if setup finds an older `notes.txt`

## Mac usage

After setup:

- press `Option + Space`
- type your note
- press `Command + Enter`

The Mac helper writes a canonical entry file and regenerates `notes.txt`.

## iPhone / iPad usage

This repo includes an Apple-friendly mobile path without needing a full iOS app.

After setup, open:

```txt
mobile/ios/SHORTCUT_SETUP.txt
```

If your chosen data directory lives in Dropbox, that generated file tells you:
- the exact Dropbox ingress folder to use
- how to create the Shortcut
- where merged notes will appear

If your chosen data directory is local-only, the generated file will tell you to rerun setup with a Dropbox-backed data directory for mobile sync.

Basic model:
- iPhone Shortcut asks for text or dictation
- it saves a plain `.txt` file into the Dropbox `ingress/dropbox/`
- your Mac automatically imports it into `entries/`
- `notes.txt` updates with the same timeline as laptop notes

## Why Dropbox first

Dropbox is a good starting point because it is:
- simple
- cross-device
- easy for iPhone shortcuts
- more OS-agnostic than iCloud

This keeps the architecture open for:
- Windows capture tools
- Android automation tools
- future HTTP/API ingestion

## Transitional cross-platform contract

The current working contract is intentionally tiny:

### Desktop direct-write contract
A client may write one plain text file per note into:

```txt
entries/YYYY/MM/DD/
```

### Mobile contract
A client should drop one plain text file per note into:

```txt
ingress/dropbox/
```

As long as a client can create a text file in the shared folder, it can participate in the current transitional system.

## Future producer contract

The long-term producer contract is different:
- producers emit `capture-event-v1` payloads
- producers append into ingress only
- producers do not know about Dropbox, `entries/`, or `notes.txt`

That contract is specified in:
- `docs/capture-event-v1.md`

## Example generated timeline

```txt
[2026-03-12 03:51:59]
A quick thought goes here

[2026-03-12 03:55:10]
- Another note
- Saved later
```

## Project structure

```txt
notesCapture/
├── .github/
├── config/
├── docs/
│   ├── architecture-v2.md
│   └── capture-event-v1.md
├── hammerspoon/
│   └── init.lua
├── mobile/
│   └── ios/
│       └── README.md
├── scripts/
│   ├── materialize_notes.sh
│   └── process_inbox.sh
├── tests/
│   ├── run_all.sh
│   └── test_notescapture.py
├── CONTRIBUTING.md
├── quicknote.swift
├── setup.sh
├── LICENSE
└── README.md
```

Generated locally but not committed:
- `bin/notesCapture`
- `config/config.env`
- `config/generated.lua`
- `data/`
- `mobile/ios/SHORTCUT_SETUP.txt`

## Setup options

Default:

```bash
./setup.sh
```

Force Dropbox if available:

```bash
./setup.sh --use-dropbox
```

Force local repo data:

```bash
./setup.sh --use-repo-data
```

Use a custom shared folder:

```bash
./setup.sh --data-dir "$HOME/Dropbox/notesCapture-data"
```

## Requirements

Current usable setup:
- macOS
- Swift compiler (`swiftc`)
- Hammerspoon
- Dropbox optional but recommended for phone capture

If `swiftc` is missing:

```bash
xcode-select --install
```

## Notes for future expansion

This structure is designed so future clients can be added without changing the core data model:
- Windows global hotkey capture
- Android Shortcut / Tasker capture
- web/API capture
- agentic processors for todos, summaries, people, and reflections

The slow durable layer remains the same:
- immutable entry files
- a generated timeline
- local user-owned data

## License

MIT
