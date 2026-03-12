# notesCapture

A lightweight macOS quick-capture note tool triggered by `Option + Space`.

It uses:
- **Hammerspoon** for the global hotkey
- a tiny **Swift/AppKit helper** for the popup note window

## Why this exists

This tool is not meant to be just another note app.
It is a **gateway module** toward a much larger, long-term, agentic personal system designed to help with:

- high productivity
- health and fitness
- conscious life reflection
- deeper friendships
- thoughtful digital presence

The core philosophy is simple:

- **capture first, structure later**
- keep one **append-only log** of raw thoughts
- let agents create **derived views** instead of editing the raw record
- use **boring, durable primitives** that can survive for a decade: plain text, local files, simple scripts, replaceable agents

The long-term idea is that a single stream of timestamped notes can become the memory layer for many future tools:

- task extraction
- weekly reflection
- learning summaries
- relationship memory
- social writing prompts
- health and behavior pattern detection

In that architecture, `notesCapture` is the simplest possible entry point: a low-friction way to get thoughts out of your head and into a durable log.

This project is inspired by ideas such as:

- capture-first personal knowledge systems
- evergreen notes and note gardens
- local-first tools
- event-sourced systems built around immutable logs
- long-horizon thinking about software that should remain useful as life changes

## Features

- `Option + Space` opens a small note window from anywhere
- `Command + Enter` saves the note
- notes are **appended** to `notes.txt` with a timestamp
- `Enter` inserts a new line
- `Command + Shift + 7` toggles bullet formatting
- `Esc` closes the window

## One-command setup after clone

Clone the repo, then run exactly one command:

```bash
./setup.sh
```

That setup script will:
- install **Hammerspoon** if Homebrew is available and Hammerspoon is not installed
- compile the Swift helper to `bin/hotkey-notes`
- create `notes.txt` if needed
- wire `~/.hammerspoon/init.lua` to this repo automatically
- register Hammerspoon to start at login
- launch or restart Hammerspoon

After setup, use:

```txt
Option + Space
```

If macOS prompts for permissions, allow Hammerspoon in:
- **Privacy & Security → Accessibility**
- **Privacy & Security → Input Monitoring**

## Quick start

```bash
git clone git@github.com:no4jargon/notesCapture.git
cd notesCapture
./setup.sh
```

## Save format

Each note is appended like this:

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
├── hammerspoon/
│   └── init.lua
├── quicknote.swift
├── setup.sh
├── LICENSE
└── README.md
```

Generated locally at runtime, but not tracked in git:
- `bin/hotkey-notes`
- `notes.txt`
- `.DS_Store`

## Notes location

Your notes are saved here:

```txt
<repo>/notes.txt
```

For example:

```txt
~/Desktop/Projects/notesCapture/notes.txt
```

## Rebuild manually

If you change the Swift helper and want to rebuild manually:

```bash
swiftc ./quicknote.swift -o ./bin/hotkey-notes
killall Hammerspoon || true
open -a Hammerspoon
```

## How it works

- `hammerspoon/init.lua` binds `Option + Space`
- Hammerspoon launches the compiled helper binary
- the Swift helper shows a floating note window
- saving appends a timestamped entry to `notes.txt` using append mode
- the Hammerspoon config resolves paths relative to the cloned repo, so it works outside `~/Desktop/Projects` too

## Requirements

- macOS
- Swift compiler (`swiftc`)
- Homebrew only if Hammerspoon is not already installed and you want setup to install it automatically

If `swiftc` is missing, install Xcode Command Line Tools and rerun:

```bash
xcode-select --install
```

## License

MIT
