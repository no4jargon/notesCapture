# notesCapture

Lightweight capture on macOS now, with a path toward a larger append-only personal event system.

## What it is

`notesCapture` is a fast capture tool, not a full notes app.

Current behavior:
- `Option + Space` opens a quick note window on Mac
- `Command + Enter` saves
- notes are merged into a generated `notes.txt`
- mobile capture can join the same timeline through Dropbox

Key design choices:
- `notes.txt` is a generated view
- producers are append-only capture clients
- canonical storage is currently per-note files in `entries/`
- the long-term target is a journal-based architecture

## Current architecture

Working layers:
1. capture
   - Mac hotkey popup via `ingress/local/`
   - iPhone Shortcut via `ingress/dropbox/`
2. canonical storage
   - one immutable note file per capture in `entries/`
3. generated view
   - `notes.txt` rebuilt from `entries/`

Flow:
- Mac helper writes a raw capture file into `ingress/local/`
- mobile clients write plain text files into `ingress/dropbox/`
- importer commits ingress files into `entries/`
- `notes.txt` is regenerated automatically

## Setup

```bash
git clone git@github.com:no4jargon/notesCapture.git
cd notesCapture
./setup.sh
```

Setup will:
- install Hammerspoon if needed
- build the Swift helper
- choose a data directory
  - Dropbox if available
  - otherwise repo-local `data/`
- configure Hammerspoon
- start the importer flow
- generate `mobile/ios/SHORTCUT_SETUP.txt`

## Data layout

Dropbox-backed example:

```txt
<Dropbox>/notesCapture-data/
├── entries/
├── ingress/
│   ├── dropbox/
│   └── local/
└── notes.txt
```

Folder meaning:
- `ingress/` → producer staging area
- `entries/` → current canonical immutable note files
- `notes.txt` → generated human-readable timeline

## Usage

### Mac
- press `Option + Space`
- type your note
- press `Command + Enter`

### iPhone / iPad
After setup, open:

```txt
mobile/ios/SHORTCUT_SETUP.txt
```

That file tells you:
- the Dropbox ingress path
- the Shortcut steps
- where merged notes appear

Basic model:
- iPhone Shortcut asks for text or dictation
- it saves a plain `.txt` file into the Dropbox `ingress/dropbox/`
- your Mac automatically imports it into `entries/`
- `notes.txt` updates with the same timeline as laptop notes

## Why Dropbox first

Dropbox is currently the simplest shared transport for:
- Mac + iPhone
- future Windows / Android clients
- eventual HTTP or API-based ingestion

Dropbox is a transport choice, not the long-term architecture.

## Transitional producer contract

Current working contract:

### Mac capture contract
The Mac helper drops one raw plain text file per note into:

```txt
ingress/local/
```

### Mobile contract
A client should drop one plain text file per note into:

```txt
ingress/dropbox/
```

## Future direction

The long-term producer contract is different:
- producers emit `capture-event-v1` payloads
- all producers write raw capture requests into `ingress/`
- producers do not know about Dropbox, `entries/`, or `notes.txt`

See:
- `docs/architecture-v2.md`
- `docs/capture-event-v1.md`

## Development

Before opening or merging a PR:

```bash
./tests/run_all.sh
```

See also:
- `CONTRIBUTING.md`
- `.github/workflows/pr-checks.yml`

## Project structure

```txt
notesCapture/
├── .github/
├── config/
├── docs/
├── hammerspoon/
├── mobile/
├── scripts/
├── tests/
├── quicknote.swift
├── setup.sh
└── README.md
```

Generated locally but not committed:
- `bin/notesCapture`
- `config/config.env`
- `config/generated.lua`
- `data/`
- `mobile/ios/SHORTCUT_SETUP.txt`

## Requirements

Current supported setup:
- macOS
- `swiftc`
- Hammerspoon
- Dropbox optional, recommended for phone capture

If `swiftc` is missing:

```bash
xcode-select --install
```

## License

MIT
