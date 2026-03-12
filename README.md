# notesCapture

A lightweight macOS quick-capture note tool triggered by `Option + Space`.

It uses:
- **Hammerspoon** for the global hotkey
- a tiny **Swift/AppKit helper** for the popup note window

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
